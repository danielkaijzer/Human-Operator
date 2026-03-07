# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import sys
import os

import aria.sdk as aria

# Add aria_tools to path
aria_tools_path = os.path.join(os.path.dirname(__file__), 'tools', 'aria_tools')
sys.path.insert(0, aria_tools_path)


from common import update_iptables

from visualizer import AriaVisualizer, AriaVisualizerStreamingClientObserver


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--interface",
        dest="streaming_interface",
        type=str,
        default="usb",
        required=False,
        help="Type of interface to use for streaming. Options are usb or wifi.",
        choices=["usb", "wifi"],
    )
    parser.add_argument(
        "--update_iptables",
        default=False,
        action="store_true",
        help="Update iptables to enable receiving the data stream, only for Linux.",
    )
    parser.add_argument(
        "--profile",
        dest="profile_name",
        type=str,
        default="profile18",
        required=False,
        help="Profile to be used for streaming.",
    )
    parser.add_argument(
        "--device-ip", help="IP address to connect to the device over wifi"
    )
    parser.add_argument(
        "--log",
        default=False,
        action="store_true",
        help="Enable data logging to files.",
    )
    parser.add_argument(
        "--no-pupil",
        dest="enable_pupil",
        default=True,
        action="store_false",
        help="Disable pupil detection to avoid potential C extension conflicts.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.update_iptables and sys.platform.startswith("linux"):
        update_iptables()

    #  Optional: Set SDK's log level to Trace or Debug for more verbose logs. Defaults to Info
    aria.set_log_level(aria.Level.Info)

    # 1. Create DeviceClient instance, setting the IP address if specified
    device_client = aria.DeviceClient()

    client_config = aria.DeviceClientConfig()
    if args.device_ip:
        client_config.ip_v4_address = args.device_ip
    device_client.set_client_config(client_config)

    # 2. Connect to the device
    device = device_client.connect()

    # 3. Retrieve the streaming_manager and streaming_client
    streaming_manager = device.streaming_manager
    streaming_client = streaming_manager.streaming_client

    # 4. Set custom config for streaming
    streaming_config = aria.StreamingConfig()
    streaming_config.profile_name = args.profile_name

    if hasattr(streaming_config, "enable_eye_gaze"):
        streaming_config.enable_eye_gaze = True

    #    Note: by default streaming uses Wifi
    if args.streaming_interface == "usb":
        streaming_config.streaming_interface = aria.StreamingInterface.Usb

    #    Use ephemeral streaming certificates
    streaming_config.security_options.use_ephemeral_certs = True
    streaming_manager.streaming_config = streaming_config

    # 5. Start streaming
    streaming_manager.start_streaming()

    # 6. Get streaming state
    streaming_state = streaming_manager.streaming_state
    print(f"Streaming state: {streaming_state}")

    #device_calibration = device.factory_calibration_json

    # Convert JSON string to calibration object
    from projectaria_tools.core.calibration import device_calibration_from_json_string
    device_calibration = device_calibration_from_json_string(device.factory_calibration_json)


    # 7. Create the visualizer observer and attach the streaming client
    # Logging is only enabled when --log flag is used
    enable_logging = args.log
    enable_pupil = args.enable_pupil
    
    aria_visualizer = AriaVisualizer()
    observer = AriaVisualizerStreamingClientObserver(
        aria_visualizer,
        device_calibration,
        enable_logging=enable_logging,
        enable_pupil_detection=enable_pupil
    )
    aria_visualizer.set_observer(observer)  # Store reference for cleanup
    streaming_client.set_streaming_client_observer(observer)
    streaming_client.subscribe()

    # def gaze_cb(sample):
    #     # sample.pixel_xy is assumed to be (u, v) in RGB pixels.
    #     observer = aria_visualizer_streaming_client_observer
    #     observer.on_eye_gaze_received(sample.pixel_xy if sample.is_valid else None)

    # streaming_client.set_eye_gaze_callback(gaze_cb)

    # 8. Visualize the streaming data until we close the window
    render_error = None
    try:
        aria_visualizer.render_loop()
    except Exception as e:
        render_error = e
        print(f"[Main] Error in render_loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure cleanup happens even if there's an exception
        print("[Main] Cleaning up...")
        try:
            if enable_logging:
                observer.finalize_logging_session()
        except Exception as e:
            print(f"[Main] Error during logging cleanup: {e}")

    # 9. Stop streaming and disconnect the device
    print("[Main] Stopping streaming...")
    try:
        streaming_client.unsubscribe()
    except Exception as e:
        print(f"[Main] Error unsubscribing: {e}")
    
    try:
        streaming_manager.stop_streaming()
    except Exception as e:
        print(f"[Main] Error stopping streaming: {e}")
    
    try:
        device_client.disconnect(device)
    except Exception as e:
        print(f"[Main] Error disconnecting device: {e}")
    
    # Re-raise render error if it occurred
    if render_error:
        raise render_error


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] Unhandled exception in main: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
