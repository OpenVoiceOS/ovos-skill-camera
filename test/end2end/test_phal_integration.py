"""End-to-end skill <-> PHAL plugin integration test for ovos-skill-camera.

Exercises the real skill together with its companion hardware plugin,
``ovos-PHAL-plugin-camera`` (``PHALCamera``), on the SAME FakeBus.

Only the camera hardware (the OpenCV ``Camera`` open/close/get_frame methods and
``cv2.imwrite``) is mocked. Every bus handler runs for real, so the test proves
the full skill -> PHAL round-trip on one bus:

    "take a picture" -> skill pings   ovos.phal.camera.ping
                     -> PHAL replies  ovos.phal.camera.pong   (camera present)
                     -> skill emits   ovos.phal.camera.get
                     -> PHAL captures a (mocked) frame and replies
                        ovos.phal.camera.get.response

Run: pytest test/end2end/test_phal_integration.py -v
"""
import time
from unittest import TestCase
from unittest.mock import MagicMock, patch

import numpy as np
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import get_minicroft

import ovos_PHAL_plugin_camera as cammod

SKILL_ID = "ovos-skill-camera.openvoiceos"
LANG = "en-US"


class TestCameraPhalIntegration(TestCase):
    """Skill + ovos-PHAL-plugin-camera on one bus, camera hardware mocked."""

    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_minicroft([SKILL_ID])

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "minicroft", None):
            cls.minicroft.stop()

    def setUp(self):
        # Patch ONLY the camera hardware layer: the OpenCV-backed Camera I/O
        # and cv2.imwrite. The PHAL bus handlers themselves run for real.
        self._frame = np.zeros((4, 4, 3), dtype=np.uint8)
        self._patches = [
            patch.object(cammod.Camera, "open", return_value=MagicMock(name="stream")),
            patch.object(cammod.Camera, "close", return_value=None),
            patch.object(cammod.Camera, "get_frame", return_value=self._frame),
            patch.object(cammod.cv2, "imwrite", return_value=True),
        ]
        for p in self._patches:
            p.start()

        self.phal = cammod.PHALCamera(bus=self.minicroft.bus, config={})
        # skill and plugin share one in-process bus; the cross-device session
        # guard is irrelevant here, so accept the skill's forwarded requests.
        self.phal.validate_message_context = lambda message: True

        self.pongs = []
        self.get_responses = []
        self.minicroft.bus.on(
            "ovos.phal.camera.pong", lambda m: self.pongs.append(m)
        )
        self.minicroft.bus.on(
            "ovos.phal.camera.get.response", lambda m: self.get_responses.append(m)
        )

    def tearDown(self):
        try:
            self.phal.shutdown()
        except Exception:
            pass
        for p in self._patches:
            p.stop()

    def _drive(self, utterance):
        session = Session(f"e2e-phal-{hash(utterance)}")
        session.lang = LANG
        session.pipeline = ["ovos-padatious-pipeline-plugin-high"]
        handled = []
        self.minicroft.bus.on("ovos.utterance.handled", lambda m: handled.append(m))
        message = Message(
            "recognizer_loop:utterance",
            {"utterances": [utterance], "lang": LANG},
            {"session": session.serialize()},
        )
        self.minicroft.bus.emit(message)
        deadline = time.monotonic() + 15
        while not handled and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertTrue(handled, f"utterance {utterance!r} was not handled")

    def test_take_picture_round_trip(self):
        # (a) skill detects the camera via ping/pong and emits camera.get,
        # (b) the PHAL handle_take_picture runs and replies get.response.
        self._drive("take a picture")

        self.assertTrue(
            self.pongs,
            "camera PHAL plugin never answered the availability ping (pong)",
        )
        self.assertTrue(
            self.get_responses,
            "camera PHAL plugin did not emit ovos.phal.camera.get.response",
        )
        # the (mocked) camera hardware was actually driven by the PHAL handler
        self.assertTrue(
            cammod.cv2.imwrite.called,
            "PHAL handler never wrote a frame via cv2.imwrite",
        )
