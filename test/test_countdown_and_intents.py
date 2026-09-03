"""Unit tests for ovos-skill-camera (issue #72):

* numeric countdown slot on ``take_picture.intent``
* webcam synonym phrasings on ``have_camera.intent``
* the new ``picture_location.intent`` / ``picture.location.dialog``

Camera/PHAL are fully mocked; the skill is instantiated without the real
``OVOSSkill.__init__`` (no bus connection, no filesystem settings) so these
run fast and offline.
"""
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message

from ovos_skill_camera import WebcamSkill


def _make_skill(has_camera=True, settings=None):
    patcher = patch.object(WebcamSkill, "lang", new_callable=PropertyMock,
                            return_value="en-us")
    patcher.start()
    skill = object.__new__(WebcamSkill)
    skill.skill_id = "ovos-skill-camera.openvoiceos"
    skill.bus = MagicMock(spec=MessageBusClient)
    skill._settings = dict(settings or {})
    skill.gui = MagicMock()
    skill.speak = MagicMock()
    skill.speak_dialog = MagicMock()
    skill.play_audio = MagicMock()
    skill.sess2cam = {}
    skill.sess_has_camera = MagicMock(return_value=has_camera)
    skill.play_camera_sound = MagicMock()
    skill._lang_patcher = patcher
    return skill


class TestNumericCountdown(TestCase):
    """"take a picture in {countdown} seconds" style phrasings."""

    def tearDown(self):
        patch.stopall()

    def test_numeric_countdown_is_honored(self):
        skill = _make_skill()
        msg = Message("recognizer_loop:utterance", {"countdown": "5"})
        skill.handle_take_picture(msg)

        # counts down from the parsed number, not the fixed 3-2-1
        spoken = [c.args[0] for c in skill.speak.call_args_list]
        self.assertEqual(spoken, ["5", "4", "3", "2", "1"])
        shown = [c.args[0] for c in skill.gui.show_text.call_args_list]
        self.assertEqual(shown, ["5", "4", "3", "2", "1"])

    def test_boolean_countdown_setting_unchanged(self):
        # no numeric slot present -> falls back to the existing fixed 3-2-1
        # boolean behaviour driven by settings["countdown"]
        skill = _make_skill(settings={"countdown": True})
        msg = Message("recognizer_loop:utterance", {})
        skill.handle_take_picture(msg)

        spoken = [c.args[0] for c in skill.speak.call_args_list]
        self.assertEqual(spoken, ["3", "2", "1"])

    def test_no_countdown_when_neither_set(self):
        skill = _make_skill(settings={})
        msg = Message("recognizer_loop:utterance", {})
        skill.handle_take_picture(msg)

        skill.speak.assert_not_called()

    def test_no_camera_skips_countdown_entirely(self):
        skill = _make_skill(has_camera=False)
        msg = Message("recognizer_loop:utterance", {"countdown": "5"})
        skill.handle_take_picture(msg)

        skill.speak.assert_not_called()
        skill.speak_dialog.assert_called_once_with("camera_error")


class TestPictureLocation(TestCase):
    def tearDown(self):
        patch.stopall()

    def test_speaks_pictures_folder(self):
        skill = _make_skill(settings={"pictures_folder": "/home/user/Pics"})
        msg = Message("recognizer_loop:utterance", {})
        skill.handle_picture_location(msg)

        skill.speak_dialog.assert_called_once_with(
            "picture.location", {"path": "/home/user/Pics"}
        )

    def test_defaults_to_pictures_home(self):
        skill = _make_skill(settings={})
        msg = Message("recognizer_loop:utterance", {})
        skill.handle_picture_location(msg)

        skill.speak_dialog.assert_called_once_with(
            "picture.location", {"path": "~/Pictures"}
        )


class TestIntentFilePhrasings(TestCase):
    """Padacioso probe against the shipped .intent files (no bus needed)."""

    @classmethod
    def setUpClass(cls):
        from padacioso import IntentContainer
        import os

        locale_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   "locale", "en-US")
        cls.container = IntentContainer()
        cls.container.add_intent(
            "take_picture",
            open(os.path.join(locale_dir, "take_picture.intent")).read().splitlines(),
        )
        cls.container.add_intent(
            "have_camera",
            open(os.path.join(locale_dir, "have_camera.intent")).read().splitlines(),
        )
        cls.container.add_intent(
            "picture_location",
            open(os.path.join(locale_dir, "picture_location.intent")).read().splitlines(),
        )

    def _best(self, utterance):
        return self.container.calc_intent(utterance)

    def test_numeric_countdown_phrasing_matches_take_picture(self):
        for utt in [
            "take a picture with a 3 second countdown",
            "picture in 5 seconds",
        ]:
            result = self._best(utt)
            self.assertEqual(result.get("name"), "take_picture", utt)

    def test_webcam_phrasing_matches_have_camera(self):
        for utt in ["is my webcam working", "do I have a webcam",
                    "is my web cam working", "do I have a web cam"]:
            result = self._best(utt)
            self.assertEqual(result.get("name"), "have_camera", utt)

    def test_picture_location_phrasing_matches(self):
        for utt in ["where is my last picture saved",
                    "where are my last pictures stored",
                    "where do my pictures go"]:
            result = self._best(utt)
            self.assertEqual(result.get("name"), "picture_location", utt)

    def test_negative_utterances_do_not_match_camera_intents(self):
        for utt in ["what's the weather", "play some music",
                    "launch spotify", "count to ten"]:
            result = self._best(utt)
            self.assertNotIn(result.get("name"),
                              {"take_picture", "have_camera", "picture_location"},
                              utt)
