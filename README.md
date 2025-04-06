# Starblitz Assault

Blast into a relentless, side-scrolling dogfight across galaxies teeming with hostile alien fleets. Pilot the advanced Starblitz fighter, upgrade devastating weapons, dodge bullet-storm chaos, and obliterate massive boss enemies. Your reflexes and courage stand between humanity and cosmic annihilation.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/StarblitzAssault.git
cd StarblitzAssault

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py
```

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

## Development

### Project Structure

```
StarblitzAssault/
├─ .logs/          # Application logs
├─ .tests/         # Temporary tests
├─ .unused/        # Unused/deprecated files 
├─ assets/         # Game assets
│  ├─ backgrounds/ # Background images
│  ├─ music/       # Music files
│  ├─ sounds/      # Sound effects
│  └─ sprites/     # Sprite sheets
├─ config/         # Game configuration
├─ src/            # Source code
│  ├─ utils/       # Utility functions
│  └─ ...          # Game component modules
├─ static/         # Static files
├─ tests/          # Permanent tests
├─ main.py         # Entry point
└─ requirements.txt # Dependencies
```

### Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit your changes (`git commit -m 'Add some amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---
*(Scaffolding based on provided rules)*
