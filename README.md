# Character Bust Extractor v4.0 - Final Version

Professional tool for extracting character busts from sprite sheets with automatic detection.

## ✨ Features

- **Automatic bust detection** - No fixed columns, finds busts wherever they are
- **Dual background removal** - Color-based (fast) or AI-powered (accurate)
- **Multiple formats** - PNG or WebP output with optimization
- **Batch processing** - Process multiple files with glob patterns
- **Smart cropping** - Preserves hands and removes fragments automatically
- **Docker support** - Containerized for easy deployment

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install Pillow numpy scipy

# For AI background removal (optional)
pip install rembg onnxruntime
```

### Basic Usage

```bash
# Process a single file
python bust_extractor_advanced.py sprite_sheet.png

# With WebP output
python bust_extractor_advanced.py sprite.png --format webp

# Batch processing
python bust_extractor_advanced.py "*.png" --format webp

# AI background removal
python bust_extractor_advanced.py photo.jpg --bg-method ai
```

## 📖 Usage Examples

### Single File Processing
```bash
# Automatic output directory (busts_<filename>/)
python bust_extractor_advanced.py my_sprites.png

# Custom output directory
python bust_extractor_advanced.py sprites.png -o my_output

# WebP with high quality
python bust_extractor_advanced.py chars.png --format webp --quality 95

# Custom names
python bust_extractor_advanced.py busts.png \\
    --names "idle,happy,angry,thinking,surprised,sad"
```

### Batch Processing
```bash
# All PNG files
python bust_extractor_advanced.py "*.png"

# Specific pattern
python bust_extractor_advanced.py "character_*.png" --format webp

# With custom settings
python bust_extractor_advanced.py "*.png" \\
    --format webp \\
    --quality 90 \\
    --padding 40
```

### Advanced Options
```bash
# Full configuration
python bust_extractor_advanced.py sprite.png \\
    --output-dir custom_output \\
    --format webp \\
    --quality 90 \\
    --padding 40 \\
    --bg-method ai \\
    --bg-tolerance 35 \\
    --names "idle,happy,angry,thinking" \\
    --verbose

# No preview generation
python bust_extractor_advanced.py sprite.png --no-preview

# Verbose output
python bust_extractor_advanced.py sprite.png -v
```

## 🐳 Docker Usage

### Quick Docker Start
```bash
# Build image
docker build -t bust-extractor .

# Process a file
docker run --rm \\
  -v $(pwd):/input:ro \\
  -v $(pwd)/output:/output \\
  bust-extractor /input/sprite.png

# Batch with WebP
docker run --rm \\
  -v $(pwd):/input:ro \\
  -v $(pwd)/output:/output \\
  bust-extractor "/input/*.png" --format webp
```

See [DOCKER_USAGE.md](DOCKER_USAGE.md) for complete Docker documentation.

## ⚙️ Configuration Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `input_pattern` | - | Input file or glob pattern | Required |
| `--output-dir` | `-o` | Output directory | `busts_<filename>` |
| `--format` | `-f` | Output format (png/webp) | `png` |
| `--quality` | `-q` | Quality 1-100 | `95` |
| `--padding` | `-p` | Padding in pixels | `30` |
| `--bg-method` | `-b` | Background method (color/ai) | `color` |
| `--bg-tolerance` | `-t` | Color tolerance | `30` |
| `--names` | `-n` | Comma-separated names | Auto |
| `--no-preview` | - | Skip preview | False |
| `--verbose` | `-v` | Verbose output | False |

## 📁 Output Structure

```
busts_sprite_sheet/
├── idle.png          # Individual busts with transparent background
├── happy.png
├── angry.png
├── thinking.png
└── preview.png       # Preview of all busts
```

## 🎯 Background Removal Methods

### Color-Based (Default)
- **Fast** - Processes instantly
- **Best for**: Solid backgrounds (black, white, green screen)
- **No extra dependencies**

```bash
python bust_extractor_advanced.py sprite.png --bg-method color
```

### AI-Powered
- **Accurate** - Uses U2-Net neural network
- **Best for**: Complex backgrounds, photographs, gradients
- **Requires**: `rembg` and `onnxruntime` packages

```bash
# Install dependencies first
pip install rembg onnxruntime

# Then use AI method
python bust_extractor_advanced.py photo.jpg --bg-method ai
```

## 🎨 Format Comparison

### PNG
- **Lossless** - Perfect quality
- **Larger files** - ~1-2MB per bust
- **Best for**: High-quality archives, editing
- **Use when**: Quality is priority

### WebP
- **Efficient** - 25-35% smaller than PNG
- **High quality** - Minimal visual loss at Q90+
- **Best for**: Web use, storage optimization
- **Use when**: File size matters

## 📊 Performance

| Mode | Speed | Quality | Best For |
|------|-------|---------|----------|
| Color + PNG | ⚡⚡⚡ | ⭐⭐⭐ | Solid backgrounds |
| Color + WebP | ⚡⚡⚡ | ⭐⭐⭐ | Web deployment |
| AI + PNG | ⚡ | ⭐⭐⭐⭐ | Photos, complex BG |
| AI + WebP | ⚡ | ⭐⭐⭐⭐ | Complex BG + size |

## 🔧 Troubleshooting

### Issue: Rembg not found
```bash
# Install AI dependencies
pip install rembg onnxruntime

# For GPU acceleration (optional)
pip install onnxruntime-gpu
```

### Issue: Background not fully removed
```bash
# Increase tolerance for color-based
python bust_extractor_advanced.py sprite.png --bg-tolerance 40

# Or use AI method
python bust_extractor_advanced.py sprite.png --bg-method ai
```

### Issue: Bust hands are cut off
The advanced version automatically detects bust boundaries, so hands should never be cut off. If this happens, increase padding:

```bash
python bust_extractor_advanced.py sprite.png --padding 50
```

## 📦 Files Included

- `bust_extractor_advanced.py` - Main program ⭐
- `requirements_advanced.txt` - Python dependencies
- `Dockerfile` - Docker image definition
- `docker-compose.yml` - Docker Compose configuration
- `DOCKER_USAGE.md` - Complete Docker documentation
- `README.md` - This file

## 🎓 Examples from Your Data

Your original sprite sheet was processed with these results:

**Input:** `Gemini_Generated_Image_w81nyiw81nyiw81n.png` (2816×1536px)

**Output:**
- `idle.png` - 671×1198px
- `happy.png` - 625×1190px
- `angry.png` - 859×1190px ⭐ (perfect hands!)
- `thinking.png` - 641×1184px

**Processing:**
- Method: Color-based
- Detected: 29 components
- Filtered to: 4 main busts
- Removed: 17 total fragments
- Time: ~2-3 seconds

## 🌟 Tips

1. **Use color-based for speed** - It's instant and works great for most sprite sheets
2. **Use AI for photos** - When background is complex or has gradients
3. **WebP for web** - 30% smaller files with minimal quality loss
4. **Batch processing** - Process entire folders at once
5. **Verbose mode** - Use `-v` to see detailed progress

## 📝 License

MIT License - Free to use for commercial and personal projects.

## 👤 Author

raven2cz

## 🎉 Done!

Your sprite sheet busts are ready to use in RPG Maker MZ, Unity, Godot, or any game engine!
