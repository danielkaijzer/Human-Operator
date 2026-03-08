#!/usr/bin/env python3
"""
Video stream client that captures frames and sends them to the LLM for motor command generation.
"""

import cv2
import json
import time
import threading
import requests
import numpy as np
from utils.llm import LLMClient
from utils.speech import VoiceCommandListener
from utils.prompts import SYSTEM_PROMPT, PLANNING_PROMPT, CHECK_PROMPT

STREAM_URL = "https://technique-bool-wiley-african.trycloudflare.com/video"
RECEIVER_URL = "https://amsterdam-river-lease-toolbox.trycloudflare.com/execute"

# EMS defaults
EMS_AMPLITUDE = 60
EMS_DURATION = 1.0
EMS_FREQUENCY = 100

# Template image for testing (when stream is unavailable)
TEMPLATE_IMAGE_WIDTH = 640
TEMPLATE_IMAGE_HEIGHT = 480


def get_latest_frame() -> bytes:
    """
    Capture the latest frame from the video stream.
    Falls back to a red template image if stream is unavailable (for testing).
    """
    try:
        # Open the stream
        cap = cv2.VideoCapture(STREAM_URL)
        
        if not cap.isOpened():
            raise Exception("Failed to open video stream")
        
        # Read one frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise Exception("Failed to read frame from stream")
        
        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()
    
    except Exception as e:
        print(f"[!] Error getting frame from stream: {e}")
        print("[*] Using red template image for testing...")
        
        # Create a red template image for testing
        template_frame = np.zeros((TEMPLATE_IMAGE_HEIGHT, TEMPLATE_IMAGE_WIDTH, 3), dtype='uint8')
        template_frame[:, :] = (0, 0, 255)  # Red in BGR format
        
        # Add white text
        cv2.putText(template_frame, "TEMPLATE IMAGE", (int(TEMPLATE_IMAGE_WIDTH * 0.15), int(TEMPLATE_IMAGE_HEIGHT * 0.5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
        cv2.putText(template_frame, "Video stream offline", (int(TEMPLATE_IMAGE_WIDTH * 0.1), int(TEMPLATE_IMAGE_HEIGHT * 0.65)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)
        
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', template_frame)
        return buffer.tobytes()



def action_to_finger_mapping(action: str) -> str:
    """
    Map action names to receiver finger/command codes.
    
    Based on vlm_test.py's PLANNING_PROMPT:
    - p = pinky
    - m = middle
    - i = index (also closes thumb+index for gripping)
    - x = RESET/END sequence (clears stacking, doesn't execute a finger)
    
    Only these codes are supported by receiver.py relay control.
    
    Wrist left uses EMS channel 2 directly (no relay needed).
    """
    mapping = {
        "clench_hand": "x",      # reset/end sequence
        "close_index": "i",      # index (includes thumb+index for gripping)
        "close_middle": "m",     # middle
        "close_pinky": "p",      # pinky
        "close_thumb": "i",      # grouped with index as thumb+index grip
        # Wrist actions - keep mapped but receiver needs update:
        "wrist_left": "wrist_left",
        # These are NOT relay-compatible and will be skipped:
        # "close_ring": not supported by hardware
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
    - wrist_left uses EMS channel 2 only (no relay command)
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
            if finger_code in ["wrist_right", "biceps_flex", "lean_left", "lean_right"]:
                print(f"[!] Skipping unsupported action: {action_name}")
                current_time += float(duration) + 0.5
                continue

            if time_key not in receiver_format:
                receiver_format[time_key] = []

            # Wrist left: EMS on channel 2 only (no relay needed)
            if finger_code == "wrist_left":
                receiver_format[time_key].append({
                    "type": "EMS",
                    "channel": 2,
                    "amplitude": EMS_AMPLITUDE,
                    "duration": float(duration),
                    "frequency": EMS_FREQUENCY
                })
            else:
                # Finger actions: send RELAY first (finger select), then EMS on channel 1
                receiver_format[time_key].append({
                    "type": "RELAY",
                    "finger": finger_code
                })
                receiver_format[time_key].append({
                    "type": "EMS",
                    "channel": 1,
                    "amplitude": EMS_AMPLITUDE,
                    "duration": float(duration),
                    "frequency": EMS_FREQUENCY
                })
            
            # Move to next action time (current duration + small buffer)
            current_time += float(duration) + 0.5
    
    return receiver_format


def repair_json_response(raw_text: str) -> str:
    """
    Repair common JSON formatting issues from Claude.
    Handles unquoted numeric keys like: 1: [...] -> "1": [...]
    """
    import re
    
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



def on_command_ready(command: str):
    """Callback when voice command is ready"""
    
    print(f"\n[*] Getting latest frame...")
    frame_bytes = get_latest_frame()
    
    # Create prompt combining frame content and voice command
    prompt = f"{SYSTEM_PROMPT}\n\nUser voice command: {command}"
    
    print(f"[*] Sending to LLM with voice command: {command}")
    client = LLMClient()
    
    start_time = time.time()
    response = client.ask_with_image(prompt, frame_bytes)
    elapsed = time.time() - start_time
    
    print(f"\n[Response Time: {elapsed:.2f}s]")
    
    # Extract JSON from response
    try:
        # Repair common JSON formatting issues
        json_str = repair_json_response(response)
        claude_actions = json.loads(json_str)
        
        print("[✓] Claude Response:")
        print(json.dumps(claude_actions, indent=2))
        
        # Transform to receiver format and execute
        print("\n[*] Transforming to receiver format...")
        receiver_payload = transform_actions_to_receiver_format(claude_actions)
        
        print("[✓] Receiver payload:")
        print(json.dumps(receiver_payload, indent=2))
        
        # Send to receiver
        execute_motor_commands(receiver_payload)
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[!] Failed to parse JSON: {e}")
        print("Raw response:", response)
    
    print("\n" + "="*50 + "\n")


def execute_motor_commands(receiver_payload: dict):
    """Send motor command sequence to receiver.py"""
    try:
        print(f"[*] Sending motor commands to receiver...")
        response = requests.post(RECEIVER_URL, json=receiver_payload, timeout=10)
        
        if response.status_code == 200:
            print(f"[✓] Receiver acknowledged (HTTP {response.status_code})")
            try:
                print(f"    Response: {response.json()}")
            except:
                print(f"    Response body: {response.text}")
        else:
            print(f"[!] Receiver returned HTTP {response.status_code}")
            print(f"    Response: {response.text}")
    except Exception as e:
        print(f"[!] Error sending to receiver: {e}")


def main():
    """Main loop: listen for voice commands and process with video frames."""
    print(f"Connecting to stream: {STREAM_URL}")
    print("Starting voice listener...\n")
    
    # Start voice listener in background thread
    listener = VoiceCommandListener(on_command_ready=on_command_ready)
    voice_thread = threading.Thread(target=listener.start, daemon=True)
    voice_thread.start()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Exiting...")


if __name__ == "__main__":
    main()
