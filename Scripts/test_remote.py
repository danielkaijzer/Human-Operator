import requests
import json

RECEIVER_URL = "https://atlas-delhi-forest-stephen.trycloudflare.com/execute"

def send_test_signal():
    print(f"--- Sending Manual Low-Level Signal to {RECEIVER_URL} ---")
    
    # Direct hardware parameters in standardized format
    test_data = {
        "0": [
            {"type": "GVS", "channel": 1, "amplitude": 6, "duration": 1.0, "frequency": 100}
        ],
        "1.5": [
            {"type": "GVS", "channel": 2, "amplitude": 6, "duration": 1.0, "frequency": 100}
        ]
    }
    
    try:
        response = requests.post(RECEIVER_URL, json=test_data, timeout=10)
        if response.status_code == 200:
            print(f"✅ SUCCESS: Receiver acknowledged sequence.")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ FAIL: Receiver returned {response.status_code}")
            print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    send_test_signal()
