#!/usr/bin/env python3
"""
Video stream client that captures frames and sends them to the LLM for motor command generation.
"""

import cv2
import json
import os
import time
import threading
import requests
from utils.llm import LLMClient
from utils.speech import VoiceCommandListener
from utils.prompts import SYSTEM_PROMPT, PLANNING_PROMPT, CHECK_PROMPT

RECEIVER_URL = os.getenv("RECEIVER_URL", "http://127.0.0.1:5001/execute")

# Camera config
CAMERA_INDEX = 0
FRAME_RESIZE = (512, 384)
JPEG_QUALITY = 60

# EMS defaults
EMS_AMPLITUDE = 60
EMS_DURATION = 1.0
EMS_FREQUENCY = 100
EMS_PULSE_WIDTH = 1000


def get_latest_frame() -> bytes:
    """
    Capture the latest frame from the local camera with retry logic.
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            cap = cv2.VideoCapture(CAMERA_INDEX)
            
            if not cap.isOpened():
                if attempt < max_retries - 1:
                    print(f"[!] Camera not opened (attempt {attempt+1}/{max_retries}), retrying...")
                    time.sleep(0.5)
                    continue
                else:
                    raise Exception(f"Failed to open camera {CAMERA_INDEX} after {max_retries} attempts")
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                if attempt < max_retries - 1:
                    print(f"[!] Failed to read frame (attempt {attempt+1}/{max_retries}), retrying...")
                    time.sleep(0.5)
                    continue
                else:
                    raise Exception(f"Failed to read frame from camera after {max_retries} attempts")
            
            # Resize and encode with quality settings (matching vlm_test.py approach)
            resized = cv2.resize(frame, FRAME_RESIZE)
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            _, buffer = cv2.imencode('.jpg', resized, encode_params)
            return buffer.tobytes()
        
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[!] Error getting frame from camera: {e}")
                raise
            time.sleep(0.5)

    raise RuntimeError("Failed to capture frame after retries")



# Maps each LLM action to how it drives the hardware:
#   relay_target: relay electrode to select before stimulating
#   ems_channel:  stimulator channel to fire
# Only channel 2 is wired to the relay board, so all three actions route
# through it. The firmware enables one electrode at a time, which makes the
# actions mutually exclusive (one action per step).
ACTION_SPEC = {
    "grab":        {"relay_target": "grab",        "ems_channel": 2},
    "arm_left":  {"relay_target": "arm_left",  "ems_channel": 2},
    "arm_right": {"relay_target": "arm_right", "ems_channel": 2},
}




def transform_actions_to_receiver_format(claude_response: dict) -> dict:
    """
    Transform the LLM's response format to receiver.py's timestamped format.

    Handles both numeric ("1", "2") and "sequence_1" style step keys.

    INPUT (numeric keys):
    {
      "1": [["grab", 1.0]],
      "2": [["arm_left", 1.5]]
    }

    OUTPUT (for receiver.py):
    {
      "0.0": [
        {"type": "RELAY", "target": "grab"},
        {"type": "EMS", "channel": 2, "amplitude": 60, "duration": 1.0, ...}
      ],
      "2.0": [
        {"type": "RELAY", "target": "arm_left"},
        {"type": "EMS", "channel": 2, "amplitude": 60, "duration": 1.5, ...}
      ],
      "4.5": [
        {"type": "RELAY", "target": "x"}
      ]
    }

    Per-action behavior comes from ACTION_SPEC: each action selects its relay
    electrode, then fires EMS on channel 2. Only one relay is active at a time,
    so actions are mutually exclusive.

    Timing logic:
    - Each action starts at cumulative_time (sum of all previous durations).
    - Duration in the action is how long the EMS stimulation lasts.
    - Unknown actions are logged and skipped.
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
            spec = ACTION_SPEC.get(action_name)

            # Skip unknown actions, but still advance time so later steps stay ordered.
            if spec is None:
                print(f"[!] Skipping unsupported action: {action_name}")
                current_time += float(duration) + 1.0
                continue

            time_key = str(current_time)
            if time_key not in receiver_format:
                receiver_format[time_key] = []

            # Route the relevant arm relay first (grab drives the channel directly).
            if spec["relay_target"] is not None:
                receiver_format[time_key].append({
                    "type": "RELAY",
                    "target": spec["relay_target"]
                })
            receiver_format[time_key].append({
                "type": "EMS",
                "channel": spec["ems_channel"],
                "amplitude": EMS_AMPLITUDE,
                "duration": float(duration),
                "frequency": EMS_FREQUENCY,
                "pulse_width": EMS_PULSE_WIDTH
            })

            # Move to next action time (current duration + 1 second buffer for relay to open)
            current_time += float(duration) + 1.0

    # Always append "x" command (reset relay) at the end
    final_time = str(current_time)
    receiver_format[final_time] = [{
        "type": "RELAY",
        "target": "x"
    }]

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
    """Main loop: display live camera feed and listen for voice commands."""
    print(f"Using camera index {CAMERA_INDEX}")
    print("Starting voice listener...\n")
    print("Press 'q' to quit\n")
    
    # Open camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[!] Error: Could not open camera {CAMERA_INDEX}")
        return
    
    # Start voice listener in background thread
    listener = VoiceCommandListener(on_command_ready=on_command_ready)
    voice_thread = threading.Thread(target=listener.start, daemon=True)
    voice_thread.start()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[!] Failed to read frame from camera")
                break
            
            # Overlay status text
            cv2.putText(frame, "Listening for voice commands...", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "Press 'q' to quit", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Display frame
            cv2.imshow('Camera Feed', frame)
            
            # Check for 'q' key to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
    except KeyboardInterrupt:
        print("\n[*] Interrupted")
    finally:
        listener.stop()
        cap.release()
        cv2.destroyAllWindows()
        print("[*] Exiting...")


if __name__ == "__main__":
    main()
