# Character Bust Extractor - Docker Usage

## Quick Start

### Build the Docker Image

```bash
# Build the image
docker build -t bust-extractor .

# Or use docker-compose
docker-compose build
```

### Basic Usage

#### Method 1: Using Docker Run

```bash
# Process a single file (output to busts_<filename>/)
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor /input/sprite_sheet.png

# Process with custom output directory
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor /input/sprite.png -o /output/my_busts

# Process with WebP output
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor /input/sprite.png --format webp --quality 90

# Batch processing - all PNGs
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor "/input/*.png" --format webp
```

#### Method 2: Using Docker Compose

```bash
# Show help
docker-compose run --rm bust-extractor --help

# Process a file
docker-compose run --rm bust-extractor /input/sprite.png

# Process with options
docker-compose run --rm bust-extractor \
  /input/sprite.png \
  --format webp \
  --quality 90 \
  --padding 40

# Batch processing
docker-compose run --rm bust-extractor "/input/*.png" --format webp
```

## Volume Mapping

The container uses two mount points:

- `/input` - Mount your sprite sheets here (read-only)
- `/output` - Processed busts will be saved here

Example directory structure:
```
your-project/
├── sprite_sheet_1.png
├── sprite_sheet_2.png
└── output/              # Created automatically
    ├── busts_sprite_sheet_1/
    │   ├── idle.png
    │   ├── happy.png
    │   └── ...
    └── busts_sprite_sheet_2/
        └── ...
```

## Configuration Examples

### WebP Output with High Quality
```bash
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor /input/sprites.png \
  --format webp \
  --quality 95
```

### AI Background Removal
First, uncomment rembg in `requirements_advanced.txt` and rebuild:
```bash
# Edit requirements_advanced.txt to uncomment rembg lines
docker build -t bust-extractor .

# Then use AI method
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor /input/photo.jpg \
  --bg-method ai
```

### Custom Names
```bash
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor /input/chars.png \
  --names "normal,smile,frown,surprised,thinking,angry"
```

### Verbose Output
```bash
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor /input/sprite.png -v
```

## Management Commands

### Stop Container
```bash
# Stop running container
docker stop bust-extractor

# Or with docker-compose
docker-compose stop
```

### Remove Container
```bash
# Remove container
docker rm bust-extractor

# Or with docker-compose
docker-compose down
```

### Clean Up Images
```bash
# Remove the image
docker rmi bust-extractor

# Remove all unused images
docker image prune -a
```

## Auto-Start Prevention

The container is configured with `restart: "no"` in docker-compose.yml, which means:
- ✓ Container will NOT start automatically on system boot
- ✓ Container will NOT restart if it crashes
- ✓ You must manually run it each time

This is by design for a processing tool that should only run on-demand.

## Advanced Usage

### GPU Support (for AI mode)

For faster AI processing with NVIDIA GPU:

1. Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

2. Uncomment GPU section in `docker-compose.yml`

3. Build with GPU support:
```bash
docker-compose build
```

4. Run with GPU:
```bash
docker-compose run --rm bust-extractor \
  /input/sprite.png \
  --bg-method ai
```

### Batch Processing Multiple Directories

```bash
# Process all PNGs in multiple directories
for dir in sprites1 sprites2 sprites3; do
  docker run --rm \
    -v $(pwd)/$dir:/input:ro \
    -v $(pwd)/output:/output \
    bust-extractor "/input/*.png" --format webp
done
```

### Using as a Service

If you want to process files continuously:

```bash
# Watch directory and process new files
while true; do
  docker run --rm \
    -v $(pwd)/watch:/input:ro \
    -v $(pwd)/output:/output \
    bust-extractor "/input/*.png"
  sleep 60  # Check every minute
done
```

## Troubleshooting

### Permission Issues
If you get permission errors:
```bash
# Add user flag
docker run --rm \
  --user $(id -u):$(id -g) \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor /input/sprite.png
```

### Output Not Appearing
Check that output directory exists and is writable:
```bash
mkdir -p output
chmod 755 output
```

### Container Won't Stop
Force stop and remove:
```bash
docker stop -t 0 bust-extractor
docker rm -f bust-extractor
```

## Examples

### Example 1: Quick Processing
```bash
# Place sprite_sheet.png in current directory
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor /input/sprite_sheet.png
  
# Check results in output/busts_sprite_sheet/
```

### Example 2: Batch Convert to WebP
```bash
# Process all PNGs, convert to WebP
docker run --rm \
  -v $(pwd)/sprites:/input:ro \
  -v $(pwd)/output:/output \
  bust-extractor "/input/*.png" \
  --format webp \
  --quality 85
```

### Example 3: Custom Everything
```bash
docker run --rm \
  -v $(pwd):/input:ro \
  -v $(pwd)/custom_output:/output \
  bust-extractor /input/characters.png \
  -o /output/my_characters \
  --format webp \
  --quality 90 \
  --padding 40 \
  --bg-tolerance 35 \
  --names "idle,happy,angry,thinking" \
  --verbose
```

## Notes

- Container runs as root by default - consider using `--user` flag for production
- Input is mounted read-only for safety
- Output directory is created automatically
- Container removes itself after processing (--rm flag)
- No automatic startup - runs only when invoked
