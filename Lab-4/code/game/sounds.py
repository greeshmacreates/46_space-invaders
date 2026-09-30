import math
import random
import array
import pygame


def _tone(freq_start, freq_end, duration, volume=0.4, square=True, rate=44100):
    """Generate a simple sliding tone as mono signed 16-bit samples."""
    n = int(rate * duration)
    samples = array.array("h")
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = freq_start + (freq_end - freq_start) * t
        phase += 2 * math.pi * freq / rate
        wave = math.sin(phase)
        if square:
            wave = 1.0 if wave >= 0 else -1.0
        envelope = 1.0 - t  # fade out
        samples.append(int(wave * envelope * volume * 32767))
    return samples


def _noise(duration, volume=0.5, rate=44100):
    n = int(rate * duration)
    samples = array.array("h")
    for i in range(n):
        envelope = (1.0 - i / n) ** 2
        samples.append(int(random.uniform(-1, 1) * envelope * volume * 32767))
    return samples


def _make_sound(samples):
    return pygame.mixer.Sound(buffer=samples.tobytes())


class Sounds:
    """Procedurally generated sound effects (no audio files needed).
    If audio can't be initialised, every play method silently does nothing."""

    def __init__(self):
        self.enabled = False
        self.fire = self.explosion = self.game_over = None
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

            self.fire = _make_sound(_tone(900, 350, 0.12, volume=0.25))
            self.explosion = _make_sound(_noise(0.3, volume=0.5))

            over = array.array("h")
            for start, end in [(440, 380), (370, 300), (290, 200), (190, 90)]:
                over.extend(_tone(start, end, 0.25, volume=0.4))
            self.game_over = _make_sound(over)
            self.enabled = True
        except Exception as exc:  # no audio device, etc.
            print("Sound disabled:", exc)

    def _play(self, sound):
        if self.enabled and sound is not None:
            sound.play()

    def play_fire(self):
        self._play(self.fire)

    def play_explosion(self):
        self._play(self.explosion)

    def play_game_over(self):
        self._play(self.game_over)
