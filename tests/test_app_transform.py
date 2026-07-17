import json
import pytest

from app import (
    action_to_finger_mapping,
    repair_json_response,
    transform_actions_to_receiver_format,
)


# --- action_to_finger_mapping ---

def test_known_actions_map_to_expected_relay_targets():
    assert action_to_finger_mapping("close_middle") == "middle"
    assert action_to_finger_mapping("close_thumb") == "thumb"
    assert action_to_finger_mapping("wrist_left") == "wrist_left"
    assert action_to_finger_mapping("clench_hand") == "x"


def test_unknown_action_falls_back_to_x():
    assert action_to_finger_mapping("not_a_real_action") == "x"


# --- repair_json_response ---

def test_repair_quotes_unquoted_numeric_keys():
    raw = '{\n  1: [["close_middle", 1.0]]\n}'
    repaired = repair_json_response(raw)
    # should now be valid JSON
    parsed = json.loads(repaired)
    assert parsed == {"1": [["close_middle", 1.0]]}


def test_repair_strips_markdown_code_fence():
    raw = '```json\n{"1": [["close_thumb", 2.0]]}\n```'
    repaired = repair_json_response(raw)
    assert json.loads(repaired) == {"1": [["close_thumb", 2.0]]}


def test_repair_raises_when_no_json_object_present():
    with pytest.raises(ValueError):
        repair_json_response("no braces in this response at all")


# --- transform_actions_to_receiver_format ---

def test_single_numeric_action_produces_relay_then_ems_then_trailing_reset():
    result = transform_actions_to_receiver_format({"1": [["close_middle", 1.0]]})

    assert result["0.0"] == [
        {"type": "RELAY", "finger": "middle"},
        {"type": "EMS", "channel": 1, "amplitude": 60, "duration": 1.0, "frequency": 100, "pulse_width": 1000},
    ]
    # trailing safety reset one second after the action's duration ends
    assert result["2.0"] == [{"type": "RELAY", "finger": "x"}]


def test_sequence_key_format_is_accepted_and_ordered_numerically():
    result = transform_actions_to_receiver_format({
        "sequence_2": [["close_pinky", 1.0]],
        "sequence_1": [["close_thumb", 1.0]],
    })
    # sequence_1 must be scheduled before sequence_2 regardless of dict order
    assert result["0.0"][0] == {"type": "RELAY", "finger": "thumb"}
    assert result["2.0"][0] == {"type": "RELAY", "finger": "pinky"}


def test_unsupported_action_is_skipped_but_still_advances_the_clock():
    result = transform_actions_to_receiver_format({"1": [["biceps_flex", 1.0]]})
    # no RELAY/EMS pair emitted for biceps_flex itself
    assert all(
        entry.get("finger") != "biceps_flex"
        for entries in result.values()
        for entry in entries
    )
    # only the trailing reset remains, after the clock still advanced
    assert result == {"2.0": [{"type": "RELAY", "finger": "x"}]}
