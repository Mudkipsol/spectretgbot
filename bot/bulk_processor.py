#!/usr/bin/env python3
"""
Bulk Processing Module
Handle batch operations for all spoofing modules with progress tracking
"""

import os
import json
import time
import zipfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Import all spoofing modules
from photo_spoofer import batch_spoof_image
from gif_spoofer import batch_spoof_gifs, spoof_gif_advanced
from video_to_gif import batch_convert_videos_to_gifs
from frame_extractor import batch_extract_frames
from spoof_engine import run_spoof_pipeline
import spoof_engine as se

class BulkProgressTracker:
    """Thread-safe progress tracking for bulk operations."""
    
    def __init__(self, total_items):
        self.total_items = total_items
        self.completed_items = 0
        self.failed_items = 0
        self.current_item = ""
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def update_progress(self, completed=0, failed=0, current_item=""):
        with self.lock:
            self.completed_items += completed
            self.failed_items += failed
            if current_item:
                self.current_item = current_item
    
    def get_progress(self):
        with self.lock:
            elapsed = time.time() - self.start_time
            progress_percent = (self.completed_items + self.failed_items) / self.total_items * 100
            
            return {
                "total": self.total_items,
                "completed": self.completed_items,
                "failed": self.failed_items,
                "pending": self.total_items - self.completed_items - self.failed_items,
                "progress_percent": progress_percent,
                "current_item": self.current_item,
                "elapsed_time": elapsed,
                "estimated_remaining": (elapsed / max(1, self.completed_items + self.failed_items)) * (self.total_items - self.completed_items - self.failed_items) if self.completed_items + self.failed_items > 0 else 0
            }

def create_batch_report(results, operation_type, start_time, end_time):
    """Create a detailed report for batch operations."""
    
    total_items = len(results)
    successful_items = len([r for r in results if r.get("status") == "success"])
    failed_items = total_items - successful_items
    
    report = {
        "operation_type": operation_type,
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": end_time - start_time,
        "summary": {
            "total_items": total_items,
            "successful": successful_items,
            "failed": failed_items,
            "success_rate": (successful_items / total_items * 100) if total_items > 0 else 0
        },
        "results": results
    }
    
    # Save report
    report_path = os.path.join("output", f"batch_report_{operation_type}_{int(start_time)}.json")
    os.makedirs("output", exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report_path

def bulk_spoof_photos(image_paths, platform="generic", settings=None, max_workers=3):
    """
    Bulk spoof photos with progress tracking.
    
    Args:
        image_paths: List of image file paths
        platform: Target platform
        settings: Spoofing settings dict
        max_workers: Number of parallel workers
    
    Returns:
        Dict with results and report path
    """
    start_time = time.time()
    tracker = BulkProgressTracker(len(image_paths))
    results = []
    
    print(f"🖼️ Starting bulk photo spoofing: {len(image_paths)} images for {platform.upper()}")
    
    def process_image(img_path):
        try:
            tracker.update_progress(current_item=os.path.basename(img_path))
            
            # Apply settings if provided
            clean_meta = settings.get("clean_meta", True) if settings else True
            tweak_weight = settings.get("tweak_weight", True) if settings else True
            apply_filter = settings.get("apply_filter", True) if settings else True
            simulate_platform = settings.get("simulate_platform", True) if settings else True
            
            spoofed_path = batch_spoof_image(
                img_path, platform, clean_meta, tweak_weight, apply_filter, simulate_platform
            )
            
            tracker.update_progress(completed=1)
            return {"original": img_path, "spoofed": spoofed_path, "status": "success"}
            
        except Exception as e:
            tracker.update_progress(failed=1)
            return {"original": img_path, "spoofed": None, "status": "failed", "error": str(e)}
    
    # Process with thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(process_image, path): path for path in image_paths}
        
        for future in as_completed(future_to_path):
            result = future.result()
            results.append(result)
            
            # Progress update
            progress = tracker.get_progress()
            if progress["completed"] % 5 == 0:  # Update every 5 completions
                print(f"⏳ Progress: {progress['completed']}/{progress['total']} ({progress['progress_percent']:.1f}%)")
    
    end_time = time.time()
    report_path = create_batch_report(results, "photo_spoofing", start_time, end_time)
    
    successful = len([r for r in results if r["status"] == "success"])
    print(f"✅ Bulk photo spoofing complete: {successful}/{len(image_paths)} successful")
    
    return {"results": results, "report_path": report_path, "tracker": tracker.get_progress()}

def bulk_spoof_videos(video_paths, preset="TIKTOK_CLEAN", max_workers=2):
    """
    Bulk spoof videos with progress tracking.
    
    Args:
        video_paths: List of video file paths
        preset: Spoofing preset
        max_workers: Number of parallel workers (limited for video processing)
    
    Returns:
        Dict with results and report path
    """
    start_time = time.time()
    tracker = BulkProgressTracker(len(video_paths))
    results = []
    
    print(f"🎬 Starting bulk video spoofing: {len(video_paths)} videos with {preset} preset")
    
    def process_video(video_path):
        try:
            tracker.update_progress(current_item=os.path.basename(video_path))
            print(f"🎬 Processing: {os.path.basename(video_path)}")
            
            # Set spoofing engine globals based on preset
            if preset == "TIKTOK_CLEAN":
                se.PRESET_MODE = "TIKTOK_SAFE"
                se.FORGERY_PROFILE = "TIKTOK_IPHONE"
                se.TRANSCODE_PROFILE = "TIKTOK_IOS"
                se.STYLE_MORPH_PRESET = "TIKTOK_CLEAN"
            elif preset == "IG_RAW_LOOK":
                se.PRESET_MODE = "IG_REELS_SAFE"
                se.FORGERY_PROFILE = "IG_ANDROID"
                se.TRANSCODE_PROFILE = "IG_REELS"
                se.STYLE_MORPH_PRESET = "IG_RAW_LOOK"
            elif preset == "CINEMATIC_FADE":
                se.PRESET_MODE = "YT_SHORTS_SAFE"
                se.FORGERY_PROFILE = "CANON_PRO"
                se.TRANSCODE_PROFILE = "YT_WEB"
                se.STYLE_MORPH_PRESET = "CINEMATIC_FADE"
            elif preset == "OF_WASH":
                se.PRESET_MODE = "OF_WASH"
                se.FORGERY_PROFILE = "OF_CREATOR"
                se.TRANSCODE_PROFILE = "MOBILE_NATIVE"
                se.STYLE_MORPH_PRESET = "IG_RAW_LOOK"
            
            # Get existing output files before processing
            os.makedirs("output", exist_ok=True)
            existing_files = set(os.listdir("output"))
            
            # Process video
            run_spoof_pipeline(video_path)
            
            # Find new output files created after processing
            current_files = set(os.listdir("output"))
            new_files = current_files - existing_files
            
            # Look for the output file
            output_candidates = []
            for file in new_files:
                if file.startswith("spoofed_") and file.endswith("_final_output.mp4"):
                    output_candidates.append(os.path.join("output", file))
            
            # If no new files, check all files (fallback)
            if not output_candidates:
                all_output_files = []
                for file in os.listdir("output"):
                    if file.startswith("spoofed_") and file.endswith("_final_output.mp4"):
                        all_output_files.append(os.path.join("output", file))
                
                if all_output_files:
                    # Get the most recent file
                    latest_output = max(all_output_files, key=os.path.getctime)
                    output_candidates = [latest_output]
            
            if output_candidates:
                latest_output = output_candidates[0] if len(output_candidates) == 1 else max(output_candidates, key=os.path.getctime)
                print(f"✅ Video processed: {os.path.basename(latest_output)}")
                tracker.update_progress(completed=1)
                return {"original": video_path, "spoofed": latest_output, "status": "success"}
            else:
                print(f"❌ No output file found for: {os.path.basename(video_path)}")
                tracker.update_progress(failed=1)
                return {"original": video_path, "spoofed": None, "status": "failed", "error": "No output file generated"}
                
        except Exception as e:
            print(f"❌ Error processing {os.path.basename(video_path)}: {str(e)}")
            tracker.update_progress(failed=1)
            return {"original": video_path, "spoofed": None, "status": "failed", "error": str(e)}
    
    # Process videos sequentially to avoid file conflicts (max_workers=1 for videos)
    if max_workers > 1:
        print("🔧 Using sequential processing for video stability")
        max_workers = 1
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Process one at a time for videos to avoid output file conflicts
        for i, video_path in enumerate(video_paths):
            print(f"📹 Processing video {i+1}/{len(video_paths)}: {os.path.basename(video_path)}")
            future = executor.submit(process_video, video_path)
            result = future.result()
            results.append(result)
            
            # Progress update
            progress = tracker.get_progress()
            print(f"⏳ Progress: {progress['completed']}/{progress['total']} ({progress['progress_percent']:.1f}%) - ETA: {progress['estimated_remaining']:.0f}s")
    
    end_time = time.time()
    report_path = create_batch_report(results, "video_spoofing", start_time, end_time)
    
    successful = len([r for r in results if r["status"] == "success"])
    print(f"✅ Bulk video spoofing complete: {successful}/{len(video_paths)} successful")
    
    return {"results": results, "report_path": report_path, "tracker": tracker.get_progress()}

def bulk_spoof_gifs(gif_paths, platform="reddit", variance_strength="medium", max_workers=3):
    """
    Bulk spoof GIFs with progress tracking.
    
    Args:
        gif_paths: List of GIF file paths
        platform: Target platform (reddit, twitter, threads, discord)
        variance_strength: Spoofing variance level
        max_workers: Number of parallel workers
    
    Returns:
        Dict with results and report path
    """
    start_time = time.time()
    tracker = BulkProgressTracker(len(gif_paths))
    results = []
    
    print(f"🎭 Starting bulk GIF spoofing: {len(gif_paths)} GIFs for {platform.upper()}")
    
    def process_gif(gif_path):
        try:
            tracker.update_progress(current_item=os.path.basename(gif_path))
            print(f"🎭 Processing: {os.path.basename(gif_path)}")
            
            spoofed_path = spoof_gif_advanced(gif_path, platform, variance_strength, True)
            
            print(f"✅ GIF processed: {os.path.basename(spoofed_path)}")
            tracker.update_progress(completed=1)
            return {"original": gif_path, "spoofed": spoofed_path, "status": "success"}
            
        except Exception as e:
            print(f"❌ Error processing {os.path.basename(gif_path)}: {str(e)}")
            tracker.update_progress(failed=1)
            return {"original": gif_path, "spoofed": None, "status": "failed", "error": str(e)}
    
    # Process with thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(process_gif, path): path for path in gif_paths}
        
        for future in as_completed(future_to_path):
            result = future.result()
            results.append(result)
            
            # Progress update
            progress = tracker.get_progress()
            if progress["completed"] % 2 == 0:
                print(f"⏳ Progress: {progress['completed']}/{progress['total']} ({progress['progress_percent']:.1f}%)")
    
    end_time = time.time()
    report_path = create_batch_report(results, "gif_spoofing", start_time, end_time)
    
    successful = len([r for r in results if r["status"] == "success"])
    print(f"✅ Bulk GIF spoofing complete: {successful}/{len(gif_paths)} successful")
    
    return {"results": results, "report_path": report_path, "tracker": tracker.get_progress()}

def bulk_convert_to_gifs(video_paths, platform="general", fps=15, width=400, max_workers=3):
    """Bulk convert videos to GIFs with progress tracking."""
    start_time = time.time()
    tracker = BulkProgressTracker(len(video_paths))
    
    print(f"🎬➡️🎭 Starting bulk video to GIF conversion: {len(video_paths)} videos")
    
    def process_video(video_path):
        try:
            tracker.update_progress(current_item=os.path.basename(video_path))
            from video_to_gif import convert_video_to_gif
            
            gif_path = convert_video_to_gif(video_path, fps=fps, width=width, platform=platform)
            tracker.update_progress(completed=1)
            return {"original": video_path, "gif": gif_path, "status": "success"}
            
        except Exception as e:
            tracker.update_progress(failed=1)
            return {"original": video_path, "gif": None, "status": "failed", "error": str(e)}
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(process_video, path): path for path in video_paths}
        
        for future in as_completed(future_to_path):
            result = future.result()
            results.append(result)
            
            progress = tracker.get_progress()
            if progress["completed"] % 2 == 0:
                print(f"⏳ Progress: {progress['completed']}/{progress['total']} ({progress['progress_percent']:.1f}%)")
    
    end_time = time.time()
    report_path = create_batch_report(results, "video_to_gif", start_time, end_time)
    
    successful = len([r for r in results if r["status"] == "success"])
    print(f"✅ Bulk GIF conversion complete: {successful}/{len(video_paths)} successful")
    
    return {"results": results, "report_path": report_path, "tracker": tracker.get_progress()}

def bulk_extract_frames(video_paths, method="evenly_spaced", frame_count=10, max_workers=3):
    """Bulk extract frames from videos with progress tracking."""
    start_time = time.time()
    tracker = BulkProgressTracker(len(video_paths))
    
    print(f"🎬📸 Starting bulk frame extraction: {len(video_paths)} videos, {frame_count} frames each")
    
    def process_video(video_path):
        try:
            tracker.update_progress(current_item=os.path.basename(video_path))
            from frame_extractor import extract_frames_by_count
            
            frames = extract_frames_by_count(video_path, frame_count, method)
            tracker.update_progress(completed=1)
            return {"video": video_path, "frames": frames, "count": len(frames), "status": "success"}
            
        except Exception as e:
            tracker.update_progress(failed=1)
            return {"video": video_path, "frames": [], "count": 0, "status": "failed", "error": str(e)}
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(process_video, path): path for path in video_paths}
        
        for future in as_completed(future_to_path):
            result = future.result()
            results.append(result)
            
            progress = tracker.get_progress()
            if progress["completed"] % 3 == 0:
                print(f"⏳ Progress: {progress['completed']}/{progress['total']} ({progress['progress_percent']:.1f}%)")
    
    end_time = time.time()
    report_path = create_batch_report(results, "frame_extraction", start_time, end_time)
    
    successful = len([r for r in results if r["status"] == "success"])
    total_frames = sum(r["count"] for r in results if r["status"] == "success")
    print(f"✅ Bulk frame extraction complete: {successful}/{len(video_paths)} videos, {total_frames} frames total")
    
    return {"results": results, "report_path": report_path, "tracker": tracker.get_progress()}

def create_bulk_output_zip(results, operation_type):
    """Create ZIP file containing all successful outputs."""
    try:
        zip_path = os.path.join("output", f"bulk_{operation_type}_{int(time.time())}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for result in results:
                if result["status"] == "success":
                    if "spoofed" in result and result["spoofed"]:
                        # Single file output (photos, videos)
                        if os.path.exists(result["spoofed"]):
                            arcname = os.path.basename(result["spoofed"])
                            zipf.write(result["spoofed"], arcname)
                    
                    elif "frames" in result and result["frames"]:
                        # Multiple files output (frame extraction)
                        for frame_path in result["frames"]:
                            if os.path.exists(frame_path):
                                arcname = os.path.basename(frame_path)
                                zipf.write(frame_path, arcname)
                    
                    elif "gif" in result and result["gif"]:
                        # GIF output
                        if os.path.exists(result["gif"]):
                            arcname = os.path.basename(result["gif"])
                            zipf.write(result["gif"], arcname)
        
        file_size = os.path.getsize(zip_path) / (1024 * 1024)  # MB
        print(f"📦 Created bulk output ZIP: {file_size:.1f}MB")
        return zip_path
        
    except Exception as e:
        print(f"❌ Failed to create ZIP file: {e}")
        return None

def get_bulk_operation_status(operation_id):
    """Get status of ongoing bulk operation (placeholder for future implementation)."""
    # This would be used for real-time progress tracking in the Telegram bot
    # For now, return dummy data
    return {
        "operation_id": operation_id,
        "status": "completed",
        "progress": 100,
        "message": "Operation completed successfully"
    }

if __name__ == "__main__":
    # Test bulk operations
    print("Testing bulk processor...")
    
    # Test with dummy files (replace with actual files for testing)
    test_images = ["test1.jpg", "test2.jpg"] if any(os.path.exists(f) for f in ["test1.jpg", "test2.jpg"]) else []
    test_videos = ["test1.mp4", "test2.mp4"] if any(os.path.exists(f) for f in ["test1.mp4", "test2.mp4"]) else []
    
    if test_images:
        result = bulk_spoof_photos(test_images, "reddit")
        print(f"Photo bulk test: {len(result['results'])} items processed")
    
    if test_videos:
        result = bulk_extract_frames(test_videos, "evenly_spaced", 5)
        print(f"Frame extraction bulk test: {len(result['results'])} items processed")
