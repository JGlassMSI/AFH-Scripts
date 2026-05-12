import signal
from types import FrameType
from typing import Optional

from debug import logger
from inputs import PhidgetController

phidget_backend = "Phidget22"
controller: Optional[PhidgetController] = None


def signal_handler(signum: int, frame: Optional[FrameType]) -> None:
    logger.info("Received signal %s, shutting down...", signum)
    if controller is not None:
        controller.stop()


def main() -> None:
    global controller
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    controller = PhidgetController(backend=phidget_backend)
    controller.run()


if __name__ == "__main__":
    main()
