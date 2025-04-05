# Starblitz Assault

Blast into a relentless, side-scrolling dogfight across galaxies teeming with hostile alien fleets. Pilot the advanced Starblitz fighter, upgrade devastating weapons, dodge bullet-storm chaos, and obliterate massive boss enemies. Your reflexes and courage stand between humanity and cosmic annihilation.

## Features

- Fast-paced side-scrolling space shooter gameplay
- Multiple enemy formation patterns
- Procedurally generated sound effects
- Dynamic background music
- Smooth player controls with responsive movement

## Controls

- **Arrow Keys**: Move the ship
- **Space**: Fire weapons
- **M**: Toggle music pause/play
- **+/-**: Increase/decrease music volume
- **ESC**: Quit the game

## Sound Effects & Music System

Starblitz Assault features a built-in procedural sound generator and a dynamic sound system:

- Procedurally generated laser, explosion, and powerup sounds
- Background music with fade-in/out and volume controls
- Multi-channel audio for different game elements
- Randomized laser sound variations during continuous fire

### Sound Generation

To regenerate the game's sound effects, run:

```bash
python assets/simple_sound_gen.py
```

This will create WAV files in the `assets/sounds` directory that are automatically loaded by the game.

### Adding Music

Place MP3 or OGG files in the `assets/music` directory. You can play them using:

```python
sound_manager.play_music("your-music-file.mp3")
```

---
*(Scaffolding based on provided rules)*
