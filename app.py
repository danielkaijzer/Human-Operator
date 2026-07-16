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
from utils.actions import repair_json_response, transform_actions_to_receiver_format
from utils.llm import LLMClient
from utils.speech import VoiceCommandListener
from utils.prompts import SYSTEM_PROMPT

RECEIVER_URL = os.getenv("RECEIVER_URL", "http://127.0.0.1:5001/execute")

# Camera config
CAMERA_INDEX = 0
FRAME_RESIZE = (512, 384)
JPEG_QUALITY = 60


def get_latest_frame() -> bytes:
    """
    Capture the latest frame from the local camera with retry logic.
    """
    max_retries = 3

    for attempt in range(max_retries):
        try:
            cap = cv2.VideoCapture(CAMERA_INDEX)

            if not cap.isOpened():
                raise RuntimeError(f"Failed to open camera {CAMERA_INDEX}")

            ret, frame = cap.read()
            cap.release()

            if not ret:
                raise RuntimeError("Failed to read frame from camera")

            # Resize and encode with quality settings (matching vlm_test.py approach)
            resized = cv2.resize(frame, FRAME_RESIZE)
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            _, buffer = cv2.imencode('.jpg', resized, encode_params)
            return buffer.tobytes()

        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[!] Error getting frame from camera: {e}")
                raise
            print(f"[!] {e} (attempt {attempt + 1}/{max_retries}), retrying...")
            time.sleep(0.5)

    raise RuntimeError("Failed to capture frame after retries")



def on_command_ready(command: str):
    """Callback when voice command is ready"""
    
    print("\n[*] Getting latest frame...")
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
        print("[*] Sending motor commands to receiver...")
        response = requests.post(RECEIVER_URL, json=receiver_payload, timeout=10)
        
        if response.status_code == 200:
            print(f"[✓] Receiver acknowledged (HTTP {response.status_code})")
            try:
                print(f"    Response: {response.json()}")
            except ValueError:
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
        cap.release()
        cv2.destroyAllWindows()
        print("[*] Exiting...")


if __name__ == "__main__":
    main()
