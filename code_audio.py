import os
import time
import pygame


def play_code(code, channel, audio_dir="digit_audio", gap=0.15):
    """Plays each digit of `code` in sequence on the given pygame Channel.
    `channel` should be a channel not used for anything else at the time
    (e.g. reuse scene_audio's scene_channel while no scene audio is playing).
    """
    for digit in code:
        path = os.path.join(audio_dir, f"{digit}.mp3")
        if not os.path.exists(path):
            print(f"Missing digit audio file: {path}")
            continue
        try:
            sound = pygame.mixer.Sound(path)
            channel.play(sound)
            while channel.get_busy():
                time.sleep(0.05)
            time.sleep(gap)
        except Exception as e:
            print(f"Error playing digit '{digit}': {e}")

def play_code_sequence(pre_audio, code, post_audio, channel):
    """Plays a sequence of audio clips: pre_audio, code digits, and post_audio."""
    if pre_audio:
        pre_path = os.path.join("scene_audio", f"{pre_audio}.mp3")
        if os.path.exists(pre_path):
            try:
                pre_sound = pygame.mixer.Sound(pre_path)
                channel.play(pre_sound)
                while channel.get_busy():
                    time.sleep(0.05)
            except Exception as e:
                print(f"Error playing pre_audio '{pre_audio}': {e}")

    play_code(code, channel)

    if post_audio:
        post_path = os.path.join("scene_audio", f"{post_audio}.mp3")
        if os.path.exists(post_path):
            try:
                post_sound = pygame.mixer.Sound(post_path)
                channel.play(post_sound)
                while channel.get_busy():
                    time.sleep(0.05)
            except Exception as e:
                print(f"Error playing post_audio '{post_audio}': {e}")