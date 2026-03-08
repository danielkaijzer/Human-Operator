from flask import Flask, request, jsonify
import json
import os
import time
import serial
import serial.tools.list_ports

# data structure
# {
#   "0.0": [
#     {"type": "RELAY", "finger": "i"},
#     {"type": "EMS", "channel": 1, "amplitude": 60, "duration": 1.0, "frequency": 100}
#   ],
#   "1.5": [
#     {"type": "RELAY", "finger": "x"}
#   ]
# }
# Note: Channel 1 = finger actions (require RELAY first), Channel 2 = wrist left (no relay needed)
# Import the existing stimulator class
try:
    from hcint_estim import HCIntEstim # type: ignore
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
                    print(f"❌ STIMULATOR SERIAL CONNECTION ERROR: {e}")
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

# New Relay Controller Class
class RelayController:
    def __init__(self, port=None, baudrate=115200, timeout=1):
        self.port = port
        self.ser = None
        self.error = None
        if port:
            try:
                self.ser = serial.Serial(port, baudrate, timeout=timeout)
                time.sleep(1.5)  # Let the Arduino reset and boot
                print(f"✅ Connected to relay MCU on {port}")
            except Exception as e:
                self.error = str(e)
                print(f"❌ RELAY SERIAL CONNECTION ERROR: {e}")
    def close(self):
        if self.ser: self.ser.close()
    def send_command(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.write(cmd.encode('utf-8'))
            self.ser.flush()
            print(f"✅ [REAL HARDWARE SENT] Relay: {cmd.strip()}")
        else:
            print(f"⚠️ [SIMULATION MODE] Relay: {cmd.strip()}")
            if self.error: print(f"   Error: {self.error}")

app = Flask(__name__)

def find_serial_ports():
    ports = serial.tools.list_ports.comports()
    valid_ports = []
    for p in ports:
        search_text = f"{p.device} {p.description}".lower()
        if any(id.lower() in search_text for id in ["usb", "serial", "arduino", "silicon", "ch340", "cp210", "usbmodem"]):
            valid_ports.append(p.device)
    return valid_ports

# Detect ports
found_ports = find_serial_ports()
env_stim_port = os.environ.get("STIM_PORT")
env_relay_port = os.environ.get("RELAY_PORT")

# Assign ports (prioritize environment variables, fallback to auto-discovery)
stim_port = env_stim_port if env_stim_port else (found_ports[0] if len(found_ports) > 0 else None)
relay_port = env_relay_port if env_relay_port else (found_ports[1] if len(found_ports) > 1 else None)

stimulator = HCIntEstim(port=stim_port)
relay_mcu = RelayController(port=relay_port)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ready", 
        "stim_port": stim_port or "SIMULATED",
        "stim_hardware_connected": stimulator.ser is not None and stimulator.ser.is_open,
        "stim_last_error": stimulator.error,
        "relay_port": relay_port or "SIMULATED",
        "relay_hardware_connected": relay_mcu.ser is not None and relay_mcu.ser.is_open,
        "relay_last_error": relay_mcu.error
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
                ctype = cmd.get("type", "EMS").upper()

                # Process Relay Commands
                if ctype == "RELAY":
                    # Expects finger to be 'p', 'm', 'i', or 'x'
                    finger = cmd.get("finger", "x")
                    relay_mcu.send_command(finger)
                
                # Process Stimulation Commands
                else:
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
        
        hardware_status = {
            "stimulator": "REAL" if stimulator.ser else "SIMULATED",
            "relay": "REAL" if relay_mcu.ser else "SIMULATED"
        }
        return jsonify({"status": "executed", "hardware_mode": hardware_status}), 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"🚀 Receiver starting on port 5001...")
    print(f"🛠️ Stimulator Port: {stim_port or 'NONE'}")
    print(f"🛠️ Relay Port: {relay_port or 'NONE'}")
    app.run(host='0.0.0.0', port=5001)