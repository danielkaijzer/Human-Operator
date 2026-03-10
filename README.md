<p align="left">
  <img src="https://img.shields.io/badge/Winner-MIT%20Hard%20Mode%202026-gold?style=for-the-badge&logo=mit&logoColor=white" alt="MIT Winner Badge">
  <img src="https://img.shields.io/badge/Watch-YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="Video">
</p>
<p align="center">
  <img width="1200" height="628" alt="Human Operator" src="https://github.com/user-attachments/assets/581d8f0a-ff4f-443f-bf0b-99a2538cd598" />
</p>
A Human Augmentation Tool for On-Body Intelligence with EMS. Winning project at MIT Hard Mode 2026 for the Learn track.

# Human Operator

**Human Operator** is a human augmentation tool that allows AI to briefly take control of your body to help you learn and do things you normally cannot do. To do this, it uses a Vision-Language Model for human motor control through Electrical Muscle Stimulation (EMS). Vision-based commands are generated via open-ended speech input through the Claude API to control finger and wrist stimulation for intuitive on-body interaction.

**:trophy: Winning project at MIT Hard Mode 2026 (Learn Track) :trophy:**

<div align="center">
  <img src="https://github.com/user-attachments/assets/2b088e69-b861-4d76-951c-7a69cf5c6d5c" width="32%" alt="AI makes hand wave" />
  <!--img src="https://github.com/user-attachments/assets/ef0a94e8-5e5c-4ef3-a405-54e7458c02cf" width="32%" alt="AI makes index move" /-->
  <img src="https://github.com/user-attachments/assets/366eef6b-59c4-4773-bbd3-4310cee81fad" width="32%" alt="AI makes hand play piano" />
  <img src="https://github.com/user-attachments/assets/483c7c5d-858b-47a7-a765-e2fee5f27b1a" width="32%" alt="AI makes hand do 'OK' sign"/>
  <p><sub>Left to right: AI stimulates wrist muscle to say 'Hello' back • AI stimulates fingers in sequence to play melody • AI stimulates fingers to form 'OK' sign</sub></p>
</div>

[Watch Full Video Demo](https://www.youtube.com/watch?v=JpiPKwkBz4c)

## Team
- **Peter He** – [Portfolio](https://peterhe.dev) | [GitHub](https://github.com/molegod) | [LinkedIn](https://www.linkedin.com/in/ph475/)
- **Ashley Neall** – [Portfolio](https://aneall.github.io/) | [GitHub](https://github.com/aneall) | [LinkedIn](https://www.linkedin.com/in/ashley-neall/)
- **Valdemar Danry** – [Portfolio](https://valdemardanry.com) | [GitHub](https://github.com/valleballe) | [LinkedIn](https://www.linkedin.com/in/valdemar-danry)
- **Daniel Kaijzer** - [Portfolio]() | [Github](https://github.com/danielkaijzer) | [Linkedin](https://www.linkedin.com/in/danielkaijzer/) 
- **Yutong Wu** - [Portfolio]() | [Github](https://github.com/ichbinHallie0426) | [Linkedin](https://www.linkedin.com/in/yutong-wu-4b66661b5/) 
- **Sean Lewis** - [Portfolio](https://seanhardestylewis.com/) | [Github](https://github.com/seanhlewis) | [Linkedin](https://www.linkedin.com/in/seanhardestylewis/) 

## Prerequisites

- **Python 3.10.x**
- **Conda**, **Miniconda** or other environment setup
- **Arduino IDE 2.3.x** (for firmware setup)
- **Claude API key** (from Anthropic)

## Hardware Setup

### Components

**EMS & Control:**
- [TENS/EMS Gel Electrodes](https://www.amazon.com/dp/B0BL2HR17G?th=1)
- Arduino-compatible microcontroller (Arduino Micro recommended)
- [5V Relays](https://www.amazon.com/dp/B09G6H7JDT) for finger control (pinky, middle, index)
- Custom or commercial TENS/EMS unit with electronic control capability

**Sensing:**
- Camera module (integrated or USB) for POV video capture

## Software Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Human-Operator
   ```

2. **Create Python environment:**
   ```bash
   conda env create -f environment.yml
   conda activate human-operator
   ```

3. **Configure API key:**
   ```bash
   cp .env_empty .env
   # Edit .env and add your Anthropic API key:
   # ANTHROPIC_API_KEY=your_api_key_here
   ```

4. **Upload Arduino firmware:**
   - Open Arduino IDE
   - Load `firmware/human_operator_ems/human_operator_ems.ino`
   - Upload to your Arduino board
   - Verify serial communication works (115200 baud)

## Running the Application

### Main Application

Start the real-time EMS control system:

```bash
python app.py
```

This launches:
- **Video capture** from your camera
- **AI processing** via Claude API for vision-based motor commands
- **Hardware control** for EMS stimulation of pinky, middle, and index fingers
- **Voice trigger** ("Hey Operator") to activate commands

Commands are triggered by physical interaction detected in your POV video.

### Manual Stimulation GUI

Test and calibrate EMS parameters with the GUI:

```bash
python utils/stimGUIfingersHardMode.py
```

This tool allows you to:
- Manually trigger finger stimulation (pinky, middle, index)
- Adjust amplitude, frequency, and pulse width
- Visualize stimulation parameters in real-time
- Perfect for hardware calibration and testing

## System Architecture

```
app.py (Main Application)
    ├── Video Capture (OpenCV)
    ├── Vision-Language Model (Claude API)
    ├── Command Planning (Motor control sequences)
    └── Hardware Interface (receiver.py)
         └── Flask Server (receiver.py)
              └── Serial Communication → Arduino Firmware
                   └── Relay Control (Finger EMS)

stimGUIfingersHardMode.py (Manual Testing GUI)
    └── Direct Hardware Interface (PyQt5 + Serial)
```


## Additional Demo: Obstacle Avoidance

Run a ball-detection demo that triggers avoidance responses:

```bash
python utils/ball_demo.py
```


## Troubleshooting

**Arduino not detected:**
- Check USB cable connection
- Verify correct board selection in Arduino IDE
- Confirm serial port settings (115200 baud)

**No camera detected:**
- Verify camera permissions (especially on macOS)

**Missing API key:**
- Ensure `.env` file exists in the root directory
- Verify `ANTHROPIC_API_KEY` is correctly set


## Acknowledgments

Inspired by research and systems from the [Human Computer Integration Lab](https://lab.plopes.org/) at UChicago on neuromuscular interfaces and electrode placement optimization:
* [Full-Hand Electro Tactile Feedback without Obstructing Palmar Side of Hand](https://github.com/humancomputerintegration/BOH-Electro-Tactile)
* [Generative Muscle Stimulation: Providing Users with Physical Assistance by Constraining Multimodal-AI with Embodied Knowledge](https://arxiv.org/pdf/2505.10648)
* [Increasing Electrical Muscle Stimulation’s Dexterity by means of
Back of the Hand Actuation](https://lab.plopes.org/published/2021-CHI-BackHandEMS.pdf)