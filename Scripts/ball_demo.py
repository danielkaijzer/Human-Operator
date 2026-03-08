"""
The idea:
    - One person throws a bright orange object towards the camera. This script will handle the object detection and output a message that the object is approaching. Another program will use this signal to trigger an action to stop the object.
    - We will mask this using OpenCV and as the object comes towards the camera we will trigger an output signal
    - We can send a message out over UDP ("object approaching")

"""

import cv2
import numpy as np
import requests
import time
import json
from collections import deque

# --- Configuration ---
RECEIVER_URL = "https://atlas-delhi-forest-stephen.trycloudflare.com/execute"

EMS_COMMAND = {
    "0": [
        {"type": "EMS", "channel": 1, "amplitude": 60, "duration": 1.0, "frequency": 100}
    ]
}

# HSV range for bright orange
# Ball 1 Settings
# BALL_LOW = np.array([165, 125, 0])
# BALL_HIGH = np.array([255, 255, 255])

# Ball 2 Settings
BALL_LOW = np.array([0, 100, 0])
BALL_HIGH = np.array([5, 255, 255])

# TODO: Play around with these parameters
MIN_CONTOUR_AREA = 1000       # ignore small noise
AREA_BUFFER_SIZE = 5          # rolling buffer length
APPROACH_RATIO = 4          # latest area must be this factor larger than earliest
COOLDOWN_SECONDS = 1.0        # minimum time between UDP sends


def detect_approach(area_buffer):
    """Return True if the object area is consistently growing (approaching)."""
    if len(area_buffer) < AREA_BUFFER_SIZE:
        return False
    earliest = area_buffer[0]
    latest = area_buffer[-1]
    if earliest == 0:
        return False
    # Check overall growth
    if latest / earliest < APPROACH_RATIO:
        return False
    # Check trend is mostly upward (each frame >= previous)
    increasing = sum(1 for i in range(1, len(area_buffer)) if area_buffer[i] >= area_buffer[i - 1])
    return increasing >= len(area_buffer) // 2


def main():
    # The front facing (OV5640) defaults to 0
    camera_index_1 = 0

    cap1 = cv2.VideoCapture(camera_index_1)

    if not cap1.isOpened():
        print(f"Error: Could not open camera with index {camera_index_1}.")
        print("Please make sure your camera is connected and the correct index is used.")
        return

    area_buffer = deque(maxlen=AREA_BUFFER_SIZE)
    last_send_time = 0.0

    while True:
        ret1, frame1 = cap1.read()
        if not ret1:
            print("Error: Can't receive frame from camera 1 (stream end?). Exiting ...")
            break

        # Convert to HSV and create orange mask
        hsv = cv2.cvtColor(frame1, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, BALL_LOW, BALL_HIGH)

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)

        # Find contours and pick the largest
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        status_text = "Scanning..."
        approaching = False

        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)

            if area > MIN_CONTOUR_AREA:
                # Draw bounding rectangle
                x, y, w, h = cv2.boundingRect(largest)
                cv2.rectangle(frame1, (x, y), (x + w, y + h), (0, 165, 255), 2)
                cv2.putText(frame1, f"Area: {int(area)}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

                area_buffer.append(area)

                if detect_approach(area_buffer):
                    approaching = True
                    status_text = "OBJECT APPROACHING!"
                    now = time.time()
                    if now - last_send_time > COOLDOWN_SECONDS:
                        try:
                            response = requests.post(RECEIVER_URL, json=EMS_COMMAND, timeout=5)
                            print(f"[HTTP] Sent EMS command to {RECEIVER_URL} -> {response.status_code}")
                        except Exception as e:
                            print(f"[HTTP] Error: {e}")
                        last_send_time = now
                else:
                    status_text = "object detected"
            else:
                area_buffer.clear()
        else:
            area_buffer.clear()

        # Draw status text
        color = (0, 0, 255) if approaching else (0, 255, 0)
        cv2.putText(frame1, status_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        # Show camera feed and mask side-by-side
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        combined = np.hstack((frame1, mask_bgr))
        cv2.imshow('Ball Detection', combined)

        if cv2.waitKey(1) == ord('q'):
            break

    cap1.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
