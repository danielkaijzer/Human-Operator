"""Unit tests for the pure action-plan transformation logic in utils/actions.py."""

import json

import pytest

from utils.actions import (
    EMS_AMPLITUDE,
    EMS_FREQUENCY,
    EMS_PULSE_WIDTH,
    action_to_finger_mapping,
    repair_json_response,
    transform_actions_to_receiver_format,
)


class TestActionToFingerMapping:
    def test_known_actions_map_to_relay_targets(self):
        assert action_to_finger_mapping("close_index") == "index"
        assert action_to_finger_mapping("close_middle") == "middle"
        assert action_to_finger_mapping("close_ring") == "ring"
        assert action_to_finger_mapping("close_pinky") == "pinky"
        assert action_to_finger_mapping("close_thumb") == "thumb"
        assert action_to_finger_mapping("wrist_left") == "wrist_left"
        assert action_to_finger_mapping("wrist_right") == "wrist_right"

    def test_clench_hand_maps_to_reset(self):
        assert action_to_finger_mapping("clench_hand") == "x"

    def test_unknown_action_defaults_to_reset(self):
        assert action_to_finger_mapping("do_a_backflip") == "x"


class TestTransformActionsToReceiverFormat:
    def test_single_action_emits_relay_then_ems_then_final_reset(self):
        result = transform_actions_to_receiver_format(
            {"1": [["close_index", 1.0]]}
        )

        assert result["0.0"] == [
            {"type": "RELAY", "finger": "index"},
            {
                "type": "EMS",
                "channel": 1,
                "amplitude": EMS_AMPLITUDE,
                "duration": 1.0,
                "frequency": EMS_FREQUENCY,
                "pulse_width": EMS_PULSE_WIDTH,
            },
        ]
        # 1.0s duration + 1.0s relay buffer -> trailing all-off at 2.0
        assert result["2.0"] == [{"type": "RELAY", "finger": "x"}]
        assert set(result.keys()) == {"0.0", "2.0"}

    def test_cumulative_timing_across_actions(self):
        result = transform_actions_to_receiver_format(
            {"1": [["close_index", 1.0], ["close_middle", 2.0]]}
        )

        # Second action starts after first duration + 1s buffer.
        assert result["2.0"][0] == {"type": "RELAY", "finger": "middle"}
        # Final reset at 2.0 + 2.0 + 1.0 = 5.0
        assert result["5.0"] == [{"type": "RELAY", "finger": "x"}]

    def test_numeric_keys_sorted_numerically_not_lexically(self):
        result = transform_actions_to_receiver_format(
            {
                "10": [["close_middle", 1.0]],
                "2": [["close_index", 1.0]],
            }
        )

        # Key "2" must execute first even though "10" < "2" lexically.
        assert result["0.0"][0]["finger"] == "index"
        assert result["2.0"][0]["finger"] == "middle"

    def test_sequence_keys_supported(self):
        result = transform_actions_to_receiver_format(
            {
                "sequence_2": [["close_middle", 1.0]],
                "sequence_1": [["close_index", 1.0]],
            }
        )

        assert result["0.0"][0]["finger"] == "index"
        assert result["2.0"][0]["finger"] == "middle"

    def test_non_step_keys_like_plan_are_ignored(self):
        result = transform_actions_to_receiver_format(
            {
                "plan": "close the index finger",
                "1": [["close_index", 1.0]],
            }
        )

        fingers = [cmd["finger"] for cmds in result.values() for cmd in cmds if cmd["type"] == "RELAY"]
        assert fingers == ["index", "x"]

    def test_unsupported_actions_skipped_but_still_advance_time(self):
        result = transform_actions_to_receiver_format(
            {"1": [["biceps_flex", 2.0], ["close_index", 1.0]]}
        )

        # biceps_flex is dropped entirely, but its 2.0 + 1.0 window still elapses.
        assert "0.0" not in result
        assert result["3.0"][0] == {"type": "RELAY", "finger": "index"}
        assert result["5.0"] == [{"type": "RELAY", "finger": "x"}]

    def test_empty_plan_still_ends_with_all_off(self):
        result = transform_actions_to_receiver_format({})

        assert result == {"0.0": [{"type": "RELAY", "finger": "x"}]}


class TestRepairJsonResponse:
    def test_plain_json_passes_through(self):
        raw = '{"1": [["close_index", 1.0]]}'
        assert json.loads(repair_json_response(raw)) == {"1": [["close_index", 1.0]]}

    def test_strips_markdown_code_fences(self):
        raw = 'Here you go:\n```json\n{"1": [["close_index", 1.0]]}\n```\nDone.'
        assert json.loads(repair_json_response(raw)) == {"1": [["close_index", 1.0]]}

    def test_quotes_unquoted_numeric_keys(self):
        raw = '{\n  1: [["close_index", 1.0]]\n}'
        assert json.loads(repair_json_response(raw)) == {"1": [["close_index", 1.0]]}

    def test_extracts_object_from_surrounding_prose(self):
        raw = 'Sure! {"plan": "wave"} hope that helps'
        assert json.loads(repair_json_response(raw)) == {"plan": "wave"}

    def test_raises_when_no_json_object_present(self):
        with pytest.raises(ValueError):
            repair_json_response("no json here at all")
