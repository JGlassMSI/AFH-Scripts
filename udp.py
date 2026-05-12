import socket
import time
from typing import Any, Dict, List, Optional, cast

from config import config
from debug import logger


def _parse_mac(mac: str) -> bytes:
    normalized = mac.strip().replace("-", "").replace(":", "").lower()
    if len(normalized) != 12:
        raise ValueError(f"Invalid MAC length: {mac}")
    try:
        return bytes.fromhex(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid MAC format: {mac}") from exc


class UdpSender:
    def __init__(self) -> None:
        self.sequence_number = 0

    def send(self, command: str, udp_port: Optional[int] = None, target_ip: Optional[str] = None) -> Dict[str, Any]:
        self.sequence_number += 1
        payload = command
        target_port = int(config["udp_port"]) if udp_port is None else int(udp_port)
        target_ip_value = str(config["broadcast_ip"]) if target_ip is None else str(target_ip)
        if bool(config["append_sequence"]):
            payload = f"{command}|seq={self.sequence_number}"

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        success_count = 0
        try:
            for i in range(int(config["send_repeats"])):
                try:
                    sock.sendto(payload.encode("utf-8"), (target_ip_value, target_port))
                    logger.info(
                        "UDP sent (%s/%s): %s -> %s:%s",
                        i + 1,
                        config["send_repeats"],
                        payload,
                        target_ip_value,
                        target_port,
                    )
                    success_count += 1
                except OSError as e:
                    logger.error("UDP send failed on attempt %s: %s", i + 1, e)
                    if i < config["send_repeats"] - 1:
                        time.sleep(float(config["send_interval_seconds"]) * (2**i))
                    continue

                if i < config["send_repeats"] - 1:
                    time.sleep(float(config["send_interval_seconds"]))
        finally:
            sock.close()

        if success_count == 0:
            return {
                "ok": False,
                "target": "udp_broadcast",
                "command": command,
                "error": {"code": "SEND_FAILED", "message": "No UDP packets were sent successfully"},
            }

        return {
            "ok": True,
            "target": "udp_broadcast",
            "command": command,
            "sent_count": success_count,
        }


class WolSender:
    def __init__(self) -> None:
        self.broadcast_ip = str(config.get("broadcast_ip", "192.168.252.255"))
        self.wol_port = int(config.get("wol_port", 9))
        configured_macs_raw = config.get("wol_mac_addresses", [])
        if isinstance(configured_macs_raw, list):
            configured_macs = cast(List[Any], configured_macs_raw)
            self.mac_addresses: List[str] = [str(item) for item in configured_macs]
        else:
            self.mac_addresses = []

    def send(self) -> Dict[str, Any]:
        if not self.mac_addresses:
            return {
                "ok": False,
                "target": "wake_on_lan",
                "error": {
                    "code": "NO_MACS_CONFIGURED",
                    "message": "No MAC addresses configured for Wake-on-LAN",
                },
            }

        sent_count = 0
        errors: List[Dict[str, str]] = []

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            for mac in self.mac_addresses:
                mac_str = str(mac)
                try:
                    mac_bytes = _parse_mac(mac_str)
                    magic_packet = b"\xff" * 6 + (mac_bytes * 16)
                    sock.sendto(magic_packet, (self.broadcast_ip, self.wol_port))
                    sent_count += 1
                    logger.info(
                        "WOL magic packet sent to %s via %s:%s",
                        mac_str,
                        self.broadcast_ip,
                        self.wol_port,
                    )
                except Exception as exc:
                    errors.append({"mac": mac_str, "error": str(exc)})
                    logger.error("WOL send failed for %s: %s", mac_str, exc)

        if sent_count == 0:
            return {
                "ok": False,
                "target": "wake_on_lan",
                "error": {
                    "code": "WOL_SEND_FAILED",
                    "message": "Failed to send Wake-on-LAN to all configured MACs",
                    "details": errors,
                },
            }

        result: Dict[str, Any] = {
            "ok": True,
            "target": "wake_on_lan",
            "sent_count": sent_count,
        }
        if errors:
            result["warnings"] = errors
        return result
