"""
Lucid Clinic — VNC Controller
Manages VNC connections to clinic machines and executes screen actions.
Provides both a live VNC controller and a mock controller for development.
"""

import io
import base64
import logging
import struct
import socket
import time
from abc import ABC, abstractmethod
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("lucid.agent.vnc")


class BaseVNCController(ABC):
    """Abstract base for VNC controllers (live + mock)."""

    def __init__(self, width: int = 1024, height: int = 768):
        self.width = width
        self.height = height
        self.connected = False

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def screenshot(self) -> bytes:
        """Capture screen as PNG bytes."""
        pass

    @abstractmethod
    def click(self, x: int, y: int):
        """Left click at coordinates."""
        pass

    @abstractmethod
    def double_click(self, x: int, y: int):
        """Double click at coordinates."""
        pass

    @abstractmethod
    def right_click(self, x: int, y: int):
        """Right click at coordinates."""
        pass

    @abstractmethod
    def type_text(self, text: str):
        """Type a string of text."""
        pass

    @abstractmethod
    def key(self, combo: str):
        """Send key combo (e.g., 'ctrl+s', 'Return', 'Tab')."""
        pass

    @abstractmethod
    def mouse_move(self, x: int, y: int):
        """Move mouse to coordinates."""
        pass

    @abstractmethod
    def scroll(self, x: int, y: int, direction: str, amount: int = 3):
        """Scroll at position. Direction: up/down/left/right."""
        pass

    def screenshot_base64(self) -> str:
        """Capture screen and return as base64-encoded PNG."""
        png_bytes = self.screenshot()
        return base64.standard_b64encode(png_bytes).decode("utf-8")


class MockVNCController(BaseVNCController):
    """
    Mock VNC controller for development/testing.
    Generates placeholder screenshots and logs actions.
    """

    def __init__(self, width: int = 1024, height: int = 768):
        super().__init__(width, height)
        self.action_log: list[dict] = []
        self._step = 0

    def connect(self):
        logger.info("[MOCK VNC] Connected to mock display %dx%d", self.width, self.height)
        self.connected = True

    def disconnect(self):
        logger.info("[MOCK VNC] Disconnected")
        self.connected = False

    def _log_action(self, action: str, **kwargs):
        self._step += 1
        entry = {"step": self._step, "action": action, **kwargs}
        self.action_log.append(entry)
        logger.info("[MOCK VNC] Step %d: %s %s", self._step, action, kwargs)

    def _generate_mock_screenshot(self) -> bytes:
        """Generate a placeholder PNG showing a mock EZBIS-like screen."""
        img = Image.new("RGB", (self.width, self.height), color=(240, 240, 245))
        draw = ImageDraw.Draw(img)

        # Title bar
        draw.rectangle([(0, 0), (self.width, 30)], fill=(0, 51, 102))
        draw.text((10, 5), "EZBIS Office - Patient Management (MOCK)", fill="white")

        # Menu bar
        draw.rectangle([(0, 30), (self.width, 55)], fill=(220, 220, 225))
        for i, menu in enumerate(["File", "Edit", "View", "Patient", "Schedule", "Reports"]):
            draw.text((15 + i * 90, 35), menu, fill=(30, 30, 30))

        # Content area — mock patient list
        draw.rectangle([(10, 65), (self.width - 10, 90)], fill=(0, 51, 102))
        draw.text((20, 70), "Account    Name                    Phone           Last Visit   Status", fill="white")

        rows = [
            "6211C      Steve Dahlkamp          (555) 123-4567  2024-08-15   Active",
            "7845A      Mary Johnson             (555) 234-5678  2024-06-20   Warm",
            "3021B      Robert Williams          (555) 345-6789  2023-11-10   Cool",
            "9182D      Patricia Brown            (555) 456-7890  2023-03-05   Cold",
            "4567E      James Davis              (555) 567-8901  2022-01-15   Dormant",
        ]
        for j, row in enumerate(rows):
            y = 95 + j * 25
            bg = (255, 255, 255) if j % 2 == 0 else (245, 245, 250)
            draw.rectangle([(10, y), (self.width - 10, y + 24)], fill=bg)
            draw.text((20, y + 4), row, fill=(30, 30, 30))

        # Show recent action
        if self.action_log:
            last = self.action_log[-1]
            draw.rectangle([(10, self.height - 35), (self.width - 10, self.height - 5)], fill=(255, 255, 230))
            draw.text((15, self.height - 30), f"Last action: {last['action']} {last}", fill=(100, 100, 0))

        # Step counter
        draw.text((self.width - 120, 5), f"Step: {self._step}", fill=(200, 200, 200))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def screenshot(self) -> bytes:
        self._log_action("screenshot")
        return self._generate_mock_screenshot()

    def click(self, x: int, y: int):
        self._log_action("left_click", x=x, y=y)

    def double_click(self, x: int, y: int):
        self._log_action("double_click", x=x, y=y)

    def right_click(self, x: int, y: int):
        self._log_action("right_click", x=x, y=y)

    def type_text(self, text: str):
        self._log_action("type", text=text)

    def key(self, combo: str):
        self._log_action("key", combo=combo)

    def mouse_move(self, x: int, y: int):
        self._log_action("mouse_move", x=x, y=y)

    def scroll(self, x: int, y: int, direction: str, amount: int = 3):
        self._log_action("scroll", x=x, y=y, direction=direction, amount=amount)


class LiveVNCController(BaseVNCController):
    """
    Live VNC controller using raw RFB protocol via socket.
    Connects to a real VNC server on Nick's clinic machine via Tailscale.
    """

    def __init__(self, host: str, port: int, password: str,
                 width: int = 1024, height: int = 768):
        super().__init__(width, height)
        self.host = host
        self.port = port
        self.password = password
        self._sock: socket.socket | None = None

    def connect(self):
        """Connect to VNC server. Requires vnc server to be running."""
        try:
            # We use a subprocess-based approach with screenshot tools
            # rather than implementing full RFB protocol here.
            # The actual VNC interaction will use pyautogui-style commands
            # sent through the Tailscale tunnel.
            logger.info("Connecting to VNC at %s:%d", self.host, self.port)
            self.connected = True
            logger.info("VNC connected successfully")
        except Exception as e:
            logger.error("VNC connection failed: %s", str(e))
            raise ConnectionError(f"Could not connect to VNC at {self.host}:{self.port}") from e

    def disconnect(self):
        self.connected = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        logger.info("VNC disconnected")

    def screenshot(self) -> bytes:
        if not self.connected:
            raise RuntimeError("Not connected to VNC")
        # In production: capture screen from VNC framebuffer
        # Placeholder — will be implemented when Nick's machine is set up
        raise NotImplementedError(
            "Live VNC screenshot requires vnc server connection. "
            "Set AGENT_MOCK_MODE=true for development."
        )

    def click(self, x: int, y: int):
        if not self.connected:
            raise RuntimeError("Not connected to VNC")
        raise NotImplementedError("Live VNC click — awaiting clinic machine setup")

    def double_click(self, x: int, y: int):
        if not self.connected:
            raise RuntimeError("Not connected to VNC")
        raise NotImplementedError("Live VNC double_click — awaiting clinic machine setup")

    def right_click(self, x: int, y: int):
        if not self.connected:
            raise RuntimeError("Not connected to VNC")
        raise NotImplementedError("Live VNC right_click — awaiting clinic machine setup")

    def type_text(self, text: str):
        if not self.connected:
            raise RuntimeError("Not connected to VNC")
        raise NotImplementedError("Live VNC type — awaiting clinic machine setup")

    def key(self, combo: str):
        if not self.connected:
            raise RuntimeError("Not connected to VNC")
        raise NotImplementedError("Live VNC key — awaiting clinic machine setup")

    def mouse_move(self, x: int, y: int):
        if not self.connected:
            raise RuntimeError("Not connected to VNC")
        raise NotImplementedError("Live VNC mouse_move — awaiting clinic machine setup")

    def scroll(self, x: int, y: int, direction: str, amount: int = 3):
        if not self.connected:
            raise RuntimeError("Not connected to VNC")
        raise NotImplementedError("Live VNC scroll — awaiting clinic machine setup")


def create_vnc_controller(mock_mode: bool = True, **kwargs) -> BaseVNCController:
    """Factory: create the appropriate VNC controller."""
    if mock_mode:
        return MockVNCController(
            width=kwargs.get("width", 1024),
            height=kwargs.get("height", 768),
        )
    return LiveVNCController(
        host=kwargs["host"],
        port=kwargs["port"],
        password=kwargs["password"],
        width=kwargs.get("width", 1024),
        height=kwargs.get("height", 768),
    )
