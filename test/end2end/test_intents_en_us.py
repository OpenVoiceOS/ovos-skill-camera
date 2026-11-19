"""E2E intent-routing tests for ovos-skill-camera.

A request that reaches its intent must run the handler lifecycle in order.

Run: pytest test/end2end/ -v
"""
from unittest import TestCase

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovos_spec_tools import SpecMessage
from ovoscope import CaptureSession
from ovoscope.routing import PIPELINE, TALLY, get_prototype_minicroft

SKILL_ID = "ovos-skill-camera.openvoiceos"
LANG = "en-US"


class _IntentRoutingMixin:
    """Shared MiniCroft setup."""

    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_prototype_minicroft([SKILL_ID], lang=LANG)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'minicroft', None):
            cls.minicroft.stop()

    def _assert_routes(self, utterance: str, intent_file: str):
        # OVOS-PIPELINE-1 §9.2/§8: the orchestrator broadcasts the generic
        # SpecMessage.INTENT_MATCHED (data.intent_name carries the matched
        # intent), then wraps the per-skill dispatch in the handler-lifecycle
        # trio. The dispatch topic drops the ".intent" suffix.
        intent_msg_type = f"{SKILL_ID}:{intent_file.removesuffix('.intent')}"
        session = Session(f"e2e-en_us-{intent_file}-{hash(utterance)}")
        session.lang = LANG
        session.pipeline = PIPELINE
        message = Message(
            "recognizer_loop:utterance",
            {"utterances": [utterance], "lang": LANG},
            {"session": session.serialize()},
        )
        capture = CaptureSession(self.minicroft)
        capture.capture(message, timeout=30)
        types = [m.msg_type for m in capture.finish()]
        TALLY.assert_routed(utterance, intent_msg_type, types)
        lifecycle = [
            f"{SKILL_ID}.activate",
            str(SpecMessage.INTENT_MATCHED),
            str(SpecMessage.INTENT_HANDLER_START),
            intent_msg_type,
            "mycroft.skill.handler.start",
            "mycroft.skill.handler.complete",
            str(SpecMessage.INTENT_HANDLER_COMPLETE),
            "ovos.utterance.handled",
        ]
        seen = [t for t in types if t in lifecycle]
        self.assertEqual(seen, lifecycle,
                         f"{utterance!r}: handler lifecycle out of order: {types}")


class TestIntent1_Have_camera_intent(_IntentRoutingMixin, TestCase):
    """File intent: have_camera.intent"""
    def test_can_i_use_the_camera(self):
        self._assert_routes(r"can I use the camera", r"have_camera.intent")

    def test_can_you_access_the_camera(self):
        self._assert_routes(r"can you access the camera", r"have_camera.intent")

    def test_do_you_have_a_camera(self):
        self._assert_routes(r"do you have a camera", r"have_camera.intent")

    def test_is_a_camera_available(self):
        self._assert_routes(r"is a camera available", r"have_camera.intent")

    def test_is_the_camera_working(self):
        self._assert_routes(r"is the camera working", r"have_camera.intent")

class TestIntent2_Take_picture_intent(_IntentRoutingMixin, TestCase):
    """File intent: take_picture.intent"""
    def test_take_a_photo(self):
        self._assert_routes(r"take a photo", r"take_picture.intent")

    def test_take_a_picture(self):
        self._assert_routes(r"take a picture", r"take_picture.intent")

    def test_take_a_selfie(self):
        self._assert_routes(r"take a selfie", r"take_picture.intent")

    def test_snap_a_photo_of_me(self):
        self._assert_routes(r"snap a photo of me", r"take_picture.intent")

    def test_use_the_camera_to_take_a_selfie(self):
        self._assert_routes(r"use the camera to take a selfie", r"take_picture.intent")
