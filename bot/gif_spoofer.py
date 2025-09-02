#!/usr/bin/env python3
"""
Advanced GIF Spoofing Module for Reddit/Twitter/Social Media
Specialized techniques for animated content detection evasion
"""

import os
import random
import uuid
import subprocess
import shutil
from PIL import Image, ImageSequence, ImageEnhance, ImageFilter, ImageOps
import numpy as np
import cv2

def get_output_path(original_path, suffix="", extension=None):
    """Generate output file path in the output folder."""
    base, ext = os.path.splitext(original_path)
    if extension:
        ext = extension
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    filename = os.path.basename(base) + suffix + ext
    return os.path.join(output_dir, filename)

def apply_gif_frame_variance(frame, frame_index, total_frames, variance_strength="medium"):
    """Apply per-frame variance to break GIF loop detection."""
    
    variance_settings = {
        "light": {"color": (0.98, 1.02), "contrast": (0.99, 1.01), "brightness": (0.99, 1.01)},
        "medium": {"color": (0.95, 1.05), "contrast": (0.97, 1.03), "brightness": (0.98, 1.02)},
        "heavy": {"color": (0.92, 1.08), "contrast": (0.95, 1.05), "brightness": (0.96, 1.04)}
    }
    
    settings = variance_settings.get(variance_strength, variance_settings["medium"])
    
    # Color variance with sinusoidal pattern to maintain visual flow
    phase = 2 * np.pi * frame_index / total_frames
    color_factor = random.uniform(*settings["color"]) + 0.01 * np.sin(phase)
    enhancer = ImageEnhance.Color(frame)
    frame = enhancer.enhance(color_factor)
    
    # Contrast variance
    contrast_factor = random.uniform(*settings["contrast"]) + 0.005 * np.cos(phase)
    enhancer = ImageEnhance.Contrast(frame)
    frame = enhancer.enhance(contrast_factor)
    
    # Brightness variance (very subtle)
    brightness_factor = random.uniform(*settings["brightness"])
    enhancer = ImageEnhance.Brightness(frame)
    frame = enhancer.enhance(brightness_factor)
    
    return frame

def apply_platform_gif_optimization(frame, platform="reddit"):
    """Apply platform-specific optimizations for GIFs."""
    
    if platform.lower() == "reddit":
        # Reddit: Slight sharpening and color enhancement
        frame = frame.filter(ImageFilter.UnsharpMask(radius=0.5, percent=120, threshold=2))
        enhancer = ImageEnhance.Color(frame)
        frame = enhancer.enhance(1.05)
        
    elif platform.lower() == "twitter":
        # Twitter: Subtle blur to combat compression artifacts
        frame = frame.filter(ImageFilter.GaussianBlur(radius=0.3))
        enhancer = ImageEnhance.Contrast(frame)
        frame = enhancer.enhance(1.02)
        
    elif platform.lower() == "threads":
        # Threads: Color saturation boost
        enhancer = ImageEnhance.Color(frame)
        frame = enhancer.enhance(1.08)
        
    return frame

def apply_micro_transformations(frame, frame_index):
    """Apply imperceptible transformations that break hash detection."""
    
    # Convert to numpy for pixel-level manipulation
    frame_array = np.array(frame)
    h, w = frame_array.shape[:2]
    
    # Handle RGBA vs RGB
    channels = frame_array.shape[2] if len(frame_array.shape) == 3 else 1
    
    # Micro rotation (0.1-0.2 degrees) - reduced for better stability
    angle = 0.1 * np.sin(frame_index * 0.05)  # Smaller, slower oscillation
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    if channels == 4:  # RGBA
        # Process RGB and Alpha separately
        rgb_part = frame_array[:, :, :3]
        alpha_part = frame_array[:, :, 3]
        
        rgb_rotated = cv2.warpAffine(rgb_part, rotation_matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
        alpha_rotated = cv2.warpAffine(alpha_part, rotation_matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
        
        frame_array = np.dstack((rgb_rotated, alpha_rotated))
    else:
        frame_array = cv2.warpAffine(frame_array, rotation_matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
    
    # Micro pixel shift (1 pixel max for stability)
    shift_x = random.randint(0, 1)
    shift_y = random.randint(0, 1)
    if shift_x != 0 or shift_y != 0:
        shift_matrix = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
        if channels == 4:  # RGBA
            rgb_part = frame_array[:, :, :3]
            alpha_part = frame_array[:, :, 3]
            
            rgb_shifted = cv2.warpAffine(rgb_part, shift_matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
            alpha_shifted = cv2.warpAffine(alpha_part, shift_matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
            
            frame_array = np.dstack((rgb_shifted, alpha_shifted))
        else:
            frame_array = cv2.warpAffine(frame_array, shift_matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
    
    return Image.fromarray(frame_array.astype(np.uint8))

def add_imperceptible_noise(frame, noise_strength=3):
    """Add imperceptible noise to break pixel-perfect detection."""
    frame_array = np.array(frame, dtype=np.float32)
    
    # Generate subtle noise
    noise = np.random.normal(0, noise_strength, frame_array.shape)
    
    # Apply noise with spatial variance
    frame_array += noise
    frame_array = np.clip(frame_array, 0, 255)
    
    return Image.fromarray(frame_array.astype(np.uint8))

def spoof_gif_advanced(gif_path, platform="reddit", variance_strength="medium", optimization=True):
    """
    Advanced GIF spoofing with platform-specific optimizations.
    
    Args:
        gif_path: Path to input GIF
        platform: Target platform (reddit, twitter, threads)
        variance_strength: Frame variance level (light, medium, heavy)
        optimization: Apply platform-specific optimizations
    
    Returns:
        Path to spoofed GIF
    """
    try:
        print(f"🎬 Spoofing GIF for {platform.upper()} with {variance_strength} variance")
        
        img = Image.open(gif_path)
        frames = []
        durations = []
        frame_count = 0
        
        # Extract original frame durations and count frames
        original_duration = None
        for frame in ImageSequence.Iterator(img):
            frame_count += 1
            # Get frame duration (default to 100ms if not available)
            duration = frame.info.get('duration', 100)
            if duration <= 0:  # Fix invalid durations
                duration = 100
            durations.append(duration)
            if original_duration is None:
                original_duration = duration
        
        print(f"🎭 Processing {frame_count} frames with {original_duration}ms base duration")
        
        # Reset and process frames
        img.seek(0)
        processed_frames = 0
        
        for frame_index, frame in enumerate(ImageSequence.Iterator(img)):
            frame = frame.convert("RGBA")  # Preserve transparency if present
            
            # Apply frame variance (breaks loop detection)
            frame = apply_gif_frame_variance(frame, frame_index, frame_count, variance_strength)
            
            # Apply micro transformations (breaks hash detection)
            frame = apply_micro_transformations(frame, frame_index)
            
            # Add imperceptible noise
            frame = add_imperceptible_noise(frame)
            
            # Apply platform optimizations
            if optimization:
                frame = apply_platform_gif_optimization(frame, platform)
            
            # Convert back to P mode for better GIF compression
            frame = frame.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
            
            frames.append(frame)
            processed_frames += 1
            
            # Progress update for long GIFs
            if processed_frames % 10 == 0:
                print(f"⏳ Processed {processed_frames}/{frame_count} frames")
        
        # Save spoofed GIF
        output_path = get_output_path(gif_path, suffix=f"_spoofed_{platform}")
        
        # Calculate adjusted durations (platform-specific micro-adjustments)
        adjusted_durations = []
        for i, duration in enumerate(durations):
            if platform.lower() == "reddit":
                # Slightly faster for Reddit (5% speed increase)
                adj_duration = max(20, int(duration * 0.95))
            elif platform.lower() == "twitter":
                # Standard timing with slight variance
                variance = 1 + (i % 3 - 1) * 0.02  # -2%, 0%, +2% variance
                adj_duration = max(20, int(duration * variance))
            elif platform.lower() == "threads":
                # Slightly slower for Threads
                adj_duration = max(20, int(duration * 1.05))
            else:
                # Default with minimal variance
                adj_duration = max(20, int(duration * (1 + (i % 2) * 0.01)))
            
            adjusted_durations.append(adj_duration)
        
        # Save with proper animation settings
        frames[0].save(
            output_path,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=adjusted_durations,  # Use per-frame durations
            loop=0,  # Infinite loop
            optimize=False,  # Disable PIL optimize to preserve timing
            disposal=2  # Clear frame before next (prevents artifacts)
        )
        
        print(f"✅ GIF spoofed successfully: {processed_frames} frames processed")
        return output_path
        
    except Exception as e:
        print(f"[⚠️] PIL-based GIF processing failed: {e}")
        print("🔄 Trying FFmpeg-based fallback...")
        try:
            return spoof_gif_with_ffmpeg(gif_path, platform, variance_strength)
        except Exception as fallback_error:
            raise RuntimeError(f"GIF spoofing failed: {e}. Fallback also failed: {fallback_error}")

def spoof_gif_with_ffmpeg(gif_path, platform="reddit", variance_strength="medium"):
    """Fallback GIF spoofing using FFmpeg for better compatibility."""
    try:
        # Auto-detect FFMPEG path
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is None:
            windows_ffmpeg = "C:\\Tools\\FFmpeg\\ffmpeg.exe"
            if os.path.exists(windows_ffmpeg):
                ffmpeg_path = windows_ffmpeg
            else:
                raise RuntimeError("FFmpeg not found")
        
        print(f"🔧 Using FFmpeg fallback for {platform.upper()} GIF spoofing")
        
        # Create temporary directory for frames
        temp_dir = f"temp_gif_frames_{random.randint(1000, 9999)}"
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Extract frames using FFmpeg
            extract_cmd = [
                ffmpeg_path, "-i", gif_path, 
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                f"{temp_dir}/frame_%04d.png"
            ]
            
            result = subprocess.run(extract_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(f"Frame extraction failed: {result.stderr.decode()}")
            
            # Get list of extracted frames
            frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.png')])
            if not frame_files:
                raise RuntimeError("No frames extracted")
            
            print(f"🎭 Processing {len(frame_files)} frames with FFmpeg pipeline")
            
            # Process each frame (lighter processing for stability)
            for i, frame_file in enumerate(frame_files):
                frame_path = os.path.join(temp_dir, frame_file)
                frame = Image.open(frame_path)
                
                # Apply lighter transformations for FFmpeg pipeline
                if variance_strength != "light":
                    # Only apply platform optimization and minimal noise
                    frame = apply_platform_gif_optimization(frame, platform)
                    frame = add_imperceptible_noise(frame, noise_strength=1)
                
                # Save processed frame
                frame.save(frame_path, "PNG", optimize=True)
            
            # Reassemble with FFmpeg using platform-specific settings
            output_path = get_output_path(gif_path, suffix=f"_spoofed_{platform}")
            
            # Platform-specific FFmpeg parameters
            if platform.lower() == "reddit":
                fps = "20"  # Slightly faster for Reddit
                filters = "scale=480:-1:flags=lanczos"
            elif platform.lower() == "twitter":
                fps = "15"
                filters = "scale=640:-1:flags=lanczos"
            else:
                fps = "15" 
                filters = "scale=500:-1:flags=lanczos"
            
            reassemble_cmd = [
                ffmpeg_path, "-y", "-framerate", fps,
                "-i", f"{temp_dir}/frame_%04d.png",
                "-vf", filters,
                "-loop", "0",  # Infinite loop
                "-f", "gif",
                output_path
            ]
            
            result = subprocess.run(reassemble_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"GIF reassembly failed: {result.stderr.decode()}")
            
            if not os.path.exists(output_path):
                raise RuntimeError("Output GIF was not created")
            
            print(f"✅ FFmpeg GIF spoofing successful: {len(frame_files)} frames processed")
            return output_path
            
        finally:
            # Clean up temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg GIF processing timed out")
    except Exception as e:
        raise RuntimeError(f"FFmpeg GIF spoofing failed: {e}")

def batch_spoof_gifs(gif_paths, platform="reddit", variance_strength="medium"):
    """Batch process multiple GIFs with spoofing."""
    results = []
    
    for i, gif_path in enumerate(gif_paths):
        try:
            print(f"🎬 Processing GIF {i+1}/{len(gif_paths)}: {os.path.basename(gif_path)}")
            spoofed_path = spoof_gif_advanced(gif_path, platform, variance_strength)
            results.append({"original": gif_path, "spoofed": spoofed_path, "status": "success"})
        except Exception as e:
            print(f"❌ Failed to process {gif_path}: {e}")
            results.append({"original": gif_path, "spoofed": None, "status": "failed", "error": str(e)})
    
    return results

def optimize_gif_for_platform(gif_path, platform="reddit", max_size_mb=8):
    """Optimize GIF file size and quality for specific platforms."""
    try:
        img = Image.open(gif_path)
        frames = []
        
        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("RGB")
            
            # Platform-specific resizing
            if platform.lower() == "reddit":
                # Reddit prefers smaller, optimized GIFs
                max_width = 480
            elif platform.lower() == "twitter":
                # Twitter handles larger GIFs well
                max_width = 640
            else:
                max_width = 520
            
            # Resize if too large
            if frame.width > max_width:
                ratio = max_width / frame.width
                new_height = int(frame.height * ratio)
                frame = frame.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            frames.append(frame)
        
        # Save optimized version
        output_path = get_output_path(gif_path, suffix=f"_optimized_{platform}")
        
        frames[0].save(
            output_path,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            loop=0,
            optimize=True,
            quality=85
        )
        
        # Check file size
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"✅ GIF optimized: {size_mb:.1f}MB")
        
        return output_path
        
    except Exception as e:
        raise RuntimeError(f"GIF optimization failed: {e}")

if __name__ == "__main__":
    # Test the module
    test_gif = "test.gif"
    if os.path.exists(test_gif):
        result = spoof_gif_advanced(test_gif, "reddit", "medium")
        print(f"Test result: {result}")
