from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, 
                            QSlider, QLineEdit, QHBoxLayout, QRadioButton, 
                            QButtonGroup, QGridLayout, QGroupBox, QSizePolicy, QMessageBox)
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import serial
import sys
import os
import time
from datetime import datetime

from hcint_estim import *

class StimulationGUI(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle('HUMAN OPERATOR')
        self.setGeometry(100, 100, 1440, 810)  
        
        # Apply global application dark/black-and-white futuristic style
        self.setStyleSheet("""
            QWidget {
                background-color: #0A0A0A;
                color: #FFFFFF;
                font-family: "Orbitron", "OCR A Extended", "Consolas", monospace;
                text-transform: uppercase;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 0px;
                margin-top: 2ex;
                font-weight: bold;
                letter-spacing: 2px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                color: #FFFFFF;
                background-color: #0A0A0A;
            }
            QLabel {
                color: #FFFFFF;
                letter-spacing: 1px;
            }
            QLineEdit {
                background-color: #000000;
                color: #FFFFFF;
                border: 1px solid #FFFFFF;
                border-radius: 0px;
                padding: 4px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 2px solid #FFFFFF;
                background-color: #1A1A1A;
            }
            QSlider::groove:horizontal {
                border: 1px solid #333333;
                height: 4px;
                background: #111111;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 1px solid #FFFFFF;
                width: 14px;
                margin: -10px 0;
                border-radius: 0px; /* Square handles for sci-fi look */
            }
            QSlider::handle:horizontal:hover {
                background: #CCCCCC;
            }
            QRadioButton {
                color: #FFFFFF;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border-radius: 0px;
                border: 1px solid #FFFFFF;
                background-color: #000000;
            }
            QRadioButton::indicator:checked {
                background-color: #FFFFFF;
            }
        """)

        # Initialize hardware connections
        self.stimulator = None
        self.relay_serial = None
        
        self.initUI()
        
    def initUI(self):
        layout = QGridLayout()
        layout.setContentsMargins(15, 80, 15, 15)
        layout.setColumnStretch(0, 4)  # Left side (waveform, sliders) takes 4 parts
        layout.setColumnStretch(1, 1)  # Right side takes 1 part

        # Create a placeholder for the waveform and integrate with matplotlib
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFixedSize(1130, 300) 

        layout.addWidget(self.canvas, 0, 0, 1, 1)

        # ---------------------------------------------------------
        # RIGHT PANEL CONSOLIDATION
        # ---------------------------------------------------------
        right_panel_layout = QVBoxLayout()

        # 1. Main Control Buttons 
        self.stim_btn_default_style = """
            QPushButton { background-color: #FFFFFF; color: #000000; border-radius: 0px; padding: 10px; font-size: 26px; font-weight: bold; border: none; letter-spacing: 2px;}
            QPushButton:hover { background-color: #CCCCCC; }
            QPushButton:pressed { background-color: #999999; }
        """
        self.stimulation_btn = QPushButton("START")
        self.stimulation_btn.setStyleSheet(self.stim_btn_default_style)
        self.stimulation_btn.setFixedHeight(100)
        self.stimulation_btn.clicked.connect(self.start_stimulation)

        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setStyleSheet("""
            QPushButton { background-color: #000000; color: #FFFFFF; border-radius: 0px; padding: 10px; font-size: 26px; border: 2px solid #FFFFFF; font-weight: bold; letter-spacing: 2px;}
            QPushButton:hover { background-color: #111111; border: 2px solid #FFFFFF; color: #FFFFFF; }
            QPushButton:pressed { background-color: #333333; }
        """)
        self.stop_btn.setFixedHeight(100)
        self.stop_btn.clicked.connect(self.stop_stimulation)

        # Layout for Save and Reset side-by-side
        save_reset_layout = QHBoxLayout()
        utility_btn_style = """
            QPushButton { background-color: #111111; color: #FFFFFF; border-radius: 0px; padding: 5px; font-size: 18px; border: 1px solid #FFFFFF; }
            QPushButton:hover { background-color: #222222; }
            QPushButton:pressed { background-color: #000000; }
        """
        
        self.save_btn = QPushButton("SAVE CONFIG")
        self.save_btn.setStyleSheet(utility_btn_style)
        self.save_btn.setFixedHeight(50)
        self.save_btn.clicked.connect(self.save_settings)

        self.reset_btn = QPushButton("RESET")
        self.reset_btn.setStyleSheet(utility_btn_style)
        self.reset_btn.setFixedHeight(50)
        self.reset_btn.clicked.connect(self.reset_settings)
        
        save_reset_layout.addWidget(self.save_btn)
        save_reset_layout.addWidget(self.reset_btn)

        right_panel_layout.addWidget(self.stimulation_btn)
        right_panel_layout.addWidget(self.stop_btn)
        right_panel_layout.addLayout(save_reset_layout)
        right_panel_layout.addSpacing(10)

        # 2. Stimulator Serial Configuration
        stim_serial_group = QGroupBox("EMS")
        stim_serial_group.setStyleSheet("font-size: 16px;")
        stim_serial_layout = QVBoxLayout()
        
        stim_port_layout = QHBoxLayout()
        stim_port_layout.addWidget(QLabel("PORT:"))
        self.port_text = QLineEdit("/dev/ttyUSB0")
        self.port_text.setStyleSheet("font-size: 14px; font-weight: normal;")
        stim_port_layout.addWidget(self.port_text)
        
        stim_baud_layout = QHBoxLayout()
        stim_baud_layout.addWidget(QLabel("BAUD:"))
        self.baud_text = QLineEdit("115200")
        self.baud_text.setStyleSheet("font-size: 14px; font-weight: normal;")
        stim_baud_layout.addWidget(self.baud_text)
        
        self.connect_btn_default_style = """
            QPushButton { background-color: #111111; color: #FFFFFF; border-radius: 0px; padding: 5px; font-size: 16px; border: 1px solid #FFFFFF; font-weight: normal;}
            QPushButton:hover { background-color: #222222; }
            QPushButton:pressed { background-color: #000000; }
        """
        self.connect_btn_active_style = """
            QPushButton { background-color: #FFFFFF; color: #000000; border-radius: 0px; padding: 5px; font-size: 16px; border: none; font-weight: bold;}
        """
        
        self.connect_btn = QPushButton("CONNECT STIMULATORS")
        self.connect_btn.setStyleSheet(self.connect_btn_default_style)
        self.connect_btn.setFixedHeight(40)
        self.connect_btn.clicked.connect(self.connect_to_serial)

        stim_serial_layout.addLayout(stim_port_layout)
        stim_serial_layout.addLayout(stim_baud_layout)
        stim_serial_layout.addWidget(self.connect_btn)
        stim_serial_group.setLayout(stim_serial_layout)
        right_panel_layout.addWidget(stim_serial_group)

        # 3. Relay MCU Serial Configuration
        relay_serial_group = QGroupBox("RELAYS")
        relay_serial_group.setStyleSheet("font-size: 16px;")
        relay_serial_layout = QVBoxLayout()
        
        relay_port_layout = QHBoxLayout()
        relay_port_layout.addWidget(QLabel("PORT:"))
        self.relay_port_text = QLineEdit("/dev/ttyACM0")
        self.relay_port_text.setStyleSheet("font-size: 14px; font-weight: normal;")
        relay_port_layout.addWidget(self.relay_port_text)
        
        relay_baud_layout = QHBoxLayout()
        relay_baud_layout.addWidget(QLabel("BAUD:"))
        self.relay_baud_text = QLineEdit("115200")
        self.relay_baud_text.setStyleSheet("font-size: 14px; font-weight: normal;")
        relay_baud_layout.addWidget(self.relay_baud_text)
        
        self.connect_relay_btn = QPushButton("CONNECT RELAYS")
        self.connect_relay_btn.setStyleSheet(self.connect_btn_default_style)
        self.connect_relay_btn.setFixedHeight(40)
        self.connect_relay_btn.clicked.connect(self.connect_to_relay_serial)

        relay_serial_layout.addLayout(relay_port_layout)
        relay_serial_layout.addLayout(relay_baud_layout)
        relay_serial_layout.addWidget(self.connect_relay_btn)
        relay_serial_group.setLayout(relay_serial_layout)
        right_panel_layout.addWidget(relay_serial_group)

        # 4. Relay Control Buttons
        relay_control_group = QGroupBox("FINGER CONNECTIONS")
        relay_control_group.setStyleSheet("font-size: 16px;")
        relay_control_layout = QGridLayout()
        
        relay_btn_style = """
            QPushButton { background-color: #000000; color: #FFFFFF; border-radius: 0px; padding: 10px; font-size: 14px; border: 1px solid #FFFFFF; font-weight: normal;}
            QPushButton:hover { background-color: #222222;}
            QPushButton:pressed { background-color: #444444; }
            QPushButton:checked { background-color: #FFFFFF; color: #000000; font-weight: bold; }
        """
        
        self.btn_pinky = QPushButton("PINKY (P)")
        self.btn_pinky.setStyleSheet(relay_btn_style)
        self.btn_pinky.setCheckable(True)
        self.btn_pinky.clicked.connect(lambda: self.send_relay_command('p'))
        
        self.btn_middle = QPushButton("MIDDLE (M)")
        self.btn_middle.setStyleSheet(relay_btn_style)
        self.btn_middle.setCheckable(True)
        self.btn_middle.clicked.connect(lambda: self.send_relay_command('m'))
        
        self.btn_index = QPushButton("INDEX (I)")
        self.btn_index.setStyleSheet(relay_btn_style)
        self.btn_index.setCheckable(True)
        self.btn_index.clicked.connect(lambda: self.send_relay_command('i'))
        
        self.btn_all_off = QPushButton("ISOLATE (X)")
        self.btn_all_off.setStyleSheet("""
            QPushButton { background-color: #FFFFFF; color: #000000; border-radius: 0px; padding: 10px; font-size: 14px; border: none; font-weight: bold;}
            QPushButton:hover { background-color: #CCCCCC; }
            QPushButton:pressed { background-color: #999999; }
        """)
        self.btn_all_off.clicked.connect(self.isolate_relays)

        relay_control_layout.addWidget(self.btn_pinky, 0, 0)
        relay_control_layout.addWidget(self.btn_middle, 0, 1)
        relay_control_layout.addWidget(self.btn_index, 1, 0)
        relay_control_layout.addWidget(self.btn_all_off, 1, 1)
        
        relay_control_group.setLayout(relay_control_layout)
        right_panel_layout.addWidget(relay_control_group)

        right_panel_layout.addStretch(1)
        layout.addLayout(right_panel_layout, 0, 1, 8, 1)

        # ---------------------------------------------------------
        # LEFT PANEL (Sliders and Toggles)
        # ---------------------------------------------------------
        vertical_layout = QVBoxLayout()
        vertical_layout.addSpacing(20)

        # Channel selection
        channel_layout = QHBoxLayout()
        channel_label = QLabel("TARGET CHANNEL")
        channel_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        channel_label.setFixedWidth(300)

        self.channel_buttons = QButtonGroup(self)
        channel_options = [("CH 01", True, 1), ("CH 02", False, 2)]
        for text, checked, value in channel_options:
            rb = QRadioButton(text)
            rb.setChecked(checked)
            rb.setProperty("value", value)
            rb.setStyleSheet("font-size: 20px;")
            self.channel_buttons.addButton(rb)
            channel_layout.addWidget(rb)
            channel_layout.addStretch(1)

        full_channel_layout = QHBoxLayout()
        full_channel_layout.addWidget(channel_label)
        full_channel_layout.addLayout(channel_layout)

        vertical_layout.addLayout(full_channel_layout)
        vertical_layout.addSpacing(20)

        # Add sliders with text boxes (Hardcoded bounds for EMS)
        self.sliders = {}
        slider_specs = [
            ("AMPLITUDE", 0, 60, 20, "mA x10"),
            ("PULSE WIDTH", 0, 1000, 300, "μs"),
            ("FREQUENCY", 0, 100, 100, "Hz"),
            ("DURATION", 0, 10000, 1000, "ms")
        ]
        max_slider_width = 680
        
        for name, min_val, max_val, init_val, unit in slider_specs:
            container = QWidget()
            slider_layout = QHBoxLayout(container)
            
            display_name = f"{name} ({unit})"
            slider_label = QLabel(display_name)
            slider_label.setStyleSheet("font-size: 20px; font-weight: bold;")
            slider_label.setFixedWidth(300)
            
            slider = QSlider(Qt.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(init_val)
            slider.setFixedWidth(max_slider_width)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval((max_val - min_val) // 10)
            
            value_box = QLineEdit()
            value_box.setFixedWidth(100)
            value_box.setStyleSheet("font-size: 20px; text-align: center;")
            value_box.setText(str(init_val))
            value_box.setReadOnly(False)
            
            slider.valueChanged.connect(lambda value, box=value_box: box.setText(str(value)))
            slider.valueChanged.connect(self.update_waveform)
            value_box.returnPressed.connect(lambda box=value_box, s=slider: self.update_slider_from_textbox(box, s))
            
            slider_layout.addWidget(slider_label)
            slider_layout.addSpacing(20)
            slider_layout.addWidget(slider)
            slider_layout.addWidget(value_box)
            
            vertical_layout.addWidget(container)
            
            self.sliders[name] = {
                'slider': slider,
                'textbox': value_box,
                'min': min_val,
                'max': max_val,
                'unit': unit
            }

        vertical_layout.addStretch(1)
        layout.addLayout(vertical_layout, 1, 0, 6, 1)
        
        self.setLayout(layout)
        self.update_waveform() 

    # ---------------------------------------------------------
    # RELAY SERIAL METHODS
    # ---------------------------------------------------------
    def connect_to_relay_serial(self):
        try:
            port = self.relay_port_text.text().strip()
            baudrate = int(self.relay_baud_text.text().strip())
            
            if self.relay_serial and self.relay_serial.is_open:
                self.relay_serial.close()
                
            self.relay_serial = serial.Serial(port, baudrate, timeout=1)
            time.sleep(1.5) 
            
            self.connect_relay_btn.setText("RELAYS LINKED")
            self.connect_relay_btn.setStyleSheet(self.connect_btn_active_style)
            
        except (serial.SerialException, ValueError) as e:
            QMessageBox.critical(self, "LINK FAILED", f"Failed to connect to relay MCU: {str(e)}")
            self.connect_relay_btn.setText("INITIALIZE RELAYS")
            self.connect_relay_btn.setStyleSheet(self.connect_btn_default_style)
            self.relay_serial = None

    def send_relay_command(self, cmd):
        if self.relay_serial and self.relay_serial.is_open:
            try:
                self.relay_serial.write(cmd.encode('utf-8'))
            except serial.SerialException as e:
                QMessageBox.critical(self, "LINK LOST", f"Connection to Relay MCU dropped: {str(e)}")
                self.relay_serial.close()
                self.relay_serial = None
                self.connect_relay_btn.setText("INITIALIZE RELAYS")
                self.connect_relay_btn.setStyleSheet(self.connect_btn_default_style)
        else:
            QMessageBox.warning(self, "OFFLINE", "Awaiting relay initialization.")

    def isolate_relays(self):
        # Visually uncheck the finger buttons
        self.btn_pinky.setChecked(False)
        self.btn_middle.setChecked(False)
        self.btn_index.setChecked(False)
        
        # Send the isolation command to the MCU
        self.send_relay_command('x')

    # ---------------------------------------------------------
    # STIMULATION CONTROL METHODS
    # ---------------------------------------------------------
    def update_slider_from_textbox(self, textbox, slider):
        try:
            value = int(textbox.text())
            min_val = slider.minimum()
            max_val = slider.maximum()
            
            if min_val <= value <= max_val:
                slider.setValue(value)
                self.update_waveform()  
            else:
                textbox.setText(str(slider.value()))
        except ValueError:
            textbox.setText(str(slider.value()))

    def get_channel(self):
        for button in self.channel_buttons.buttons():
            if button.isChecked():
                return button.property("value")
        return 1  

    def connect_to_serial(self):
        try:
            port = self.port_text.text().strip()
            baudrate = int(self.baud_text.text().strip())
            
            if self.stimulator:
                self.stimulator.close()
                
            self.stimulator = HCIntEstim(port, baudrate)
            self.connect_btn.setText("STIMULATOR LINKED")
            self.connect_btn.setStyleSheet(self.connect_btn_active_style)
            
        except (ConnectionError, ValueError, serial.SerialException) as e:
            QMessageBox.critical(self, "LINK FAILED", f"Failed to connect: {str(e)}")
            self.connect_btn.setText("INITIALIZE LINK")
            self.connect_btn.setStyleSheet(self.connect_btn_default_style)
            self.stimulator = None

    def start_stimulation(self):
        if not self.stimulator:
            QMessageBox.warning(self, "OFFLINE", "Awaiting stimulator initialization.")
            return
            
        try:
            channel = self.get_channel()
            amplitude = self.sliders["AMPLITUDE"]["slider"].value()
            frequency = self.sliders["FREQUENCY"]["slider"].value()
            pulse_width = self.sliders["PULSE WIDTH"]["slider"].value()
            duration_ms = self.sliders["DURATION"]["slider"].value()
            duration_sec = duration_ms / 1000.0  
            
            # Executing EMS stimulation
            self.stimulator.stim_ems(
                channel=channel, amplitude=amplitude, freq=frequency,
                pulse_width=pulse_width, duration=duration_sec
            )
                
            self.stimulation_btn.setText("TRANSMITTING...")
            self.stimulation_btn.setStyleSheet("""
                QPushButton { background-color: #111111; color: #FFFFFF; border-radius: 0px; padding: 10px; font-size: 26px; border: 2px dashed #FFFFFF; font-weight: bold; letter-spacing: 2px;}
            """)
            
        except Exception as e:
            QMessageBox.critical(self, "TRANSMIT ERROR", f"Failed to start stimulation: {str(e)}")

    def stop_stimulation(self):
        if not self.stimulator:
            return
            
        try:
            self.stimulator.send_command("stop")
            self.stimulation_btn.setText("START")
            self.stimulation_btn.setStyleSheet(self.stim_btn_default_style)
            
        except Exception as e:
            QMessageBox.critical(self, "ABORT ERROR", f"Failed to stop stimulation: {str(e)}")

    def save_settings(self):
        try:
            if not os.path.exists("settings"):
                os.makedirs("settings")
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"settings/human_operator_cfg_{timestamp}.txt"
            
            with open(filename, "w") as f:
                f.write(f"SYSTEM: HUMAN OPERATOR\n")
                f.write(f"MODE: EMS\n")
                f.write(f"CHANNEL: {self.get_channel()}\n")
                f.write(f"FREQUENCY: {self.sliders['FREQUENCY']['slider'].value()} Hz\n")
                f.write(f"PULSE WIDTH: {self.sliders['PULSE WIDTH']['slider'].value()} μs\n")
                f.write(f"POLARITY: BIPHASIC\n")  
                f.write(f"AMPLITUDE: {self.sliders['AMPLITUDE']['slider'].value()} {self.sliders['AMPLITUDE']['unit']}\n")
                f.write(f"DURATION: {self.sliders['DURATION']['slider'].value()} ms\n")
                
            QMessageBox.information(self, "DATA SAVED", f"Configuration dumped to {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "I/O ERROR", f"Failed to write configuration: {str(e)}")

    def reset_settings(self):
        for button in self.channel_buttons.buttons():
            if button.property("value") == 1:
                button.setChecked(True)
                break
        
        self.sliders["AMPLITUDE"]["slider"].setValue(20)
        self.sliders["PULSE WIDTH"]["slider"].setValue(300)
        self.sliders["FREQUENCY"]["slider"].setValue(100)
        self.sliders["DURATION"]["slider"].setValue(1000)
        
        self.update_waveform()

    def update_waveform(self):
        try:
            amplitude = self.sliders["AMPLITUDE"]["slider"].value()/10
            frequency = self.sliders["FREQUENCY"]["slider"].value()
            pulse_width = self.sliders["PULSE WIDTH"]["slider"].value() / 1000.0  
            duration = self.sliders["DURATION"]["slider"].value()  
            
            self.figure.clear()
            self.figure.subplots_adjust(left=0.07, right=0.95, top=0.85, bottom=0.2)
            ax = self.figure.add_subplot(111)
            
            # --- Dark Mode / Sci-Fi Adjustments for Matplotlib ---
            self.figure.patch.set_facecolor('#0A0A0A') 
            ax.set_facecolor('#000000') 
            ax.tick_params(colors='#FFFFFF') 
            ax.xaxis.label.set_color('#FFFFFF')
            ax.yaxis.label.set_color('#FFFFFF')
            ax.title.set_color('#FFFFFF')
            
            for spine in ax.spines.values():
                spine.set_edgecolor('#FFFFFF')
                spine.set_linewidth(1.5)
            # --------------------------------------------

            # EMS Biphasic Waveform Generation
            time_arr = np.linspace(0, duration, 10000)
            period = 1000.0 / frequency if frequency > 0 else float('inf')  
            waveform = np.zeros_like(time_arr)
            
            if period > 0 and period != float('inf'):
                biphasic_waveform = np.zeros_like(time_arr)
                for i in range(len(time_arr)):
                    if (time_arr[i] % period) < pulse_width:
                        biphasic_waveform[i] = amplitude
                    elif (time_arr[i] % period) < pulse_width*2:
                        biphasic_waveform[i] = -amplitude
                waveform = biphasic_waveform
            
            max_y = self.sliders["AMPLITUDE"]["slider"].maximum() * 1.1/10 
            ax.set_ylim(-max_y, max_y)  
            
            period = 1000.0 / frequency if frequency > 0 else 0
            time_for_5_periods = 5 * period  

            if frequency > 0 and duration > time_for_5_periods:
                ax.set_xlim(0, time_for_5_periods)
            else:
                ax.set_xlim(0, duration) 
            
            # Matplotlib doesn't automatically load custom system fonts easily without manual font cache mapping,
            # so standardizing on 'monospace' keeps the aesthetic consistent across machines.
            font_dict = {'family': 'monospace', 'weight': 'bold'}
            
            ax.set_xlabel('TIME (MS)', fontdict=font_dict, fontsize=12)
            ax.set_ylabel('AMPLITUDE (mA)', fontdict=font_dict, fontsize=12)
            
            ax.set_title("HUMAN OPERATOR", fontdict=font_dict, fontsize=24, pad=15)
            
            # Subtle gridlines
            ax.grid(True, linestyle='-', color='#222222', alpha=1.0)
            
            # Bright white plotting line for maximum contrast
            ax.step(time_arr, waveform, color='#FFFFFF', linewidth=2.5, where='post')
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating waveform: {e}")
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            self.figure.patch.set_facecolor('#0A0A0A')
            ax.set_facecolor('#000000')
            ax.text(0.5, 0.5, f"SIGNAL RENDER FAILURE: {str(e)}", 
                    horizontalalignment='center', verticalalignment='center', color='white', 
                    family='monospace', weight='bold')
            self.canvas.draw()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = StimulationGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()