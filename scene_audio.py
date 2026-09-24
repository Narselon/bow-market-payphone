import pygame
import os
import time

class SceneAudio:
    def __init__(self, audio_dir="scene_audio", sounds_dir="sounds"):
        self.audio_dir = audio_dir
        self.sounds_dir = sounds_dir
        self.current_scene_sound = None
        
        # Initialize multiple mixer channels for different audio types
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        try:
            pygame.mixer.init(channels=4)  # Initialize with 4 channels
            print("Audio system initialized successfully")
            
            # Reserve specific channels
            self.beep_channel = pygame.mixer.Channel(0)
            self.scene_channel = pygame.mixer.Channel(1)
            self.keypad_channel = pygame.mixer.Channel(2)
            
        except Exception as e:
            print(f"Error initializing audio system: {e}")
            # Fallback initialization
            try:
                pygame.mixer.init()
                print("Fallback audio initialization successful")
            except Exception as e:
                print(f"Critical audio initialization error: {e}")
        
        # Create directories if they don't exist
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(sounds_dir, exist_ok=True)
        
        # Pre-load common sounds
        self.beep_sound = None
        try:
            beep_path = os.path.join(self.sounds_dir, "beep.mp3")
            if os.path.exists(beep_path):
                self.beep_sound = pygame.mixer.Sound(beep_path)
        except Exception as e:
            print(f"Error loading beep sound: {e}")
    
    def is_playing(self):
        """Check if scene audio is currently playing"""
        try:
            return self.scene_channel.get_busy()
        except Exception as e:
            print(f"Error checking if audio is playing: {e}")
            return False
        
    def play_key_beep(self, *args, **kwargs):
        """Play a short beep sound before scene audio."""
        if kwargs.get('skip_beep', False):
            return
            
        try:
            if self.beep_sound and self.beep_channel:
                # Stop any currently playing beep
                self.beep_channel.stop()
                self.beep_channel.play(self.beep_sound)
                time.sleep(0.1)  # Shorter delay to feel more responsive
        except Exception as e:
            print(f"Error playing beep: {e}")
        
    def play_scene_audio(self, scene_id):
        """Plays audio associated with a scene."""
        try:
            # First stop any currently playing scene audio
            self.scene_channel.stop()
            
            # Special scenes that skip beep
            skip_beep_scenes = ['intro', 'no_numbers_scene']
            
            # Load and play scene audio - removed beep here since keypad already plays it
            audio_path = os.path.join(self.audio_dir, f"{scene_id}.mp3")
            if os.path.exists(audio_path):
                scene_sound = pygame.mixer.Sound(audio_path)
                self.scene_channel.play(scene_sound)
                self.current_scene_sound = scene_id
                print(f"Playing audio for scene: {scene_id}")
            else:
                print(f"Audio file not found for scene: {scene_id}")
                self.current_scene_sound = None
                
        except Exception as e:
            print(f"Error in play_scene_audio: {e}")
            self.current_scene_sound = None
            
    def stop_audio(self):
        """Stops all audio playback"""
        try:
            # Stop all channels
            self.beep_channel.stop()
            self.scene_channel.stop()
            self.keypad_channel.stop()
            self.current_scene_sound = None
        except Exception as e:
            print(f"Error stopping audio: {e}")
