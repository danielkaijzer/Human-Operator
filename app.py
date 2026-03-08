#!/usr/bin/env python3
"""
Video stream client that captures frames and sends them to the LLM for motor command generation.
"""

import cv2
from llm import LLMClient
import json
import time
import threading
from speech import VoiceCommandListener

STREAM_URL = "https://technique-bool-wiley-african.trycloudflare.com/video"

SYSTEM_PROMPT = """You generate motor movement commands for a human body when receiving POV images. 
Here are the json action options available:
- "clench_hand"
- "close_thumb"
- "close_index"
- "close_middle"
- "close_ring"
- "close_pinky"
- "wrist_left"
- "wrist_right"
- "biceps_flex" (to move lower arm up)
- "lean_left" (strafing left via GVS)
- "lean_right" (strafing right)

JSON structure for sequence of actions:
{
  "sequence_1": [["action1", duration_seconds], ["action2", duration_seconds]],
  "sequence_2": [["action3", duration_seconds]]
}

Instructions:
- Only return valid JSON
- Only include actions you want to change
- Durations in seconds (float values)
- Respond based on what you see in the POV image"""


def get_latest_frame() -> bytes:
    """Capture the latest frame from the video stream."""
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
        print(f"Error getting frame: {e}")
        raise


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
        # Find JSON object in response
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON found in response")
        
        json_str = response[start_idx:end_idx]
        actions = json.loads(json_str)
        
        print("[✓] JSON Response:")
        print(json.dumps(actions, indent=2))
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[!] Failed to extract JSON: {e}")
        print("Raw response:", response)
    
    print("\n" + "="*50 + "\n")


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
