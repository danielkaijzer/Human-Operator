<p align="left">
  <img src="https://img.shields.io/badge/Winner-MIT%20Hard%20Mode%202026-gold?style=for-the-badge&logo=mit&logoColor=white" alt="MIT Winner Badge">
  <img src="https://img.shields.io/badge/Watch-YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="Video">
</p>
<p align="center">
  <img width="1200" height="628" alt="Human Operator" src="https://github.com/user-attachments/assets/581d8f0a-ff4f-443f-bf0b-99a2538cd598" />
</p>

# Human Operator

Human Operator is a wearable human-augmentation system that maps voice + first-person vision input to relay-routed Electrical Muscle Stimulation (EMS) actions.

This project won MIT Hard Mode 2026 (Learn Track).

<div align="center">
  <img src="https://github.com/user-attachments/assets/2b088e69-b861-4d76-951c-7a69cf5c6d5c" width="32%" alt="AI makes hand wave" />
  <img src="https://github.com/user-attachments/assets/366eef6b-59c4-4773-bbd3-4310cee81fad" width="32%" alt="AI makes hand play piano" />
  <img src="https://github.com/user-attachments/assets/483c7c5d-858b-47a7-a765-e2fee5f27b1a" width="32%" alt="AI makes hand do OK sign"/>
  <p><sub>Left to right: AI stimulates wrist muscle to wave • AI stimulates fingers in sequence to play melody • AI stimulates fingers to form an OK sign</sub></p>
</div>

[Watch Full Video Demo](https://youtu.be/fCLxENGs7CY?si=noS9cT161CwEFh5Q)

## What This Repository Contains

- `app.py`: Main runtime loop (camera + voice trigger + LLM + command dispatch)
- `utils/receiver.py`: Flask hardware gateway for timed relay/EMS command execution
- `manual_control_app.py`: PyQt GUI for manual calibration and direct stimulation testing
- `firmware/human_operator_ems/human_operator_ems.ino`: Arduino relay controller firmware
- `run_hardware.sh`: Recommended one-command launcher for real relay hardware mode

## Team
- Peter He - [Portfolio](https://peterhe.dev) | [GitHub](https://github.com/molegod) | [LinkedIn](https://www.linkedin.com/in/ph475/)
- Valdemar Danry - [Portfolio](https://valdemardanry.com) | [GitHub](https://github.com/valleballe) | [LinkedIn](https://www.linkedin.com/in/valdemar-danry)
- Daniel Kaijzer - [GitHub](https://github.com/danielkaijzer) | [LinkedIn](https://www.linkedin.com/in/danielkaijzer/)
- Yutong Wu - [GitHub](https://github.com/ichbinHallie0426) | [LinkedIn](https://www.linkedin.com/in/yutong-wu-4b66661b5/)
- Ashley Neall - [Portfolio](https://aneall.github.io/) | [GitHub](https://github.com/aneall) | [LinkedIn](https://www.linkedin.com/in/ashley-neall/)
- Sean Hardesty Lewis - [Portfolio](https://seanhardestylewis.com/) | [GitHub](https://github.com/seanhlewis) | [LinkedIn](https://www.linkedin.com/in/seanhardestylewis/)

## Safety and Responsibility

This repository controls physical electrical stimulation hardware.

- Use only with appropriate supervision and informed consent.
- Keep stimulation intensities conservative during calibration.
- Ensure emergency stop access (software stop and physical disconnect).
- Do not use on people with contraindications to EMS.

## Prerequisites

- Python 3.10+
- macOS/Linux shell environment
- Arduino IDE (for flashing firmware)
- Anthropic API key (`ANTHROPIC_API_KEY`)
- Hardware:
  - Relay MCU (Arduino-compatible)
  - Relay board
  - EMS/stimulator device (optional in relay-only mode)
  - Camera for first-person capture

## Quick Start (Recommended)

1. Clone and enter the project:

```bash
git clone https://github.com/danielkaijzer/Human-Operator.git
cd Human-Operator
```

2. Create and activate a local virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyserial requests
```

3. Configure environment variables (LLM key):

```bash
cp .env_empty .env
# then edit .env and set:
# ANTHROPIC_API_KEY=your_key_here
```

4. Flash relay firmware to your Arduino-compatible board:

- Open `firmware/human_operator_ems/human_operator_ems.ino`
- Select correct board/port in Arduino IDE
- Upload at 115200 baud serial settings

5. Run full stack in relay-only hardware mode:

```bash
./run_hardware.sh
```

Optional custom relay port:

```bash
RELAY_PORT=/dev/cu.wchusbserial10 ./run_hardware.sh
```

What `run_hardware.sh` does:

- Starts `utils/receiver.py` in `HARDWARE_MODE=relay`
- Waits for `/health`
- Verifies `relay_hardware_connected=true`
- Launches `app.py` with `RECEIVER_URL` set
- Cleans up background receiver process on exit

## Running Modes

### Mode A: Relay-Only (Default and Most Stable)

Use this for reliable relay switching and wiring validation:

```bash
HARDWARE_MODE=relay RELAY_PORT=/dev/cu.usbserial-210 python utils/receiver.py
```

Check health from another terminal:

```bash
curl -sS http://127.0.0.1:5001/health
```

Expected key fields:

- `"hardware_mode": "relay"`
- `"relay_hardware_connected": true`

### Mode B: Full Mode (Relay + Stim)

Enable full stim path explicitly:

```bash
HARDWARE_MODE=full STIM_PORT=/dev/cu.usbserial-XXX RELAY_PORT=/dev/cu.usbserial-YYY python utils/receiver.py
```

Notes:

- Stim is intentionally disabled unless full mode is explicitly enabled.
- If a device shows as `SIMULATED`, that serial port failed to open.

## Main App Runtime

Start the app (if not using `run_hardware.sh`):

```bash
python app.py
```

Runtime flow:

1. Wait for voice command trigger.
2. Capture latest camera frame.
3. Send prompt + image to Claude.
4. Transform action plan into timestamped relay/EMS payload.
5. POST payload to `utils/receiver.py` at `RECEIVER_URL`.

## Manual Calibration GUI

Run:

```bash
python manual_control_app.py
```

Use it to:

- Connect EMS and relay serial ports manually
- Select relay targets (`wrist_left`, `wrist_right`, `thumb`, `index`, `middle`, `ring`, `pinky`, `x`)
- Tune amplitude/frequency/pulse width
- Validate response before autonomous runtime

## Relay Targets and Firmware Mapping

Relay selector commands accepted by receiver/firmware:

- `wrist_left`
- `wrist_right`
- `thumb`
- `index`
- `middle`
- `ring`
- `pinky`
- `x` (all off / isolate)

Firmware pin mapping in `firmware/human_operator_ems/human_operator_ems.ino`:

- D2 -> `wrist_left`
- D4 -> `wrist_right`
- D3 -> `thumb`
- D5 -> `index`
- D6 -> `middle`
- D7 -> `ring`
- D8 -> `pinky`

Firmware serial debug commands:

- `test` to sweep all outputs
- `mode_low` for active-low relay boards
- `mode_high` for active-high relay boards
- `x` to set all outputs off

## API Contract (`utils/receiver.py`)

### `GET /health`

Returns receiver status and hardware connection details.

### `POST /execute`

Accepts timestamp-keyed command dictionaries. Example:

```json
{
  "0.0": [
    {"type": "RELAY", "finger": "index"},
    {"type": "EMS", "channel": 1, "amplitude": 60, "duration": 1.0, "frequency": 100, "pulse_width": 1000}
  ],
  "1.5": [
    {"type": "RELAY", "finger": "x"}
  ]
}
```

## Additional Demo

Ball-triggered avoidance demo:

```bash
python utils/ball_demo.py
```

## Troubleshooting

### Receiver says relay is simulated

- Symptom: `"relay": "SIMULATED"` in `/execute` response or `/health`
- Cause: relay serial port failed to open (busy/wrong port/power issue)
- Fixes:
  - Close Arduino Serial Monitor and any other serial tool
  - Verify correct `RELAY_PORT`
  - Re-run in explicit relay mode:
    - `HARDWARE_MODE=relay RELAY_PORT=/dev/cu.usbserial-210 python utils/receiver.py`

### Receiver starts but no physical relay click

- Run firmware `test` command over serial
- Try `mode_low` and `mode_high`
- Verify relay board power and common ground
- Verify IN pin wiring vs firmware pin map

### Camera cannot be opened

- Confirm camera permissions in macOS privacy settings
- Confirm no other app is locking the camera

### Missing API key / LLM request failures

- Ensure `.env` exists and includes `ANTHROPIC_API_KEY`
- Check network connectivity and Anthropic account access

## System Architecture

```text
app.py
  -> captures camera frame and voice command
  -> asks Claude for action plan
  -> transforms plan into receiver payload
  -> POST /execute to utils/receiver.py

utils/receiver.py (Flask)
  -> validates and executes timestamped sequence
  -> sends relay selector command to Arduino firmware
  -> sends optional EMS/GVS/ET command to stimulator

firmware/human_operator_ems/human_operator_ems.ino
  -> maps symbolic relay targets to physical output pins
```

## Acknowledgments

Inspired by work from the [Human Computer Integration Lab](https://lab.plopes.org/) at UChicago:

- [Full-Hand Electro Tactile Feedback without Obstructing Palmar Side of Hand](https://github.com/humancomputerintegration/BOH-Electro-Tactile)
- [Generative Muscle Stimulation: Providing Users with Physical Assistance by Constraining Multimodal-AI with Embodied Knowledge](https://arxiv.org/pdf/2505.10648)
- [Increasing Electrical Muscle Stimulation's Dexterity by Means of Back-of-Hand Actuation](https://lab.plopes.org/published/2021-CHI-BackHandEMS.pdf)
