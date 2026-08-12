"""Golden-utterance end-to-end coverage for ovos-skill-camera (en-US).

The golden corpus (``golden_utterances.jsonl``) is a vendored slice of the
shared ovoscope golden-utterance dataset, keyed by
``skill_id == "ovos-skill-camera.openvoiceos"``. One shared ``MiniCroft``
(module-scoped fixture) is booted for the whole suite; every row is its own
parametrized test item. Dispatched ``ovos.intent.matched`` intent names
carry no ``.intent`` suffix (OVOS-INTENT-2 naming), matching the convention
already used by ``test_intents_en_us.py`` in this repo.
"""
import json
from pathlib import Path

import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-camera.openvoiceos"
LANG = "en-US"

GOLDEN_PATH = Path(__file__).parent / "golden_utterances.jsonl"

# camera PHAL handshake fired from inside the intent handler; not relevant
# to intent-routing assertions (see test_intents_en_us.py).
_IGNORE = [
    "speak",
    "ovos.utterance.speak",
    "recognizer_loop:audio_output_start",
    "recognizer_loop:audio_output_end",
    "mycroft.audio.play_sound",
    "ovos.phal.camera.ping",
    "ovos.phal.camera.get",
]

# utterances lifted verbatim from OTHER skills' golden-utterance slices,
# picked for lexical overlap with camera's "camera"/"photo"/"picture"
# vocabulary.
NEGATIVE_UTTERANCES = [
    ("what color is this", "ovos-skill-color-picker.openvoiceos"),
    ("count to ten", "ovos-skill-count.openvoiceos"),
    ("what happened today in history", "ovos-skill-days-in-history.openvoiceos"),
    ("launch spotify", "ovos-skill-application-launcher.openvoiceos"),
    ("are you ready", "ovos-skill-boot-finished.openvoiceos"),
    ("play some music", "ovos-skill-music.openvoiceos"),
    ("what's the weather", "ovos-skill-weather.openvoiceos"),
]


def _label_to_bus_name(intent_label: str) -> str:
    return intent_label.removesuffix(".intent")


def _load_golden_rows():
    rows = []
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                continue
            rows.append(row)
    return rows


GOLDEN_ROWS = [pytest.param(r, id=r["utterance"]) for r in _load_golden_rows()]


@pytest.fixture(scope="module")
def minicroft():
    mc = get_minicroft([SKILL_ID])
    yield mc
    mc.stop()


def _types(mc, text, session_id):
    session = Session(session_id)
    session.lang = LANG
    session.pipeline = ["ovos-padatious-pipeline-plugin-high"]
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [text], "lang": LANG},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    capture = CaptureSession(
        mc,
        eof_msgs=["ovos.utterance.handled"],
        ignore_messages=_IGNORE,
    )
    capture.capture(utterance, timeout=30)
    return [m.msg_type for m in capture.finish()]


@pytest.mark.timeout(60)
@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=lambda r: r["utterance"])
def test_golden_utterance(minicroft, row):
    intent_name = _label_to_bus_name(row["intent_label"])
    types = _types(minicroft, row["utterance"], f"golden-{row['utterance']}")
    assert f"{SKILL_ID}:{intent_name}" in types, (
        f"{row['utterance']!r}: expected {SKILL_ID}:{intent_name!r}, got {types!r}"
    )


@pytest.mark.timeout(60)
@pytest.mark.parametrize("negative", NEGATIVE_UTTERANCES, ids=lambda n: n[0])
def test_negative_confusable_not_claimed(minicroft, negative):
    text, source_skill = negative
    types = _types(minicroft, text, f"negative-{text}")
    claimed = any(t.startswith(f"{SKILL_ID}:") for t in types)
    assert not claimed, f"{text!r} (from {source_skill}) was incorrectly claimed by {SKILL_ID}"
