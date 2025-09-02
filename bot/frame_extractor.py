#!/usr/bin/env python3
"""
Video Frame Extractor Module
Extract frames from videos with various selection methods and optimization
"""

import os
import cv2
import random
import shutil
import subprocess
from PIL import Image
import numpy as np

def get_output_path(original_path, suffix="", extension=".jpg"):
    """Generate output file path in the output folder."""
    base, _ = os.path.splitext(original_path)
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    filename = os.path.basename(base) + suffix + extension
    return os.path.join(output_dir, filename)

def get_video_info(video_path):
    """Get video information using OpenCV."""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError("Could not open video file")
        
        info = {
            "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "duration": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS)
        }
        
        cap.release()
        return info
        
    except Exception as e:
        raise RuntimeError(f"Failed to get video info: {e}")

def extract_frames_by_count(video_path, frame_count=10, method="evenly_spaced", quality=95):
    """
    Extract specific number of frames from video.
    
    Args:
        video_path: Path to input video
        frame_count: Number of frames to extract
        method: Selection method ('evenly_spaced', 'random', 'first', 'last', 'middle')
        quality: JPEG quality (1-100)
    
    Returns:
        List of extracted frame paths
    """
    try:
        print(f"🎬 Extracting {frame_count} frames using '{method}' method")
        
        video_info = get_video_info(video_path)
        total_frames = video_info["total_frames"]
        
        if frame_count > total_frames:
            frame_count = total_frames
            print(f"⚠️ Requested more frames than available, extracting all {total_frames} frames")
        
        # Determine frame indices based on method
        if method == "evenly_spaced":
            if frame_count == 1:
                frame_indices = [total_frames // 2]
            else:
                step = total_frames / (frame_count - 1)
                frame_indices = [int(i * step) for i in range(frame_count)]
                frame_indices[-1] = min(frame_indices[-1], total_frames - 1)
                
        elif method == "random":
            frame_indices = sorted(random.sample(range(total_frames), frame_count))
            
        elif method == "first":
            frame_indices = list(range(min(frame_count, total_frames)))
            
        elif method == "last":
            start_frame = max(0, total_frames - frame_count)
            frame_indices = list(range(start_frame, total_frames))
            
        elif method == "middle":
            middle = total_frames // 2
            half_count = frame_count // 2
            start = max(0, middle - half_count)
            end = min(total_frames, start + frame_count)
            frame_indices = list(range(start, end))
            
        else:
            raise ValueError(f"Unknown extraction method: {method}")
        
        # Extract frames
        cap = cv2.VideoCapture(video_path)
        extracted_paths = []
        
        for i, frame_idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if ret:
                # Calculate timestamp
                timestamp = frame_idx / video_info["fps"]
                
                # Save frame
                output_path = get_output_path(
                    video_path, 
                    suffix=f"_frame_{i+1:03d}_t{timestamp:.2f}s",
                    extension=".jpg"
                )
                
                # Convert BGR to RGB for PIL
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                pil_image.save(output_path, "JPEG", quality=quality, optimize=True)
                
                extracted_paths.append(output_path)
                
                if (i + 1) % 10 == 0:
                    print(f"⏳ Extracted {i + 1}/{len(frame_indices)} frames")
        
        cap.release()
        
        print(f"✅ Extracted {len(extracted_paths)} frames successfully")
        return extracted_paths
        
    except Exception as e:
        raise RuntimeError(f"Frame extraction failed: {e}")

def extract_frames_by_time(video_path, time_points, quality=95):
    """
    Extract frames at specific time points.
    
    Args:
        video_path: Path to input video
        time_points: List of time points in seconds
        quality: JPEG quality (1-100)
    
    Returns:
        List of extracted frame paths
    """
    try:
        print(f"🎬 Extracting frames at {len(time_points)} specific time points")
        
        video_info = get_video_info(video_path)
        max_time = video_info["duration"]
        
        # Filter valid time points
        valid_times = [t for t in time_points if 0 <= t <= max_time]
        if len(valid_times) < len(time_points):
            print(f"⚠️ Filtered {len(time_points) - len(valid_times)} invalid time points")
        
        cap = cv2.VideoCapture(video_path)
        extracted_paths = []
        
        for i, time_point in enumerate(valid_times):
            # Seek to time point
            cap.set(cv2.CAP_PROP_POS_MSEC, time_point * 1000)
            ret, frame = cap.read()
            
            if ret:
                # Save frame
                output_path = get_output_path(
                    video_path,
                    suffix=f"_time_{time_point:.2f}s",
                    extension=".jpg"
                )
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                pil_image.save(output_path, "JPEG", quality=quality, optimize=True)
                
                extracted_paths.append(output_path)
        
        cap.release()
        
        print(f"✅ Extracted {len(extracted_paths)} frames at specific times")
        return extracted_paths
        
    except Exception as e:
        raise RuntimeError(f"Time-based frame extraction failed: {e}")

def extract_frames_by_interval(video_path, interval_seconds=1.0, quality=95, max_frames=100):
    """
    Extract frames at regular intervals.
    
    Args:
        video_path: Path to input video
        interval_seconds: Time interval between frames
        quality: JPEG quality (1-100)
        max_frames: Maximum number of frames to extract
    
    Returns:
        List of extracted frame paths
    """
    try:
        print(f"🎬 Extracting frames every {interval_seconds} seconds")
        
        video_info = get_video_info(video_path)
        duration = video_info["duration"]
        
        # Calculate time points
        time_points = []
        current_time = 0
        while current_time < duration and len(time_points) < max_frames:
            time_points.append(current_time)
            current_time += interval_seconds
        
        print(f"🔧 Will extract {len(time_points)} frames")
        return extract_frames_by_time(video_path, time_points, quality)
        
    except Exception as e:
        raise RuntimeError(f"Interval-based frame extraction failed: {e}")

def extract_key_frames(video_path, sensitivity=0.3, max_frames=50, quality=95):
    """
    Extract key frames based on scene changes.
    
    Args:
        video_path: Path to input video
        sensitivity: Scene change sensitivity (0.1-1.0)
        max_frames: Maximum frames to extract
        quality: JPEG quality
    
    Returns:
        List of extracted frame paths
    """
    try:
        print(f"🎬 Extracting key frames with sensitivity {sensitivity}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError("Could not open video")
        
        frames_data = []
        frame_count = 0
        prev_frame = None
        
        # Analyze frames for scene changes
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to grayscale for comparison
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if prev_frame is not None:
                # Calculate frame difference
                diff = cv2.absdiff(prev_frame, gray)
                non_zero_count = np.count_nonzero(diff)
                total_pixels = gray.shape[0] * gray.shape[1]
                change_ratio = non_zero_count / total_pixels
                
                frames_data.append({
                    "frame_idx": frame_count,
                    "change_ratio": change_ratio,
                    "timestamp": frame_count / cap.get(cv2.CAP_PROP_FPS)
                })
            
            prev_frame = gray.copy()
            frame_count += 1
            
            if frame_count % 100 == 0:
                print(f"⏳ Analyzed {frame_count} frames")
        
        cap.release()
        
        # Sort by change ratio and select key frames
        frames_data.sort(key=lambda x: x["change_ratio"], reverse=True)
        
        # Filter frames with significant changes
        threshold = sensitivity
        key_frames = [f for f in frames_data if f["change_ratio"] > threshold]
        
        # Limit to max_frames
        key_frames = key_frames[:max_frames]
        
        # Sort by timestamp for extraction
        key_frames.sort(key=lambda x: x["timestamp"])
        
        print(f"🔧 Found {len(key_frames)} key frames")
        
        # Extract the key frames
        time_points = [f["timestamp"] for f in key_frames]
        return extract_frames_by_time(video_path, time_points, quality)
        
    except Exception as e:
        raise RuntimeError(f"Key frame extraction failed: {e}")

def extract_frames_ffmpeg(video_path, output_pattern="frame_%03d.jpg", fps=None, start_time=0, duration=None):
    """
    Extract frames using FFmpeg (faster for large videos).
    
    Args:
        video_path: Path to input video
        output_pattern: Output filename pattern
        fps: Extract at specific FPS (None = all frames)
        start_time: Start time in seconds
        duration: Duration in seconds
    
    Returns:
        List of extracted frame paths
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
        
        print(f"🎬 Extracting frames using FFmpeg")
        
        # Create output directory
        output_dir = os.path.join("output", "frames_" + os.path.splitext(os.path.basename(video_path))[0])
        os.makedirs(output_dir, exist_ok=True)
        
        # Build FFmpeg command
        cmd = [ffmpeg_path, "-i", video_path]
        
        if start_time > 0:
            cmd.extend(["-ss", str(start_time)])
        if duration:
            cmd.extend(["-t", str(duration)])
        if fps:
            cmd.extend(["-vf", f"fps={fps}"])
        
        output_path = os.path.join(output_dir, output_pattern)
        cmd.extend(["-y", output_path])
        
        print(f"🔧 Running FFmpeg extraction...")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg extraction failed: {result.stderr.decode()}")
        
        # Get list of extracted files
        extracted_files = []
        for file in sorted(os.listdir(output_dir)):
            if file.endswith(('.jpg', '.png')):
                extracted_files.append(os.path.join(output_dir, file))
        
        print(f"✅ Extracted {len(extracted_files)} frames with FFmpeg")
        return extracted_files
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg extraction timed out")
    except Exception as e:
        raise RuntimeError(f"FFmpeg frame extraction failed: {e}")

def batch_extract_frames(video_paths, method="evenly_spaced", frame_count=10, quality=95):
    """Batch extract frames from multiple videos."""
    results = []
    
    for i, video_path in enumerate(video_paths):
        try:
            print(f"🎬 Processing video {i+1}/{len(video_paths)}: {os.path.basename(video_path)}")
            
            if method == "key_frames":
                extracted_frames = extract_key_frames(video_path, max_frames=frame_count, quality=quality)
            else:
                extracted_frames = extract_frames_by_count(video_path, frame_count, method, quality)
            
            results.append({
                "video": video_path,
                "frames": extracted_frames,
                "count": len(extracted_frames),
                "status": "success"
            })
            
        except Exception as e:
            print(f"❌ Failed to extract frames from {video_path}: {e}")
            results.append({
                "video": video_path,
                "frames": [],
                "count": 0,
                "status": "failed",
                "error": str(e)
            })
    
    return results

if __name__ == "__main__":
    # Test the module
    test_video = "test.mp4"
    if os.path.exists(test_video):
        frames = extract_frames_by_count(test_video, 5, "evenly_spaced")
        print(f"Test result: {len(frames)} frames extracted")
