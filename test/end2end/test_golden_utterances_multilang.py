"""Multilingual golden-utterance end-to-end coverage for ovos-skill-camera.

test_golden_utterances.py only exercises en-US; every locale under locale/
ships all three .intent files (have_camera, take_picture,
picture_location), so this suite covers every locale in the fleet.

Dispatched ovos.intent.matched intent names carry no .intent suffix
(OVOS-INTENT-2 naming), matching test_golden_utterances.py's convention.

One MiniCroft is booted PER LOCALE (module-scoped fixture, indirectly
parametrized by lang; pytest reuses one boot per distinct lang value
across every row of that lang and tears it down before moving on).

Row construction: each row is derived mechanically from that locale's own
.intent template lines (its own bracket-alternation choices), never a
translation of the English rows. The {countdown} slot, where present, is
filled with the literal value 10.
"""
import json
import time
from pathlib import Path
from typing import List

import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-camera.openvoiceos"

END2END_DIR = Path(__file__).parent

LANGS = sorted(p.stem.split("golden_utterances_", 1)[1]
               for p in END2END_DIR.glob("golden_utterances_*.jsonl"))
assert LANGS, "no golden_utterances_<lang>.jsonl files found"

_IGNORE = [
    "speak",
    "ovos.utterance.speak",
    "recognizer_loop:audio_output_start",
    "recognizer_loop:audio_output_end",
    "mycroft.audio.play_sound",
    "ovos.phal.camera.ping",
    "ovos.phal.camera.get",
]


def _label_to_bus_name(intent_label: str) -> str:
    return intent_label.removesuffix(".intent")


def _load_rows(lang):
    path = END2END_DIR / f"golden_utterances_{lang}.jsonl"
    rows = []
    needs_manual = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                needs_manual += 1
                continue
            rows.append(row)
    assert rows or needs_manual, f"{lang}: no golden rows"
    return rows


ALL_ROWS = []
for _lang in LANGS:
    for _row in _load_rows(_lang):
        ALL_ROWS.append(_row)


def _golden_id(row):
    return f"{row['lang']}-{row['intent_label']}-{row['utterance']}"


@pytest.fixture(scope="module")
def minicroft(request):
    """One MiniCroft boot per distinct lang value, reused across every row
    of that lang."""
    lang = request.param
    mc = get_minicroft([SKILL_ID], max_wait=150, lang=lang)
    # see test_golden_utterances.py: padaos compiles in a background thread,
    # give it a moment to settle before the first assertion.
    time.sleep(2)
    yield mc
    mc.stop()


def _types(mc, text, lang, session_id) -> List[str]:
    session = Session(session_id)
    session.lang = lang
    session.pipeline = ["ovos-padatious-pipeline-plugin-high"]
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [text], "lang": lang},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    capture = CaptureSession(
        mc,
        eof_msgs=["ovos.utterance.handled"],
        ignore_messages=_IGNORE,
    )
    capture.capture(utterance, timeout=30)
    return [m.msg_type for m in capture.finish()]


KNOWN_BUGS = {}

_PARAMS = [
    pytest.param(row["lang"], row, id=_golden_id(row))
    for row in ALL_ROWS
]


@pytest.mark.timeout(300)
@pytest.mark.parametrize("minicroft,row", _PARAMS, indirect=["minicroft"])
def test_golden_utterance_multilang(minicroft, row):
    intent_name = _label_to_bus_name(row["intent_label"])
    types = _types(minicroft, row["utterance"], row["lang"], f"golden-{_golden_id(row)}")
    matched = f"{SKILL_ID}:{intent_name}" in types
    bug_key = (row["lang"], row["utterance"])
    if bug_key in KNOWN_BUGS and not matched:
        pytest.xfail(reason=f"known-bug: {KNOWN_BUGS[bug_key]}")
    assert matched, (
        f"[{row['lang']}] {row['utterance']!r}: expected {SKILL_ID}:{intent_name!r}, got {types!r}"
    )
