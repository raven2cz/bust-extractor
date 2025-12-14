#!/usr/bin/env python3
"""
Bust Extractor Pro - Backend Server
====================================

Professional web-based application for extracting character portraits (busts)
from sprite sheets with AI-powered background removal.

Features:
    - Multiple AI models: BiRefNet (best), ISNet-Anime, U2Net
    - Hybrid Validator: Smart edge-aware cleanup (Canny + Color Distance)
    - Difference Matting: Hollywood-style 2-image compositing
    - Color Decontamination: Fix semi-transparent edge colors
    - Feathering, Despill, Erode/Dilate morphology
    - Interactive mask editing with undo/redo
    - Sprite sheet generation for animation workflows

Author: raven2cz
Version: 2.0
License: MIT

Usage:
    python server.py
    
    Then open http://localhost:8000 in your browser.
"""

import os
import io
import uuid
import json
import base64
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import cv2

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# =============================================================================
# Logging Configuration
# =============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# Path Configuration
# =============================================================================

BACKEND_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

SESSIONS: Dict[str, "SessionData"] = {}
UPLOAD_DIR = PROJECT_ROOT / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ProcessingParams:
    """
    Parameters for background removal and mask refinement processing.
    
    Attributes:
        bg_method: Background removal method identifier
        bg_tolerance: Color tolerance for background detection (0-100)
        mask_erode: Mask erosion iterations (shrinks mask edges)
        mask_dilate: Mask dilation iterations (expands mask edges)
        alpha_matting: Enable AI alpha matting for softer edges
        cleaning_enabled: Enable artifact cleaning
        hybrid_strength: Strength of hybrid cleanup (0.0-1.0)
        hybrid_edge_radius: Radius for edge detection in hybrid mode
        feather_enabled: Enable edge feathering
        feather_radius: Feather blur radius in pixels
        feather_strength: Feather blend strength (0.0-1.0)
        feather_edge_only: Apply feather only to edge zone
        despill_enabled: Enable color spill removal
        despill_strength: Despill effect strength (0.0-1.0)
        despill_color: Color to remove ('auto', 'green', 'blue', 'red')
        decontaminate_enabled: Enable edge color decontamination
        decontaminate_strength: Decontamination strength (0.0-1.0)
        hybrid_cleansing_enabled: Enable hybrid validator
        min_bust_area_ratio: Minimum bust area as ratio of max (0.0-1.0)
        padding: Padding around extracted busts in pixels
    """
    bg_method: str = "rembg_birefnet-general"
    bg_tolerance: int = 30
    mask_erode: int = 0
    mask_dilate: int = 0
    alpha_matting: bool = False
    cleaning_enabled: bool = False
    hybrid_strength: float = 0.7
    hybrid_edge_radius: int = 5
    feather_enabled: bool = True
    feather_radius: int = 2
    feather_strength: float = 0.5
    feather_edge_only: bool = True
    despill_enabled: bool = False
    despill_strength: float = 0.5
    despill_color: str = "auto"
    decontaminate_enabled: bool = False
    decontaminate_strength: float = 0.5
    hybrid_cleansing_enabled: bool = False
    min_bust_area_ratio: float = 0.05
    padding: int = 30


@dataclass
class BustRegion:
    """
    Represents a detected bust region in the image.
    
    Attributes:
        id: Unique identifier for the bust
        bbox: Bounding box as (left, top, right, bottom)
        center_x: X coordinate of the bust center
        center_y: Y coordinate of the bust center
        area: Area of the bust in pixels
        name: Display name (editable by user)
        offset_x: Horizontal offset for alignment
        offset_y: Vertical offset for alignment
        enabled: Whether to include in export
    """
    id: str
    bbox: Tuple[int, int, int, int]
    center_x: int
    center_y: int
    area: int
    name: str
    offset_x: int = 0
    offset_y: int = 0
    enabled: bool = True


@dataclass
class SessionData:
    """
    Session state for a user's editing session.
    
    Attributes:
        session_id: Unique session identifier
        original_image_path: Path to uploaded original image
        processed_image_path: Path to processed (background removed) image
        mask_path: Path to current mask image
        busts: List of detected bust regions
        params: Processing parameters used
        uniform_size: Target uniform size for export (width, height)
        detected_bg_color: Auto-detected background color (R, G, B)
        auto_tolerance: Auto-calculated tolerance value
    """
    session_id: str
    original_image_path: Optional[str] = None
    processed_image_path: Optional[str] = None
    mask_path: Optional[str] = None
    busts: List[BustRegion] = field(default_factory=list)
    params: ProcessingParams = field(default_factory=ProcessingParams)
    uniform_size: Tuple[int, int] = (0, 0)
    detected_bg_color: Optional[Tuple[int, int, int]] = None
    auto_tolerance: int = 30


# =============================================================================
# Background Removal Engine
# =============================================================================


class BackgroundRemover:
    """
    Handles background removal using various AI models and algorithms.
    
    Supports multiple removal methods:
    - BiRefNet: Best quality edge detection
    - ISNet-Anime: Optimized for anime/cartoon images
    - U2Net: Fast general-purpose model
    - Color-based: Classic chroma keying
    - Difference Matting: Professional 2-image compositing
    """
    
    def __init__(self):
        """Initialize the background remover with no active session."""
        self.rembg_session = None
        self.current_model = None
        
    def get_rembg_session(self, model_name: str):
        """
        Get or create a RemBG session for the specified model.
        
        Args:
            model_name: Model identifier (may include 'rembg_' prefix)
            
        Returns:
            RemBG session object for the model
            
        Note:
            Falls back to u2net if requested model is unavailable.
        """
        # Strip prefix if present
        if model_name.startswith("rembg_"):
            actual_model = model_name.replace("rembg_", "")
        else:
            actual_model = model_name

        # Create new session if model changed
        if self.current_model != actual_model:
            try:
                from rembg import new_session
                logger.info(f"Loading RemBG model: {actual_model}")
                self.rembg_session = new_session(actual_model)
                self.current_model = actual_model
            except Exception as e:
                logger.warning(f"Failed to load {actual_model}: {e}, falling back to u2net")
                from rembg import new_session
                self.rembg_session = new_session("u2net")
                self.current_model = "u2net"
        return self.rembg_session
    
    def analyze_histogram(self, image: Image.Image) -> Tuple[Tuple[int, int, int], int]:
        """
        Analyze image edges to detect background color and optimal tolerance.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Tuple of (background_color, suggested_tolerance) where:
            - background_color is (R, G, B) tuple
            - suggested_tolerance is an integer 20-80
        """
        rgb = image.convert("RGB") if image.mode != "RGB" else image
        w, h = rgb.size
        
        # Sample pixels from image edges
        edge_pixels = []
        for x in range(0, w, max(1, w // 50)):
            for y in range(min(30, h // 8)):
                edge_pixels.append(rgb.getpixel((x, y)))
                edge_pixels.append(rgb.getpixel((x, h - 1 - y)))
        
        for y in range(0, h, max(1, h // 50)):
            for x in range(min(30, w // 8)):
                edge_pixels.append(rgb.getpixel((x, y)))
                edge_pixels.append(rgb.getpixel((w - 1 - x, y)))
        
        if not edge_pixels:
            return ((128, 128, 128), 30)
        
        # Find most common color (quantized)
        pixels_array = np.array(edge_pixels)
        quantized = (pixels_array // 4) * 4
        tuples = [tuple(int(x) for x in p) for p in quantized]
        counter = Counter(tuples)
        
        bg_color = counter.most_common(1)[0][0]
        bg_array = np.array(bg_color)
        distances = np.sqrt(np.sum((pixels_array.astype(float) - bg_array) ** 2, axis=1))
        
        # Calculate optimal tolerance
        close_mask = distances < 40
        if np.sum(close_mask) > 20:
            close_distances = distances[close_mask]
            base_tolerance = float(np.percentile(close_distances, 99))
            color_std = float(np.std(pixels_array[close_mask]))
            margin = max(10, color_std * 1.5)
            tolerance = int(base_tolerance + margin)
            tolerance = max(20, min(80, tolerance))
        else:
            tolerance = 35
        
        logger.info(f"Histogram: bg={bg_color}, tolerance={tolerance}")
        bg_color = tuple(int(x) for x in bg_color)
        return (bg_color, int(tolerance))
    
    def remove_background(
        self, 
        image: Image.Image, 
        method: str, 
        tolerance: int, 
        alpha_matting: bool,
        hybrid_strength: float = 0.7,
        hybrid_edge_radius: int = 5
    ) -> Tuple[Image.Image, Image.Image, Optional[Tuple]]:
        """
        Main background removal dispatcher.
        
        Args:
            image: Input PIL Image
            method: Removal method identifier
            tolerance: Color tolerance for color-based methods
            alpha_matting: Enable alpha matting for AI methods
            hybrid_strength: Strength for hybrid method
            hybrid_edge_radius: Edge radius for hybrid method
            
        Returns:
            Tuple of (result_image, mask_image, detected_bg_color)
        """
        if method == "difference_matting":
            # Handled separately via process_difference_matting
            return image, image.split()[3] if image.mode == 'RGBA' else Image.new("L", image.size, 255), None
        elif method == "color_based":
            return self._remove_bg_color(image, tolerance)
        elif method == "hybrid":
            return self._remove_bg_hybrid(image, tolerance, alpha_matting, 
                                          hybrid_strength, hybrid_edge_radius)
        else:
            return (*self._remove_bg_rembg(image, method, alpha_matting), None)

    def process_difference_matting(
        self, 
        img_white: Image.Image, 
        img_black: Image.Image
    ) -> Image.Image:
        """
        Professional difference matting using white and black background images.
        
        This Hollywood-style technique recovers perfect transparency by comparing
        renders on white and black backgrounds using the formula:
        
        Alpha = 1 - (White - Black) / 255
        
        Args:
            img_white: Image rendered on white background
            img_black: Image rendered on black background
            
        Returns:
            RGBA image with recovered transparency
        """
        # Ensure identical size
        if img_white.size != img_black.size:
            img_black = img_black.resize(img_white.size)
        
        # Convert to numpy float
        w_arr = np.array(img_white.convert("RGB")).astype(np.float32)
        b_arr = np.array(img_black.convert("RGB")).astype(np.float32)
        
        # Calculate alpha from difference
        # I_w - I_b = (1-alpha) * 255
        diff = w_arr - b_arr
        diff_val = np.mean(diff, axis=2)
        
        alpha = 255.0 - diff_val
        alpha = np.clip(alpha, 0, 255).astype(np.uint8)
        
        # Return black-bg image with calculated alpha
        result = img_black.convert("RGBA")
        result.putalpha(Image.fromarray(alpha))
        return result
    
    def _remove_bg_rembg(
        self, 
        image: Image.Image, 
        method: str, 
        alpha_matting: bool
    ) -> Tuple[Image.Image, Image.Image]:
        """
        Standard RemBG AI model processing.
        
        Args:
            image: Input PIL Image
            method: Model name (with or without 'rembg_' prefix)
            alpha_matting: Enable alpha matting refinement
            
        Returns:
            Tuple of (result_rgba_image, mask_grayscale_image)
        """
        from rembg import remove
        session = self.get_rembg_session(method)
        rgb = image.convert("RGB") if image.mode != "RGB" else image
        
        if alpha_matting:
            result = remove(
                rgb, 
                session=session, 
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10
            )
        else:
            result = remove(rgb, session=session)
        
        mask = result.split()[3] if result.mode == "RGBA" else Image.new("L", result.size, 255)
        return result, mask
    
    def _remove_bg_color(
        self, 
        image: Image.Image, 
        tolerance: int
    ) -> Tuple[Image.Image, Image.Image, Tuple]:
        """
        Color-based background removal using corner sampling.
        
        Args:
            image: Input PIL Image
            tolerance: Color distance tolerance
            
        Returns:
            Tuple of (result_image, mask_image, detected_bg_color)
        """
        rgb = image.convert("RGB") if image.mode == "RGBA" else image
        w, h = rgb.size
        
        # Sample corners and edges
        samples = [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1), 
                   (w//2, 0), (w//2, h-1), (0, h//2), (w-1, h//2)]
        colors = [rgb.getpixel(p) for p in samples]
        bg_color = Counter(colors).most_common(1)[0][0]
        
        # Calculate distance and create mask
        data = np.array(rgb).astype(np.float32)
        dist = np.sqrt(np.sum((data - np.array(bg_color)) ** 2, axis=2))
        alpha = np.where(dist < tolerance, 0, 255).astype(np.uint8)
        
        result = rgb.convert("RGBA")
        result.putalpha(Image.fromarray(alpha))
        
        bg_color = tuple(int(x) for x in bg_color)
        return result, Image.fromarray(alpha), bg_color
    
    def _remove_bg_hybrid(
        self, 
        image: Image.Image, 
        tolerance: int, 
        alpha_matting: bool,
        strength: float, 
        edge_radius: int
    ) -> Tuple[Image.Image, Image.Image, Tuple]:
        """
        Hybrid method combining BiRefNet quality with color-based cleanup.
        
        Strategy:
        1. Run BiRefNet for high-quality edge detection
        2. Detect background color from image edges
        3. Calculate color distance for all pixels
        4. Refine alpha in edge zones using color distance
        5. Clean suspicious interior pixels near edges
        
        Args:
            image: Input PIL Image
            tolerance: Color tolerance for cleanup
            alpha_matting: Enable alpha matting in AI step
            strength: Blend strength for color refinement (0.0-1.0)
            edge_radius: Radius for edge zone expansion
            
        Returns:
            Tuple of (result_image, mask_image, detected_bg_color)
        """
        logger.info(f"Hybrid processing: tolerance={tolerance}, strength={strength}, edge_radius={edge_radius}")
        
        # Step 1: Get BiRefNet mask
        from rembg import remove
        session = self.get_rembg_session("birefnet-general")
        rgb = image.convert("RGB") if image.mode != "RGB" else image
        
        if alpha_matting:
            ai_result = remove(
                rgb, 
                session=session, 
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10
            )
        else:
            ai_result = remove(rgb, session=session)
        
        ai_mask = np.array(ai_result.split()[3]).astype(np.float32)
        
        # Step 2: Detect background color
        w, h = rgb.size
        samples = [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1), 
                   (w//2, 0), (w//2, h-1), (0, h//2), (w-1, h//2)]
        edge_colors = [rgb.getpixel(p) for p in samples]
        bg_color = Counter(edge_colors).most_common(1)[0][0]
        bg_array = np.array(bg_color).astype(np.float32)
        
        logger.info(f"Hybrid: detected bg_color={bg_color}")
        
        # Step 3: Calculate color distance
        rgb_data = np.array(rgb).astype(np.float32)
        color_dist = np.sqrt(np.sum((rgb_data - bg_array) ** 2, axis=2))
        color_factor = np.clip(color_dist / tolerance, 0, 1)
        
        # Step 4: Define zones
        interior_mask = ai_mask > 250
        edge_mask = (ai_mask > 10) & (ai_mask <= 250)
        
        # Expand edge zone
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (edge_radius*2+1, edge_radius*2+1))
        interior_eroded = cv2.erode(interior_mask.astype(np.uint8), kernel).astype(bool)
        expanded_edge = interior_mask & ~interior_eroded
        
        # Step 5: Apply hybrid refinement
        new_mask = ai_mask.copy()
        
        # 5a: Refine edge zone
        edge_refinement = ai_mask[edge_mask] * (1.0 - strength + strength * color_factor[edge_mask])
        new_mask[edge_mask] = edge_refinement
        
        # 5b: Clean suspicious interior pixels
        suspicious = expanded_edge & (color_dist < tolerance * 0.6)
        if np.any(suspicious):
            suspicion_factor = color_dist[suspicious] / (tolerance * 0.6)
            suspicion_factor = np.clip(suspicion_factor, 0.3, 1.0)
            new_mask[suspicious] = ai_mask[suspicious] * suspicion_factor
            logger.info(f"Hybrid: cleaned {np.sum(suspicious)} suspicious pixels near edges")
        
        # 5c: Deep interior cleanup
        deep_interior = interior_eroded
        very_bg_like = color_dist < tolerance * 0.4
        deep_suspicious = deep_interior & very_bg_like
        if np.any(deep_suspicious):
            factor = color_dist[deep_suspicious] / (tolerance * 0.4)
            factor = np.clip(factor, 0.5, 1.0)
            new_mask[deep_suspicious] = ai_mask[deep_suspicious] * factor * 0.7
            logger.info(f"Hybrid: cleaned {np.sum(deep_suspicious)} deep interior pixels")
        
        # Step 6: Create result
        new_mask = np.clip(new_mask, 0, 255).astype(np.uint8)
        result = rgb.convert("RGBA")
        result.putalpha(Image.fromarray(new_mask))
        
        bg_color = tuple(int(x) for x in bg_color)
        logger.info("Hybrid: processing complete")
        
        return result, Image.fromarray(new_mask), bg_color


# =============================================================================
# Edge Refinement Engine
# =============================================================================


class EdgeRefiner:
    """
    Provides mask refinement and edge cleanup operations.
    
    Includes morphological operations, feathering, despill,
    color decontamination, and hybrid edge-aware cleanup.
    """
    
    @staticmethod
    def refine_mask(mask: Image.Image, erode: int, dilate: int) -> Image.Image:
        """
        Apply morphological erosion and/or dilation to mask.
        
        Erosion shrinks the mask, removing thin protrusions.
        Dilation expands the mask, filling small holes.
        
        Args:
            mask: Grayscale mask image
            erode: Erosion iterations (0 to skip)
            dilate: Dilation iterations (0 to skip)
            
        Returns:
            Refined mask image
        """
        if erode == 0 and dilate == 0:
            return mask
            
        mask_data = np.array(mask)
        
        if erode > 0:
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (erode * 2 + 1, erode * 2 + 1)
            )
            mask_data = cv2.erode(mask_data, kernel)
            
        if dilate > 0:
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (dilate * 2 + 1, dilate * 2 + 1)
            )
            mask_data = cv2.dilate(mask_data, kernel)
            
        return Image.fromarray(mask_data)
    
    @staticmethod
    def clean_artifacts(image: Image.Image) -> Image.Image:
        """
        Remove gray/white halos by extending core colors to edges.
        
        Strategy:
        1. Identify fully opaque 'core' pixels (alpha > 240)
        2. Dilate core colors outward
        3. Replace semi-transparent edge pixels with dilated colors
        
        Args:
            image: RGBA image with potential edge halos
            
        Returns:
            RGBA image with cleaned edges
        """
        img_arr = np.array(image)
        if img_arr.shape[2] < 4:
            return image
            
        alpha = img_arr[:, :, 3]
        rgb = img_arr[:, :, :3]
        
        # Find opaque core
        core_mask = alpha > 240
        if not np.any(core_mask):
            return image
        
        # Find semi-transparent edges
        edge_mask = (alpha > 0) & (alpha <= 240)
        if not np.any(edge_mask):
            return image
        
        # Create source from core only
        clean_rgb = rgb.copy()
        clean_rgb[~core_mask] = 0
        
        # Dilate core colors outward
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilated_rgb = clean_rgb.copy()
        for _ in range(3):
            dilated_rgb = cv2.dilate(dilated_rgb, kernel)
        
        # Replace edge colors with dilated core
        result_rgb = rgb.copy()
        replace_mask = alpha < 250
        result_rgb[replace_mask] = dilated_rgb[replace_mask]
        
        result = np.dstack((result_rgb, alpha))
        return Image.fromarray(result, "RGBA")
    
    @staticmethod
    def feather_edges(
        image: Image.Image, 
        mask: Image.Image, 
        radius: int, 
        strength: float, 
        edge_only: bool = True
    ) -> Image.Image:
        """
        Apply gaussian blur feathering to mask edges.
        
        Creates soft, natural transitions at object boundaries.
        Can be applied to edge zone only or entire mask.
        
        Args:
            image: RGBA image to modify
            mask: Grayscale mask defining object
            radius: Blur radius in pixels
            strength: Blend strength (0.0-1.0)
            edge_only: If True, only feather edge zone
            
        Returns:
            RGBA image with feathered edges
        """
        if radius <= 0 or strength <= 0:
            return image
        
        img_data = np.array(image)
        mask_data = np.array(mask).astype(np.float32)
        
        # Gaussian blur the mask
        kernel_size = radius * 2 + 1
        blurred = cv2.GaussianBlur(mask_data, (kernel_size, kernel_size), 0)
        
        if edge_only:
            # Define edge zone via erosion/dilation
            eroded = cv2.erode(
                mask_data, np.ones((3, 3), np.uint8), iterations=radius
            )
            dilated = cv2.dilate(
                mask_data, np.ones((3, 3), np.uint8), iterations=radius
            )
            edge_zone = (dilated > 0) & (eroded < 255)
            
            # Blend only in edge zone
            new_alpha = mask_data.copy()
            new_alpha[edge_zone] = (
                mask_data[edge_zone] * (1 - strength) + 
                blurred[edge_zone] * strength
            )
            
            # Protect interior
            interior = eroded >= 250
            new_alpha[interior] = 255
        else:
            # Feather entire mask
            new_alpha = mask_data * (1 - strength) + blurred * strength
        
        img_data[:, :, 3] = np.clip(new_alpha, 0, 255).astype(np.uint8)
        return Image.fromarray(img_data, "RGBA")
    
    @staticmethod
    def despill(
        image: Image.Image, 
        strength: float, 
        color: str, 
        bg_color: Optional[Tuple[int, int, int]]
    ) -> Image.Image:
        """
        Remove color spill from green/blue/red screen backgrounds.
        
        Reduces dominant color channel in semi-transparent edge pixels
        based on the detected or specified background color.
        
        Args:
            image: RGBA image with potential color spill
            strength: Effect strength (0.0-1.0)
            color: Target color ('auto', 'green', 'blue', 'red')
            bg_color: Detected background color for auto-detection
            
        Returns:
            RGBA image with reduced color spill
        """
        if strength <= 0:
            return image
        
        data = np.array(image).astype(np.float32)
        r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
        
        # Find semi-transparent edges
        edge = (a > 10) & (a < 250)
        if not np.any(edge):
            return image
        
        # Determine dominant spill color
        if color == "auto":
            if bg_color:
                br, bg_, bb = bg_color
                if bg_ > br * 1.2 and bg_ > bb * 1.2:
                    dom = "green"
                elif br > bg_ * 1.2 and br > bb * 1.2:
                    dom = "red"
                elif bb > br * 1.2 and bb > bg_ * 1.2:
                    dom = "blue"
                else:
                    dom = None
            else:
                dom = None
            if not dom:
                return image
        else:
            dom = color
        
        # Calculate effect weight based on alpha
        aw = 1.0 - (a[edge] / 255.0)
        eff = strength * aw
        
        # Remove excess color
        if dom == "green":
            exc = np.maximum(0, g[edge] - (r[edge] + b[edge]) / 2)
            g[edge] -= exc * eff
        elif dom == "red":
            exc = np.maximum(0, r[edge] - (g[edge] + b[edge]) / 2)
            r[edge] -= exc * eff
        elif dom == "blue":
            exc = np.maximum(0, b[edge] - (r[edge] + g[edge]) / 2)
            b[edge] -= exc * eff
        
        data[:, :, 0] = np.clip(r, 0, 255)
        data[:, :, 1] = np.clip(g, 0, 255)
        data[:, :, 2] = np.clip(b, 0, 255)
        
        return Image.fromarray(data.astype(np.uint8), "RGBA")
    
    @staticmethod
    def decontaminate_edges(
        image: Image.Image, 
        strength: float, 
        threshold: int = 250
    ) -> Image.Image:
        """
        Color decontamination: extend opaque colors to semi-transparent edges.
        
        Removes halos (green/white/gray/black) from hair strands and fine
        details by replacing edge colors with their nearest opaque neighbors.
        
        Args:
            image: RGBA image with edge color contamination
            strength: Blend strength (0.0-1.0)
            threshold: Alpha value defining core vs edge (0-255)
                       Pixels above this are 'core' (source)
                       Pixels below are 'edges' (target)
                       
        Returns:
            RGBA image with decontaminated edges
        """
        if strength <= 0:
            return image
            
        img_arr = np.array(image)
        if img_arr.shape[2] < 4:
            return image
            
        alpha = img_arr[:, :, 3]
        rgb = img_arr[:, :, :3]
        
        # Define core (opaque) and edge (semi-transparent) zones
        opaque_mask = alpha > threshold
        semi_mask = (alpha > 0) & (alpha <= threshold)
        
        if not np.any(semi_mask) or not np.any(opaque_mask):
            return image
            
        # Create source from opaque pixels only
        source_rgb = rgb.copy()
        source_rgb[~opaque_mask] = 0
        
        # Iterative dilation to extend colors
        iterations = int(max(1, strength * 10))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        
        valid_mask = opaque_mask.astype(np.uint8)
        current_rgb = source_rgb.copy()
        current_mask = valid_mask.copy()
        
        for _ in range(iterations):
            dilated_mask = cv2.dilate(current_mask, kernel)
            new_pixels = (dilated_mask == 1) & (current_mask == 0)
            
            if not np.any(new_pixels):
                break
                
            dilated_rgb = cv2.dilate(current_rgb, kernel)
            current_rgb[new_pixels] = dilated_rgb[new_pixels]
            current_mask = dilated_mask
            
        # Apply to result with blending
        result_rgb = rgb.copy()
        
        if strength >= 0.99:
            result_rgb[semi_mask] = current_rgb[semi_mask]
        else:
            orig = result_rgb[semi_mask].astype(np.float32)
            new_c = current_rgb[semi_mask].astype(np.float32)
            val = orig * (1.0 - strength) + new_c * strength
            result_rgb[semi_mask] = val.astype(np.uint8)
            
        result = np.dstack((result_rgb, alpha))
        return Image.fromarray(result, "RGBA")
    
    @staticmethod
    def hybrid_cleansing(
        ai_mask: Image.Image, 
        original_image: Image.Image,
        bg_color: Tuple[int, int, int], 
        tolerance: int,
        erosion_size: int = 2
    ) -> Image.Image:
        """
        Hybrid Validator: Smart edge-aware background cleanup.
        
        Identifies discrepancies where AI detected foreground but color
        analysis indicates background. Uses Canny edge detection to
        protect line art while aggressively removing background artifacts.
        
        Algorithm:
        1. Calculate color distance from background
        2. Find error regions (AI=FG, Color=BG)
        3. Detect edges (line art) via Canny
        4. For holes near edges: erode to protect lines
        5. For holes far from edges: cut cleanly
        6. Apply with feathered transitions
        
        Args:
            ai_mask: Mask from AI model
            original_image: Original RGB image
            bg_color: Detected background color (R, G, B)
            tolerance: Color distance tolerance
            erosion_size: Safety margin for edge protection
            
        Returns:
            Cleaned mask image
        """
        ai_arr = np.array(ai_mask)
        rgb = np.array(original_image.convert("RGB")).astype(np.float32)
        bg_arr = np.array(bg_color).astype(np.float32)
        
        # Calculate color distance from background
        dist = np.sqrt(np.sum((rgb - bg_arr) ** 2, axis=2))
        
        # Find discrepancy: AI says FG, Color says BG
        color_is_bg = dist < tolerance
        ai_is_fg = ai_arr > 50
        error_region = ai_is_fg & color_is_bg
        
        if not np.any(error_region):
            return ai_mask
        
        # Detect edges (line art protection)
        gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_buffer = cv2.dilate(
            edges, 
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), 
            iterations=2
        )
        
        # Connected component analysis
        error_mask_uint = error_region.astype(np.uint8)
        min_area_noise = 20
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            error_mask_uint, connectivity=8
        )
        
        final_error_mask = np.zeros_like(error_mask_uint)
        
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < min_area_noise:
                continue
            
            comp_mask = (labels == i).astype(np.uint8)
            
            # Check if hole overlaps with line art
            is_eating_line = np.any((comp_mask == 1) & (edge_buffer > 0))
            
            if is_eating_line:
                # Near line: erode to protect
                if erosion_size > 0:
                    safe_cut = cv2.erode(
                        comp_mask, 
                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), 
                        iterations=erosion_size
                    )
                    final_error_mask = cv2.bitwise_or(final_error_mask, safe_cut)
                else:
                    final_error_mask = cv2.bitwise_or(final_error_mask, comp_mask)
            else:
                # Far from lines: cut cleanly
                final_error_mask = cv2.bitwise_or(final_error_mask, comp_mask)
        
        # Scale and smooth
        error_mask = final_error_mask * 255
        if error_mask.max() > 0:
            error_mask = cv2.GaussianBlur(error_mask, (3, 3), 0)
        
        # Subtract from AI mask with feathering
        result_mask = ai_arr.copy()
        try:
            norm_err = error_mask.astype(float) / 255.0
            inv_err = 1.0 - norm_err
            current_alpha = result_mask.astype(float)
            new_alpha = current_alpha * inv_err
            result_mask = new_alpha.astype(np.uint8)
        except Exception:
            result_mask[error_mask > 127] = 0
        
        return Image.fromarray(result_mask)


# =============================================================================
# Bust Detection Engine
# =============================================================================


class BustSegmenter:
    """
    Detects and segments individual character busts from processed images.
    
    Uses connected component analysis on the alpha channel to find
    separate character regions, filtering by size and sorting by position.
    """
    
    @staticmethod
    def detect_busts(image: Image.Image, min_ratio: float) -> List[BustRegion]:
        """
        Detect bust regions in a processed RGBA image.
        
        Algorithm:
        1. Extract alpha channel
        2. Label connected components (alpha > 50)
        3. Calculate bounding box and area for each
        4. Filter by minimum area ratio
        5. Sort left-to-right by center X
        
        Args:
            image: RGBA image with transparent background
            min_ratio: Minimum bust area as fraction of largest (0.0-1.0)
                       Smaller regions are considered noise
                       
        Returns:
            List of BustRegion objects sorted left-to-right
        """
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        # Label connected components
        alpha = np.array(image.split()[3])
        labeled, n = ndimage.label(alpha > 50)
        
        regions = []
        for i in range(1, n + 1):
            comp = labeled == i
            rows, cols = np.any(comp, axis=1), np.any(comp, axis=0)
            if not np.any(rows) or not np.any(cols):
                continue
                
            rmin, rmax = np.where(rows)[0][[0, -1]]
            cmin, cmax = np.where(cols)[0][[0, -1]]
            
            regions.append({
                "bbox": (int(cmin), int(rmin), int(cmax + 1), int(rmax + 1)),
                "area": int(np.sum(comp)),
                "cx": int((cmin + cmax) // 2),
                "cy": int((rmin + rmax) // 2)
            })
        
        # Sort by horizontal position
        regions.sort(key=lambda r: r["cx"])
        
        # Filter by minimum area ratio
        if regions:
            max_area = max(r["area"] for r in regions)
            regions = [r for r in regions if r["area"] >= max_area * min_ratio]
        
        # Convert to BustRegion objects
        return [
            BustRegion(
                id=str(uuid.uuid4())[:8],
                bbox=r["bbox"],
                center_x=r["cx"],
                center_y=r["cy"],
                area=r["area"],
                name=str(i + 1)
            )
            for i, r in enumerate(regions)
        ]


# =============================================================================
# Bust Extraction Engine
# =============================================================================


class BustExtractor:
    """
    Extracts individual bust images and creates uniform-sized outputs.
    
    Handles padding, component filtering, uniform sizing for animation
    workflows, and sprite sheet generation.
    """
    
    def extract_bust(
        self, 
        image: Image.Image, 
        bbox: Tuple[int, int, int, int], 
        padding: int
    ) -> Image.Image:
        """
        Extract a single bust from the image with padding.
        
        Note: Padding is applied to LEFT/RIGHT only. Top/Bottom padding
        stays 0 to preserve baseline alignment for animation strips.
        
        Args:
            image: Source RGBA image
            bbox: Bounding box as (left, top, right, bottom)
            padding: Horizontal padding in pixels
            
        Returns:
            Cropped RGBA image of the bust
        """
        pad = max(0, int(padding))
        pad_left = pad
        pad_right = pad
        pad_top = 0
        pad_bottom = 0
        
        l, t, r, b = bbox
        
        # Apply padding to source crop
        l = max(0, l - pad_left)
        t = max(0, t - pad_top)
        r = min(image.width, r + pad_right)
        b = min(image.height, b + pad_bottom)
        
        bust = image.crop((l, t, r, b))
        
        # Filter to keep only largest component (main character)
        data = np.array(bust)
        labeled, n = ndimage.label(data[:, :, 3] > 10)
        
        if n > 1:
            sizes = [(np.sum(labeled == i), i) for i in range(1, n + 1)]
            largest = max(sizes)[1]
            data[:, :, 3] = np.minimum(
                data[:, :, 3], 
                (labeled == largest).astype(np.uint8) * 255
            )
            bust = Image.fromarray(data, "RGBA")
        
        # Get tight bounding box of remaining content
        bb = bust.getbbox()
        if not bb:
            return bust
        
        # Re-apply intended padding relative to tight content
        left = max(0, bb[0] - pad_left)
        top = max(0, bb[1] - pad_top)
        right = min(bust.width, bb[2] + pad_right)
        bottom = min(bust.height, bb[3] + pad_bottom)
        
        return bust.crop((left, top, right, bottom))
    
    def create_uniform(
        self, 
        busts: List[Image.Image], 
        target_width: int, 
        target_height: int,
        offsets: List[Tuple[int, int]]
    ) -> Tuple[List[Image.Image], Tuple[int, int]]:
        """
        Create uniform-sized bust images for animation consistency.
        
        Places each bust on a canvas of uniform size, with busts
        aligned to bottom-center plus any user-specified offsets.
        
        Args:
            busts: List of extracted bust images
            target_width: Override width (0 = auto from max bust)
            target_height: Override height (0 = auto from max bust)
            offsets: List of (x, y) offset tuples per bust
            
        Returns:
            Tuple of (uniform_images_list, (width, height))
        """
        if not busts:
            return [], (0, 0)
        
        # Calculate canvas size from largest bust
        mw = max(b.width for b in busts)
        mh = max(b.height for b in busts)
        
        w = target_width or mw
        h = target_height or mh
        
        result = []
        for i, b in enumerate(busts):
            canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            
            # Center horizontally, align to bottom
            x = (w - b.width) // 2
            y = h - b.height
            
            # Apply user offset
            if offsets and i < len(offsets):
                x += offsets[i][0]
                y += offsets[i][1]
            
            canvas.paste(b, (x, y), b)
            result.append(canvas)
        
        return result, (w, h)
    
    def create_sprite_sheet(
        self, 
        busts: List[Image.Image], 
        padding: int
    ) -> Image.Image:
        """
        Create horizontal sprite sheet from uniform bust images.
        
        Arranges busts in a single horizontal row with optional
        padding between them. Ready for use in game engines and
        animation frameworks.
        
        Args:
            busts: List of uniform-sized bust images
            padding: Gap between busts in pixels
            
        Returns:
            Single RGBA image containing all busts
        """
        if not busts:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        
        w, h = busts[0].size
        total_width = (w + padding) * len(busts) - padding
        
        sheet = Image.new("RGBA", (total_width, h), (0, 0, 0, 0))
        
        for i, b in enumerate(busts):
            sheet.paste(b, (i * (w + padding), 0), b)
        
        return sheet


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title="Bust Extractor Pro",
    description="Professional web-based sprite sheet character portrait extraction",
    version="2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize processing engines
bg_remover = BackgroundRemover()
edge_refiner = EdgeRefiner()
segmenter = BustSegmenter()
extractor = BustExtractor()


# =============================================================================
# Utility Functions
# =============================================================================


def img_to_b64(img: Image.Image, fmt: str = "PNG") -> str:
    """
    Convert PIL Image to base64-encoded string.
    
    Args:
        img: PIL Image object
        fmt: Output format (PNG, WEBP, etc.)
        
    Returns:
        Base64-encoded image string
    """
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode()


# =============================================================================
# API Endpoints
# =============================================================================


@app.get("/")
async def root():
    """
    Serve the main web interface.
    
    Returns:
        HTML page from frontend/index.html
    """
    f = FRONTEND_DIR / "index.html"
    if not f.exists():
        raise HTTPException(500, f"Frontend not found: {f}")
    return FileResponse(str(f))


@app.get("/css/{filename}")
async def get_css(filename: str):
    """Serve CSS files from frontend/css directory."""
    f = FRONTEND_DIR / "css" / filename
    if not f.exists():
        raise HTTPException(404, f"CSS file not found: {filename}")
    return FileResponse(str(f), media_type="text/css")


@app.get("/js/{filename}")
async def get_js(filename: str):
    """Serve JavaScript files from frontend/js directory."""
    f = FRONTEND_DIR / "js" / filename
    if not f.exists():
        raise HTTPException(404, f"JS file not found: {filename}")
    return FileResponse(str(f), media_type="application/javascript")


@app.get("/locales.js")
async def get_locales():
    """
    Serve localization JavaScript file.
    
    Returns:
        JavaScript file with translation strings
    """
    # Try new location first
    f = FRONTEND_DIR / "js" / "locales.js"
    if not f.exists():
        # Fallback to old location
        f = FRONTEND_DIR / "locales.js"
    if not f.exists():
        raise HTTPException(404, "Locales not found")
    return FileResponse(str(f), media_type="application/javascript")


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload and analyze a sprite sheet image.
    
    Creates a new session and analyzes the image to detect
    background color and optimal tolerance settings.
    
    Args:
        file: Uploaded image file (PNG, JPG, WebP)
        
    Returns:
        JSON with session_id, dimensions, preview, and auto-detected settings
    """
    sid = str(uuid.uuid4())
    fpath = UPLOAD_DIR / f"{sid}_original{Path(file.filename).suffix}"
    
    with open(fpath, "wb") as f:
        f.write(await file.read())
    
    try:
        img = Image.open(fpath)
        w, h = img.size
    except Exception as e:
        os.remove(fpath)
        raise HTTPException(400, str(e))
    
    # Analyze for auto settings
    bg_color, auto_tol = bg_remover.analyze_histogram(img)
    
    # Create session
    sess = SessionData(session_id=sid, original_image_path=str(fpath))
    sess.auto_tolerance = auto_tol
    sess.detected_bg_color = bg_color
    SESSIONS[sid] = sess
    
    preview = img.convert("RGBA") if img.mode != "RGBA" else img
    
    return {
        "session_id": sid,
        "width": int(w),
        "height": int(h),
        "preview": img_to_b64(preview),
        "filename": file.filename,
        "auto_tolerance": int(auto_tol),
        "bg_color": list(bg_color)
    }


@app.post("/api/remove-background")
async def remove_background(
    session_id: str = Form(...),
    method: str = Form("rembg_birefnet-general"),
    tolerance: int = Form(30),
    mask_erode: int = Form(0),
    mask_dilate: int = Form(0),
    alpha_matting: bool = Form(False),
    cleaning_enabled: bool = Form(False),
    hybrid_strength: float = Form(0.7),
    hybrid_edge_radius: int = Form(5),
    feather_enabled: bool = Form(True),
    feather_radius: int = Form(2),
    feather_strength: float = Form(0.5),
    feather_edge_only: bool = Form(True),
    despill_enabled: bool = Form(False),
    despill_strength: float = Form(0.5),
    despill_color: str = Form("auto"),
    decontaminate_enabled: bool = Form(False),
    decontaminate_strength: float = Form(0.5),
    decontaminate_threshold: int = Form(250),
    hybrid_cleansing_enabled: bool = Form(False),
    hybrid_cleansing_erosion: int = Form(2),
    secondary_file: Optional[UploadFile] = File(None)
):
    """
    Process background removal with specified method and parameters.
    
    Supports multiple AI models, color-based keying, and difference matting.
    Applies optional post-processing: morphology, feathering, despill,
    decontamination, and hybrid validation.
    
    Args:
        session_id: Active session identifier
        method: Background removal method
        tolerance: Color tolerance for color-based methods
        mask_erode: Erosion iterations
        mask_dilate: Dilation iterations
        alpha_matting: Enable alpha matting refinement
        cleaning_enabled: Enable artifact cleaning
        hybrid_strength: Hybrid method blend strength
        hybrid_edge_radius: Hybrid edge zone radius
        feather_enabled: Enable edge feathering
        feather_radius: Feather blur radius
        feather_strength: Feather blend strength
        feather_edge_only: Only feather edge zone
        despill_enabled: Enable color spill removal
        despill_strength: Despill effect strength
        despill_color: Target spill color
        decontaminate_enabled: Enable edge color cleanup
        decontaminate_strength: Decontamination strength
        decontaminate_threshold: Alpha threshold for edges
        hybrid_cleansing_enabled: Enable hybrid validator
        hybrid_cleansing_erosion: Validator erosion size
        secondary_file: Black background image for difference matting
        
    Returns:
        JSON with preview and mask as base64 images
    """
    logger.info(f"Remove Background: method={method}, session={session_id}")
    
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    
    sess = SESSIONS[session_id]
    
    # Special mode: Difference Matting
    if method == "difference_matting":
        if not secondary_file:
            raise HTTPException(
                400, 
                "Difference Matting requires secondary file (Black BG version)"
            )
        
        sec_path = UPLOAD_DIR / f"{session_id}_secondary.png"
        with open(sec_path, "wb") as f:
            f.write(await secondary_file.read())
        
        try:
            img_white = Image.open(sess.original_image_path)
            img_black = Image.open(sec_path)
            result = bg_remover.process_difference_matting(img_white, img_black)
            mask = result.split()[3]
        except Exception as e:
            logger.error(f"Difference matting error: {e}")
            raise HTTPException(400, f"Difference matting error: {e}")
        finally:
            if sec_path.exists():
                os.remove(sec_path)
    else:
        # Standard AI / color-based flow
        img = Image.open(sess.original_image_path)
        
        is_ai_model = method not in ("color_based", "hybrid")
        
        # Legacy hybrid fallback
        if method == "hybrid":
            method = "rembg_birefnet-general"
            is_ai_model = True
        
        logger.info(f"Processing: method={method}, cleaning={cleaning_enabled}")
        
        result, mask, bg = bg_remover.remove_background(
            img, method, tolerance, alpha_matting
        )
        
        if bg:
            sess.detected_bg_color = bg
        
        # Apply Hybrid Validator
        if hybrid_cleansing_enabled and sess.detected_bg_color:
            logger.info(f"Applying Hybrid Validator (erosion={hybrid_cleansing_erosion})")
            mask = edge_refiner.hybrid_cleansing(
                mask, img, sess.detected_bg_color, tolerance,
                erosion_size=hybrid_cleansing_erosion
            )
            rd = np.array(result)
            rd[:, :, 3] = np.array(mask)
            result = Image.fromarray(rd, "RGBA")
        
        # Apply morphological operations
        if is_ai_model and (mask_erode > 0 or mask_dilate > 0):
            mask = edge_refiner.refine_mask(mask, mask_erode, mask_dilate)
            rd = np.array(result)
            rd[:, :, 3] = np.array(mask)
            result = Image.fromarray(rd, "RGBA")
        
        # Apply artifact cleaning
        if is_ai_model and cleaning_enabled:
            result = edge_refiner.clean_artifacts(result)
        
        # Apply feathering
        if feather_enabled and feather_radius > 0:
            result = edge_refiner.feather_edges(
                result, mask, feather_radius, feather_strength, feather_edge_only
            )
    
    # Global post-processing
    if decontaminate_enabled:
        result = edge_refiner.decontaminate_edges(
            result, decontaminate_strength, decontaminate_threshold
        )
    
    if despill_enabled:
        result = edge_refiner.despill(
            result, despill_strength, despill_color, sess.detected_bg_color
        )
    
    # Save results
    ppath = UPLOAD_DIR / f"{session_id}_processed.png"
    result.save(ppath, "PNG")
    sess.processed_image_path = str(ppath)
    
    mpath = UPLOAD_DIR / f"{session_id}_mask.png"
    mask.save(mpath, "PNG")
    sess.mask_path = str(mpath)
    
    return {
        "preview": img_to_b64(result),
        "mask": img_to_b64(mask),
        "width": int(result.width),
        "height": int(result.height)
    }


@app.post("/api/detect-busts")
async def detect_busts(
    session_id: str = Form(...), 
    min_area_ratio: float = Form(0.05)
):
    """
    Detect individual bust regions in the processed image.
    
    Uses connected component analysis to find separate character
    regions, visualizes them with colored bounding boxes.
    
    Args:
        session_id: Active session identifier
        min_area_ratio: Minimum area as fraction of largest bust
        
    Returns:
        JSON with bust list, visualization, and count
    """
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    
    sess = SESSIONS[session_id]
    if not sess.processed_image_path:
        raise HTTPException(400, "Process image first")
    
    img = Image.open(sess.processed_image_path)
    sess.busts = segmenter.detect_busts(img, min_area_ratio)
    
    # Create visualization
    vis = img.copy()
    draw = ImageDraw.Draw(vis)
    colors = [
        (255, 100, 100), (100, 255, 100), (100, 100, 255),
        (255, 255, 100), (255, 100, 255), (100, 255, 255)
    ]
    
    for i, b in enumerate(sess.busts):
        c = colors[i % len(colors)]
        l, t, r, bo = b.bbox
        
        # Draw bounding box (3px thick)
        for o in range(3):
            draw.rectangle([l - o, t - o, r + o, bo + o], outline=c)
        
        # Draw center crosshair
        cx, cy = b.center_x, b.center_y
        draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=c)
        draw.line([(cx - 25, cy), (cx + 25, cy)], fill=(255, 255, 255), width=2)
        draw.line([(cx, cy - 25), (cx, cy + 25)], fill=(255, 255, 255), width=2)
    
    return {
        "busts": [asdict(b) for b in sess.busts],
        "visualization": img_to_b64(vis),
        "count": len(sess.busts)
    }


@app.post("/api/update-bust")
async def update_bust(
    session_id: str = Form(...),
    bust_id: str = Form(...),
    name: Optional[str] = Form(None),
    offset_x: Optional[int] = Form(None),
    offset_y: Optional[int] = Form(None),
    enabled: Optional[bool] = Form(None)
):
    """
    Update properties of a single bust.
    
    Args:
        session_id: Active session identifier
        bust_id: Bust identifier to update
        name: New display name (optional)
        offset_x: New X offset (optional)
        offset_y: New Y offset (optional)
        enabled: Enable/disable for export (optional)
        
    Returns:
        JSON with success status and updated bust data
    """
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    
    sess = SESSIONS[session_id]
    bust = next((b for b in sess.busts if b.id == bust_id), None)
    
    if not bust:
        raise HTTPException(404, "Bust not found")
    
    if name is not None:
        bust.name = name
    if offset_x is not None:
        bust.offset_x = offset_x
    if offset_y is not None:
        bust.offset_y = offset_y
    if enabled is not None:
        bust.enabled = enabled
    
    return {"success": True, "bust": asdict(bust)}


@app.post("/api/update-all-busts")
async def update_all_busts(
    session_id: str = Form(...), 
    busts_json: str = Form(...)
):
    """
    Batch update multiple bust properties.
    
    Args:
        session_id: Active session identifier
        busts_json: JSON array of bust updates
        
    Returns:
        JSON with success status and all bust data
    """
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    
    sess = SESSIONS[session_id]
    
    for u in json.loads(busts_json):
        b = next((x for x in sess.busts if x.id == u["id"]), None)
        if b:
            if "name" in u:
                b.name = u["name"]
            if "offset_x" in u:
                b.offset_x = u["offset_x"]
            if "offset_y" in u:
                b.offset_y = u["offset_y"]
            if "enabled" in u:
                b.enabled = u["enabled"]
    
    return {"success": True, "busts": [asdict(b) for b in sess.busts]}


@app.post("/api/update-mask")
async def update_mask(
    session_id: str = Form(...), 
    mask_file: UploadFile = File(...)
):
    """
    Save edited mask and regenerate processed image.
    
    Called after user edits the mask with eraser/restore tools.
    Reconstructs the processed image with the new mask.
    
    Args:
        session_id: Active session identifier
        mask_file: Edited mask image file
        
    Returns:
        JSON with updated preview and mask
    """
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    
    sess = SESSIONS[session_id]
    if not sess.original_image_path:
        raise HTTPException(400, "Original image missing")
    
    # Save new mask
    mpath = UPLOAD_DIR / f"{session_id}_mask.png"
    with open(mpath, "wb") as f:
        f.write(await mask_file.read())
    sess.mask_path = str(mpath)
    
    try:
        mask_img = Image.open(mpath).convert("L")
        orig_img = Image.open(sess.original_image_path).convert("RGBA")
        
        # Resize mask if needed
        if mask_img.size != orig_img.size:
            mask_img = mask_img.resize(orig_img.size, Image.NEAREST)
        
        # Apply mask
        result = orig_img.copy()
        result.putalpha(mask_img)
        
        # Save processed
        ppath = UPLOAD_DIR / f"{session_id}_processed.png"
        result.save(ppath, "PNG")
        sess.processed_image_path = str(ppath)
        
        return {
            "success": True,
            "preview": img_to_b64(result),
            "mask": img_to_b64(mask_img),
            "clear_busts": True
        }
    except Exception as e:
        logger.error(f"Update mask error: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/preview-alignment")
async def preview_alignment(
    session_id: str = Form(...),
    uniform_width: int = Form(0),
    uniform_height: int = Form(0),
    padding: int = Form(30)
):
    """
    Generate alignment preview overlay.
    
    Shows all busts overlaid with color tinting to visualize
    their relative positions and alignment.
    
    Args:
        session_id: Active session identifier
        uniform_width: Target width (0 = auto)
        uniform_height: Target height (0 = auto)
        padding: Horizontal padding
        
    Returns:
        JSON with preview image and dimensions
    """
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    
    sess = SESSIONS[session_id]
    if not sess.processed_image_path:
        raise HTTPException(400, "Process image first")
    
    img = Image.open(sess.processed_image_path)
    enabled = [b for b in sess.busts if b.enabled]
    
    if not enabled:
        raise HTTPException(400, "No enabled busts")
    
    extracted = [extractor.extract_bust(img, b.bbox, padding) for b in enabled]
    offsets = [(b.offset_x, b.offset_y) for b in enabled]
    uniform, (w, h) = extractor.create_uniform(
        extracted, uniform_width, uniform_height, offsets
    )
    
    # Create overlay with color tinting
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255), (255, 255, 100)]
    
    for i, u in enumerate(uniform):
        arr = np.array(u).astype(np.float32)
        c = colors[i % len(colors)]
        arr[:, :, :3] = arr[:, :, :3] * 0.6 + np.array(c) * 0.4
        arr[:, :, 3] *= 0.6
        overlay = Image.alpha_composite(
            overlay, 
            Image.fromarray(arr.astype(np.uint8), "RGBA")
        )
    
    # Draw center guides
    draw = ImageDraw.Draw(overlay)
    cx, cy = w // 2, h // 2
    draw.line([(cx, 0), (cx, h)], fill=(255, 255, 255, 180), width=2)
    draw.line([(0, cy), (w, cy)], fill=(255, 255, 255, 180), width=2)
    
    return {
        "preview": img_to_b64(overlay),
        "width": int(w),
        "height": int(h)
    }


@app.post("/api/extract")
async def extract_busts(
    session_id: str = Form(...),
    padding: int = Form(30),
    uniform_width: int = Form(0),
    uniform_height: int = Form(0),
    sprite_sheet_padding: int = Form(0),
    export_individual: bool = Form(True),
    export_sprite_sheet: bool = Form(True),
    format: str = Form("PNG")
):
    """
    Extract busts and generate output files.
    
    Creates individual bust images and/or sprite sheet based
    on settings. Saves to outputs directory.
    
    Args:
        session_id: Active session identifier
        padding: Horizontal padding around busts
        uniform_width: Target width (0 = auto)
        uniform_height: Target height (0 = auto)
        sprite_sheet_padding: Gap between busts in sheet
        export_individual: Save individual files
        export_sprite_sheet: Generate sprite sheet
        format: Output format (PNG or WEBP)
        
    Returns:
        JSON with results array, sprite sheet, and uniform size
    """
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    
    sess = SESSIONS[session_id]
    if not sess.processed_image_path or not sess.busts:
        raise HTTPException(400, "No processed image or busts")
    
    img = Image.open(sess.processed_image_path)
    enabled = [b for b in sess.busts if b.enabled]
    
    if not enabled:
        raise HTTPException(400, "No enabled busts")
    
    extracted = [extractor.extract_bust(img, b.bbox, padding) for b in enabled]
    offsets = [(b.offset_x, b.offset_y) for b in enabled]
    uniform, (w, h) = extractor.create_uniform(
        extracted, uniform_width, uniform_height, offsets
    )
    
    sess.uniform_size = (w, h)
    out_dir = OUTPUT_DIR / session_id
    out_dir.mkdir(exist_ok=True)
    
    # Determine output format
    ext = "webp" if format.upper() == "WEBP" else "png"
    save_fmt = "WEBP" if format.upper() == "WEBP" else "PNG"
    
    results = []
    if export_individual:
        for b, u in zip(enabled, uniform):
            fname = f"{b.name}.{ext}"
            u.save(out_dir / fname, save_fmt)
            results.append({
                "name": b.name,
                "filename": fname,
                "width": int(u.width),
                "height": int(u.height),
                "preview": img_to_b64(u)
            })
    
    ss_b64 = None
    if export_sprite_sheet:
        ss = extractor.create_sprite_sheet(uniform, sprite_sheet_padding)
        ss.save(out_dir / f"sprite_sheet.{ext}", save_fmt)
        ss_b64 = img_to_b64(ss)
    
    return {
        "results": results,
        "sprite_sheet": ss_b64,
        "uniform_size": {"width": int(w), "height": int(h)}
    }


@app.post("/api/download-all")
async def download_all(session_id: str = Form(...)):
    """
    Create ZIP archive of all exported files.
    
    Args:
        session_id: Active session identifier
        
    Returns:
        ZIP file download response
    """
    import zipfile
    
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    
    out_dir = OUTPUT_DIR / session_id
    if not out_dir.exists():
        raise HTTPException(400, "No output files")
    
    zpath = OUTPUT_DIR / f"{session_id}.zip"
    
    with zipfile.ZipFile(zpath, "w") as zf:
        for f in out_dir.glob("*"):
            if f.suffix.lower() in ['.png', '.webp']:
                zf.write(f, f.name)
    
    return FileResponse(str(zpath), filename="busts.zip")


# =============================================================================
# Entry Point
# =============================================================================


if __name__ == "__main__":
    print("=" * 60)
    print("🎨 Bust Extractor Pro v2.0")
    print("=" * 60)
    print(f"📁 Frontend: {FRONTEND_DIR}")
    print(f"📁 Uploads: {UPLOAD_DIR}")
    print(f"📁 Outputs: {OUTPUT_DIR}")
    print()
    print("🚀 Starting server at http://localhost:8000")
    print("⌨️  Press Ctrl+C to stop")
    print("-" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
