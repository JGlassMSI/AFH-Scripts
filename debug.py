import json
import logging
import sys
import time
from typing import Any, Dict, Optional, Set

from config import APP_DIR, config


def setup_logger() -> logging.Logger:
    log_level = getattr(logging, str(config["log_level"]).upper(), logging.INFO)
    log_path = APP_DIR / str(config["log_file"])
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout) if config["log_enabled"] else logging.NullHandler(),
        ],
    )
    return logging.getLogger(__name__)


logger = setup_logger()


class StatusWriter:
    def __init__(self, backend: str) -> None:
        self.backend = backend
        self.status_path = APP_DIR / str(config["status_file"])

    def write(
        self,
        attached: bool,
        attached_inputs: Set[int],
        last_action: Optional[str],
        last_action_time: float,
        last_action_results: Dict[str, Dict[str, Any]],
        start_time: Optional[float],
    ) -> None:
        status: Dict[str, Any] = {
            "attached": attached,
            "attached_inputs": sorted(list(attached_inputs)),
            "last_action": last_action,
            "last_action_time": last_action_time,
            "last_action_results": last_action_results,
            "uptime": time.time() - start_time if start_time else 0,
            "timestamp": time.time(),
            "backend": self.backend,
        }
        try:
            with open(self.status_path, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.error("Failed to update status file: %s", e)
