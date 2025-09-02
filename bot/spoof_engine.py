
# === PHASE 5.1: REDDIT + DATING SPOOF STACK ===
REDDIT_PRESETS = ["REDDIT_BURNER"]
DATING_PRESETS = ["TINDER_VERIFIED"]



def apply_eye_contact_drift(frame):
    h, w = frame.shape[:2]
    drift_x = int(np.random.uniform(-2, 2))
    drift_y = int(np.random.uniform(-2, 2))
    M = np.float32([[1, 0, drift_x], [0, 1, drift_y]])
    return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT101)



def smooth_loop_frames(frames, blend_frames=6):
    for i in range(blend_frames):
        alpha = i / blend_frames
        blended = cv2.addWeighted(frames[i], 1 - alpha, frames[-blend_frames + i], alpha, 0)
        frames[i] = blended
        frames[-blend_frames + i] = blended
    return frames



# === PHASE 5.0.2: UPSCALE SELECTOR ===
UPSCALE_RESOLUTION = "2K"  # Options: NONE, 2K, 4K



# === PHASE 5.0: VIDEO ENHANCEMENT STACK ===
ENABLE_ENHANCEMENT = True
ENHANCEMENT_PRESET = "OF_POLISH"  # Options: CRISP_LUX, OF_POLISH, ULTRA_RESYNC, VINTAGE_FIX



def apply_video_enhancement(frame):
    if ENHANCEMENT_PRESET == "CRISP_LUX":
        frame = cv2.detailEnhance(frame, sigma_s=5, sigma_r=0.10)
        frame = cv2.edgePreservingFilter(frame, flags=1, sigma_s=64, sigma_r=0.25)
    elif ENHANCEMENT_PRESET == "OF_POLISH":
        blur = cv2.GaussianBlur(frame, (3, 3), 0)
        frame = cv2.addWeighted(frame, 1.05, blur, -0.05, 0)
    elif ENHANCEMENT_PRESET == "ULTRA_RESYNC":
        frame = cv2.bilateralFilter(frame, 9, 75, 75)
        frame = cv2.edgePreservingFilter(frame, flags=2, sigma_s=128, sigma_r=0.35)
    elif ENHANCEMENT_PRESET == "VINTAGE_FIX":
        frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)
    return frame



# === PHASE 4.1: SENSOR FINGERPRINT INJECTION ===
def apply_sensor_fingerprint(frame, model="SONY_IMX"):
    h, w = frame.shape[:2]
    noise = np.random.normal(loc=0, scale=3, size=(h, w)).astype(np.int16)

    if model == "SONY_IMX":
        # Simulate column banding pattern
        for i in range(0, w, 20):
            noise[:, i:i+2] += np.random.randint(3, 6)
    elif model == "OMNIVISION":
        # Simulate diagonal sweep and stuck pixels
        for i in range(5, min(h, w), 15):
            noise[i:i+1, i:i+1] += 10

    # Add noise to each channel
    noisy_frame = frame.copy()
    for c in range(3):
        noisy_frame[..., c] = np.clip(noisy_frame[..., c].astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return noisy_frame



# === TRANSCODE SIGNATURE MIMICRY ===
TRANSCODE_PROFILE = "TIKTOK_IOS"  # Options: TIKTOK_IOS, YT_WEB, IG_REELS, MOBILE_NATIVE, NONE

# === PHASE 3.1: COMPRESSOR SIGNATURE EMULATION ===
def build_transcode_command(input_path, original_audio_path, output_path, profile, ffmpeg_path="ffmpeg"):
    common_flags = ["-map", "0:v:0", "-map", "1:a:0", "-y"]
    profile_map = {
        "TIKTOK_IOS": [
            "-c:v", "libx264",
            "-preset", "fast",  # Good balance of quality and speed
            "-tune", "film",  # Better quality for video content
            "-g", "30",  # GOP size
            "-b:v", "3500k",  # Higher bitrate for better quality
            "-maxrate", "4000k",
            "-bufsize", "6000k",
            "-profile:v", "main",  # Better quality than baseline
            "-level", "4.0",  # Safe level
            "-threads", "2",  # Limit threads for containers
            "-movflags", "+faststart"
        ],
        "YT_WEB": [
            "-c:v", "libx264",
            "-preset", "fast",  # Good balance of quality and speed
            "-tune", "film",  # Better quality for video content
            "-g", "30",
            "-b:v", "4000k",  # Higher bitrate for better quality
            "-maxrate", "4500k",
            "-bufsize", "6000k",
            "-profile:v", "main",  # Better quality than baseline
            "-level", "4.0",
            "-threads", "2"  # Limit threads for containers
        ],
        "IG_REELS": [
            "-c:v", "libx264",
            "-preset", "fast",  # Good balance of quality and speed
            "-tune", "film",  # Better quality for video content
            "-g", "30",  # GOP size
            "-b:v", "3200k",  # Higher bitrate for better quality
            "-maxrate", "3800k",
            "-bufsize", "5000k",
            "-profile:v", "main",  # Better quality than baseline
            "-level", "4.0",  # Safe level for high res support
            "-threads", "2",  # Limit threads for containers
            "-movflags", "+faststart"
        ],
        "MOBILE_NATIVE": [
            "-c:v", "libx264",
            "-preset", "ultrafast",  # Fastest preset for container environments
            "-tune", "zerolatency",  # Optimized for low latency
            "-g", "30",
            "-b:v", "2000k",  # Reduced bitrate for faster processing
            "-maxrate", "2500k",
            "-bufsize", "3000k",
            "-profile:v", "baseline",  # Most compatible profile
            "-level", "4.0",  # Safe level for high res
            "-threads", "2",  # Limit threads for containers
            "-movflags", "+faststart"
        ],
        "NONE": ["-c:v", "copy"]
    }
    cmd = [ffmpeg_path, "-i", input_path, "-i", original_audio_path] + profile_map.get(profile, profile_map["NONE"]) + ["-c:a", "aac"] + common_flags + [output_path]
    return cmd


import os
import sys
import uuid
import cv2
import random
import shutil
import datetime
import subprocess
import numpy as np
from PIL import Image
import imagehash
import json

# === PHASE 3.4: SPOOF PROFILE SAVE/LOAD SYSTEM ===
CONFIG_PATH = "spoof_profile.json"

def save_spoof_profile():
    profile = {
        "PRESET_MODE": PRESET_MODE,
        "FORGERY_PROFILE": FORGERY_PROFILE,
        "TRANSCODE_PROFILE": TRANSCODE_PROFILE,
        "STYLE_MORPH_PRESET": STYLE_MORPH_PRESET,
        "MOTION_PROFILE": MOTION_PROFILE,
        "ENABLE_WATERMARK_REMOVAL": ENABLE_WATERMARK_REMOVAL,
        "ENABLE_VISUAL_ECHO": ENABLE_VISUAL_ECHO,
        "ENABLE_RESOLUTION_TWEAK": ENABLE_RESOLUTION_TWEAK,
        "ENABLE_FPS_JITTER": ENABLE_FPS_JITTER,
        "FRAME_VARIANCE_STRENGTH": FRAME_VARIANCE_STRENGTH
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(profile, f, indent=2)
    print(f"[💾] Spoof profile saved to {CONFIG_PATH}")

def load_spoof_profile():
    global PRESET_MODE, FORGERY_PROFILE, TRANSCODE_PROFILE
    global STYLE_MORPH_PRESET, MOTION_PROFILE
    global ENABLE_WATERMARK_REMOVAL, ENABLE_VISUAL_ECHO
    global ENABLE_RESOLUTION_TWEAK, ENABLE_FPS_JITTER, FRAME_VARIANCE_STRENGTH

    try:
        with open(CONFIG_PATH, "r") as f:
            profile = json.load(f)
        PRESET_MODE = profile.get("PRESET_MODE", PRESET_MODE)
        FORGERY_PROFILE = profile.get("FORGERY_PROFILE", FORGERY_PROFILE)
        TRANSCODE_PROFILE = profile.get("TRANSCODE_PROFILE", TRANSCODE_PROFILE)
        STYLE_MORPH_PRESET = profile.get("STYLE_MORPH_PRESET", STYLE_MORPH_PRESET)
        MOTION_PROFILE = profile.get("MOTION_PROFILE", MOTION_PROFILE)
        ENABLE_WATERMARK_REMOVAL = profile.get("ENABLE_WATERMARK_REMOVAL", ENABLE_WATERMARK_REMOVAL)
        ENABLE_VISUAL_ECHO = profile.get("ENABLE_VISUAL_ECHO", ENABLE_VISUAL_ECHO)
        ENABLE_RESOLUTION_TWEAK = profile.get("ENABLE_RESOLUTION_TWEAK", ENABLE_RESOLUTION_TWEAK)
        ENABLE_FPS_JITTER = profile.get("ENABLE_FPS_JITTER", ENABLE_FPS_JITTER)
        FRAME_VARIANCE_STRENGTH = profile.get("FRAME_VARIANCE_STRENGTH", FRAME_VARIANCE_STRENGTH)
        print(f"[📂] Spoof profile loaded from {CONFIG_PATH}")
    except FileNotFoundError:
        print(f"[⚠️] No spoof profile found. Using defaults.")


# === CONFIGURATION ===
PRESET_MODE = "RANDOMIZED"
FORGERY_PROFILE = "TIKTOK_IPHONE"

# === PRESET MODE LOGIC ===
ENABLE_WATERMARK_REMOVAL = False
ENABLE_VISUAL_ECHO = False
ENABLE_RESOLUTION_TWEAK = False
ENABLE_FPS_JITTER = False
FRAME_VARIANCE_STRENGTH = "soft"

if PRESET_MODE == "OF_WASH":
    ENABLE_WATERMARK_REMOVAL = True
    FRAME_VARIANCE_STRENGTH = "soft"
elif PRESET_MODE == "TIKTOK_SAFE":
    ENABLE_RESOLUTION_TWEAK = True
    ENABLE_FPS_JITTER = True
    FRAME_VARIANCE_STRENGTH = "light"
elif PRESET_MODE == "IG_REELS_SAFE":
    ENABLE_RESOLUTION_TWEAK = True
    FRAME_VARIANCE_STRENGTH = "very_light"
elif PRESET_MODE == "YT_SHORTS_SAFE":
    ENABLE_RESOLUTION_TWEAK = True
    ENABLE_FPS_JITTER = True
    ENABLE_VISUAL_ECHO = True
    FRAME_VARIANCE_STRENGTH = "light"
elif PRESET_MODE == "FULL_OBFUSCATION":
    ENABLE_WATERMARK_REMOVAL = True
    ENABLE_VISUAL_ECHO = True
    ENABLE_RESOLUTION_TWEAK = True
    ENABLE_FPS_JITTER = True
    FRAME_VARIANCE_STRENGTH = "moderate"
elif PRESET_MODE == "RANDOMIZED":
    ENABLE_WATERMARK_REMOVAL = random.random() < 0.4
    ENABLE_VISUAL_ECHO = random.random() < 0.6
    ENABLE_RESOLUTION_TWEAK = random.random() < 0.7
    ENABLE_FPS_JITTER = random.random() < 0.6
    FRAME_VARIANCE_STRENGTH = random.choice(["soft", "very_light", "light", "moderate"])

def get_forged_metadata(profile):
    profiles = {
        "TIKTOK_IPHONE": {"make": "Apple", "model": "iPhone 15 Pro", "software": "TikTok iOS", "comment": "Uploaded via TikTok"},
        "IG_ANDROID": {"make": "Samsung", "model": "SM-G998U", "software": "Instagram Android", "comment": "Created with Instagram"},
        "CANON_PRO": {"make": "Canon", "model": "EOS R6", "software": "Final Cut Pro", "comment": "Edited professionally"},
        "OF_CREATOR": {"make": "Apple", "model": "iPhone 14 Pro", "software": "OF Creator Studio", "comment": "OF Verified"},
        "CUSTOM": {"make": "Spectre", "model": "Spoofer X", "software": "SpoofEngine", "comment": "Forged by SpectreSpoofer"}
    }
    return profiles.get(profile, profiles["CUSTOM"])


# === STYLE MORPHING PRESET ===
STYLE_MORPH_PRESET = "TIKTOK_CLEAN"  # Options: TIKTOK_CLEAN, IG_RAW_LOOK, VINTAGE_SOFT, CINEMATIC_FADE, NONE

def apply_style_morph(frame, preset):
    frame = frame.astype(np.float32)
    if preset == "TIKTOK_CLEAN":
        frame *= np.array([1.03, 1.02, 1.00])  # subtle blue/yellow bias
        frame += 3
    elif preset == "IG_RAW_LOOK":
        frame *= np.array([0.98, 0.98, 1.04])  # cool tone
        frame -= 4
    elif preset == "VINTAGE_SOFT":
        frame *= np.array([1.00, 0.95, 0.90])
        frame = cv2.GaussianBlur(frame, (3, 3), 0)
    elif preset == "CINEMATIC_FADE":
        # More stable CINEMATIC_FADE processing to avoid flickering
        frame = frame.astype(np.float32)
        # Apply subtle warm tone and slight saturation reduction
        frame *= np.array([1.02, 1.00, 0.98])  # Warm tone
        frame = frame * 0.95 + 8  # Slight lift and reduce contrast
        return np.clip(frame, 0, 255).astype(np.uint8)
    return np.clip(frame, 0, 255).astype(np.uint8)



# === OPTIONAL .CUBE LUT SUPPORT ===

    lut_3d = []
    size = 33
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip().startswith('#') or not line.strip():
                continue
            if line.lower().startswith('lut_3d_size'):
                size = int(line.strip().split()[-1])
                continue
            if any(c.isalpha() for c in line.strip()):
                continue
            rgb = list(map(float, line.strip().split()))
            if len(rgb) == 3:
                lut_3d.append(rgb)
    lut_3d = np.array(lut_3d).reshape((size, size, size, 3))
    return lut_3d, size

    normalized = frame / 255.0
    index = (normalized * (size - 1)).astype(int)
    r, g, b = index[..., 0], index[..., 1], index[..., 2]
    mapped = lut[r, g, b]
    return np.clip(mapped * 255.0, 0, 255).astype(np.uint8)



# === MOTION VECTOR FORGERY ===
MOTION_PROFILE = "STABILIZED_GIMBAL"  # Auto-tuned for safe overlays  # Options: HANDHELD_REAL, STABILIZED_GIMBAL, IPHONE_CROP_SHAKE, None

def apply_motion_forgery(frame, profile):
    h, w = frame.shape[:2]
    center = (w // 2, h // 2)
    max_shift = {"HANDHELD_REAL": 0.8, "STABILIZED_GIMBAL": 0.2, "IPHONE_CROP_SHAKE": 0.6}.get(profile, 0)
    max_rot = {"HANDHELD_REAL": 0.6, "STABILIZED_GIMBAL": 0.1, "IPHONE_CROP_SHAKE": 0.3}.get(profile, 0)
    
    dx = random.uniform(-max_shift, max_shift)
    dy = random.uniform(-max_shift, max_shift)
    rot = random.uniform(-max_rot, max_rot)
    M = cv2.getRotationMatrix2D(center, rot, 1.0)
    M[0, 2] += dx
    M[1, 2] += dy
    return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT101)



def apply_behavioral_motion_flow(frame, index, total_frames):
    h, w = frame.shape[:2]
    center = (w // 2, h // 2)

    # Decelerating pan curve (like a real hand slows down)
    progress = index / max(1, total_frames)
    curve_factor = np.sin(progress * np.pi)  # Smooth in-out

    max_pan_x = 2.0  # pixels
    max_pan_y = 1.0  # slight vertical drift
    pan_x = curve_factor * max_pan_x * np.sin(index / 15.0)
    pan_y = curve_factor * max_pan_y * np.cos(index / 30.0)

    # Micro jitters (simulate real grip instability)
    jitter_x = np.random.uniform(-0.3, 0.3)
    jitter_y = np.random.uniform(-0.3, 0.3)

    M = np.float32([[1, 0, pan_x + jitter_x],
                    [0, 1, pan_y + jitter_y]])

    return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT101)


# === ADVANCED PLATFORM-SPECIFIC SPOOFING ===

def apply_platform_specific_transform(frame, platform_profile, frame_index, total_frames):
    """
    Apply platform-specific transformations that are imperceptible to humans
    but significantly change digital fingerprints for platform detection.
    """
    h, w = frame.shape[:2]
    
    if platform_profile == "TIKTOK_IOS":
        # TikTok: Subtle rotation + aspect ratio shift
        # Rotate by 0.1-0.2 degrees (imperceptible but changes hash)
        rotation_angle = 0.15 + 0.05 * np.sin(2 * np.pi * frame_index / total_frames)
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, rotation_angle, 1.0)
        frame = cv2.warpAffine(frame, rotation_matrix, (w, h), borderMode=cv2.BORDER_REFLECT_101)
        
        # Micro crop (2-4 pixels) with intelligent content preservation
        crop_x = random.randint(1, 3)
        crop_y = random.randint(1, 3)
        frame = frame[crop_y:h-crop_y, crop_x:w-crop_x]
        frame = cv2.resize(frame, (w, h))
        
    elif platform_profile == "IG_REELS":
        # Instagram: Slight aspect ratio change + micro scale
        # Scale by 0.998-1.002 (changes dimensions slightly)
        scale_factor = 0.999 + 0.002 * np.sin(2 * np.pi * frame_index / total_frames)
        new_w = int(w * scale_factor)
        new_h = int(h * scale_factor)
        frame = cv2.resize(frame, (new_w, new_h))
        
        # Pad back to original size with edge extension
        if new_w < w or new_h < h:
            top = (h - new_h) // 2
            bottom = h - new_h - top
            left = (w - new_w) // 2
            right = w - new_w - left
            frame = cv2.copyMakeBorder(frame, top, bottom, left, right, cv2.BORDER_REFLECT_101)
        else:
            # Crop if scaled up
            start_x = (new_w - w) // 2
            start_y = (new_h - h) // 2
            frame = frame[start_y:start_y+h, start_x:start_x+w]
            
    elif platform_profile == "YT_WEB":
        # YouTube: Perspective shift + micro rotation
        # Apply very subtle perspective transformation
        offset = 2 + int(2 * np.sin(2 * np.pi * frame_index / total_frames))
        src_points = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        dst_points = np.float32([
            [offset, 0], [w-offset, offset], 
            [0, h-offset], [w, h]
        ])
        perspective_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        frame = cv2.warpPerspective(frame, perspective_matrix, (w, h), borderMode=cv2.BORDER_REFLECT_101)
        
    return frame


def apply_temporal_speed_variance(video_path, platform_profile, output_path, ffmpeg_path):
    """
    Apply imperceptible speed changes that break temporal fingerprints
    while maintaining natural playback feel.
    """
    if platform_profile == "TIKTOK_IOS":
        # TikTok: 0.995-1.005x speed (0.5% variance, imperceptible)
        speed_factor = random.uniform(0.995, 1.005)
        
    elif platform_profile == "IG_REELS":
        # Instagram: 0.996-1.004x speed (0.4% variance)
        speed_factor = random.uniform(0.996, 1.004)
        
    elif platform_profile == "YT_WEB":
        # YouTube: 0.997-1.003x speed (0.3% variance, most conservative)
        speed_factor = random.uniform(0.997, 1.003)
        
    else:
        speed_factor = 1.0
    
    # Only apply if variance is meaningful
    if abs(speed_factor - 1.0) > 0.001:
        print(f"🔧 Applying {speed_factor:.4f}x speed adjustment (imperceptible)")
        
        # Try with audio tempo adjustment first
        cmd = [
            ffmpeg_path, "-i", video_path,
            "-filter:v", f"setpts={1/speed_factor}*PTS",
            "-filter:a", f"atempo={speed_factor}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-threads", "2", "-y", output_path
        ]
        
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            if result.returncode == 0 and os.path.exists(output_path):
                return True
        except subprocess.TimeoutExpired:
            print(f"[⚠️] Speed adjustment timed out")
        
        # Fallback: Video-only speed adjustment (still breaks temporal fingerprints)
        print(f"🔧 Fallback: Video-only speed adjustment")
        cmd_fallback = [
            ffmpeg_path, "-i", video_path,
            "-filter:v", f"setpts={1/speed_factor}*PTS",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "copy",  # Copy audio without tempo change
            "-threads", "2", "-y", output_path
        ]
        
        try:
            result = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"✅ Video-only speed adjustment successful")
                return True
            else:
                print(f"[⚠️] Speed adjustment failed: {result.stderr.decode()[:200]}")
                return False
        except subprocess.TimeoutExpired:
            print(f"[⚠️] Speed adjustment timed out")
            return False
    
    return False  # No speed change applied


def compute_ai_detectability_score(video_path):
    cap = cv2.VideoCapture(video_path)
    frame_hashes, brightness_levels = [], []
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sample_interval = max(1, frame_count // 10)
    for i in range(frame_count):
        ret, frame = cap.read()
        if not ret: break
        if i % sample_interval == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb)
            frame_hashes.append(imagehash.phash(pil))
            brightness_levels.append(np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)))
    cap.release()
    hash_diffs = [frame_hashes[i] - frame_hashes[i-1] for i in range(1, len(frame_hashes))]
    avg_diff = np.mean(hash_diffs) if hash_diffs else 0
    bright_std = np.std(brightness_levels)

    # Adjusted thresholds — more lenient
    hash_score = min(100, avg_diff * 3.0)
    luminance_score = min(100, bright_std * 1.4)

    final = 100 - int((hash_score + luminance_score) / 2)
    if final < 40:
        label = "Highly Detectable"
    elif final < 55:
        label = "Moderately Detectable"
    else:
        label = "Safe"
    return final, label

def run_spoof_pipeline(filepath):
    try:
        # Auto-detect FFMPEG path based on environment
        FFMPEG_PATH = shutil.which("ffmpeg")
        if FFMPEG_PATH is None:
            # Fallback to Windows path if running locally
            windows_ffmpeg = "C:\\Tools\\FFmpeg\\ffmpeg.exe"
            if os.path.exists(windows_ffmpeg):
                FFMPEG_PATH = windows_ffmpeg
            else:
                print(f"[❌] FFMPEG not found in PATH or at {windows_ffmpeg}")
                return
        
        EXIFTOOL_PATH = "exiftool"
        if shutil.which(EXIFTOOL_PATH) is None:
            print(f"[❌] ExifTool not found in PATH.")
            return

        filename = os.path.basename(filepath)
        spoof_id = uuid.uuid4().hex[:8]
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        temp_video_only = os.path.join(output_dir, f"temp_{spoof_id}.mp4")
        shutil.copy(filepath, temp_video_only)

        transcoded_output = os.path.join(output_dir, f"transcoded_{spoof_id}.mp4")
        final_output = os.path.join(output_dir, f"spoofed_{spoof_id}_final_output.mp4")
        report_path = os.path.join(output_dir, f"report_{spoof_id}.txt")

        print("🔧 Spoofing:", filename)

    except Exception as e:
        print("[❌ FATAL ERROR] Engine failed during setup:")
        import traceback
        print(traceback.format_exc())
        return


    # Metadata injection
    forged = get_forged_metadata(FORGERY_PROFILE)
    random_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 365))
    formatted_date = random_date.strftime('%Y:%m:%d %H:%M:%S')
    subprocess.run([
        EXIFTOOL_PATH, "-overwrite_original",
        f"-CreateDate={formatted_date}",
        f"-ModifyDate={formatted_date}",
        f"-TrackCreateDate={formatted_date}",
        f"-TrackModifyDate={formatted_date}",
        f"-Make={forged['make']}",
        f"-Model={forged['model']}",
        f"-Software={forged['software']}",
        f"-Comment={forged['comment']}",
        f"-DateTimeOriginal={formatted_date}",
        temp_video_only
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def detect_static_watermark(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        mask = np.zeros_like(gray)
        h, w = gray.shape
        roi_size = 100
        coords = [(0, 0), (0, w-roi_size), (h-roi_size, 0), (h-roi_size, w-roi_size)]
        for y, x in coords:
            roi = thresh[y:y+roi_size, x:x+roi_size]
            if cv2.countNonZero(roi) > roi_size * roi_size * 0.05:
                mask[y:y+roi_size, x:x+roi_size] = 255
        return mask

    def remove_static_watermark(frame, mask):
        if mask.shape[:2] != frame.shape[:2]:
            mask = cv2.resize(mask, (frame.shape[1], frame.shape[0]))
        return cv2.inpaint(frame, mask, 3, cv2.INPAINT_TELEA)

    def soften_echo(frame):
        blur = cv2.GaussianBlur(frame, (5, 5), 0)
        gamma = 1.2
        lut = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in range(256)]).astype("uint8")
        return cv2.LUT(blur, lut)

    def frame_variance_spoofer(path):
        """
        Process video frames with FFmpeg pipeline for better reliability in containers
        """
        # Get video info using FFmpeg (more reliable than OpenCV in containers)
        probe_cmd = [FFMPEG_PATH, "-i", path, "-f", "null", "-"]
        probe_result = subprocess.run(probe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        
        if probe_result.returncode != 0:
            print(f"[❌] Could not read video info: {path}")
            return
            
        # Parse basic video info from FFmpeg output
        stderr_output = probe_result.stderr
        print("🔧 Using FFmpeg-based frame processing for better container compatibility")
        
        # Create temporary directory for frame processing
        temp_dir = os.path.join(os.path.dirname(path), f"frames_{uuid.uuid4().hex[:8]}")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Get original video info to preserve framerate
            probe_cmd = [FFMPEG_PATH, "-i", path, "-f", "null", "-"]
            probe_result = subprocess.run(probe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            
            # Extract original framerate from probe output
            original_fps = "30"  # Default fallback
            stderr_output = probe_result.stderr
            if "fps" in stderr_output:
                import re
                fps_match = re.search(r'(\d+\.?\d*)\s*fps', stderr_output)
                if fps_match:
                    original_fps = fps_match.group(1)
                    print(f"🔧 Detected original framerate: {original_fps} fps")
            
            # Extract frames using FFmpeg with original framerate preserved  
            extract_cmd = [
                FFMPEG_PATH, "-i", path,
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",  # Just ensure even dimensions, keep original fps
                "-q:v", "2",  # High quality for frame extraction
                "-threads", "2",  # Limit threads for container compatibility
                f"{temp_dir}/frame_%04d.png"
            ]
            
            print("🔧 Extracting frames (optimized for containers)...")
            try:
                extract_result = subprocess.run(extract_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            except subprocess.TimeoutExpired:
                print("[❌] Frame extraction timed out after 60 seconds")
                return
            
            if extract_result.returncode != 0:
                print(f"[❌] Frame extraction failed: {extract_result.stderr.decode()}")
                return
                
            # Get list of extracted frames
            frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.png')])
            if not frame_files:
                print("[❌] No frames were extracted")
                return
                
            print(f"🔧 Processing {len(frame_files)} extracted frames...")
            
            # Process frames with OpenCV (just the image processing part)
            settings = {
                "very_light": ((-0.5, 0.5), (0.998, 1.002), 0.1),
                "soft":       ((-0.7, 0.7), (0.997, 1.003), 0.1),
                "light":      ((-1.0, 1.0), (0.995, 1.005), 0.2),
                "moderate":   ((-2.0, 2.0), (0.98, 1.02),   0.4)
            }
            
            b_range, c_range, n_std = settings[FRAME_VARIANCE_STRENGTH]
            
            # Smart processing: process every nth frame based on video length
            if len(frame_files) > 300:
                process_interval = 8  # Process every 8th frame for very long videos
                print("⚡ Long video detected - using fast processing mode")
            elif len(frame_files) > 100:
                process_interval = 4  # Process every 4th frame for medium videos
            else:
                process_interval = 2  # Process every 2nd frame for short videos
            
            processed_count = 0
            for i, frame_file in enumerate(frame_files):
                if i % process_interval != 0:
                    continue
                    
                frame_path = os.path.join(temp_dir, frame_file)
                frame = cv2.imread(frame_path)
                
                if frame is None:
                    continue
                
                # Apply optimized processing for speed and container efficiency
                frame = (frame.astype(np.float32) * random.uniform(*c_range)) + random.uniform(*b_range)
                noise = np.random.normal(0, n_std, frame.shape)
                frame += noise
                frame = np.clip(frame, 0, 255).astype(np.uint8)
                
                # Apply transformations consistently to avoid flickering
                if MOTION_PROFILE and i % 20 == 0:  # Less frequent to reduce artifacts
                    frame = apply_motion_forgery(frame, MOTION_PROFILE)
                    
                # Apply style morphing to ALL processed frames for consistency
                frame = apply_style_morph(frame, STYLE_MORPH_PRESET)
                
                # 🚀 ADVANCED SPOOFING: Apply platform-specific transforms
                # This is the key to breaking platform detection
                frame = apply_platform_specific_transform(frame, TRANSCODE_PROFILE, i, len(frame_files))
                    
                if i % 15 == 0:  # Less frequent sensor fingerprinting
                    frame = apply_sensor_fingerprint(frame, model="OMNIVISION")
                
                # Save processed frame
                cv2.imwrite(frame_path, frame)
                processed_count += 1
                
                # Progress update for longer videos
                if processed_count % 20 == 0:
                    print(f"⏳ Processed {processed_count} frames...")
            
            print(f"✅ Processed {processed_count} frames total")
            
            print("🔧 Reassembling video with FFmpeg...")
            
            # Reassemble video using FFmpeg (much more reliable than OpenCV VideoWriter)
            temp_output = path + "_processed.mp4"
            reassemble_cmd = [
                FFMPEG_PATH, "-y",
                "-framerate", original_fps,  # Use original framerate to maintain speed
                "-i", f"{temp_dir}/frame_%04d.png",
                "-i", path,  # Original video for audio
                "-c:v", "libx264",
                "-preset", "fast",  # Better quality than ultrafast, still container-friendly
                "-pix_fmt", "yuv420p",
                "-profile:v", "baseline",  # Most compatible profile
                "-level", "4.0",  # Safe level for most resolutions
                "-b:v", "4000k",  # Higher bitrate for better quality
                "-threads", "2",  # Limit threads
                "-c:a", "copy",  # Copy audio from original
                "-shortest",  # Match shortest stream
                temp_output
            ]
            
            print("🔧 Reassembling video...")
            try:
                reassemble_result = subprocess.run(reassemble_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            except subprocess.TimeoutExpired:
                print("[❌] Video reassembly timed out after 120 seconds")
                return
            
            if reassemble_result.returncode == 0 and os.path.exists(temp_output):
                shutil.move(temp_output, path)
                print(f"✅ Frame processing complete using FFmpeg pipeline")
            else:
                print(f"[❌] Video reassembly failed: {reassemble_result.stderr.decode()}")
                print(f"[❌] FFmpeg stdout: {reassemble_result.stdout.decode()}")
                
        finally:
            # Clean up temporary frames
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


    print("🔧 Spoofing:", filename)
    frame_variance_spoofer(temp_video_only)
    
    # Validate that the processed video is readable
    test_cap = cv2.VideoCapture(temp_video_only)
    if not test_cap.isOpened():
        print(f"[❌] Processed video is not readable: {temp_video_only}")
        test_cap.release()
        return
    test_cap.release()
    print("✅ Processed video validation passed")
    
    # 🚀 ADVANCED SPOOFING: Apply temporal speed variance (imperceptible to humans)
    speed_adjusted_path = os.path.join(output_dir, f"speed_adjusted_{spoof_id}.mp4")
    speed_applied = apply_temporal_speed_variance(temp_video_only, TRANSCODE_PROFILE, speed_adjusted_path, FFMPEG_PATH)
    
    # Use speed-adjusted video for transcoding if successful
    source_video = speed_adjusted_path if speed_applied else temp_video_only
    if speed_applied:
        print("✅ Temporal fingerprint modified")

    transcode_cmd = build_transcode_command(source_video, filepath, transcoded_output, TRANSCODE_PROFILE, FFMPEG_PATH)
    print("🔧 Running transcode command:", " ".join(transcode_cmd))
    
    try:
        result = subprocess.run(transcode_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)  # 3 minute timeout
    except subprocess.TimeoutExpired:
        print("[❌] Transcoding timed out after 180 seconds, trying simple copy...")
        # Fallback: simple copy with audio from original
        simple_cmd = [
            FFMPEG_PATH, "-i", temp_video_only, "-i", filepath,
            "-c:v", "copy", "-c:a", "copy", "-map", "0:v:0", "-map", "1:a:0",
            "-y", transcoded_output
        ]
        try:
            result = subprocess.run(simple_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        except subprocess.TimeoutExpired:
            print("[❌] Simple copy also timed out")
            return
    
    if result.returncode != 0 or not os.path.exists(transcoded_output):
        print(f"[❌] Transcoding failed. FFmpeg STDERR:")
        print(result.stderr.decode())
        print(f"[❌] FFmpeg STDOUT:")
        print(result.stdout.decode())
        return
    
    print("✅ Transcoding completed successfully")
    # === PHASE 2.5 ADDITIONS ===

    # ➕ Subtitle Track Injection (Invisible .srt)
    blank_sub_path = os.path.join(output_dir, f"blank_{spoof_id}.srt")
    with open(blank_sub_path, "w", encoding="utf-8") as srt:
        srt.write("1\n00:00:00,000 --> 00:00:01,000\n \n")  # Minimal valid subtitle block

    subtitled_output = os.path.join(output_dir, f"spoofed_{spoof_id}_subtitled.mp4")
    result = subprocess.run([
        FFMPEG_PATH, "-i", transcoded_output, "-i", blank_sub_path,
        "-c", "copy", "-c:s", "mov_text", "-map", "0", "-map", "1",
        subtitled_output
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    os.remove(blank_sub_path)

    if not os.path.exists(subtitled_output):
        print("[❌] Subtitle injection failed. FFmpeg STDERR:")
        print(result.stderr.decode())
        return  # Exit early
    os.remove(transcoded_output)

    # ➕ Extra Metadata Injection (Title, Comment, Creation Time)
    now = datetime.datetime.utcnow().isoformat() + "Z"
    metadata_output = os.path.join(output_dir, f"spoofed_{spoof_id}_final.mp4")
    subprocess.run([
        FFMPEG_PATH, "-i", subtitled_output,
        "-metadata", "title=TikTok Original",
        "-metadata", "comment=Uploaded via iPhone",
        "-metadata", f"creation_time={now}",
        "-map", "0", "-c", "copy", metadata_output
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    os.remove(subtitled_output)

    # ➕ Unique Stream Mapping Final Shuffle
    shuffled_output = os.path.join(output_dir, f"spoofed_{spoof_id}.mp4")
    map_order = [["0:v:0", "0:a:0", "0:s:0"], ["0:s:0", "0:v:0", "0:a:0"], ["0:a:0", "0:v:0", "0:s:0"]]
    chosen_map = random.choice(map_order)
    ffmpeg_map_cmd = [FFMPEG_PATH, "-i", metadata_output]
    for m in chosen_map:
        ffmpeg_map_cmd += ["-map", m]
    ffmpeg_map_cmd += ["-c", "copy", shuffled_output]
    subprocess.run(ffmpeg_map_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    os.remove(metadata_output)


    os.remove(temp_video_only)
    # Clean up speed-adjusted file if it was created
    if speed_applied and os.path.exists(speed_adjusted_path):
        os.remove(speed_adjusted_path)
    shutil.move(shuffled_output, final_output)


    with open(report_path, "w", encoding="utf-8") as r:
        r.write(f"🎬 Spoof Report — {filename}\n")
        r.write(f"Preset Used: {PRESET_MODE}\n")
        r.write(f"Forgery Profile: {FORGERY_PROFILE}\n")
        r.write(f"Date: {datetime.datetime.now()}\n")
        r.write(f"Watermark Removed: {ENABLE_WATERMARK_REMOVAL}\n")
        r.write(f"Visual Echo: {ENABLE_VISUAL_ECHO}\n")
        r.write(f"Resolution Tweak: {ENABLE_RESOLUTION_TWEAK}\n")
        r.write(f"FPS Jitter: {ENABLE_FPS_JITTER}\n")
        r.write(f"Frame Variance: {FRAME_VARIANCE_STRENGTH}\n")
        r.write(f"Style Morph Preset: {STYLE_MORPH_PRESET}\n")
        r.write(f"Motion Profile: {MOTION_PROFILE}\n")
        r.write(f"Transcode Profile: {TRANSCODE_PROFILE}\n")
        r.write(f"Random Seed: {random.getstate()[1][0]}\n")
        score, label = compute_ai_detectability_score(final_output)
        r.write(f"AI Detectability Score: {score}% ({label})\n")



        pass  # Skipping LUT logic

# === LUT LOADING ===
        global_lut = None

if __name__ == "__main__":
    if "--batch" in sys.argv:
        input_dir = os.path.join(os.path.dirname(__file__), "..", "input")
        input_dir = os.path.abspath(input_dir)
        for file in os.listdir(input_dir):
            if file.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
                run_spoof_pipeline(os.path.join(input_dir, file))
    elif len(sys.argv) > 1:
        run_spoof_pipeline(sys.argv[1])
    else:
        print("[❌] No input provided. Use a file path or --batch.")
