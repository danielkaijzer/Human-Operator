import cv2
import numpy as np

def nothing(x):
    pass

def main():
    # Use the same camera index as your main script
    camera_index = 0
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print(f"Error: Could not open camera {camera_index}")
        return

    cv2.namedWindow('HSV Tuner')

    # Create trackbars with your current defaults as starting points
    # Hue is 0-179, Saturation/Value are 0-255
    cv2.createTrackbar('Low H', 'HSV Tuner', 5, 179, nothing)
    cv2.createTrackbar('Low S', 'HSV Tuner', 100, 255, nothing)
    cv2.createTrackbar('Low V', 'HSV Tuner', 100, 255, nothing)
    
    cv2.createTrackbar('High H', 'HSV Tuner', 20, 179, nothing)
    cv2.createTrackbar('High S', 'HSV Tuner', 255, 255, nothing)
    cv2.createTrackbar('High V', 'HSV Tuner', 255, 255, nothing)

    print("Adjust trackbars to isolate your object.")
    print("The goal is to make the object white and background black.")
    print("Press 'q' to quit and see the final values.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Get current positions of all trackbars
        l_h = cv2.getTrackbarPos('Low H', 'HSV Tuner')
        l_s = cv2.getTrackbarPos('Low S', 'HSV Tuner')
        l_v = cv2.getTrackbarPos('Low V', 'HSV Tuner')
        h_h = cv2.getTrackbarPos('High H', 'HSV Tuner')
        h_s = cv2.getTrackbarPos('High S', 'HSV Tuner')
        h_v = cv2.getTrackbarPos('High V', 'HSV Tuner')

        lower_bound = np.array([l_h, l_s, l_v])
        upper_bound = np.array([h_h, h_s, h_v])

        mask = cv2.inRange(hsv, lower_bound, upper_bound)

        # Show mask and original side-by-side
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        combined = np.hstack((frame, mask_bgr))
        
        cv2.imshow('HSV Tuner', combined)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print(f"\n--- Copy these lines into ball_demo.py ---")
            print(f"ORANGE_LOW = np.array([{l_h}, {l_s}, {l_v}])")
            print(f"ORANGE_HIGH = np.array([{h_h}, {h_s}, {h_v}])")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()