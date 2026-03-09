<p align="left">
  <img src="https://img.shields.io/badge/Winner-MIT%20Hard%20Mode%202026-gold?style=for-the-badge&logo=mit&logoColor=white" alt="MIT Winner Badge">
  <br>
</p>

# HumanOperator
A Human Augmentation Tool for On-Body Intelligence with EMS. Winning project at MIT Hard Mode 2026 for the Learn track.

## Project Setup
**Pre-requisites** – Before we get started, make sure to install the following:
   1. Conda *(or miniconda)*
   2. Python
      * Version **3.10.x**
      * IDE of choice *(e.g. Visual Studio Code)*
   3. Arduino
      * Version **2.3.8** _(other versions will likely also work, although we recommend using the newest version)_
      * Arduino IDE

### Software
HumanOperator is implemented in Python and Arduino. Be sure to confirm that you've met the pre-requisites above before cloning the repository.

Once you've cloned the repository, do the following to configure the system for your computer's **virtual environment**:

1. Open a new terminal and navigate to your Human-Operator repository:
    * cd "local_path/Human-Operator"
    
    2.1 Confirm that the environment file (i.e. **environment.yml**) is present:
    * ls

    2.2 Run the following command to create your virtual environment (i.e. **environment.yml**):
    * conda env create -f environment.yml

    2.3 Activate your virtual environment (i.e. **human-operator**):
    * conda activate human-operator

### Hardware
* **Electrical Muscle Stimulation (EMS) Electrodes**
    * [add]
* **Microcontroller**
    * [add]
* **Camera Module**
    * [add]


## Run HumanOperator

### In Simulation
[coming soon...]

### On Body
1. Activate your **human-operator** virtual environment:
    * conda activate human-operator

2. Add your Claude API key
    2.1 Run the following in the terminal:
      * cp .env_empty .env
    2.2 Open `.env` and add:
      * ANTHROPIC_API_KEY=your_api_key_here


3. Run HumanOperator for **pinky**, **middle**, and **index** _general_ finger control:
    * python app.py

4.  Run HumanOperator for _obstacle avoidance_ demo (e.g. avoiding a _ball_ flying toward the user):
    * python utils/ball_demo.py
