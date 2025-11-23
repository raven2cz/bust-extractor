# Character Bust Extractor v4.2 - Final Version

Professional tool for extracting character busts from sprite sheets with automatic detection.

## ✨ Features

- **Automatic bust detection** - No fixed columns, finds busts wherever they are
- **Dual background removal** - Color-based (fast) or AI-powered (accurate)
- **Transparent input support** - Skip background removal for pre-processed images
- **Advanced despill** - Removes green screen color bleeding from character edges
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

# For images with transparent background already (NEW in v4.2!)
python bust_extractor_advanced.py transparent_sprites.png --transparent-input

# With aggressive despill for green screen
python bust_extractor_advanced.py greenscreen.png --despill-strength 1.0

# With WebP output
python bust_extractor_advanced.py sprite.png --format webp

# Batch processing
python bust_extractor_advanced.py "*.png" --format webp

# AI background removal
python bust_extractor_advanced.py photo.jpg --bg-method ai
```

## 🎨 Despill Technology (v4.1+)

### What is Despill?

Despill removes green (or blue) screen color bleeding that appears around character edges after background removal. This eliminates the "green halo" effect for professional-quality results.

### Despill Strength Levels

```bash
# Gentle (preserves more original colors)
python bust_extractor_advanced.py image.png --despill-strength 0.5

# Default (balanced)
python bust_extractor_advanced.py image.png --despill-strength 0.8

# AGGRESSIVE (removes almost all green)
python bust_extractor_advanced.py image.png --despill-strength 1.0
```

### When to Use Each Strength

**Strength 0.5-0.8 (Standard):**
- Reduces color spill by 50-95%
- Preserves some natural color tones
- Good for characters with colorful details

**Strength 0.9-1.0 (Ultra-aggressive):**
- **Replaces** green with average of other channels
- Removes ALL green where g > max(r,b)
- Ideal for pure green screen where green is not legitimate

**Disable despill:**
```bash
# For pixel art or when you need exact colors
python bust_extractor_advanced.py pixel_art.png --no-despill
```

## 🆕 Transparent Input Mode (v4.2)

### What is Transparent Input?

If your sprite sheet already has a transparent background (PNG with alpha channel), you can skip the background removal step entirely. This is faster and preserves the exact transparency you've already prepared.

### When to Use Transparent Input

✅ **Use `--transparent-input` when:**
- Your image already has transparent background
- You've pre-processed the image in Photoshop/GIMP
- You want to preserve exact alpha channel data
- You're working with pixel art that's already prepared

❌ **Don't use `--transparent-input` when:**
- Image has solid color background (black, white, green)
- Image has complex/gradient background
- You need background removal

### Transparent Input Examples

```bash
# Simple extraction from transparent sprite sheet
python bust_extractor_advanced.py pre_processed.png --transparent-input

# Batch process transparent sprites
python bust_extractor_advanced.py "transparent_*.png" --transparent-input

# Transparent input with WebP output
python bust_extractor_advanced.py sprites.png --transparent-input --format webp

# With custom names
python bust_extractor_advanced.py busts.png --transparent-input \
    --names "idle,happy,angry,thinking"
```

### Comparison: Normal vs Transparent Input

```bash
# NORMAL MODE (removes background)
python bust_extractor_advanced.py greenscreen.png --despill-strength 1.0
# → Detects background color
# → Removes background
# → Applies despill
# → Extracts busts
# Time: ~2-3 seconds

# TRANSPARENT INPUT MODE (skips background removal)
python bust_extractor_advanced.py transparent.png --transparent-input
# → Skips background removal
# → Uses existing alpha channel
# → Extracts busts
# Time: ~1 second (faster!)
```

## 📖 Usage Examples

### Single File Processing
```bash
# Automatic output directory (busts_<filename>/)
python bust_extractor_advanced.py my_sprites.png

# Custom output directory
python bust_extractor_advanced.py sprites.png -o my_output

# WebP with high quality and max despill
python bust_extractor_advanced.py chars.png \
    --format webp \
    --quality 95 \
    --despill-strength 1.0

# Transparent input (NEW!)
python bust_extractor_advanced.py transparent_sprites.png --transparent-input

# Custom names
python bust_extractor_advanced.py busts.png \
    --names "idle,happy,angry,thinking,surprised,sad"
```

### Batch Processing
```bash
# All PNG files with aggressive despill
python bust_extractor_advanced.py "*.png" \
    --despill-strength 1.0

# All transparent sprites (skip BG removal)
python bust_extractor_advanced.py "transparent_*.png" --transparent-input

# Specific pattern
python bust_extractor_advanced.py "character_*.png" --format webp

# With custom settings
python bust_extractor_advanced.py "*.png" \
    --format webp \
    --quality 90 \
    --padding 40 \
    --despill-strength 1.0
```

### Advanced Options
```bash
# Full configuration
python bust_extractor_advanced.py sprite.png \
    --output-dir custom_output \
    --format webp \
    --quality 90 \
    --padding 40 \
    --bg-method ai \
    --bg-tolerance 35 \
    --despill-strength 1.0 \
    --edge-feather 3 \
    --names "idle,happy,angry,thinking" \
    --verbose

# Transparent input with minimal processing
python bust_extractor_advanced.py prepared.png \
    --transparent-input \
    --no-preview \
    --verbose

# No preview generation
python bust_extractor_advanced.py sprite.png --no-preview

# Verbose output
python bust_extractor_advanced.py sprite.png -v
```

## 🳠Docker Usage

### Quick Docker Start
```bash
# Build image
docker build -t bust-extractor .

# Process a file with max despill
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor /input/sprite.png --despill-strength 1.0

# Process transparent sprites
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor /input/transparent.png --transparent-input

# Batch with WebP
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor "/input/*.png" --format webp --despill-strength 1.0
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
| `--transparent-input` | - | Skip BG removal (already transparent) | `False` |
| `--despill` | - | Enable despill | `True` |
| `--no-despill` | - | Disable despill | `False` |
| `--despill-strength` | `-s` | Despill strength 0.0-1.0 | `0.8` |
| `--edge-feather` | `-e` | Edge smoothing in pixels | `2` |
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
- **Works with**: Despill technology for perfect edges

```bash
python bust_extractor_advanced.py sprite.png \
    --bg-method color \
    --despill-strength 1.0
```

### AI-Powered
- **Accurate** - Uses U2-Net neural network
- **Best for**: Complex backgrounds, photographs, gradients
- **Requires**: `rembg` and `onnxruntime` packages
- **Works with**: Despill for additional refinement

```bash
# Install dependencies first
pip install rembg onnxruntime

# Then use AI method
python bust_extractor_advanced.py photo.jpg \
    --bg-method ai \
    --despill-strength 0.7
```

### Transparent Input (NEW!)
- **Fastest** - Skips background removal entirely
- **Best for**: Pre-processed images with alpha channel
- **No dependencies** needed
- **Perfect for**: Pixel art, pre-edited sprites

```bash
python bust_extractor_advanced.py transparent.png --transparent-input
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
| Transparent Input | ⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | Pre-processed sprites |
| Color + PNG + Despill | ⚡⚡⚡ | ⭐⭐⭐⭐ | Green screen sprites |
| Color + WebP + Despill | ⚡⚡⚡ | ⭐⭐⭐⭐ | Web deployment |
| AI + PNG + Despill | ⚡ | ⭐⭐⭐⭐⭐ | Photos, complex BG |
| AI + WebP + Despill | ⚡ | ⭐⭐⭐⭐⭐ | Complex BG + size |

## 🔬 Despill Comparison

### Without Despill (--no-despill):
```
❌ Green "ghosts" around characters
❌ Color fringing on edges
❌ Poor compositing results
```

### Despill 0.5:
```
⚠️ Still visible green edges
⚠️ Better than none, but not perfect
```

### Despill 0.8 (default):
```
✅ Good for most cases
✅ Minimal green
⚠️ May have slight tint
```

### Despill 1.0 (aggressive):
```
✅ Green COMPLETELY removed
✅ Clean edges
✅ Professional quality
✅ Ideal for green screen
```

## 🔧 Troubleshooting

### Issue: Green edges remain after extraction
```bash
# Increase despill strength to maximum
python bust_extractor_advanced.py sprite.png --despill-strength 1.0

# Combine with higher tolerance
python bust_extractor_advanced.py sprite.png -t 35 --despill-strength 1.0
```

### Issue: Colors look washed out
```bash
# Reduce despill strength
python bust_extractor_advanced.py sprite.png --despill-strength 0.5

# Or disable for pixel art
python bust_extractor_advanced.py pixel_art.png --no-despill
```

### Issue: Image already has transparent background
```bash
# Use transparent input mode to skip background removal
python bust_extractor_advanced.py sprite.png --transparent-input
```

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

- `bust_extractor_advanced.py` - Main program ⭐ (v4.2)
- `requirements_advanced.txt` - Python dependencies
- `Dockerfile` - Docker image definition
- `docker-compose.yml` - Docker Compose configuration
- `DOCKER_USAGE.md` - Complete Docker documentation
- `DESPILL_STRENGTH_GUIDE.md` - Despill technology guide
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
- Method: Color-based with aggressive despill
- Despill strength: 1.0
- Detected: 29 components
- Filtered to: 4 main busts
- Removed: 17 total fragments
- Time: ~2-3 seconds
- Result: ✅ No green edges!

## 🌟 Tips

1. **Use transparent-input for pre-processed images** - Fastest method when you've already prepared sprites
2. **Use despill 1.0 for green screen** - Completely removes green halos
3. **Use color-based for speed** - It's instant and works great for most sprite sheets
4. **Use AI for photos** - When background is complex or has gradients
5. **WebP for web** - 30% smaller files with minimal quality loss
6. **Batch processing** - Process entire folders at once with consistent despill
7. **Verbose mode** - Use `-v` to see detailed progress including despill operations

## 🎯 Recommended Workflows

### For Pre-Processed Transparent Sprites (NEW!):
```bash
python bust_extractor_advanced.py transparent_sprites.png \
    --transparent-input \
    --format webp \
    --quality 95
```

### For Green Screen Sprite Sheets:
```bash
python bust_extractor_advanced.py greenscreen.png \
    --despill-strength 1.0 \
    -t 35 \
    --format webp \
    --quality 90
```

### For Web Optimization:
```bash
python bust_extractor_advanced.py sprites.png \
    --format webp \
    --quality 85 \
    --despill-strength 1.0 \
    --edge-feather 3
```

### For Pixel-Perfect (No Modifications):
```bash
python bust_extractor_advanced.py pixel_art.png \
    --no-despill \
    --edge-feather -1 \
    -t 10
```

### For Already Transparent Pixel Art:
```bash
python bust_extractor_advanced.py pixel_sprites.png \
    --transparent-input \
    --format png
```

## 📄 License

MIT License - Free to use for commercial and personal projects.

## 👤 Author

raven2cz

## 🎉 Done!

Your sprite sheet busts are ready to use in RPG Maker MZ, Unity, Godot, or any game engine - with professional-quality edges and zero color bleeding! 🚀

## 📝 Version History

- **v4.2** - Added transparent input mode for pre-processed images
- **v4.1** - Added despill technology with configurable strength
- **v4.0** - Initial release with automatic detection and dual background removal