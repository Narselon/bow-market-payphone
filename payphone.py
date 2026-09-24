import RPi.GPIO as GPIO
from datetime import datetime, time as datetime_time  # Rename to avoid conflict
import random
import threading
import pygame
import os
import time  # Add this import
from keypad import GPIO_AVAILABLE
#import keyboard  # Add this import at top
import subprocess
from typing import Optional

# Pin definitions
LIGHT_PIN = 25  # Choose an unused GPIO pin

# Initialize GPIO if available
if GPIO_AVAILABLE:
    GPIO.setup(LIGHT_PIN, GPIO.OUT)
    GPIO.output(LIGHT_PIN, GPIO.LOW)

# Initialize a separate pygame mixer for aux output
pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init(devicename="hw:0,0")  # Use default audio device (aux)

class PayPhone:
    def __init__(self, audio_dir="sounds"):
        try:
            # Define audio device names from pactl output
            self.AUX_DEVICE = "alsa_output.platform-3f00b840.mailbox.stereo-fallback"
            self.AIY_DEVICE = "alsa_output.platform-soc_sound.stereo-fallback"
            
            self.audio_dir = audio_dir
            self.ring_sound = None
            self.adventure_active = False
            self.last_ring_time = time.time()
            self.ring_volume = 1.0
            self.debug_mode = True

            # Setup PulseAudio
            self._setup_pulseaudio()
            
            # Initialize mixer for AUX
            self._init_mixer()
            
            self.load_sounds()
            print("Creating ring thread...")
            self.ring_thread = threading.Thread(target=self._random_ring_controller, daemon=True)
            self.ring_thread.start()
            print("Ring thread started successfully")
            print("Debug mode active - Press 'r' key to test ring")
        except Exception as e:
            print(f"Error in PayPhone initialization: {e}")
            import traceback
            traceback.print_exc()

    def _setup_pulseaudio(self):
        """Setup PulseAudio configuration"""
        try:
            # Switch to AUX by default
            self._switch_audio_output(self.AUX_DEVICE)
            print(f"Initial audio setup: {self.AUX_DEVICE}")
        except Exception as e:
            print(f"PulseAudio setup error: {e}")

    def _switch_audio_output(self, sink_name: str) -> None:
        """Switch PulseAudio output device"""
        try:
            time.sleep(0.5)
            result = subprocess.run(
                ["pactl", "set-default-sink", sink_name],
                check=False,  # Don't raise exception
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"Switched audio to {sink_name}")
            else:
                print(f"Error switching to {sink_name}: {result.stderr}")
                
        except Exception as e:
            print(f"Error in audio switch: {e}")

    def _init_mixer(self):
        """Initialize pygame mixer"""
        try:
            print("Attempting to quit mixer...")
            pygame.mixer.quit()
            print("Mixer quit successfully")
            print("Pre-initializing mixer...")
            pygame.mixer.pre_init(44100, -16, 2, 2048)
            print("Mixer pre-init successful")
            print("Initializing mixer...")
            pygame.mixer.init()
            print("Mixer initialized successfully")
        except Exception as e:
            print(f"Mixer initialization error: {e}")
            import traceback
            traceback.print_exc()

    def load_sounds(self):
        """Load the ring sound file"""
        ring_path = os.path.join(self.audio_dir, "ring.mp3")
        if os.path.exists(ring_path):
            try:
                self.ring_sound = pygame.mixer.Sound(ring_path)
                self.ring_sound.set_volume(self.ring_volume)
                print(f"Ring sound loaded from {ring_path}")
            except Exception as e:
                print(f"Error loading ring sound: {e}")
        else:
            print(f"Ring sound not found at {ring_path}")

    def set_light(self, state):
        """Control the payphone light"""
        if GPIO_AVAILABLE:
            GPIO.output(LIGHT_PIN, state)

    def play_ring(self, duration=3):
        """Play the ring sound and control light"""
        if self.ring_sound:
            print("Attempting to play ring sound on aux...")
            self.set_light(GPIO.HIGH)
            self.ring_sound.play()
            time.sleep(duration)
            self.ring_sound.stop()
            self.set_light(GPIO.LOW)
            print("Ring sound completed")

    def _random_ring_controller(self):
        """Background thread to handle random ringing"""
        while True:
            now = datetime.now().time()
            current_time = time.time()
            
            # Debug output
            if datetime_time(14,0) <= now <= datetime_time(17,0):
                print(f"Current time {now} is within ring window")
            
            # Only ring between 2 PM and 5 PM
            if (datetime_time(14,0) <= now <= datetime_time(17,0) and 
                not self.adventure_active and
                current_time - self.last_ring_time >= 300):  # At least 5 minutes since last ring
                
                if random.random() < 0.3:  # Increase chance to 30%
                    print("Triggering random ring...")
                    self.play_ring()
                    self.last_ring_time = current_time
                
            time.sleep(60)  # Check every minute

    def _debug_ring_trigger(self, _):
        """Debug method to trigger ring manually"""
        if self.debug_mode and not self.adventure_active:
            print("Manual ring triggered")
            self.play_ring()

    def start_adventure(self):
        """Switch to AIY speaker when adventure starts"""
        self.adventure_active = True
        self.set_light(GPIO.HIGH)
        self._switch_audio_output(self.AIY_DEVICE)

    def stop_adventure(self):
        """Switch back to AUX for ringing"""
        self.adventure_active = False
        self.set_light(GPIO.LOW)
        self._switch_audio_output(self.AUX_DEVICE)
        self.load_sounds()

# Create a global instance
payphone = PayPhone()