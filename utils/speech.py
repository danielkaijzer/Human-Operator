#!/usr/bin/env python3
from RealtimeSTT import AudioToTextRecorder
import pygame
import time
import threading

# Initialize pygame mixer for audio playback
pygame.mixer.init()

TRIGGER_WORD = "hey"
VERIFY_SOUND = "audio/verify.mp3"
SILENCE_THRESHOLD = 0.5  # seconds


class VoiceCommandListener:
    def __init__(self, on_command_ready=None):
        """
        Initialize voice listener.
        
        Args:
            on_command_ready: Callback function called with command string when ready
        """
        self.on_command_ready = on_command_ready
        self.last_speech_time = None
        self.command_buffer = []
        self.triggered = False
        self.recorder = None
        self.silence_timer = None
        self.listening = False
    
    def on_realtime_update(self, text):
        """Real-time transcription feedback"""
        if not self.triggered:
            print(f"[listening] {text}")
    
    def on_realtime_stabilized(self, text):
        """Stabilized real-time transcription"""
        if self.triggered:
            print(f"[command] {text}")
            self.command_buffer.append(text)
            self.last_speech_time = time.time()
            
            # Reset silence timer
            self._reset_silence_timer()
    
    def _reset_silence_timer(self):
        """Reset the silence detection timer"""
        if self.silence_timer:
            self.silence_timer.cancel()
        
        self.silence_timer = threading.Timer(SILENCE_THRESHOLD, self._on_silence_timeout)
        self.silence_timer.start()
    
    def _on_silence_timeout(self):
        """Called when silence timeout is reached"""
        if self.triggered:
            command = " ".join(self.command_buffer)
            print(f"\n[silence detected] {SILENCE_THRESHOLD}s of silence")
            print(f"[command ready] {command}")
            
            # Call callback if registered
            if self.on_command_ready:
                self.on_command_ready(command)
            
            self.triggered = False
            self.command_buffer = []
            self.last_speech_time = None
            self.silence_timer = None
    
    def process_text(self, text):
        """Process transcribed text"""
        text = text.lower().strip()
        
        # Check for trigger word
        if TRIGGER_WORD in text and not self.triggered:
            print(f"\n[✓] Wake word detected! Full text: '{text}'")
            self.triggered = True
            self.command_buffer = []
            
            # Play verify sound
            try:
                sound = pygame.mixer.Sound(VERIFY_SOUND)
                sound.play()
            except Exception as e:
                print(f"[!] Could not play sound: {e}")
            
            # Extract text after trigger word
            trigger_idx = text.find(TRIGGER_WORD)
            after_trigger = text[trigger_idx + len(TRIGGER_WORD):].strip()
            # Remove leading punctuation (comma, period, etc.)
            after_trigger = after_trigger.lstrip(',.!?;:- ')
            
            print(f"[extracted] '{after_trigger}'")
            
            if after_trigger:
                self.command_buffer.append(after_trigger)
            
            self.last_speech_time = time.time()
            self._reset_silence_timer()
    
    def start(self):
        """Start listening for voice commands"""
        print("Initializing AudioToTextRecorder...")
        print(f"Listening for '{TRIGGER_WORD}'...\n")
        
        self.recorder = AudioToTextRecorder(
            model="base",
            language="en",
            enable_realtime_transcription=True,
            use_main_model_for_realtime=False,
            realtime_model_type="tiny",
            silero_use_onnx=True,
            silero_sensitivity=0.6,
            post_speech_silence_duration=0.5,
            on_realtime_transcription_update=self.on_realtime_update,
            on_realtime_transcription_stabilized=self.on_realtime_stabilized,
            no_log_file=True,
            spinner=False
        )
        
        try:
            while True:
                self.recorder.text(self.process_text)
        except KeyboardInterrupt:
            print("\n[*] Stopped")


if __name__ == '__main__':
    listener = VoiceCommandListener()
    listener.start()
