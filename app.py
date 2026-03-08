#!/usr/bin/env python3
"""
Video stream client that captures frames and sends them to the LLM for motor command generation.
"""

import cv2
import json
import time
import threading
from utils.llm import LLMClient
from utils.speech import VoiceCommandListener
from utils.prompts import SYSTEM_PROMPT, PLANNING_PROMPT, CHECK_PROMPT

STREAM_URL = "https://technique-bool-wiley-african.trycloudflare.com/video"


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
