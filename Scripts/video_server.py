"""

Stream camera video over HTTP as MJPEG.

Usage:
    python video_server.py [--camera 0] [--port 8080] [--host 0.0.0.0]

View in browser:
    http://<your-ip>:8080/video   - MJPEG stream
    http://<your-ip>:8080/        - Simple HTML page with the stream embedded
"""

import argparse
import socket
import cv2
import threading
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn, TCPServer

# Shared state
lock = threading.Lock()
current_frame = None
running = True


def capture_frames(camera_index):
    """Continuously capture frames from the camera."""
    global current_frame, running

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Error: Could not open camera {camera_index}")
        running = False
        return

    print(f"Camera {camera_index} opened successfully")

    while running:
        ret, frame = cap.read()
        if not ret:
            print("Error: Can't receive frame. Exiting...")
            running = False
            break
        with lock:
            current_frame = frame

    cap.release()


class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head><title>Camera Stream</title></head>
<body style="margin:0; background:#111; display:flex; justify-content:center; align-items:center; height:100vh;">
    <img src="/video" style="max-width:100%; max-height:100vh;">
</body>
</html>"""
            self.wfile.write(html.encode())

        elif self.path == "/video":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()

            while running:
                with lock:
                    frame = current_frame

                if frame is None:
                    continue

                ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not ret:
                    continue

                try:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b"\r\n")
                except BrokenPipeError:
                    break

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress per-request logs to keep output clean
        pass


class ThreadingHTTPServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def get_local_ip():
    """Get this machine's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    global running

    parser = argparse.ArgumentParser(description="Stream camera video over HTTP")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    args = parser.parse_args()

    # Start camera capture in a background thread
    capture_thread = threading.Thread(target=capture_frames, args=(args.camera,), daemon=True)
    capture_thread.start()

    local_ip = get_local_ip()
    print(f"Starting video server on {args.host}:{args.port}")
    print(f"View stream at: http://{local_ip}:{args.port}/")
    print("Press Ctrl+C to stop")

    server = ThreadingHTTPServer((args.host, args.port), StreamHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        running = False
        server.shutdown()


if __name__ == "__main__":
    main()
