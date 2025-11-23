#!/usr/bin/env python3
"""
Character Bust Extractor - Professional Advanced Version
=========================================================

A professional tool for extracting character busts from sprite sheets with
automatic detection, background removal, and batch processing capabilities.

Features:
    - Automatic bust detection (no fixed columns)
    - Color-based or AI-powered background removal
    - PNG or WebP output with optimization
    - Batch processing support
    - Connected components analysis for fragment removal
    - Smart cropping with configurable padding

Usage:
    # Single file processing with automatic output directory
    python bust_extractor_advanced.py sprite_sheet.png

    # Single file with custom output directory
    python bust_extractor_advanced.py sprite_sheet.png -o my_output

    # Single file with WebP output
    python bust_extractor_advanced.py sprite_sheet.png --format webp

    # Single file with AI background removal
    python bust_extractor_advanced.py sprite_sheet.png --bg-method ai

    # Batch processing - all PNG files in directory
    python bust_extractor_advanced.py "*.png"

    # Batch processing with specific pattern
    python bust_extractor_advanced.py "characters_*.png" --format webp

    # Full configuration example
    python bust_extractor_advanced.py sprite.png \\
        --output-dir custom_output \\
        --format webp \\
        --quality 90 \\
        --padding 40 \\
        --bg-method ai \\
        --bg-tolerance 35 \\
        --names "idle,happy,angry,thinking"

Arguments:
    input_pattern       Input file or glob pattern (e.g., "*.png", "chars_*.jpg")
    -o, --output-dir    Output directory (default: auto-generated from filename)
    -f, --format        Output format: 'png' or 'webp' (default: png)
    -q, --quality       Output quality 1-100 (default: 95)
    -p, --padding       Padding around busts in pixels (default: 30)
    -b, --bg-method     Background removal: 'color' or 'ai' (default: color)
    -t, --bg-tolerance  Color tolerance for color-based removal (default: 30)
    -n, --names         Comma-separated bust names (default: idle,happy,angry,thinking,...)
    --no-preview        Skip preview generation
    -v, --verbose       Enable verbose output

Examples:
    # Process single file with defaults
    $ python bust_extractor_advanced.py my_sprites.png
    
    # Batch process all PNGs, output as WebP
    $ python bust_extractor_advanced.py "*.png" --format webp --quality 90
    
    # Use AI background removal for complex backgrounds
    $ python bust_extractor_advanced.py photo_sprites.jpg --bg-method ai
    
    # Custom names for 6 busts
    $ python bust_extractor_advanced.py chars.png \\
        --names "normal,smile,frown,surprised,thinking,angry"

Requirements:
    - Pillow>=10.0.0
    - numpy>=1.24.0
    - scipy>=1.11.0
    
    Optional (for AI background removal):
    - rembg>=2.0.50
    - onnxruntime>=1.16.0

Author: raven2cz
Version: 4.0
License: MIT
"""

import os
import sys
import argparse
import glob
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
from collections import Counter

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage


@dataclass
class BustConfig:
    """Configuration for bust extraction."""
    
    input_path: str
    output_dir: Optional[str] = None
    output_format: str = "png"  # 'png' or 'webp'
    quality: int = 95
    padding: int = 30
    bg_method: str = "color"  # 'color' or 'ai'
    bg_tolerance: int = 30
    names: Optional[List[str]] = None
    generate_preview: bool = True
    verbose: bool = False


class BustExtractor:
    """
    Advanced character bust extractor with automatic detection.
    
    This extractor uses connected components analysis to automatically detect
    bust regions without requiring fixed column divisions. It supports both
    color-based and AI-powered background removal.
    """
    
    # Default bust names for auto-naming
    DEFAULT_NAMES = ["idle", "happy", "angry", "thinking", "surprised", "sad", 
                     "confused", "excited", "tired", "determined"]
    
    def __init__(self, config: BustConfig):
        """
        Initialize the bust extractor.
        
        Args:
            config: Configuration object with extraction parameters
        """
        self.config = config
        self.image = None
        self.busts = []
        
        # Lazy import of rembg only if AI method is selected
        self.rembg_remove = None
        if config.bg_method == "ai":
            try:
                from rembg import remove
                self.rembg_remove = remove
                if config.verbose:
                    print("✓ AI background removal enabled (rembg)")
            except ImportError:
                print("ERROR: AI background removal requires 'rembg' package.")
                print("Install with: pip install rembg onnxruntime")
                sys.exit(1)
        
    def log(self, message: str, force: bool = False):
        """
        Log a message if verbose mode is enabled.
        
        Args:
            message: Message to log
            force: Force output even if not verbose
        """
        if self.config.verbose or force:
            print(message)
    
    def load_image(self) -> bool:
        """
        Load the input image.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.image = Image.open(self.config.input_path).convert('RGB')
            self.log(f"✓ Loaded: {self.config.input_path}", force=True)
            self.log(f"  Size: {self.image.size[0]}x{self.image.size[1]}px")
            return True
        except Exception as e:
            print(f"✗ Error loading image: {e}")
            return False
    
    def detect_background_color(self, image: Image.Image) -> Tuple[int, int, int]:
        """
        Detect the dominant background color from image corners.
        
        Args:
            image: PIL Image
            
        Returns:
            RGB tuple of the most common corner color
        """
        corners = [
            image.getpixel((0, 0)),
            image.getpixel((image.width - 1, 0)),
            image.getpixel((0, image.height - 1)),
            image.getpixel((image.width - 1, image.height - 1))
        ]
        
        # Find most common corner color
        bg_color = Counter(corners).most_common(1)[0][0]
        self.log(f"  Background color: RGB{bg_color}")
        
        return bg_color
    
    def remove_background_color(self, image: Image.Image) -> Image.Image:
        """
        Remove background using color-based detection.
        
        This method is fast and works well for solid color backgrounds
        (black, white, green screen, etc.)
        
        Args:
            image: Input PIL Image
            
        Returns:
            PIL Image with transparent background
        """
        self.log("  Method: Color-based detection")
        
        # Detect background color
        bg_color = self.detect_background_color(image)
        
        # Convert to RGBA
        img_rgba = image.convert('RGBA')
        data = np.array(img_rgba)
        
        # Calculate Euclidean distance in RGB space
        bg_array = np.array(bg_color)
        rgb_data = data[:, :, :3]
        distance = np.sqrt(np.sum((rgb_data - bg_array) ** 2, axis=2))
        
        # Create alpha mask based on tolerance
        tolerance = self.config.bg_tolerance
        alpha = np.where(distance < tolerance, 0, 255).astype(np.uint8)
        
        # Smooth edges for better quality
        alpha_smoothed = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(1))
        data[:, :, 3] = np.array(alpha_smoothed)
        
        return Image.fromarray(data, 'RGBA')
    
    def remove_background_ai(self, image: Image.Image) -> Image.Image:
        """
        Remove background using AI (rembg U2-Net).
        
        This method is slower but works with complex backgrounds like
        photographs or gradient backgrounds.
        
        Args:
            image: Input PIL Image
            
        Returns:
            PIL Image with transparent background
        """
        self.log("  Method: AI-powered (U2-Net)")
        
        # Convert to RGB for rembg
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Use rembg for background removal
        return self.rembg_remove(image)
    
    def remove_background(self, image: Image.Image) -> Image.Image:
        """
        Remove background from image using configured method.
        
        Args:
            image: Input PIL Image
            
        Returns:
            PIL Image with transparent background
        """
        if self.config.bg_method == "ai":
            return self.remove_background_ai(image)
        else:
            return self.remove_background_color(image)
    
    def detect_bust_regions(self, image: Image.Image) -> List[Tuple[int, int, int, int]]:
        """
        Automatically detect bust regions using connected components analysis.
        
        This method finds all connected regions in the image and filters them
        to identify the main character busts, sorting them left to right.
        
        Args:
            image: PIL Image with alpha channel
            
        Returns:
            List of (left, top, right, bottom) bounding boxes for each bust
        """
        self.log("\nDetecting bust regions...")
        
        # Get alpha channel
        data = np.array(image)
        alpha = data[:, :, 3]
        
        # Create binary mask (threshold at 10 to ignore nearly-transparent pixels)
        binary_mask = alpha > 10
        
        # Label all connected components
        labeled_array, num_features = ndimage.label(binary_mask)
        self.log(f"  Found {num_features} connected components")
        
        # Analyze each component
        regions = []
        for i in range(1, num_features + 1):
            component_mask = (labeled_array == i)
            
            # Find bounding box
            rows = np.any(component_mask, axis=1)
            cols = np.any(component_mask, axis=0)
            
            if not np.any(rows) or not np.any(cols):
                continue
            
            rmin, rmax = np.where(rows)[0][[0, -1]]
            cmin, cmax = np.where(cols)[0][[0, -1]]
            
            # Calculate properties
            area = np.sum(component_mask)
            center_x = (cmin + cmax) / 2
            
            regions.append({
                'bbox': (cmin, rmin, cmax, rmax),
                'area': area,
                'center_x': center_x
            })
        
        # Sort by horizontal position (left to right)
        regions.sort(key=lambda r: r['center_x'])
        
        # Filter out small fragments (keep only large busts)
        # Assume main busts are at least 10% of the largest component
        if regions:
            max_area = max(r['area'] for r in regions)
            threshold = max_area * 0.1
            regions = [r for r in regions if r['area'] >= threshold]
        
        self.log(f"  Identified {len(regions)} main bust(s)")
        
        # Extract and log bounding boxes
        bboxes = [r['bbox'] for r in regions]
        for i, bbox in enumerate(bboxes):
            left, top, right, bottom = bbox
            width, height = right - left, bottom - top
            self.log(f"  Bust {i+1}: pos=({left},{top}), size={width}x{height}px")
        
        return bboxes
    
    def extract_bust(self, image: Image.Image, bbox: Tuple[int, int, int, int]) -> Image.Image:
        """
        Extract a bust region with padding and cleanup.
        
        Args:
            image: Full image with transparent background
            bbox: Bounding box (left, top, right, bottom)
            
        Returns:
            Extracted and cleaned bust image
        """
        left, top, right, bottom = bbox
        
        # Add padding
        padding = self.config.padding
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(image.width, right + padding)
        bottom = min(image.height, bottom + padding)
        
        # Extract region
        bust = image.crop((left, top, right, bottom))
        
        # Isolate main component (remove any remaining fragments)
        bust = self.isolate_main_component(bust)
        
        # Final trim to actual content
        final_bbox = bust.getbbox()
        if final_bbox:
            bust = bust.crop(final_bbox)
        
        return bust
    
    def isolate_main_component(self, image: Image.Image) -> Image.Image:
        """
        Keep only the largest connected component, removing fragments.
        
        Args:
            image: PIL Image with alpha channel
            
        Returns:
            PIL Image with only the main component
        """
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        data = np.array(image)
        alpha = data[:, :, 3]
        
        # Binary mask
        binary_mask = alpha > 10
        
        # Label components
        labeled_array, num_features = ndimage.label(binary_mask)
        
        if num_features == 0:
            return image
        
        # Find largest component
        component_sizes = [(np.sum(labeled_array == i), i) 
                          for i in range(1, num_features + 1)]
        
        if not component_sizes:
            return image
        
        largest_component = max(component_sizes, key=lambda x: x[0])[1]
        
        # Create mask with only largest component
        isolated_mask = (labeled_array == largest_component).astype(np.uint8) * 255
        
        # Apply mask to alpha channel
        result_data = data.copy()
        result_data[:, :, 3] = np.minimum(data[:, :, 3], isolated_mask)
        
        if num_features > 1:
            self.log(f"    Removed {num_features - 1} fragment(s)")
        
        return Image.fromarray(result_data, 'RGBA')
    
    def save_bust(self, bust: Image.Image, name: str, output_dir: Path):
        """
        Save a bust image in the configured format.
        
        Args:
            bust: PIL Image to save
            name: Base filename (without extension)
            output_dir: Output directory path
        """
        # Determine file extension and format
        if self.config.output_format.lower() == "webp":
            ext = "webp"
            save_format = "WebP"
            # WebP specific options
            save_kwargs = {
                'quality': self.config.quality,
                'method': 6,  # Best compression
                'lossless': self.config.quality >= 100
            }
        else:
            ext = "png"
            save_format = "PNG"
            # PNG specific options
            save_kwargs = {
                'optimize': True,
                'compress_level': 9 if self.config.quality >= 90 else 6
            }
        
        # Save file
        output_file = output_dir / f"{name}.{ext}"
        bust.save(output_file, save_format, **save_kwargs)
        
        return output_file
    
    def create_preview(self, output_dir: Path):
        """
        Create a preview image showing all extracted busts side by side.
        
        Args:
            output_dir: Output directory for preview
        """
        if not self.busts or not self.config.generate_preview:
            return
        
        # Calculate dimensions
        max_height = max(img.height for img in self.busts)
        total_width = sum(img.width for img in self.busts)
        
        # Create preview with dark gray background
        preview = Image.new('RGBA', (total_width, max_height), (50, 50, 50, 255))
        
        # Paste each bust
        x_offset = 0
        for img in self.busts:
            y_offset = (max_height - img.height) // 2
            preview.paste(img, (x_offset, y_offset), img)
            x_offset += img.width
        
        # Save preview
        preview_file = self.save_bust(preview, "preview", output_dir)
        self.log(f"\n✓ Preview: {preview_file}", force=True)
    
    def process(self) -> bool:
        """
        Execute the complete extraction pipeline.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load image
            if not self.load_image():
                return False
            
            # Remove background from entire image
            self.log("\nRemoving background...")
            no_bg_image = self.remove_background(self.image)
            self.log("✓ Background removed")
            
            # Automatically detect bust regions
            bust_bboxes = self.detect_bust_regions(no_bg_image)
            
            if not bust_bboxes:
                print("✗ No busts detected!")
                return False
            
            # Determine output directory
            if self.config.output_dir:
                output_dir = Path(self.config.output_dir)
            else:
                # Auto-generate from input filename
                input_stem = Path(self.config.input_path).stem
                output_dir = Path(f"busts_{input_stem}")
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract each bust
            self.log(f"\nExtracting {len(bust_bboxes)} bust(s)...", force=True)
            
            # Get bust names
            names = self.config.names or self.DEFAULT_NAMES
            
            for i, bbox in enumerate(bust_bboxes):
                name = names[i] if i < len(names) else f"bust_{i+1}"
                
                self.log(f"\nBust {i+1}/{len(bust_bboxes)}: {name}")
                
                # Extract and clean
                bust = self.extract_bust(no_bg_image, bbox)
                self.log(f"  Size: {bust.size[0]}x{bust.size[1]}px")
                
                # Save
                output_file = self.save_bust(bust, name, output_dir)
                self.log(f"  ✓ Saved: {output_file}", force=True)
                
                # Store for preview
                self.busts.append(bust)
            
            # Create preview
            self.create_preview(output_dir)
            
            self.log(f"\n{'='*60}", force=True)
            self.log(f"✓ Success! {len(self.busts)} busts → {output_dir}", force=True)
            self.log(f"{'='*60}", force=True)
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            if self.config.verbose:
                import traceback
                traceback.print_exc()
            return False


def process_single_file(input_file: str, args: argparse.Namespace) -> bool:
    """
    Process a single sprite sheet file.
    
    Args:
        input_file: Path to input file
        args: Command line arguments
        
    Returns:
        True if successful
    """
    # Parse bust names if provided
    names = None
    if args.names:
        names = [n.strip() for n in args.names.split(',')]
    
    # Create configuration
    config = BustConfig(
        input_path=input_file,
        output_dir=args.output_dir,
        output_format=args.format,
        quality=args.quality,
        padding=args.padding,
        bg_method=args.bg_method,
        bg_tolerance=args.bg_tolerance,
        names=names,
        generate_preview=not args.no_preview,
        verbose=args.verbose
    )
    
    # Process
    extractor = BustExtractor(config)
    return extractor.process()


def process_batch(pattern: str, args: argparse.Namespace) -> Tuple[int, int]:
    """
    Process multiple files matching a glob pattern.
    
    Args:
        pattern: Glob pattern (e.g., "*.png", "chars_*.jpg")
        args: Command line arguments
        
    Returns:
        Tuple of (successful_count, failed_count)
    """
    # Find matching files
    files = glob.glob(pattern)
    
    if not files:
        print(f"✗ No files matching pattern: {pattern}")
        return 0, 0
    
    print(f"\nBatch processing: {len(files)} file(s)")
    print("=" * 60)
    
    successful = 0
    failed = 0
    
    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] Processing: {file_path}")
        print("-" * 60)
        
        # For batch processing, auto-generate output dir from filename
        # unless user specified a custom one
        if not args.output_dir:
            # Temporarily set output_dir to None for auto-generation
            args_copy = argparse.Namespace(**vars(args))
            args_copy.output_dir = None
        else:
            args_copy = args
        
        if process_single_file(file_path, args_copy):
            successful += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Batch complete: {successful} successful, {failed} failed")
    print(f"{'='*60}")
    
    return successful, failed


def main():
    """Main entry point with argument parsing."""
    
    parser = argparse.ArgumentParser(
        description="Advanced Character Bust Extractor with automatic detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Single file:
    %(prog)s sprite_sheet.png
    %(prog)s sprite.png -o my_busts --format webp
    %(prog)s photo.jpg --bg-method ai --quality 90
    
  Batch processing:
    %(prog)s "*.png" --format webp
    %(prog)s "characters_*.png" --bg-method ai
    %(prog)s "*.jpg" --padding 40 --names "a,b,c,d"
        """
    )
    
    # Required argument
    parser.add_argument(
        'input_pattern',
        help='Input file or glob pattern (e.g., "*.png", "chars_*.jpg")'
    )
    
    # Output options
    parser.add_argument(
        '-o', '--output-dir',
        help='Output directory (default: auto-generated from filename)'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['png', 'webp'],
        default='png',
        help='Output format (default: png)'
    )
    parser.add_argument(
        '-q', '--quality',
        type=int,
        default=95,
        help='Output quality 1-100 (default: 95)'
    )
    
    # Processing options
    parser.add_argument(
        '-p', '--padding',
        type=int,
        default=30,
        help='Padding around busts in pixels (default: 30)'
    )
    parser.add_argument(
        '-b', '--bg-method',
        choices=['color', 'ai'],
        default='color',
        help='Background removal method (default: color)'
    )
    parser.add_argument(
        '-t', '--bg-tolerance',
        type=int,
        default=30,
        help='Color tolerance for color-based removal (default: 30)'
    )
    
    # Bust naming
    parser.add_argument(
        '-n', '--names',
        help='Comma-separated bust names (e.g., "idle,happy,angry")'
    )
    
    # Flags
    parser.add_argument(
        '--no-preview',
        action='store_true',
        help='Skip preview generation'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate quality
    if not 1 <= args.quality <= 100:
        parser.error("Quality must be between 1 and 100")
    
    # Print header
    print("=" * 60)
    print("Character Bust Extractor v4.0")
    print("=" * 60)
    
    # Check if input is a glob pattern or single file
    if '*' in args.input_pattern or '?' in args.input_pattern:
        # Batch processing
        successful, failed = process_batch(args.input_pattern, args)
        sys.exit(0 if failed == 0 else 1)
    else:
        # Single file processing
        if not os.path.exists(args.input_pattern):
            print(f"✗ File not found: {args.input_pattern}")
            sys.exit(1)
        
        success = process_single_file(args.input_pattern, args)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
