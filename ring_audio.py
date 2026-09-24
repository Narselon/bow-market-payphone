import pygame.mixer as aux_mixer
import os

class RingAudio:
    def __init__(self):
        # Initialize a separate mixer for aux output (typically hw:0,0 or default)
        aux_mixer.init(devicename="default")
        self.ring_sound = None
        self.load_ring_sound()
    
    def load_ring_sound(self):
        ring_path = os.path.join("sounds", "ring.mp3")
        if os.path.exists(ring_path):
            self.ring_sound = aux_mixer.Sound(ring_path)
        else:
            print(f"Ring sound file not found at {ring_path}")
    
    def play_ring(self):
        if self.ring_sound:
            self.ring_sound.play()
    
    def stop_ring(self):
        if self.ring_sound:
            self.ring_sound.stop()