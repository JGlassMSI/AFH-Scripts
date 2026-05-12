from typing import Any, Dict, Optional

from config import config
from udp import UdpSender, WolSender


class ActionDispatcher:
    def __init__(self) -> None:
        self.udp_sender = UdpSender() if bool(config.get("enable_udp_broadcast_target", True)) else None
        self.wol_sender = WolSender() if bool(config.get("enable_wol_on_action", True)) else None

    def dispatch_udp_command(
        self,
        command: str,
        udp_port: Optional[int] = None,
        target_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.udp_sender is None:
            return {
                "ok": False,
                "target": "udp_broadcast",
                "command": command,
                "error": {"code": "TARGET_DISABLED", "message": "UDP broadcast target is disabled"},
            }
        return self.udp_sender.send(command, udp_port=udp_port, target_ip=target_ip)
