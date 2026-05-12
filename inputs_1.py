import threading
import sys
import time
from typing import Any, Dict, Optional, Set, cast

try:
    import msvcrt
except ImportError:
    msvcrt = None

from Phidget22.Devices.DigitalInput import DigitalInput  # type: ignore[import-untyped]

from actions import ActionDispatcher
from config import config
from debug import StatusWriter, logger


class PhidgetController:
    def __init__(self, backend: str) -> None:
        self.backend = backend
        self.inputs: Dict[int, Any] = {}
        self.attached_inputs: Set[int] = set()
        self.channel_state: Dict[int, bool] = {}
        self.dispatcher = ActionDispatcher()
        self.status_writer = StatusWriter(backend)
        self.on_action_name = str(config.get("action_on_name", "EXHIBITION_ON"))
        self.off_action_name = str(config.get("action_off_name", "EXHIBITION_OFF"))
        self.last_input_time: Dict[int, float] = {}
        self.last_action_time = 0.0
        self.last_action: Optional[str] = None
        self.last_action_results: Dict[str, Dict[str, Any]] = {}
        self.pending_install_on_timer: Optional[threading.Timer] = None
        self.pending_macro_off_timer: Optional[threading.Timer] = None
        self.timer_lock = threading.Lock()
        self.running = True
        self.attached = False
        self.start_time: Optional[float] = None
        self.test_hotkeys_enabled = (
            bool(config.get("enable_test_hotkeys", True))
            and (msvcrt is not None)
            and bool(getattr(sys.stdin, "isatty", lambda: False)())
        )

    def process_test_hotkeys(self) -> None:
        if not self.test_hotkeys_enabled or msvcrt is None:
            return

        while msvcrt.kbhit():
            key = msvcrt.getwch()

            if key in ("\x00", "\xe0"):
                if msvcrt.kbhit():
                    msvcrt.getwch()
                continue

            key = key.lower()
            hotkey_on = str(config.get("hotkey_on", "o")).lower()
            hotkey_off = str(config.get("hotkey_off", "f")).lower()
            hotkey_broadcast_on = str(config.get("hotkey_broadcast_on", "b")).lower()
            hotkey_macro_on = str(config.get("hotkey_macro_on", "1")).lower()
            hotkey_macro_off = str(config.get("hotkey_macro_off", "9")).lower()
            hotkey_quit = str(config.get("hotkey_quit", "q")).lower()

            if key == hotkey_on:
                logger.info("Test hotkey ON triggered")
                self.handle_action(self.on_action_name)
            elif key == hotkey_off:
                logger.info("Test hotkey OFF triggered")
                self.handle_action(self.off_action_name)
            elif key == hotkey_broadcast_on:
                logger.info("Test hotkey BROADCAST ON triggered")
                self.send_broadcast_on_now()
            elif key == hotkey_macro_on:
                logger.info("Test hotkey MACRO ON triggered")
                self.send_macro_on_now()
            elif key == hotkey_macro_off:
                logger.info("Test hotkey MACRO OFF triggered")
                self.send_macro_off_now()
            elif key == hotkey_quit:
                logger.info("Test hotkey QUIT triggered")
                self.stop()

    def send_macro_on_now(self) -> None:
        macro_on_command = str(config.get("macro_on_command", "macro 1"))
        macro_udp_port = int(config.get("macro_udp_port", config.get("udp_port", 5000)))
        macro_target_ip = str(config.get("macro_target_ip", "192.168.252.50"))
        result = self.dispatcher.dispatch_udp_command(
            macro_on_command,
            udp_port=macro_udp_port,
            target_ip=macro_target_ip,
        )
        if bool(result.get("ok")):
            logger.info("Macro ON command sent: %s -> %s:%s", macro_on_command, macro_target_ip, macro_udp_port)
        else:
            logger.error("Macro ON command failed: %s", result.get("error"))

    def send_broadcast_on_now(self) -> None:
        self.send_macro_on_now()

        broadcast_on_command = str(config.get("broadcast_on_command", "INSTALL_ON"))
        result = self.dispatcher.dispatch_udp_command(broadcast_on_command)
        if bool(result.get("ok")):
            logger.info("Broadcast ON command sent: %s", broadcast_on_command)
        else:
            logger.error("Broadcast ON command failed: %s", result.get("error"))

        if bool(config.get("enable_wol_on_action", True)) and self.dispatcher.wol_sender is not None:
            wol_result = self.dispatcher.wol_sender.send()
            if bool(wol_result.get("ok")):
                logger.info("WOL sent from BROADCAST ON hotkey")
            else:
                logger.error("WOL failed from BROADCAST ON hotkey: %s", wol_result.get("error"))

    def send_macro_off_now(self) -> None:
        macro_off_command = str(config.get("macro_off_command", "macro 9"))
        macro_udp_port = int(config.get("macro_udp_port", config.get("udp_port", 5000)))
        macro_target_ip = str(config.get("macro_target_ip", "192.168.252.50"))
        result = self.dispatcher.dispatch_udp_command(
            macro_off_command,
            udp_port=macro_udp_port,
            target_ip=macro_target_ip,
        )
        if bool(result.get("ok")):
            logger.info("Macro OFF command sent: %s -> %s:%s", macro_off_command, macro_target_ip, macro_udp_port)
        else:
            logger.error("Macro OFF command failed: %s", result.get("error"))

    def build_input_channel(self, index: int) -> Any:
        channel = cast(Any, DigitalInput())
        if int(config["serial_number"]) != -1:
            channel.setDeviceSerialNumber(int(config["serial_number"]))
        channel.setChannel(index)

        def on_attach_handler(ch: Any, idx: int = index) -> None:
            self.on_attach(idx, ch)

        def on_detach_handler(ch: Any, idx: int = index) -> None:
            self.on_detach(idx, ch)

        def on_state_change_handler(ch: Any, state: Any, idx: int = index) -> None:
            self.on_input_change(idx, ch, bool(state))

        channel.setOnAttachHandler(on_attach_handler)
        channel.setOnDetachHandler(on_detach_handler)
        channel.setOnStateChangeHandler(on_state_change_handler)
        return channel

    def on_attach(self, index: int, _channel: Any) -> None:
        logger.info("Input channel attached: %s (backend: %s)", index, self.backend)
        self.attached_inputs.add(index)
        self.attached = len(self.attached_inputs) > 0
        self.update_status()

    def on_detach(self, index: int, _channel: Any) -> None:
        logger.warning("Input channel detached: %s", index)
        if index in self.attached_inputs:
            self.attached_inputs.remove(index)
        self.channel_state.pop(index, None)
        self.last_input_time.pop(index, None)
        self.attached = len(self.attached_inputs) > 0
        self.update_status()

    def on_input_change(self, index: int, _channel: Any, state: bool) -> None:
        if not self.attached:
            return

        if index not in self.channel_state:
            self.channel_state[index] = bool(state)
            logger.info("Baseline state captured: index=%s, state=%s", index, state)
            return

        previous_state = self.channel_state[index]
        current_state = bool(state)
        self.channel_state[index] = current_state

        if current_state == previous_state:
            return

        now = time.time()
        previous = self.last_input_time.get(index, 0.0)
        if now - previous < float(config["debounce_seconds"]):
            return

        self.last_input_time[index] = now

        if current_state != bool(config["press_on_state"]):
            return

        logger.info("Input changed: index=%s, state=%s", index, state)

        if index == int(config["on_input"]):
            self.handle_action(self.on_action_name)
        elif index == int(config["off_input"]):
            self.handle_action(self.off_action_name)

    def handle_action(self, action: str) -> None:
        now = time.time()

        if self.last_action == action and (now - self.last_action_time) < float(config["lock_seconds"]):
            logger.info("Ignored duplicate action within lock window: %s", action)
            return

        self.last_action = action
        self.last_action_time = now

        if action == self.on_action_name:
            self.last_action_results = self.handle_on_action()
        elif action == self.off_action_name:
            self.last_action_results = self.handle_off_action()
        else:
            self.last_action_results = {
                "dispatcher": {
                    "ok": False,
                    "error": {"code": "UNKNOWN_ACTION", "message": f"Unknown action: {action}"},
                }
            }

        for target_name, result in self.last_action_results.items():
            if bool(result.get("ok")):
                logger.info("Action %s succeeded on target %s", action, target_name)
            else:
                logger.error("Action %s failed on target %s: %s", action, target_name, result.get("error"))

        self.update_status()

    def cancel_install_timer(self) -> None:
        with self.timer_lock:
            if self.pending_install_on_timer is not None:
                self.pending_install_on_timer.cancel()
                self.pending_install_on_timer = None

    def cancel_macro_timer(self) -> None:
        with self.timer_lock:
            if self.pending_macro_off_timer is not None:
                self.pending_macro_off_timer.cancel()
                self.pending_macro_off_timer = None

    def schedule_install_on(self) -> None:
        delay = float(config.get("install_on_delay_seconds", 300.0))
        install_on_command = str(config.get("broadcast_on_command", "INSTALL_ON"))

        def send_install_on() -> None:
            result = self.dispatcher.dispatch_udp_command(install_on_command)
            if bool(result.get("ok")):
                logger.info(
                    "Delayed ON command sent successfully: %s (after %.2fs)",
                    install_on_command,
                    delay,
                )
            else:
                logger.error("Delayed ON command failed: %s", result.get("error"))

            with self.timer_lock:
                self.pending_install_on_timer = None

        timer = threading.Timer(delay, send_install_on)
        timer.daemon = True
        with self.timer_lock:
            self.pending_install_on_timer = timer
        timer.start()
        logger.info("Scheduled delayed ON command: %s in %.2fs", install_on_command, delay)

    def schedule_macro_off(self) -> None:
        delay = float(config.get("macro_off_delay_seconds", 0.0))
        macro_off_command = str(config.get("macro_off_command", "macro 9"))
        macro_udp_port = int(config.get("macro_udp_port", config.get("udp_port", 5000)))
        macro_target_ip = str(config.get("macro_target_ip", "192.168.252.50"))

        def send_macro_off() -> None:
            result = self.dispatcher.dispatch_udp_command(
                macro_off_command,
                udp_port=macro_udp_port,
                target_ip=macro_target_ip,
            )
            if bool(result.get("ok")):
                logger.info(
                    "Macro OFF command sent successfully: %s (after %.2fs, %s:%s)",
                    macro_off_command,
                    delay,
                    macro_target_ip,
                    macro_udp_port,
                )
            else:
                logger.error("Macro OFF command failed: %s", result.get("error"))

            with self.timer_lock:
                self.pending_macro_off_timer = None

        timer = threading.Timer(delay, send_macro_off)
        timer.daemon = True
        with self.timer_lock:
            self.pending_macro_off_timer = timer
        timer.start()
        logger.info(
            "Scheduled macro OFF command: %s in %.2fs to %s:%s",
            macro_off_command,
            delay,
            macro_target_ip,
            macro_udp_port,
        )

    def handle_on_action(self) -> Dict[str, Dict[str, Any]]:
        macro_on_command = str(config.get("macro_on_command", "macro 1"))
        macro_udp_port = int(config.get("macro_udp_port", config.get("udp_port", 5000)))
        macro_target_ip = str(config.get("macro_target_ip", "192.168.252.50"))
        self.cancel_install_timer()
        self.cancel_macro_timer()

        results: Dict[str, Dict[str, Any]] = {
            "udp_broadcast": self.dispatcher.dispatch_udp_command(
                macro_on_command,
                udp_port=macro_udp_port,
                target_ip=macro_target_ip,
            )
        }

        if bool(config.get("enable_wol_on_action", True)) and self.dispatcher.wol_sender is not None:
            results["wake_on_lan"] = self.dispatcher.wol_sender.send()

        self.schedule_install_on()
        return results

    def handle_off_action(self) -> Dict[str, Dict[str, Any]]:
        self.cancel_install_timer()
        self.cancel_macro_timer()

        install_off_command = str(config.get("broadcast_off_command", "INSTALL_OFF"))
        results: Dict[str, Dict[str, Any]] = {
            "udp_broadcast": self.dispatcher.dispatch_udp_command(install_off_command)
        }

        if bool(config.get("enable_macro_off_message", True)):
            self.schedule_macro_off()
        else:
            logger.info("Macro OFF message disabled by config; skipping macro command send")

        return results

    def update_status(self) -> None:
        self.status_writer.write(
            attached=self.attached,
            attached_inputs=self.attached_inputs,
            last_action=self.last_action,
            last_action_time=self.last_action_time,
            last_action_results=self.last_action_results,
            start_time=self.start_time,
        )

    def connect(self) -> None:
        desired_inputs = [int(config["on_input"]), int(config["off_input"])]
        attempts = 0
        max_attempts = int(config["max_reconnect_attempts"])

        while self.running:
            try:
                logger.info("Attempting to open Phidget (attempt %s)...", attempts + 1)
                for idx in desired_inputs:
                    if idx not in self.inputs:
                        self.inputs[idx] = self.build_input_channel(idx)
                    self.inputs[idx].openWaitForAttachment(int(config["attach_timeout_ms"]))

                self.attached = True
                logger.info("Connected input channels: %s", desired_inputs)
                self.update_status()
                return
            except Exception as e:
                logger.error("Phidget connection failed: %s", e)
                attempts += 1

                if max_attempts > 0 and attempts >= max_attempts:
                    logger.error("Max reconnection attempts reached.")
                    raise

                time.sleep(float(config["reconnect_interval_seconds"]))

    def run(self) -> None:
        self.start_time = time.time()
        try:
            self.connect()
            logger.info("Listening for button presses. Press Ctrl+C to stop.")
            if self.test_hotkeys_enabled:
                logger.info(
                    "Test hotkeys enabled: [%s]=ON, [%s]=OFF, [%s]=BROADCAST ON, [%s]=MACRO ON, [%s]=MACRO OFF, [%s]=QUIT",
                    config.get("hotkey_on", "o"),
                    config.get("hotkey_off", "f"),
                    config.get("hotkey_broadcast_on", "b"),
                    config.get("hotkey_macro_on", "1"),
                    config.get("hotkey_macro_off", "9"),
                    config.get("hotkey_quit", "q"),
                )

            while self.running:
                self.process_test_hotkeys()
                time.sleep(0.2)
                if not self.attached:
                    logger.warning("Phidget detached, attempting reconnection...")
                    self.close_inputs()
                    self.connect()

        except KeyboardInterrupt:
            logger.info("Stopping...")
        except Exception as e:
            logger.error("Unexpected error: %s", e)
        finally:
            self.cleanup()

    def close_inputs(self) -> None:
        for channel in self.inputs.values():
            try:
                channel.close()
            except Exception:
                pass
        self.inputs = {}

    def cleanup(self) -> None:
        try:
            self.cancel_install_timer()
            self.cancel_macro_timer()
            self.close_inputs()
            logger.info("Phidget closed.")
        except Exception as e:
            logger.error("Error closing Phidget: %s", e)

    def stop(self) -> None:
        self.running = False
