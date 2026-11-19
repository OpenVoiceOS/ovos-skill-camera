"""The countdown slot is read in every locale that has a numtag lexicon.

Each row is a phrase of the locale's own take_picture.intent. padacioso cuts
the slot out of the phrase; the handler must count down from the number a
speaker says. The gold is the number in the phrase, not a parser result.
"""
from os.path import dirname, join
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message
from padacioso import IntentContainer

from ovos_skill_camera import WebcamSkill

LOCALE = join(dirname(dirname(__file__)), "locale")

# (locale dir, skill lang, utterance, seconds)
ROWS = [
    ("da-DK", "da-dk", "tag et billede om fem sekunder", 5),
    ("da-DK", "da-dk", "billede om ti sekunder", 10),
    ("de-DE", "de-de", "mach ein Foto in fünf Sekunden", 5),
    ("de-DE", "de-de", "mach ein Bild in zehn Sekunden", 10),
    ("en-US", "en-us", "take a picture in five seconds", 5),
    ("en-US", "en-us", "photo in ten seconds", 10),
    ("en-US", "en-us", "photo in fifteen seconds", 15),
    ("en-US", "en-us", "photo in 7 seconds", 7),
    ("es-ES", "es-es", "haz una foto en cinco segundos", 5),
    ("es-ES", "es-es", "haz una foto con cuenta atrás de diez segundos", 10),
    ("eu-ES", "eu-es", "argazkia bost segundotan", 5),
    ("eu-ES", "eu-es", "argazkia hamar segundotan", 10),
    ("fr-FR", "fr-fr", "prends une photo avec un compte à rebours de cinq secondes", 5),
    ("fr-FR", "fr-fr", "prends une photo avec un compte à rebours de dix secondes", 10),
    ("kab", "kab", "tawlaft deg semmus n tesdatin", 5),
    ("kab", "kab", "tawlaft deg mraw n tesdatin", 10),
    ("nl-NL", "nl-nl", "foto in vijf seconden", 5),
    ("nl-NL", "nl-nl", "foto in tien seconden", 10),
    ("oc-FR", "oc-fr", "fòto d'aicí a cinc segondas", 5),
    ("oc-FR", "oc-fr", "fòto d'aicí a dètz segondas", 10),
    ("pl-PL", "pl-pl", "zdjęcie za pięć sekund", 5),
    ("pl-PL", "pl-pl", "zdjęcie za dziesięć sekund", 10),
    ("pt-BR", "pt-br", "foto em cinco segundos", 5),
    ("pt-BR", "pt-br", "foto em dez segundos", 10),
    ("ru-RU", "ru-ru", "фото через пять секунд", 5),
    ("ru-RU", "ru-ru", "фото через десять секунд", 10),
    ("sv-SE", "sv-se", "bild om fem sekunder", 5),
    ("sv-SE", "sv-se", "bild om tio sekunder", 10),
]


def _slot(locale, utterance):
    with open(join(LOCALE, locale, "take_picture.intent"), encoding="utf-8") as f:
        container = IntentContainer()
        container.add_intent("take_picture", f.read().splitlines())
    match = container.calc_intent(utterance)
    assert match["name"] == "take_picture", (utterance, match)
    return match["entities"]["countdown"]


def _make_skill(lang, settings=None):
    patcher = patch.object(WebcamSkill, "lang", new_callable=PropertyMock, return_value=lang)
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
    skill.sess_has_camera = MagicMock(return_value=True)
    skill.play_camera_sound = MagicMock()
    return skill


def _spoken(skill, countdown):
    skill.handle_take_picture(Message("recognizer_loop:utterance", {"countdown": countdown}))
    return [call.args[0] for call in skill.speak.call_args_list]


@pytest.fixture(autouse=True)
def _stop_patches():
    yield
    patch.stopall()


@pytest.mark.parametrize("locale,lang,utterance,seconds", ROWS)
def test_countdown_from_the_spoken_number(locale, lang, utterance, seconds):
    skill = _make_skill(lang)
    countdown = _slot(locale, utterance)
    assert _spoken(skill, countdown) == [str(n) for n in range(seconds, 0, -1)]


@pytest.mark.parametrize("countdown", ["", "gibberish"])
def test_no_number_keeps_the_settings_fallback(countdown):
    skill = _make_skill("en-us", settings={"countdown": True})
    assert _spoken(skill, countdown) == ["3", "2", "1"]


@pytest.mark.parametrize("countdown", ["", "gibberish"])
def test_no_number_and_no_setting_does_not_count(countdown):
    skill = _make_skill("en-us")
    assert _spoken(skill, countdown) == []
