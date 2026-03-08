"""
VLM-Controlled EMS Test Script

Uses Claude's vision API to observe a live camera feed and control EMS electrodes
based on a user-described task. Two threads: main thread runs camera capture + display,
daemon thread sends frames to Claude API and executes EMS commands.
"""

import cv2
import requests
import time
import base64
import os
import threading
import anthropic

# --- Configuration ---
RECEIVER_URL = "https://appearance-prime-compute-sorted.trycloudflare.com/execute"
API_INTERVAL = 1.5          # seconds between API calls
CAMERA_INDEX = 0
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 256

# EMS defaults
EMS_AMPLITUDE = 60
EMS_DURATION = 1.0
EMS_FREQUENCY = 100

# Frame encoding
JPEG_QUALITY = 60
FRAME_RESIZE = (512, 384)

# Cooldown: skip EMS if triggered within this many seconds
EMS_COOLDOWN = 3.0

# --- Claude tool definitions ---
TOOLS = [
    {
        "name": "trigger_ems",
        "description": "Trigger EMS stimulation on a specific finger. Use this when the observed scene matches the task criteria.",
        "input_schema": {
            "type": "object",
            "properties": {
                "finger": {
                    "type": "string",
                    "enum": ["p", "m", "i", "x"],
                    "description": "Which finger to stimulate: p=pinky, m=middle, i=index, x=all"
                }
            },
            "required": ["finger"]
        }
    },
    {
        "name": "do_nothing",
        "description": "Explicitly choose to take no action this frame. Use when the scene does not match the task criteria.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


def encode_frame(frame):
    """Resize frame, JPEG encode, and return base64 string."""
    resized = cv2.resize(frame, FRAME_RESIZE)
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
    _, buf = cv2.imencode('.jpg', resized, encode_params)
    return base64.standard_b64encode(buf).decode('utf-8')


def send_ems_command(finger):
    """Send RELAY command (finger select) then EMS command to receiver."""
    relay_cmd = {
        "0": [
            {"type": "RELAY", "finger": finger}
        ]
    }
    ems_cmd = {
        "0": [
            {"type": "EMS", "channel": 1, "amplitude": EMS_AMPLITUDE,
             "duration": EMS_DURATION, "frequency": EMS_FREQUENCY}
        ]
    }

    try:
        resp = requests.post(RECEIVER_URL, json=relay_cmd, timeout=5)
        print(f"[EMS] RELAY finger={finger} -> {resp.status_code}")
    except Exception as e:
        print(f"[EMS] RELAY error: {e}")
        return

    try:
        resp = requests.post(RECEIVER_URL, json=ems_cmd, timeout=5)
        print(f"[EMS] Stimulation sent -> {resp.status_code}")
    except Exception as e:
        print(f"[EMS] Stimulation error: {e}")


def vlm_loop(client, task_description, shared, lock, stop_event):
    """Daemon thread: periodically send frames to Claude and execute decisions."""
    system_prompt = (
        "You are controlling an EMS (electrical muscle stimulation) system through a camera feed. "
        "You observe the scene and decide whether to trigger EMS on a finger or do nothing.\n\n"
        f"YOUR TASK: {task_description}\n\n"
        "Available fingers: p=pinky, m=middle, i=index, x=all.\n"
        "Call trigger_ems when the scene matches the task criteria. "
        "Call do_nothing when it does not. You must call exactly one tool."
    )

    last_ems_time = 0.0

    while not stop_event.is_set():
        time.sleep(API_INTERVAL)
        if stop_event.is_set():
            break

        # Grab latest frame
        with lock:
            frame = shared.get("frame")
        if frame is None:
            continue

        # Encode frame
        frame_b64 = encode_frame(frame)

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                tools=TOOLS,
                tool_choice={"type": "any"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": frame_b64
                                }
                            },
                            {
                                "type": "text",
                                "text": "Analyze this frame and decide: should you trigger EMS or do nothing?"
                            }
                        ]
                    }
                ]
            )

            # Parse tool use from response
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    if tool_name == "trigger_ems":
                        finger = tool_input.get("finger", "x")
                        now = time.time()
                        if now - last_ems_time >= EMS_COOLDOWN:
                            print(f"[VLM] TRIGGER EMS -> finger={finger}")
                            send_ems_command(finger)
                            last_ems_time = now
                            with lock:
                                shared["last_decision"] = f"TRIGGER finger={finger}"
                        else:
                            remaining = EMS_COOLDOWN - (now - last_ems_time)
                            print(f"[VLM] Cooldown active ({remaining:.1f}s remaining), skipping EMS")
                            with lock:
                                shared["last_decision"] = f"TRIGGER (cooldown, skipped)"
                    elif tool_name == "do_nothing":
                        print("[VLM] Do nothing")
                        with lock:
                            shared["last_decision"] = "Do nothing"
                    break  # Only process first tool call

        except Exception as e:
            print(f"[VLM] API error: {e}")
            with lock:
                shared["last_decision"] = f"Error: {e}"


def main():
    # Get API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        api_key = input("Enter your Anthropic API key: ").strip()
        if not api_key:
            print("No API key provided. Exiting.")
            return

    # Get task description
    task_description = input("Describe the task (e.g. 'flex the middle finger when you see a hand wave'): ").strip()
    if not task_description:
        print("No task provided. Exiting.")
        return

    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=api_key)

    # Open camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Error: Could not open camera with index {CAMERA_INDEX}.")
        return

    # Shared state between threads
    shared = {"frame": None, "last_decision": "Waiting..."}
    lock = threading.Lock()
    stop_event = threading.Event()

    # Start VLM daemon thread
    vlm_thread = threading.Thread(
        target=vlm_loop,
        args=(client, task_description, shared, lock, stop_event),
        daemon=True
    )
    vlm_thread.start()
    print(f"[Main] Camera open. VLM loop started (interval={API_INTERVAL}s).")
    print(f"[Main] Task: {task_description}")
    print("[Main] Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Can't receive frame. Exiting.")
            break

        # Update shared frame
        with lock:
            shared["frame"] = frame.copy()
            last_decision = shared["last_decision"]

        # Overlay last decision on frame
        color = (0, 0, 255) if "TRIGGER" in last_decision else (0, 255, 0)
        cv2.putText(frame, f"VLM: {last_decision}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Task: {task_description[:60]}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow('VLM EMS Control', frame)

        if cv2.waitKey(1) == ord('q'):
            break

    # Cleanup
    stop_event.set()
    cap.release()
    cv2.destroyAllWindows()
    print("[Main] Shut down.")


if __name__ == "__main__":
    main()
