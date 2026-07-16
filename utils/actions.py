#!/usr/bin/env python3
"""
Pure transformation logic for turning Claude action plans into receiver payloads.

Kept free of hardware/UI dependencies (cv2, serial, audio) so it can be unit
tested without a camera, microphone, or relay board attached.
"""

import re

# EMS defaults
EMS_AMPLITUDE = 60
EMS_DURATION = 1.0
EMS_FREQUENCY = 100
EMS_PULSE_WIDTH = 1000


def action_to_finger_mapping(action: str) -> str:
    """
    Map action names to receiver finger/command codes.

    Map actions to relay target names expected by firmware.

    Supported relay targets:
    - wrist_left, wrist_right, thumb, index, middle, ring, pinky
    - x = reset/all off
    """
    mapping = {
        "clench_hand": "x",      # reset/end sequence
        "close_index": "index",
        "close_middle": "middle",
        "close_pinky": "pinky",
        "close_thumb": "thumb",
        "close_ring": "ring",
        "wrist_left": "wrist_left",
        "wrist_right": "wrist_right",
        # These are not relay-compatible and will be skipped:
        # "biceps_flex": requires different command type
        # "lean_left": GVS command, not relay
        # "lean_right": GVS command, not relay
    }
    return mapping.get(action, "x")


def transform_actions_to_receiver_format(claude_response: dict) -> dict:
    """
    Transform Claude's response format to receiver.py's timestamped format.

    Handles both formats:
    INPUT (numeric keys):
    {
      "1": [["close_middle", 1.0], ["clench_hand", 0.5]],
      "2": [["close_pinky", 2.0]]
    }

    INPUT (sequence keys):
    {
      'sequence_1': [['close_middle', 1.0], ['clench_hand', 0.5]],
      'sequence_2': [['close_pinky', 2.0]]
    }

    OUTPUT (for receiver.py):
    {
      "0": [
        {"type": "RELAY", "finger": "m"},
        {"type": "EMS", "channel": 1, "amplitude": 60, "duration": 1.0, "frequency": 100}
      ],
      "1.0": [
        {"type": "RELAY", "finger": "x"},
        {"type": "EMS", "channel": 1, "amplitude": 60, "duration": 0.5, "frequency": 100}
      ],
      "1.5": [
        {"type": "RELAY", "finger": "p"},
        {"type": "EMS", "channel": 1, "amplitude": 60, "duration": 2.0, "frequency": 100}
      ]
    }

    Timing logic:
    - Each action starts at cumulative_time (sum of all previous durations)
    - Duration in the action is how long the EMS stimulation lasts
    - All supported actions select one relay target then stimulate EMS channel 1
    - Unsupported actions (biceps, lean) are logged but not sent
    """
    receiver_format = {}
    current_time = 0.0

    # Determine key format and sort accordingly
    numeric_keys = [k for k in claude_response.keys() if k.isdigit()]
    sequence_keys = [k for k in claude_response.keys() if k.startswith('sequence_')]

    if numeric_keys:
        # Sort by numeric value
        sorted_keys = sorted(numeric_keys, key=lambda x: int(x))
    elif sequence_keys:
        # Sort by sequence number
        sorted_keys = sorted(sequence_keys, key=lambda x: int(x.split('_')[1]))
    else:
        # Unknown format, use as-is
        sorted_keys = list(claude_response.keys())

    for key in sorted_keys:
        actions = claude_response[key]

        for action_name, duration in actions:
            # Map action to finger code
            finger_code = action_to_finger_mapping(action_name)

            # Create timestamped entry key
            time_key = str(current_time)

            # Skip unsupported actions (biceps, lean, etc.)
            if action_name in ["biceps_flex", "lean_left", "lean_right"]:
                print(f"[!] Skipping unsupported action: {action_name}")
                current_time += float(duration) + 1.0
                continue

            if time_key not in receiver_format:
                receiver_format[time_key] = []

            # All supported actions: RELAY select first, then EMS on channel 1
            receiver_format[time_key].append({
                "type": "RELAY",
                "finger": finger_code
            })
            receiver_format[time_key].append({
                "type": "EMS",
                "channel": 1,
                "amplitude": EMS_AMPLITUDE,
                "duration": float(duration),
                "frequency": EMS_FREQUENCY,
                "pulse_width": EMS_PULSE_WIDTH
            })

            # Move to next action time (current duration + 1 second buffer for relay to open)
            current_time += float(duration) + 1.0

    # Always append "x" command (disable all fingers) at the end
    final_time = str(current_time)
    receiver_format[final_time] = [{
        "type": "RELAY",
        "finger": "x"
    }]

    return receiver_format


def repair_json_response(raw_text: str) -> str:
    """
    Repair common JSON formatting issues from Claude.
    Handles unquoted numeric keys like: 1: [...] -> "1": [...]
    """
    # Extract content between curly braces
    text = raw_text.strip()

    # Remove markdown code fences if present
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            inner = parts[1]
            if inner.startswith("json"):
                inner = inner[4:]
            text = inner.strip()

    # Find the JSON object content (between { and })
    start = text.find('{')
    end = text.rfind('}') + 1

    if start == -1 or end == 0:
        raise ValueError("No JSON object found")

    json_content = text[start:end]

    # Fix unquoted numeric keys: change `1:` to `"1":`
    # Pattern: word boundary, one or more digits, colon
    json_content = re.sub(r'(\n\s*)(\d+):', r'\1"\2":', json_content)

    return json_content
