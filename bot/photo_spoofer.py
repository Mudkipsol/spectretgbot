
import os
import random
import shutil
from PIL import Image, ImageEnhance, ImageFilter, ImageSequence
import piexif

def get_output_path(original_path, suffix=""):
    """Generates a consistent output file path in the /output folder with a suffix."""
    base, ext = os.path.splitext(original_path)
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    filename = os.path.basename(base) + suffix + ext
    return os.path.join(output_dir, filename)

def clean_image_metadata(image_path):
    """Removes EXIF metadata from the image to anonymize fingerprinting."""
    try:
        img = Image.open(image_path)
        data = list(img.getdata())
        img_no_exif = Image.new(img.mode, img.size)
        img_no_exif.putdata(data)
        output_path = get_output_path(image_path, suffix='_cleaned')
        img_no_exif.save(output_path)
        return output_path
    except Exception as e:
        raise RuntimeError(f"Metadata cleaning failed: {e}")

def modify_image_weight(image_path, target_kb=500):
    """Reduces image file size by iteratively lowering quality to target weight."""
    try:
        img = Image.open(image_path)
        output_path = get_output_path(image_path, suffix='_weighted')
        quality = 95
        img.save(output_path, quality=quality)
        while os.path.getsize(output_path) / 1024 > target_kb and quality > 10:
            quality -= 5
            img.save(output_path, quality=quality)
        return output_path
    except Exception as e:
        raise RuntimeError(f"Image weight modification failed: {e}")

def apply_light_filter(image_path):
    """Applies minor color, contrast, and sharpness tweaks for obfuscation."""
    try:
        img = Image.open(image_path)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(random.uniform(0.95, 1.05))
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(random.uniform(0.95, 1.05))
        img = img.filter(ImageFilter.SHARPEN)
        output_path = get_output_path(image_path, suffix='_filtered')
        img.save(output_path)
        return output_path
    except Exception as e:
        raise RuntimeError(f"Filter application failed: {e}")

def simulate_platform_artifacts(image_path, platform):
    """Simulates compression artifacts typical of Reddit, Twitter, or Threads uploads."""
    try:
        img = Image.open(image_path)
        img = img.convert("RGB")
        suffix = f'_{platform.lower()}'
        quality_map = {
            "twitter": 70,
            "reddit": 85,
            "threads": 75
        }
        quality = quality_map.get(platform.lower(), 80)
        output_path = get_output_path(image_path, suffix=suffix)
        img.save(output_path, format="JPEG", quality=quality)
        return output_path
    except Exception as e:
        raise RuntimeError(f"Platform simulation failed: {e}")

def spoof_gif(image_path, platform="generic"):
    """Processes animated GIFs by tweaking every frame lightly for obfuscation."""
    try:
        img = Image.open(image_path)
        frames = []
        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("RGB")
            enhancer = ImageEnhance.Color(frame)
            frame = enhancer.enhance(random.uniform(0.95, 1.05))
            enhancer = ImageEnhance.Contrast(frame)
            frame = enhancer.enhance(random.uniform(0.95, 1.05))
            frame = frame.filter(ImageFilter.SHARPEN)
            frames.append(frame)

        output_path = get_output_path(image_path, suffix=f'_{platform.lower()}_gif')
        frames[0].save(
            output_path,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            loop=0,
            optimize=True
        )
        return output_path
    except Exception as e:
        raise RuntimeError(f"GIF spoofing failed: {e}")

def batch_spoof_image(image_path, platform="generic", clean_meta=True, tweak_weight=True, apply_filter=True, simulate_platform=True):
    """Runs a full spoof pipeline on one image based on toggle options."""
    try:
        result_path = image_path
        if clean_meta:
            result_path = clean_image_metadata(result_path)
        if tweak_weight:
            result_path = modify_image_weight(result_path)
        if apply_filter:
            result_path = apply_light_filter(result_path)
        if simulate_platform:
            result_path = simulate_platform_artifacts(result_path, platform)
        return result_path
    except Exception as e:
        return f"[ERROR] Spoofing failed for {os.path.basename(image_path)}: {e}"
