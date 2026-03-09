<p align="left">
  <img src="https://img.shields.io/badge/Winner-MIT%20Hard%20Mode%202026-gold?style=for-the-badge&logo=mit&logoColor=white" alt="MIT Winner Badge">
  <br>
</p>


# HumanOperator
![wytDSC00747](https://github.com/user-attachments/assets/70bae2e8-b78c-4ce7-b910-94a5cd008b63)

A Human Augmentation Tool for On-Body Intelligence with EMS. Winning project at MIT Hard Mode 2026 for the Learn track.

### Team
- **Peter He** - [Portfolio](https://peterhe.dev) | [Github](https://github.com/molegod) | [Linkedin](https://www.linkedin.com/in/ph475/)
- **Valdemar Danry** - [Portfolio]() | [Github]() | [Linkedin]()
- **Daniel Kaijzer** - [Portfolio]() | [Github]() | [Linkedin]() 
- **Yutong Wu** - [Portfolio]() | [Github]() | [Linkedin]() 
- **Ashley Neall** - [Portfolio]() | [Github]() | [Linkedin]()
- **Sean Lewis** - [Portfolio]() | [Github]() | [Linkedin]() 



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

#### Human Operator Wearable:
* **Electrical Muscle Stimulation (EMS) Electrodes**
    * [Normal TENS Unit Gel Electrodes](https://www.amazon.com/dp/B0BL2HR17G?th=1)
    
* **Microcontroller**
    * Arduino Micro Based Board for Relay.
    
* **Relays**
    * [5V Relays](https://www.amazon.com/dp/B09G6H7JDT)
    * A photomosfet may be better suited for switching but these relays do work as well but slower.
    
* **TENS/EMS Unit**
    * A custom board was used, but any TENS/EMS unit that is controllable to be on and off electronically can be used to replicate this project. Modifications may be needed for them to be controlled electronically. 

### Glasses
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
  
## Thanks
Shoutout to the HCI Group at UChicago for their papers and software systems that inspired a lot of our work (and electrode placement)

