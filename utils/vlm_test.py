"""
VLM-Controlled EMS Test Script

Uses Claude's vision API to observe a live camera feed and control EMS electrodes
based on a user-described task. Two threads: main thread runs camera capture + display,
daemon thread sends frames to Claude API and executes EMS commands.
"""

import cv2
import requests
import time
import json
import base64
import os
import threading
import anthropic

from prompts import PLANNING_PROMPT, CHECK_PROMPT

# --- Configuration ---
RECEIVER_URL = "https://amsterdam-river-lease-toolbox.trycloudflare.com/execute"
API_INTERVAL = 1.0          # seconds between API calls
CAMERA_INDEX = 0
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024

# EMS defaults
EMS_AMPLITUDE = 60
EMS_DURATION = 1.0
EMS_FREQUENCY = 100

# Frame encoding
JPEG_QUALITY = 60
FRAME_RESIZE = (512, 384)

# Minimum delay between EMS commands during execution
EMS_COOLDOWN = 3.0


def encode_frame(frame):
    """Resize frame, JPEG encode, and return base64 string."""
    resized = cv2.resize(frame, FRAME_RESIZE)
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
    _, buf = cv2.imencode('.jpg', resized, encode_params)
    return base64.standard_b64encode(buf).decode('utf-8')


def parse_json_response(raw_text):
    """Extract and parse JSON from Claude's response, handling markdown fences and preamble."""
    text = raw_text.strip()

    # Strip markdown code fences
    if "```" in text:
        # Find content between first ``` and last ```
        parts = text.split("```")
        if len(parts) >= 3:
            inner = parts[1]
            # Remove optional language tag (e.g. "json\n")
            if inner.startswith("json"):
                inner = inner[4:]
            text = inner.strip()

    # If still not starting with [ or {, try to find the first [ or {
    if not text.startswith("[") and not text.startswith("{"):
        bracket = text.find("[")
        brace = text.find("{")
        if bracket >= 0 and (brace < 0 or bracket < brace):
            text = text[bracket:]
        elif brace >= 0:
            text = text[brace:]

    # Trim trailing junk after the closing bracket/brace
    if text.startswith("["):
        depth = 0
        for idx, ch in enumerate(text):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    text = text[:idx + 1]
                    break
    elif text.startswith("{"):
        depth = 0
        for idx, ch in enumerate(text):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    text = text[:idx + 1]
                    break

    return json.loads(text)


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


def generate_plan(client, task_description, frame_b64):
    """Send a frame to Claude and get back a JSON plan of steps."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=PLANNING_PROMPT,
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
                        "text": f"TASK: {task_description}\n\nObserve the current scene and create your step-by-step plan as a JSON array."
                    }
                ]
            }
        ]
    )

    # Extract text content and parse JSON
    raw_text = ""
    for block in response.content:
        if block.type == "text":
            raw_text += block.text

    print(f"[Debug] Raw plan response:\n{raw_text[:500]}")

    return parse_json_response(raw_text)


def check_before_step(client, task_description, step, frame_b64):
    """Quick vision check: is the hand in position for the next step? Returns (ok, message)."""
    desc = step.get("description", "")
    action = step.get("action", "")
    finger = step.get("finger", "")

    step_summary = f"Next step: {action}"
    if finger:
        step_summary += f" finger={finger}"
    step_summary += f" — {desc}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=128,
        system=CHECK_PROMPT,
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
                        "text": f"TASK: {task_description}\n\n{step_summary}\n\nIs the hand ready? Respond with JSON."
                    }
                ]
            }
        ]
    )

    raw_text = ""
    for block in response.content:
        if block.type == "text":
            raw_text += block.text

    result = parse_json_response(raw_text)
    return result.get("ok", True), result.get("message", "")


def execute_plan(client, task_description, plan, shared, lock, stop_event):
    """Execute a prebuilt plan step by step with live vision checks before EMS steps."""
    total = len(plan)
    for i, step in enumerate(plan):
        if stop_event.is_set():
            break

        action = step.get("action", "wait")
        delay = float(step.get("delay", 0))
        desc = step.get("description", "")

        # Update display with upcoming step
        with lock:
            shared["last_decision"] = f"[{i+1}/{total}] {desc}"
            shared["step_info"] = f"Step {i+1}/{total}"

        # Wait the specified delay before executing
        if delay > 0:
            print(f"[Plan] Waiting {delay}s before step {i+1}...")
            wait_end = time.time() + delay
            while time.time() < wait_end and not stop_event.is_set():
                time.sleep(0.2)

        if stop_event.is_set():
            break

        # Live vision check before EMS steps
        if action == "ems":
            with lock:
                check_frame = shared.get("frame")
            if check_frame is not None:
                try:
                    frame_b64 = encode_frame(check_frame)
                    ok, correction = check_before_step(client, task_description, step, frame_b64)
                    if not ok and correction:
                        print(f"[Check] Hand not ready: {correction}")
                        with lock:
                            shared["last_decision"] = f"[{i+1}/{total}] CMD: {correction}"
                        # Wait for human to reposition
                        wait_end = time.time() + 5.0
                        while time.time() < wait_end and not stop_event.is_set():
                            time.sleep(0.2)
                        if stop_event.is_set():
                            break
                except Exception as e:
                    print(f"[Check] Vision check failed (proceeding anyway): {e}")

        # Execute the step
        if action == "ems":
            finger = step.get("finger", "x")
            print(f"[Plan] Step {i+1}/{total}: EMS finger={finger} - {desc}")
            send_ems_command(finger)
            with lock:
                shared["last_decision"] = f"[{i+1}/{total}] EMS finger={finger}"

        elif action == "text":
            message = step.get("message", "")
            print(f"[Plan] Step {i+1}/{total}: TEXT '{message}' - {desc}")
            with lock:
                shared["last_decision"] = f"[{i+1}/{total}] CMD: {message}"

        elif action == "wait":
            print(f"[Plan] Step {i+1}/{total}: WAIT - {desc}")

    if not stop_event.is_set():
        with lock:
            shared["last_decision"] = "Plan complete!"
            shared["step_info"] = "Done"
        print("[Plan] All steps executed.")


def vlm_loop(client, task_description, shared, lock, stop_event):
    """Daemon thread: observe scene, generate plan, execute it."""
    # Wait for first frame
    while not stop_event.is_set():
        with lock:
            frame = shared.get("frame")
        if frame is not None:
            break
        time.sleep(0.1)

    if stop_event.is_set():
        return

    # Phase 1: Observe scene and generate plan
    with lock:
        shared["last_decision"] = "Observing scene..."
        shared["step_info"] = "Planning"
    print("[VLM] Capturing frame for planning...")

    with lock:
        frame = shared["frame"]
    frame_b64 = encode_frame(frame)

    try:
        print("[VLM] Sending frame to Claude for planning...")
        plan = generate_plan(client, task_description, frame_b64)
        print(f"[VLM] Plan received with {len(plan)} steps:")
        for i, step in enumerate(plan):
            print(f"  {i+1}. [{step.get('action')}] {step.get('description', '')} (delay: {step.get('delay', 0)}s)")

        with lock:
            shared["last_decision"] = f"Plan ready: {len(plan)} steps"
            shared["step_info"] = "Executing"

        time.sleep(1)  # Brief pause before execution starts

        # Phase 2: Execute the plan with live checks
        execute_plan(client, task_description, plan, shared, lock, stop_event)

    except json.JSONDecodeError as e:
        print(f"[VLM] Failed to parse plan JSON: {e}")
        with lock:
            shared["last_decision"] = "Error: bad plan format"
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
    shared = {"frame": None, "last_decision": "Waiting...", "step_info": ""}
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
            step_info = shared["step_info"]

        # Overlay info on frame
        if "EMS" in last_decision:
            color = (0, 0, 255)
        elif "CMD:" in last_decision:
            color = (255, 200, 0)
        else:
            color = (0, 255, 0)
        cv2.putText(frame, f"{last_decision}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Task: {task_description[:60]}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        if step_info:
            cv2.putText(frame, step_info, (10, 85),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

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
