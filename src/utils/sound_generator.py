"""Procedural sound effects generator for the game."""

import os
import math
import array
import random
import wave
import struct
import numpy as np
from typing import List, Tuple, Optional
from src.config import SOUNDS_DIR

class SoundGenerator:
    """
    Generates procedural game sound effects.
    
    This class creates various arcade-style sound effects 
    for different game events like laser shots, explosions, 
    powerups, and UI feedback.
    """
    
    def __init__(self, sample_rate: int = 44100):
        """
        Initialize the sound generator.
        
        Args:
            sample_rate: Sample rate for generated sounds (default: 44100 Hz)
        """
        self.sample_rate = sample_rate
        self.amplitude = 32767  # Maximum amplitude for 16-bit audio
        
        # Ensure sounds directory exists
        if not os.path.exists(SOUNDS_DIR):
            try:
                os.makedirs(SOUNDS_DIR)
                print(f"Created sounds directory at {SOUNDS_DIR}")
            except (OSError, PermissionError) as e:
                print(f"Error creating sounds directory: {e}")
    
    def _clamp_sample(self, sample: np.ndarray) -> np.ndarray:
        """Clamp samples between -1.0 and 1.0."""
        return np.clip(sample, -1.0, 1.0)
    
    def _apply_envelope(self, samples: np.ndarray, attack: float = 0.01, 
                       decay: float = 0.1, sustain: float = 0.8, 
                       release: float = 0.1) -> np.ndarray:
        """
        Apply an ADSR envelope to the samples.
        
        Args:
            samples: The audio samples
            attack: Attack time in seconds
            decay: Decay time in seconds  
            sustain: Sustain level (0.0 to 1.0)
            release: Release time in seconds
            
        Returns:
            Modified samples with envelope applied
        """
        total_samples = len(samples)
        
        # Convert times to sample counts, ensuring they don't exceed the total
        attack_samples = min(int(attack * self.sample_rate), total_samples // 4)
        decay_samples = min(int(decay * self.sample_rate), total_samples // 4)
        release_samples = min(int(release * self.sample_rate), total_samples // 4)
        
        # Ensure we don't exceed total samples
        sustain_samples = total_samples - attack_samples - decay_samples - release_samples
        
        # Generate envelope
        envelope = np.ones(total_samples)
        
        # Attack phase (linear ramp up)
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Decay phase (exponential decay to sustain level)
        if decay_samples > 0:
            decay_curve = np.linspace(0, 1, decay_samples) ** 0.5  # Square root for more natural decay
            decay_envelope = 1.0 - (1.0 - sustain) * decay_curve
            envelope[attack_samples:attack_samples + decay_samples] = decay_envelope
        
        # Sustain phase (constant)
        if sustain_samples > 0:
            envelope[attack_samples + decay_samples:attack_samples + decay_samples + sustain_samples] = sustain
        
        # Release phase (exponential decay to zero)
        if release_samples > 0:
            release_start = attack_samples + decay_samples + sustain_samples
            release_end = total_samples
            actual_release_samples = release_end - release_start
            
            if actual_release_samples > 0:
                release_curve = np.linspace(0, 1, actual_release_samples) ** 2  # Square for more natural release
                release_envelope = sustain * (1.0 - release_curve)
                envelope[release_start:release_end] = release_envelope
        
        # Apply envelope
        return samples * envelope
    
    def _apply_lowpass_filter(self, samples: np.ndarray, cutoff_freq: float) -> np.ndarray:
        """
        Apply a simple lowpass filter to the samples.
        
        Args:
            samples: The audio samples
            cutoff_freq: Cutoff frequency in Hz
            
        Returns:
            Filtered samples
        """
        # Simple one-pole lowpass filter
        dt = 1.0 / self.sample_rate
        rc = 1.0 / (2.0 * math.pi * cutoff_freq)
        alpha = dt / (rc + dt)
        
        filtered_samples = np.zeros_like(samples)
        filtered_samples[0] = samples[0]
        
        for i in range(1, len(samples)):
            filtered_samples[i] = filtered_samples[i-1] + alpha * (samples[i] - filtered_samples[i-1])
            
        return filtered_samples
    
    def _save_samples_to_wav(self, samples: np.ndarray, filename: str) -> str:
        """
        Save audio samples to a WAV file.
        
        Args:
            samples: Audio samples (-1.0 to 1.0)
            filename: Name of the file to save (without extension)
            
        Returns:
            Path to the saved file
        """
        filepath = os.path.join(SOUNDS_DIR, f"{filename}.wav")
        
        # Convert to 16-bit PCM
        samples_int = (samples * self.amplitude).astype(np.int16)
        
        # Save to WAV file
        try:
            with wave.open(filepath, 'w') as wav_file:
                # Set parameters: 1 channel (mono), 2 bytes per sample (16-bit), 
                # sample rate, number of frames, compression type, compression name
                wav_file.setparams((1, 2, self.sample_rate, len(samples), 'NONE', 'not compressed'))
                wav_file.writeframes(samples_int.tobytes())
            
            print(f"Saved sound effect to {filepath}")
            return filepath
        except (IOError, PermissionError) as e:
            print(f"Error saving sound file: {e}")
            return ""
    
    def generate_laser(self, duration: float = 0.2, freq_start: float = 880, 
                      freq_end: float = 220, volume: float = 0.7, 
                      filename: Optional[str] = "laser") -> str:
        """
        Generate a laser/blaster sound effect.
        
        Args:
            duration: Sound length in seconds
            freq_start: Starting frequency in Hz
            freq_end: Ending frequency in Hz
            volume: Volume level (0.0 to 1.0)
            filename: Name to save as (without extension) or None to not save
            
        Returns:
            Path to the saved sound file or empty string if not saved
        """
        # Create samples array
        num_samples = int(self.sample_rate * duration)
        samples = np.zeros(num_samples)
        
        # Generate sound
        for i in range(num_samples):
            t = i / self.sample_rate
            # Linear frequency sweep from start to end
            freq = freq_start + (freq_end - freq_start) * (i / num_samples)
            # Add slight noise for texture
            noise = random.uniform(-0.1, 0.1) * (i / num_samples)
            # Create sample
            samples[i] = math.sin(2 * math.pi * freq * t) + noise
        
        # Normalize and apply volume
        samples = self._clamp_sample(samples) * volume
        
        # Apply envelope for better sound
        samples = self._apply_envelope(samples, attack=0.01, decay=0.1, sustain=0.7, release=0.1)
        
        # Save if filename provided
        if filename:
            return self._save_samples_to_wav(samples, filename)
        return ""
    
    def generate_explosion(self, duration: float = 0.8, intensity: float = 0.8,
                          filename: Optional[str] = "explosion") -> str:
        """
        Generate an explosion sound effect.
        
        Args:
            duration: Sound length in seconds
            intensity: Explosion intensity (affects noise level and filtering)
            filename: Name to save as (without extension) or None to not save
            
        Returns:
            Path to the saved sound file or empty string if not saved
        """
        # Create samples array
        num_samples = int(self.sample_rate * duration)
        samples = np.zeros(num_samples)
        
        # Generate noise with decreasing amplitude
        for i in range(num_samples):
            t = i / self.sample_rate
            # Amplitude decreases over time
            amp = 1.0 - (i / num_samples) ** 0.5
            # White noise with some low frequency rumble
            noise = random.uniform(-1.0, 1.0)
            rumble = math.sin(2 * math.pi * 40 * t) * 0.3
            samples[i] = (noise * 0.7 + rumble * 0.3) * amp
        
        # Apply lowpass filter
        cutoff = 1000 + 3000 * intensity
        samples = self._apply_lowpass_filter(samples, cutoff)
        
        # Add some high-frequency crackling at the start
        if intensity > 0.5:
            for i in range(int(num_samples * 0.3)):
                if random.random() < 0.2:
                    # Random spikes that decrease in amplitude
                    spike_amp = random.uniform(0.4, 0.8) * (1.0 - (i / num_samples))
                    samples[i] += spike_amp * random.choice([-1, 1])
        
        # Apply envelope
        samples = self._apply_envelope(samples, attack=0.01, decay=0.2, sustain=0.5, release=0.6)
        
        # Normalize and scale
        samples = self._clamp_sample(samples) * 0.9
        
        # Save if filename provided
        if filename:
            return self._save_samples_to_wav(samples, filename)
        return ""
    
    def generate_powerup(self, duration: float = 0.4, base_freq: float = 440, 
                        filename: Optional[str] = "powerup") -> str:
        """
        Generate a powerup/reward sound effect.
        
        Args:
            duration: Sound length in seconds
            base_freq: Base frequency in Hz
            filename: Name to save as (without extension) or None to not save
            
        Returns:
            Path to the saved sound file or empty string if not saved
        """
        # Create samples array
        num_samples = int(self.sample_rate * duration)
        samples = np.zeros(num_samples)
        
        # Generate ascending notes
        for i in range(num_samples):
            t = i / self.sample_rate
            
            # Create a rising sequence of notes
            progress = i / num_samples
            note_idx = int(progress * 4)  # 4 notes in sequence
            
            # Major scale frequency ratios
            ratios = [1.0, 1.25, 1.5, 2.0]  # Root, major third, fifth, octave
            
            # Get frequency for current note
            freq = base_freq * ratios[min(note_idx, len(ratios) - 1)]
            
            # Add some shimmer/vibrato
            vibrato = math.sin(2 * math.pi * 8 * t) * 0.1
            
            # Create sample with slight harmonics
            samples[i] = (
                0.7 * math.sin(2 * math.pi * freq * t) +  # Fundamental
                0.2 * math.sin(2 * math.pi * freq * 2 * t) +  # 1st harmonic
                0.1 * math.sin(2 * math.pi * freq * 3 * t)    # 2nd harmonic
            ) * (1.0 + vibrato)
        
        # Apply envelope
        samples = self._apply_envelope(samples, attack=0.01, decay=0.1, sustain=0.8, release=0.2)
        
        # Normalize
        samples = self._clamp_sample(samples) * 0.8
        
        # Save if filename provided
        if filename:
            return self._save_samples_to_wav(samples, filename)
        return ""
    
    def generate_menu_select(self, duration: float = 0.15, 
                           filename: Optional[str] = "menu_select") -> str:
        """
        Generate a UI menu selection sound effect.
        
        Args:
            duration: Sound length in seconds
            filename: Name to save as (without extension) or None to not save
            
        Returns:
            Path to the saved sound file or empty string if not saved
        """
        # Create samples array
        num_samples = int(self.sample_rate * duration)
        samples = np.zeros(num_samples)
        
        # Generate two-tone beep
        for i in range(num_samples):
            t = i / self.sample_rate
            # First half is higher pitch, second half is lower
            if i < num_samples / 2:
                freq = 880  # Higher frequency (A5)
            else:
                freq = 1320  # Higher frequency (E6)
            
            # Create sample with slight harmonics
            samples[i] = 0.8 * math.sin(2 * math.pi * freq * t) + 0.2 * math.sin(2 * math.pi * freq * 2 * t)
        
        # Apply short envelope
        samples = self._apply_envelope(samples, attack=0.01, decay=0.05, sustain=0.8, release=0.1)
        
        # Normalize
        samples = self._clamp_sample(samples) * 0.7
        
        # Save if filename provided
        if filename:
            return self._save_samples_to_wav(samples, filename)
        return ""
    
    def generate_all_sounds(self) -> List[str]:
        """
        Generate a complete set of game sound effects.
        
        Returns:
            List of paths to the generated sound files
        """
        generated_files = []
        
        # Generate laser variants
        generated_files.append(self.generate_laser(duration=0.2, freq_start=880, freq_end=220, filename="laser1"))
        generated_files.append(self.generate_laser(duration=0.15, freq_start=1200, freq_end=600, filename="laser2"))
        generated_files.append(self.generate_laser(duration=0.3, freq_start=660, freq_end=330, filename="laser3"))
        
        # Generate explosion variants
        generated_files.append(self.generate_explosion(duration=0.6, intensity=0.6, filename="explosion_small"))
        generated_files.append(self.generate_explosion(duration=0.8, intensity=0.8, filename="explosion_medium"))
        generated_files.append(self.generate_explosion(duration=1.0, intensity=0.9, filename="explosion_large"))
        
        # Generate powerup sounds
        generated_files.append(self.generate_powerup(duration=0.4, base_freq=440, filename="powerup1"))
        generated_files.append(self.generate_powerup(duration=0.5, base_freq=523.25, filename="powerup2"))
        
        # Generate UI sounds
        generated_files.append(self.generate_menu_select(duration=0.15, filename="menu_select"))
        generated_files.append(self.generate_menu_select(duration=0.1, filename="menu_click"))
        
        return [f for f in generated_files if f]  # Remove empty strings (failed generations)


# Example usage if run directly
if __name__ == "__main__":
    generator = SoundGenerator()
    generated_files = generator.generate_all_sounds()
    print(f"Generated {len(generated_files)} sound effects") 