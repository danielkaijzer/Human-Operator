from flask import Flask, request, jsonify
import json
import os
import time
import serial
import serial.tools.list_ports

# Import the existing stimulator class
try:
    from hcint_estim import HCIntEstim
except ImportError:
    class HCIntEstim:
        def __init__(self, port=None, baudrate=115200, timeout=1):
            self.port = port
            self.ser = None
            self.error = None
            if port:
                try:
                    self.ser = serial.Serial(port, baudrate, timeout=timeout)
                    print(f"✅ Connected to stimulator on {port}")
                except Exception as e:
                    self.error = str(e)
                    print(f"❌ SERIAL CONNECTION ERROR: {e}")
        def close(self):
            if self.ser: self.ser.close()
        def send_command(self, cmd):
            if self.ser and self.ser.is_open:
                self.ser.write(cmd.encode())
                self.ser.flush()
                print(f"✅ [REAL HARDWARE SENT] {cmd.strip()}")
            else:
                print(f"⚠️ [SIMULATION MODE] {cmd.strip()}")
                if self.error: print(f"   Error: {self.error}")
        def stim_ems(self, channel, amplitude, freq, pulse_width, duration):
            self.send_command(f"ems,{channel},{amplitude},{freq},{pulse_width},{duration}\n")
        def stim_gvs(self, channel, amplitude, polarity, duration):
            self.send_command(f"gvs,{channel},{amplitude},{polarity},{duration}\n")
        def stim_et(self, channel, amplitude, polarity, freq, pulse_width, duration):
            self.send_command(f"et,{channel},{amplitude},{polarity},{freq},{pulse_width},{duration}\n")

app = Flask(__name__)

def find_serial_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        search_text = f"{p.device} {p.description}".lower()
        if any(id.lower() in search_text for id in ["usb", "serial", "arduino", "silicon", "ch340", "cp210", "usbmodem"]):
            return p.device
    return None

env_port = os.environ.get("STIM_PORT")
port = env_port if env_port else find_serial_port()
stimulator = HCIntEstim(port=port)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ready", 
        "port": port or "SIMULATED",
        "hardware_connected": stimulator.ser is not None and stimulator.ser.is_open,
        "last_error": stimulator.error
    }), 200

@app.route('/execute', methods=['POST'])
def execute_sequence():
    try:
        data = request.json
        print(f"\n📥 Received sequence: {json.dumps(data, indent=2)}")
        
        # Sort sequence keys
        try:
            sorted_keys = sorted(data.keys(), key=lambda x: float(x))
        except:
            sorted_keys = data.keys()

        for timestamp in sorted_keys:
            commands = data[timestamp]
            print(f"⏱️ Time {timestamp}s: Running {len(commands)} commands")
            
            for cmd in commands:
                # Get parameters with defaults as per standardized format
                ctype = cmd.get("type", "EMS").upper()
                chan = int(cmd.get("channel", 1))
                amp = float(cmd.get("amplitude", 6))
                dur = float(cmd.get("duration", 0.5))
                freq = int(cmd.get("frequency", 100))
                pw = int(cmd.get("pulse_width", 300))
                pol = int(cmd.get("polarity", 0))

                if ctype == "EMS":
                    stimulator.stim_ems(chan, amp, freq, pw, dur)
                elif ctype == "GVS":
                    stimulator.stim_gvs(chan, amp, pol, dur)
                elif ctype == "ET":
                    stimulator.stim_et(chan, amp, pol, freq, pw, dur)
        
        return jsonify({"status": "executed", "hardware_mode": "REAL" if stimulator.ser else "SIMULATED"}), 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"🚀 Receiver starting on port 5001...")
    print(f"🛠️ Hardware Port: {port or 'NONE'}")
    app.run(host='0.0.0.0', port=5001)
