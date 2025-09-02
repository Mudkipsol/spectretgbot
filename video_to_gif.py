#!/usr/bin/env python3
"""
Video to GIF Converter Module
Converts videos to optimized GIFs with quality preservation and platform optimization
"""

import os
import subprocess
import shutil
from PIL import Image, ImageSequence
import cv2

def get_output_path(original_path, suffix="", extension=".gif"):
    """Generate output file path in the output folder."""
    base, _ = os.path.splitext(original_path)
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    filename = os.path.basename(base) + suffix + extension
    return os.path.join(output_dir, filename)

def get_video_info(video_path, ffmpeg_path="ffmpeg"):
    """Extract video information using FFmpeg."""
    try:
        probe_cmd = [ffmpeg_path, "-i", video_path, "-f", "null", "-"]
        result = subprocess.run(probe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        
        stderr_output = result.stderr
        info = {}
        
        # Extract duration
        import re
        duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', stderr_output)
        if duration_match:
            hours, minutes, seconds = duration_match.groups()
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            info['duration'] = total_seconds
        
        # Extract framerate
        fps_match = re.search(r'(\d+\.?\d*)\s*fps', stderr_output)
        if fps_match:
            info['fps'] = float(fps_match.group(1))
        
        # Extract resolution
        res_match = re.search(r'(\d+)x(\d+)', stderr_output)
        if res_match:
            info['width'] = int(res_match.group(1))
            info['height'] = int(res_match.group(2))
        
        return info
        
    except Exception as e:
        print(f"[⚠️] Could not extract video info: {e}")
        return {}

def convert_video_to_gif(video_path, start_time=0, duration=None, fps=15, width=None, quality="medium", platform="general"):
    """
    Convert video to GIF with advanced optimization.
    
    Args:
        video_path: Path to input video
        start_time: Start time in seconds
        duration: Duration in seconds (None = entire video)
        fps: Output FPS for GIF
        width: Output width (height auto-calculated)
        quality: Quality level (low, medium, high)
        platform: Target platform (reddit, twitter, discord, general)
    
    Returns:
        Path to output GIF
    """
    try:
        # Auto-detect FFMPEG path
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is None:
            windows_ffmpeg = "C:\\Tools\\FFmpeg\\ffmpeg.exe"
            if os.path.exists(windows_ffmpeg):
                ffmpeg_path = windows_ffmpeg
            else:
                raise RuntimeError("FFmpeg not found")
        
        print(f"🎬 Converting video to GIF for {platform.upper()}")
        
        # Get video info
        video_info = get_video_info(video_path, ffmpeg_path)
        
        # Platform-specific optimization
        platform_settings = {
            "reddit": {"max_width": 480, "fps": 12, "quality": "medium"},
            "twitter": {"max_width": 640, "fps": 15, "quality": "high"},
            "discord": {"max_width": 400, "fps": 10, "quality": "medium"},
            "general": {"max_width": 600, "fps": 15, "quality": "medium"}
        }
        
        settings = platform_settings.get(platform.lower(), platform_settings["general"])
        
        # Use platform defaults if not specified
        if width is None:
            width = settings["max_width"]
        if fps > settings["fps"]:
            fps = settings["fps"]
        if quality == "auto":
            quality = settings["quality"]
        
        # Quality settings
        quality_map = {
            "low": {"colors": 128, "dither": "none"},
            "medium": {"colors": 256, "dither": "bayer"},
            "high": {"colors": 256, "dither": "floyd_steinberg"}
        }
        
        q_settings = quality_map.get(quality, quality_map["medium"])
        
        # Build FFmpeg command
        cmd = [ffmpeg_path, "-i", video_path]
        
        # Add time parameters
        if start_time > 0:
            cmd.extend(["-ss", str(start_time)])
        if duration:
            cmd.extend(["-t", str(duration)])
        
        # Video filters for optimal GIF conversion
        filters = []
        
        # Scale filter with high-quality downsampling
        if width:
            filters.append(f"scale={width}:-1:flags=lanczos")
        
        # Frame rate filter
        filters.append(f"fps={fps}")
        
        # Palette optimization for better colors
        palette_filter = f"palettegen=max_colors={q_settings['colors']}:reserve_transparent=0"
        
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        
        # Output parameters
        temp_output = get_output_path(video_path, suffix="_temp", extension=".gif")
        
        cmd.extend([
            "-c:v", "gif",
            "-y", temp_output
        ])
        
        print(f"🔧 Running conversion: {fps}fps, {width}px width, {quality} quality")
        
        # Run conversion with timeout
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr.decode()}")
        
        if not os.path.exists(temp_output):
            raise RuntimeError("Output GIF was not created")
        
        # Post-process with PIL for final optimization
        print("🔧 Optimizing GIF...")
        final_output = get_output_path(video_path, suffix=f"_{platform}_gif")
        
        img = Image.open(temp_output)
        frames = []
        
        for frame in ImageSequence.Iterator(img):
            # Apply dithering based on quality setting
            if q_settings["dither"] != "none":
                frame = frame.convert("RGB")
                if q_settings["dither"] == "floyd_steinberg":
                    frame = frame.quantize(colors=q_settings["colors"], method=Image.Quantize.FLOYDSTEINBERG)
                else:
                    frame = frame.quantize(colors=q_settings["colors"])
            frames.append(frame)
        
        # Save final optimized GIF
        save_kwargs = {
            "format": "GIF",
            "save_all": True,
            "append_images": frames[1:] if len(frames) > 1 else [],
            "loop": 0,
            "optimize": True
        }
        
        # Platform-specific timing
        if platform.lower() == "reddit":
            save_kwargs["duration"] = int(1000 / fps) + 10  # Slightly slower for Reddit
        else:
            save_kwargs["duration"] = int(1000 / fps)
        
        frames[0].save(final_output, **save_kwargs)
        
        # Clean up temp file
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        # Get file size info
        size_mb = os.path.getsize(final_output) / (1024 * 1024)
        print(f"✅ GIF created: {size_mb:.1f}MB, {len(frames)} frames")
        
        return final_output
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("Video conversion timed out (5 minutes)")
    except Exception as e:
        raise RuntimeError(f"Video to GIF conversion failed: {e}")

def extract_gif_segment(video_path, start_time, end_time, fps=15, width=400, platform="general"):
    """Extract a specific segment from video as GIF."""
    duration = end_time - start_time
    if duration <= 0:
        raise ValueError("End time must be greater than start time")
    
    return convert_video_to_gif(
        video_path=video_path,
        start_time=start_time,
        duration=duration,
        fps=fps,
        width=width,
        platform=platform
    )

def create_gif_from_video_clips(video_path, clips, fps=15, width=400, platform="general"):
    """
    Create GIF from multiple video clips/segments.
    
    Args:
        video_path: Path to source video
        clips: List of (start_time, end_time) tuples
        fps: Output framerate
        width: Output width
        platform: Target platform
    
    Returns:
        Path to combined GIF
    """
    try:
        ffmpeg_path = shutil.which("ffmpeg") or "C:\\Tools\\FFmpeg\\ffmpeg.exe"
        
        print(f"🎬 Creating GIF from {len(clips)} video segments")
        
        # Extract each clip
        temp_gifs = []
        for i, (start, end) in enumerate(clips):
            print(f"🔧 Processing clip {i+1}/{len(clips)}: {start}s - {end}s")
            temp_gif = extract_gif_segment(video_path, start, end, fps, width, platform)
            temp_gifs.append(temp_gif)
        
        if len(temp_gifs) == 1:
            return temp_gifs[0]
        
        # Combine GIFs using PIL
        print("🔧 Combining GIF segments...")
        all_frames = []
        
        for gif_path in temp_gifs:
            img = Image.open(gif_path)
            for frame in ImageSequence.Iterator(img):
                all_frames.append(frame.copy())
        
        # Save combined GIF
        output_path = get_output_path(video_path, suffix=f"_combined_{platform}_gif")
        
        if all_frames:
            all_frames[0].save(
                output_path,
                format="GIF",
                save_all=True,
                append_images=all_frames[1:],
                loop=0,
                optimize=True,
                duration=int(1000 / fps)
            )
        
        # Clean up temp files
        for temp_gif in temp_gifs:
            if os.path.exists(temp_gif):
                os.remove(temp_gif)
        
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"✅ Combined GIF created: {size_mb:.1f}MB, {len(all_frames)} frames")
        
        return output_path
        
    except Exception as e:
        raise RuntimeError(f"Failed to create GIF from clips: {e}")

def batch_convert_videos_to_gifs(video_paths, fps=15, width=400, platform="general"):
    """Batch convert multiple videos to GIFs."""
    results = []
    
    for i, video_path in enumerate(video_paths):
        try:
            print(f"🎬 Converting video {i+1}/{len(video_paths)}: {os.path.basename(video_path)}")
            gif_path = convert_video_to_gif(video_path, fps=fps, width=width, platform=platform)
            results.append({"original": video_path, "gif": gif_path, "status": "success"})
        except Exception as e:
            print(f"❌ Failed to convert {video_path}: {e}")
            results.append({"original": video_path, "gif": None, "status": "failed", "error": str(e)})
    
    return results

if __name__ == "__main__":
    # Test the module
    test_video = "test.mp4"
    if os.path.exists(test_video):
        result = convert_video_to_gif(test_video, fps=10, width=400, platform="reddit")
        print(f"Test result: {result}")
