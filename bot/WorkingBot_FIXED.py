#!/usr/bin/env python3
# SpectreSpoofer Assistant Bot - Live mode with Railway server + credit deductions

import smtplib
from email.message import EmailMessage
import requests
import platform
import hashlib
import logging
import os
import shutil
import glob
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from photo_spoofer import batch_spoof_image, clone_spoof_image
from spoof_engine import run_spoof_pipeline
import spoof_engine as se  # used to set runtime globals for the engine

# Try to import V2 engine if available
try:
    import spoof_engine_v2 as se_v2
    USE_V2_ENGINE = True
    print("✅ Using Enhanced Spoof Engine V2 (High Quality + Audio Spoofing)")
except ImportError:
    USE_V2_ENGINE = False
    print("⚠️ Using Legacy Spoof Engine")

# Import new modules
from gif_spoofer import spoof_gif_advanced, batch_spoof_gifs
from video_to_gif import convert_video_to_gif, extract_gif_segment, create_gif_from_video_clips
from frame_extractor import extract_frames_by_count, extract_frames_by_time, extract_key_frames
from bulk_processor import bulk_spoof_photos, bulk_spoof_videos, bulk_spoof_gifs, bulk_convert_to_gifs, bulk_extract_frames, create_bulk_output_zip

# Custom bulk function for key frames
async def bulk_extract_frames_custom(video_paths, method, frame_count, max_workers=2):
    """Custom bulk frame extraction for key frames method."""
    results = []
    for i, video_path in enumerate(video_paths):
        try:
            print(f"🎬 Processing video {i+1}/{len(video_paths)}: {os.path.basename(video_path)}")
            if method == "key_frames":
                frames = await asyncio.to_thread(extract_key_frames, video_path, 0.3, frame_count)
            else:
                frames = await asyncio.to_thread(extract_frames_by_count, video_path, frame_count, method)
            
            results.append({
                "video": video_path,
                "frames": frames,
                "count": len(frames),
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
    
    return {"results": results}

# ========= LIVE SERVER / AUTH =========
BASE_URL = "https://web-production-00cb2.up.railway.app"

# Use your Railway SERVER_SECRET for protected routes like /view_keys, /reset_hwid
SERVER_SECRET = "G7xZ!4u8s2h#9Kq@WpLm%RaV"
AUTH = {"Authorization": SERVER_SECRET}

# Telegram bot token (keep what you have or move to env)
BOT_TOKEN = "7588145178:AAGKlponItxiaqIxpBNAJuA6ujQKSv066Nc"

# IO paths
DOWNLOAD_DIR = "./downloads"
OUTPUT_DIR = "output"

verified_users = {}  # Stores {telegram_user_id: license_key} after successful verification

# --- Credits helper ---
def _deduct_credits_sync(user_id: int, amount: int = 1):
    """
    Synchronous helper: posts to /consume_credits for the verified user's license key.
    Returns (ok, remaining_or_reason).
    """
    key = verified_users.get(user_id)
    if not key:
        return False, "User not verified / no license key"
    try:
        r = requests.post(
            f"{BASE_URL}/consume_credits",
            json={"key": key, "amount": int(max(1, amount))},
            timeout=15
        )
        data = r.json()
        if r.status_code == 200:
            return True, data.get("remaining_credits")
        else:
            return False, data.get("error", f"HTTP {r.status_code}")
    except Exception as e:
        return False, str(e)

async def deduct_credits_for_user(user_id: int, amount: int = 1):
    """Async wrapper so we don't block the event loop."""
    return await asyncio.to_thread(_deduct_credits_sync, user_id, amount)

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def generate_hwid():
    sys_info = f"{platform.node()}-{platform.system()}-{platform.machine()}"
    return hashlib.sha256(sys_info.encode()).hexdigest()[:16]

def send_support_email(user, message):
    try:
        email = EmailMessage()
        email["Subject"] = f"[Spectre Support] Message from {user}"
        email["From"] = "team@spectrespoofer.com"
        email["To"] = "team@spectrespoofer.com"
        email.set_content(f"User: {user}\n\nMessage:\n{message}")

        with smtplib.SMTP_SSL("smtppro.zoho.com", 465) as smtp:
            # If you moved the SMTP app password to env, load it here instead
            smtp.login("team@spectrespoofer.com", "sEzGG3W0X8aC")
            smtp.send_message(email)
        return True
    except Exception as e:
        logging.error(f"❌ Failed to send support email: {e}")
        return False

def main_menu():
    keyboard = [
        [InlineKeyboardButton("🎥 Video Spoof", callback_data='send_video')],
        [InlineKeyboardButton("🖼️ Photo Spoof", callback_data='photo_spoofer')],
        [InlineKeyboardButton("🎭 GIF Spoof", callback_data='gif_spoof')],
        [InlineKeyboardButton("🎬➡️🎭 Video to GIF", callback_data='video_to_gif')],
        [InlineKeyboardButton("📸 Frame Extractor", callback_data='frame_extractor')],
        [InlineKeyboardButton("📦 Bulk Processing", callback_data='bulk_processing')],
        [InlineKeyboardButton("⚙️ Settings", callback_data='spoof_settings')],
        [InlineKeyboardButton("🔧 My License", callback_data='my_license')],
        [InlineKeyboardButton("💬 Help & Support", callback_data='help')]
    ]
    return InlineKeyboardMarkup(keyboard)

def preset_menu():
    keyboard = [
        [InlineKeyboardButton("🔵 OnlyFans Mode", callback_data='preset_onlyfans')],
        [InlineKeyboardButton("🎵 TikTok Mode", callback_data='preset_tiktok')],
        [InlineKeyboardButton("📸 Instagram Mode", callback_data='preset_instagram')],
        [InlineKeyboardButton("🎥 YouTube Shorts Mode", callback_data='preset_youtube')]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data='back_to_menu')]
    ])

def photo_preset_menu():
    keyboard = [
        [InlineKeyboardButton("🧵 IG Threads Mode", callback_data='photo_ig_threads')],
        [InlineKeyboardButton("🐦 Twitter Mode", callback_data='photo_twitter')],
        [InlineKeyboardButton("👽 Reddit Mode", callback_data='photo_reddit')],
        [InlineKeyboardButton("🎭 Clone Spoof (Multiple Versions)", callback_data='photo_clone_menu')],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def photo_clone_menu():
    keyboard = [
        [InlineKeyboardButton("🧵 IG Threads (3 Clones)", callback_data='photo_clone_ig_threads')],
        [InlineKeyboardButton("🐦 Twitter (3 Clones)", callback_data='photo_clone_twitter')],
        [InlineKeyboardButton("👽 Reddit (3 Clones)", callback_data='photo_clone_reddit')],
        [InlineKeyboardButton("🔙 Back", callback_data='photo_spoofer')]
    ]
    return InlineKeyboardMarkup(keyboard)

def gif_platform_menu():
    keyboard = [
        [InlineKeyboardButton("📖 Reddit", callback_data='gif_reddit')],
        [InlineKeyboardButton("🐦 Twitter", callback_data='gif_twitter')],
        [InlineKeyboardButton("🧵 Threads", callback_data='gif_threads')],
        [InlineKeyboardButton("💬 Discord", callback_data='gif_discord')],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def video_to_gif_menu():
    keyboard = [
        [InlineKeyboardButton("🎬 Full Video to GIF", callback_data='vid2gif_full')],
        [InlineKeyboardButton("✂️ Custom Segment", callback_data='vid2gif_segment')],
        [InlineKeyboardButton("🎯 Key Moments", callback_data='vid2gif_moments')],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def frame_extraction_menu():
    keyboard = [
        [InlineKeyboardButton("⚡ Quick Extract (10 frames)", callback_data='frames_quick')],
        [InlineKeyboardButton("🎯 Custom Count", callback_data='frames_custom')],
        [InlineKeyboardButton("🔑 Key Frames", callback_data='frames_key')],
        [InlineKeyboardButton("📐 Time Intervals", callback_data='frames_interval')],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def bulk_processing_menu():
    keyboard = [
        [InlineKeyboardButton("📦🖼️ Bulk Photo Spoof", callback_data='bulk_photos')],
        [InlineKeyboardButton("📦🎥 Bulk Video Spoof", callback_data='bulk_videos')],
        [InlineKeyboardButton("📦🎭 Bulk Video to GIF", callback_data='bulk_vid2gif')],
        [InlineKeyboardButton("📦📸 Bulk Frame Extract", callback_data='bulk_frames')],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def bulk_photo_platform_menu():
    keyboard = [
        [InlineKeyboardButton("🧵 IG Threads Mode", callback_data='bulk_photo_ig_threads')],
        [InlineKeyboardButton("🐦 Twitter Mode", callback_data='bulk_photo_twitter')],
        [InlineKeyboardButton("👽 Reddit Mode", callback_data='bulk_photo_reddit')],
        [InlineKeyboardButton("🔙 Back to Bulk Menu", callback_data="bulk_processing")]
    ]
    return InlineKeyboardMarkup(keyboard)

def bulk_video_preset_menu():
    keyboard = [
        [InlineKeyboardButton("🔵 OnlyFans Mode", callback_data='bulk_video_onlyfans')],
        [InlineKeyboardButton("🎵 TikTok Mode", callback_data='bulk_video_tiktok')],
        [InlineKeyboardButton("📸 Instagram Mode", callback_data='bulk_video_instagram')],
        [InlineKeyboardButton("🎥 YouTube Shorts Mode", callback_data='bulk_video_youtube')],
        [InlineKeyboardButton("🔙 Back to Bulk Menu", callback_data="bulk_processing")]
    ]
    return InlineKeyboardMarkup(keyboard)

def bulk_gif_platform_menu():
    keyboard = [
        [InlineKeyboardButton("📖 Reddit", callback_data='bulk_gif_reddit')],
        [InlineKeyboardButton("🐦 Twitter", callback_data='bulk_gif_twitter')],
        [InlineKeyboardButton("🧵 Threads", callback_data='bulk_gif_threads')],
        [InlineKeyboardButton("💬 Discord", callback_data='bulk_gif_discord')],
        [InlineKeyboardButton("🔙 Back to Bulk Menu", callback_data="bulk_processing")]
    ]
    return InlineKeyboardMarkup(keyboard)

def bulk_frame_method_menu():
    keyboard = [
        [InlineKeyboardButton("⚡ Quick (10 frames)", callback_data='bulk_frames_quick')],
        [InlineKeyboardButton("🎯 Custom Count (15)", callback_data='bulk_frames_custom')],
        [InlineKeyboardButton("🔑 Key Frames", callback_data='bulk_frames_key')],
        [InlineKeyboardButton("📐 Time Intervals", callback_data='bulk_frames_interval')],
        [InlineKeyboardButton("🔙 Back to Bulk Menu", callback_data="bulk_processing")]
    ]
    return InlineKeyboardMarkup(keyboard)

def spoof_settings_menu():
    keyboard = [
        [InlineKeyboardButton("🖼️ Set Photo Batch Preset", callback_data='set_photo_batch_preset')],
        [InlineKeyboardButton("🎥 Set Video Batch Preset", callback_data='set_video_batch_preset')],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data='back_to_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------------- Commands ----------------

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /verify <LICENSE> """
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /verify YOUR_LICENSE_KEY")
        return

    license_key = context.args[0]
    hwid = generate_hwid()
    telegram_user = update.effective_user.username or str(update.effective_user.id)

    try:
        r = requests.post(
            f"{BASE_URL}/verify",
            json={
                "key": license_key,
                "hwid": hwid,
                "telegram_id": telegram_user  # server expects 'telegram_id'
            },
            timeout=15
        )
        data = r.json()
        if r.status_code == 200 and data.get("valid") is True:
            verified_users[update.effective_user.id] = license_key  # remember user
            await update.message.reply_text(
                f"✅ License Verified!\n"
                f"Tier: {data.get('tier','?')}\n"
                f"Credits: {data.get('credits','?')}"
            )
        else:
            await update.message.reply_text(f"❌ Verification Failed: {data.get('reason', 'Unknown error')}")
    except Exception as e:
        logging.error(f"Error verifying: {e}")
        await update.message.reply_text("❌ Server error during verification.")

async def spoof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /spoof <LICENSE> — exercise the server counter (optional) """
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /spoof YOUR_LICENSE_KEY")
        return

    license_key = context.args[0]
    hwid = generate_hwid()
    try:
        r = requests.post(f"{BASE_URL}/spoof", json={"key": license_key, "hwid": hwid}, timeout=15)
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            await update.message.reply_text(
                f"🎭 Spoof Successful!\n"
                f"Tier: {data['tier']}\n"
                f"Remaining Spoofs: {data['remaining_spoofs']}"
            )
        else:
            await update.message.reply_text(f"❌ Spoof Failed: {data.get('error', 'Unknown error')}")
    except Exception as e:
        logging.error(f"Spoof error: {e}")
        await update.message.reply_text("❌ Server error during spoof attempt.")

async def reset_hwid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /reset_hwid <LICENSE> <ADMIN_PASSWORD> """
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /reset_hwid YOUR_LICENSE_KEY ADMIN_PASSWORD")
        return

    license_key, admin_password = context.args
    try:
        r = requests.post(
            f"{BASE_URL}/reset_hwid",
            json={"key": license_key, "admin_password": admin_password},
            headers=AUTH,
            timeout=15
        )
        data = r.json()
        if r.status_code == 200:
            await update.message.reply_text("✅ HWID reset successfully.")
        else:
            await update.message.reply_text(f"❌ Reset Failed: {data.get('error', 'Unknown error')}")
    except Exception as e:
        logging.error(f"Reset HWID error: {e}")
        await update.message.reply_text("❌ Server error during HWID reset.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /status <LICENSE> """
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /status YOUR_LICENSE_KEY")
        return

    license_key = context.args[0]
    try:
        r = requests.post(f"{BASE_URL}/key_stats", json={"key": license_key}, timeout=15)
        data = r.json()
        if r.status_code == 200:
            await update.message.reply_text(
                f"🔐 License Info:\n"
                f"Key: {data['key']}\n"
                f"Tier: {data['tier']}\n"
                f"Credits: {data['credits']}\n"
                f"Issued to: {data['issued_to']}\n"
                f"Expires: {data['expires_at']}\n"
                f"Days Active: {data['days_since_created']}"
            )
        else:
            await update.message.reply_text(f"❌ Status Error: {data.get('error', 'Unknown error')}")
    except Exception as e:
        logging.error(f"Status error: {e}")
        await update.message.reply_text("❌ Server error checking license status.")

# ---------------- UI flows ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in verified_users:
        try:
            with open("logo.png", "rb") as logo:
                await update.message.reply_photo(logo)
        except Exception:
            pass
        await update.message.reply_text(
            "👻 Spectre Spoofer — Elite Content Manipulator\n"
            "Send your videos or images below and receive perfectly spoofed media — 100% covert, 100% yours.",
            reply_markup=main_menu()
        )
        return

    await update.message.reply_text(
        "🔐 Please enter your license key to activate access.\n\n"
        "Send it as a message (not a command)."
    )
    context.user_data['awaiting_license'] = True

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Debug logging for all callbacks
    print(f"[DEBUG] Callback received: {query.data}")

    if query.data == 'manage_plan':
        username = update.effective_user.username
        if not username:
            await query.edit_message_text("❌ Cannot retrieve your Telegram username.")
            return

        try:
            # If you want email == username@yourdomain, align with your server’s /billing_portal expectation
            r = requests.get(f"{BASE_URL}/billing_portal?email={username}@example.com", timeout=15)
            data = r.json()
            if r.status_code == 200 and 'portal_url' in data:
                await query.edit_message_text(
                    f"🔁 Manage your subscription here:\n\n{data['portal_url']}\n\nAfter making changes, tap '↻ Refresh Info' to sync.",
                    reply_markup=back_button()
                )
            else:
                await query.edit_message_text("⚠️ Could not load billing portal.")
        except Exception as e:
            logging.error(f"Billing portal error: {e}")
            await query.edit_message_text("❌ Error accessing billing portal.")

    if query.data == 'send_video':
        context.user_data['expected_file_type'] = 'video'
        await query.edit_message_text("🎨 Choose your Spoofing Mode:", reply_markup=preset_menu())

    elif query.data == 'photo_spoofer':
        await query.edit_message_text("🎨 Choose your Photo Spoofing Mode:", reply_markup=photo_preset_menu())

    elif query.data == 'photo_clone_menu':
        await query.edit_message_text("🎭 Clone Spoof: Create Multiple Unique Versions\n\nSelect platform:", reply_markup=photo_clone_menu())
    
    elif query.data.startswith('photo_clone_'):
        platform_mapping = {
            'photo_clone_ig_threads': "IG_THREADS",
            'photo_clone_twitter': "TWITTER",
            'photo_clone_reddit': "REDDIT"
        }
        selected_platform = platform_mapping.get(query.data)
        context.user_data['expected_file_type'] = 'photo_clone'
        context.user_data['selected_photo_platform'] = selected_platform
        context.user_data['clone_count'] = 3  # Default 3 clones
        await query.edit_message_text(
            f"✅ Clone Spoof Mode: {selected_platform}\n"
            f"📥 Will create 3 unique versions\n\n"
            f"Send your photo now.",
            reply_markup=back_button()
        )

    elif query.data == 'gif_spoof':
        await query.edit_message_text("🎭 Choose your GIF Platform:", reply_markup=gif_platform_menu())

    elif query.data == 'video_to_gif':
        await query.edit_message_text("🎬➡️🎭 Choose GIF Conversion Mode:", reply_markup=video_to_gif_menu())

    elif query.data == 'frame_extractor':
        await query.edit_message_text("📸 Choose Frame Extraction Method:", reply_markup=frame_extraction_menu())

    elif query.data == 'bulk_processing':
        await query.edit_message_text("📦 Choose Bulk Operation:", reply_markup=bulk_processing_menu())

    elif query.data.startswith('photo_'):
        preset_mapping = {
            'photo_ig_threads': "IG_THREADS",
            'photo_twitter': "TWITTER",
            'photo_reddit': "REDDIT"
        }
        selected_platform = preset_mapping.get(query.data)
        context.user_data['expected_file_type'] = 'photo'
        context.user_data['selected_photo_platform'] = selected_platform
        await query.edit_message_text(
            f"✅ Mode set: {query.data.split('_')[1].capitalize()} Mode!\n"
            f"📥 Please send your photo.",
            reply_markup=back_button()
        )

    elif query.data.startswith('gif_'):
        platform_mapping = {
            'gif_reddit': "reddit",
            'gif_twitter': "twitter", 
            'gif_threads': "threads",
            'gif_discord': "discord"
        }
        selected_platform = platform_mapping.get(query.data)
        context.user_data['expected_file_type'] = 'gif'
        context.user_data['selected_gif_platform'] = selected_platform
        await query.edit_message_text(
            f"✅ Platform set: {selected_platform.capitalize()}!\n"
            f"🎭 Please send your GIF to spoof.\n\n"
            f"📝 Note: Telegram may convert your GIF to MP4 - that's fine, we'll handle it!",
            reply_markup=back_button()
        )

    elif query.data.startswith('vid2gif_'):
        context.user_data['expected_file_type'] = 'video_for_gif'
        context.user_data['gif_conversion_mode'] = query.data
        if query.data == 'vid2gif_full':
            await query.edit_message_text(
                "🎬➡️🎭 Full Video to GIF Mode!\n"
                "📥 Send your video to convert to GIF.",
                reply_markup=back_button()
            )
        elif query.data == 'vid2gif_segment':
            await query.edit_message_text(
                "✂️ Custom Segment Mode!\n"
                "📥 Send your video, then specify start/end times.",
                reply_markup=back_button()
            )
        elif query.data == 'vid2gif_moments':
            await query.edit_message_text(
                "🎯 Key Moments Mode!\n" 
                "📥 Send your video to extract key moments as GIF.",
                reply_markup=back_button()
            )

    elif query.data.startswith('frames_'):
        context.user_data['expected_file_type'] = 'video_for_frames'
        context.user_data['frame_extraction_mode'] = query.data
        if query.data == 'frames_quick':
            await query.edit_message_text(
                "⚡ Quick Extract Mode!\n"
                "📥 Send your video to extract 10 frames.",
                reply_markup=back_button()
            )
        elif query.data == 'frames_custom':
            await query.edit_message_text(
                "🎯 Custom Count Mode!\n"
                "📥 Send your video, then specify frame count.",
                reply_markup=back_button()
            )
        elif query.data == 'frames_key':
            await query.edit_message_text(
                "🔑 Key Frames Mode!\n"
                "📥 Send your video to extract important frames.",
                reply_markup=back_button()
            )
        elif query.data == 'frames_interval':
            await query.edit_message_text(
                "📐 Time Intervals Mode!\n"
                "📥 Send your video, then specify interval.",
                reply_markup=back_button()
            )

    # Handle bulk configuration selections (specific handlers first)
    elif query.data.startswith('bulk_photo_'):
        platform_mapping = {
            'bulk_photo_ig_threads': "IG_THREADS",
            'bulk_photo_twitter': "TWITTER",
            'bulk_photo_reddit': "REDDIT"
        }
        selected_platform = platform_mapping.get(query.data)
        context.user_data['expected_file_type'] = 'bulk_photos'
        context.user_data['bulk_files'] = []
        context.user_data['bulk_photo_platform'] = selected_platform
        await query.edit_message_text(
            f"✅ Bulk Photo Mode: {selected_platform}\n\n"
            f"📦🖼️ Now send multiple photos for bulk spoofing.\n"
            f"💬 Type 'START' when ready to process all photos.",
            reply_markup=back_button()
        )

    elif query.data.startswith('bulk_video_'):
        preset_mapping = {
            'bulk_video_onlyfans': "OF_WASH",
            'bulk_video_tiktok': "TIKTOK_CLEAN",
            'bulk_video_instagram': "IG_RAW_LOOK",
            'bulk_video_youtube': "CINEMATIC_FADE"
        }
        selected_preset = preset_mapping.get(query.data)
        
        # Debug logging
        print(f"[DEBUG] Bulk video callback: {query.data}")
        print(f"[DEBUG] Selected preset: {selected_preset}")
        
        context.user_data['expected_file_type'] = 'bulk_videos'
        context.user_data['bulk_files'] = []
        context.user_data['bulk_video_preset'] = selected_preset
        
        try:
            await query.edit_message_text(
                f"✅ Bulk Video Mode: {selected_preset}\n\n"
                f"📦🎥 Now send multiple videos for bulk spoofing.\n"
                f"💬 Type 'START' when ready to process all videos.",
                reply_markup=back_button()
            )
        except Exception as e:
            print(f"[ERROR] Failed to edit message: {e}")
            await query.answer("Configuration saved! Please go back to main menu.", show_alert=True)

    elif query.data.startswith('bulk_gif_'):
        platform_mapping = {
            'bulk_gif_reddit': "reddit",
            'bulk_gif_twitter': "twitter",
            'bulk_gif_threads': "threads", 
            'bulk_gif_discord': "discord"
        }
        selected_platform = platform_mapping.get(query.data)
        context.user_data['expected_file_type'] = 'bulk_vid2gif'
        context.user_data['bulk_files'] = []
        context.user_data['bulk_gif_platform'] = selected_platform
        await query.edit_message_text(
            f"✅ Bulk GIF Platform: {selected_platform.capitalize()}\n\n"
            f"📦🎭 Now send multiple videos to convert to GIFs.\n"
            f"💬 Type 'START' when ready to convert all videos.",
            reply_markup=back_button()
        )

    elif query.data.startswith('bulk_frames_'):
        method_mapping = {
            'bulk_frames_quick': "evenly_spaced_10",
            'bulk_frames_custom': "evenly_spaced_15",
            'bulk_frames_key': "key_frames",
            'bulk_frames_interval': "time_intervals"
        }
        selected_method = method_mapping.get(query.data)
        context.user_data['expected_file_type'] = 'bulk_frames'
        context.user_data['bulk_files'] = []
        context.user_data['bulk_frame_method'] = selected_method
        method_display = query.data.replace('bulk_frames_', '').replace('_', ' ').title()
        await query.edit_message_text(
            f"✅ Bulk Frame Method: {method_display}\n\n"
            f"📦📸 Now send multiple videos for frame extraction.\n"
            f"💬 Type 'START' when ready to extract frames.",
            reply_markup=back_button()
        )

    # Handle general bulk operation selections (after specific handlers)
    elif query.data.startswith('bulk_'):
        if query.data == 'bulk_photos':
            await query.edit_message_text("📦🖼️ Choose Bulk Photo Platform:", reply_markup=bulk_photo_platform_menu())
        elif query.data == 'bulk_videos':
            await query.edit_message_text("📦🎥 Choose Bulk Video Mode:", reply_markup=bulk_video_preset_menu())
        elif query.data == 'bulk_vid2gif':
            await query.edit_message_text("📦🎭 Choose Bulk GIF Platform:", reply_markup=bulk_gif_platform_menu())
        elif query.data == 'bulk_frames':
            await query.edit_message_text("📦📸 Choose Bulk Frame Method:", reply_markup=bulk_frame_method_menu())

    elif query.data.startswith('preset_'):
        preset_mapping = {
            'preset_onlyfans': "OF_WASH",
            'preset_tiktok': "TIKTOK_CLEAN",
            'preset_instagram': "IG_RAW_LOOK",
            'preset_youtube': "CINEMATIC_FADE"
        }
        selected_preset = preset_mapping.get(query.data)
        context.user_data['expected_file_type'] = 'video'
        context.user_data['selected_preset'] = selected_preset
        await query.edit_message_text(
            f"✅ Mode set: {query.data.split('_')[1].capitalize()} Mode!\n"
            f"📥 Please send your video.",
            reply_markup=back_button()
        )

    elif query.data == 'batch_spoof':
        context.user_data['expected_file_type'] = 'batch'
        context.user_data['batch_paths'] = []
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Start Batch", callback_data="start_batch")],
            [InlineKeyboardButton("🧹 Clear Queue", callback_data="clear_batch")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
        ])
        await query.edit_message_text(
            "📦 Send multiple photos or videos now. They’ll be *queued*.\n"
            "When you’re ready, press **Start Batch**.",
            parse_mode="Markdown",
            reply_markup=kb
        )

    elif query.data == 'start_batch':
        paths = context.user_data.get('batch_paths', [])
        if not paths:
            await query.edit_message_text("🟡 Your batch queue is empty. Send files first.", reply_markup=back_button())
            return
        await query.edit_message_text(f"🚀 Starting batch for {len(paths)} file(s)…")
        outputs = await asyncio.to_thread(run_batch_spoof_pipeline, paths, context)

        sent = 0
        for outp in outputs:
            try:
                ext = os.path.splitext(outp)[-1].lower()
                if ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"]:
                    with open(outp, "rb") as f:
                        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=f)
                else:
                    with open(outp, "rb") as f:
                        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
                sent += 1
            except Exception as e:
                logging.error(f"Failed to send batch item {outp}: {e}")

        context.user_data['batch_paths'] = []
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Batch complete. Sent {sent}/{len(outputs)} file(s).",
            reply_markup=back_button()
        )

        # 🔻 Deduct credits equal to number of successful outputs
        if sent > 0:
            ok, info = await deduct_credits_for_user(update.effective_user.id, sent)
            if ok:
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"💳 Credits consumed: {sent}. Remaining: {info}"
                    )
                except Exception:
                    pass
            else:
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"[⚠️] Could not deduct {sent} credit(s): {info}"
                    )
                except Exception:
                    pass

    elif query.data == 'clear_batch':
        context.user_data['batch_paths'] = []
        await query.edit_message_text("🧹 Cleared the batch queue.", reply_markup=back_button())

    elif query.data == 'spoof_settings':
        await query.edit_message_text("⚙️ Spoof Settings:", reply_markup=spoof_settings_menu())

    elif query.data == 'my_license':
        username = update.effective_user.username or update.effective_user.first_name
        try:
            r = requests.get(f"{BASE_URL}/view_keys", headers=AUTH, timeout=15)
            data = r.json()

            if r.status_code != 200 or "keys" not in data:
                await query.edit_message_text("❌ Could not retrieve your license info.")
                return

            licenses = [k for k in data["keys"] if k["issued_to"] == username]
            if not licenses:
                await query.edit_message_text("❌ No license found for your Telegram username.")
                return

            lic = licenses[0]  # First matching license
            keyboard = [
                [InlineKeyboardButton("🔼 Upgrade / Manage Plan", callback_data="manage_plan")],
                [InlineKeyboardButton("↻ Refresh Info", callback_data="refresh_license")],
                [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
            ]

            await query.edit_message_text(
                f"🔐 License Info for @{username}:\n"
                f"Key: {lic['key'][:6]}...{lic['key'][-4:]}\n"
                f"Tier: {lic['tier']}\n"
                f"Credits: {lic['credits']}\n"
                f"HWID: {lic.get('hwid', 'Not bound')}\n"
                f"Expires: {lic['expires_at']}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logging.error(f"License lookup error: {e}")
            await query.edit_message_text("⚠️ Error loading license data.")

    elif query.data == "refresh_license":
        username = update.effective_user.username or update.effective_user.first_name
        try:
            r = requests.get(f"{BASE_URL}/view_keys", headers=AUTH, timeout=15)
            data = r.json()

            if r.status_code != 200 or "keys" not in data:
                await query.edit_message_text("❌ Could not refresh license info.")
                return

            licenses = [k for k in data["keys"] if k["issued_to"] == username]
            if not licenses:
                await query.edit_message_text("❌ No license found under your Telegram username.")
                return

            lic = licenses[0]
            keyboard = [
                [InlineKeyboardButton("🔼 Upgrade / Manage Plan", callback_data="manage_plan")],
                [InlineKeyboardButton("↻ Refresh Info", callback_data="refresh_license")],
                [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]
            ]
            await query.edit_message_text(
                f"🔄 Refreshed License Info for @{username}:\n"
                f"Key: {lic['key'][:6]}...{lic['key'][-4:]}\n"
                f"Tier: {lic['tier']}\n"
                f"Credits: {lic['credits']}\n"
                f"HWID: {lic.get('hwid', 'Not bound')}\n"
                f"Expires: {lic['expires_at']}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logging.error(f"Refresh license error: {e}")
            await query.edit_message_text("⚠️ Error refreshing license data.")

    elif query.data == 'set_photo_batch_preset':
        keyboard = [
            [InlineKeyboardButton("IG Threads", callback_data='photo_preset_ig')],
            [InlineKeyboardButton("Twitter", callback_data='photo_preset_twitter')],
            [InlineKeyboardButton("Reddit", callback_data='photo_preset_reddit')],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data='spoof_settings')]
        ]
        await query.edit_message_text("🖼️ Choose Photo Batch Preset:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'set_video_batch_preset':
        keyboard = [
            [InlineKeyboardButton("OnlyFans", callback_data='video_preset_of')],
            [InlineKeyboardButton("TikTok", callback_data='video_preset_tiktok')],
            [InlineKeyboardButton("Instagram", callback_data='video_preset_instagram')],
            [InlineKeyboardButton("YouTube", callback_data='video_preset_youtube')],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data='spoof_settings')]
        ]
        await query.edit_message_text("🎥 Choose Video Batch Preset:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith('photo_preset_'):
        preset_map = {
            'photo_preset_ig': "IG_THREADS",
            'photo_preset_twitter': "TWITTER",
            'photo_preset_reddit': "REDDIT"
        }
        context.user_data['photo_batch_preset'] = preset_map[query.data]
        await query.edit_message_text("✅ Photo Batch Preset set!", reply_markup=spoof_settings_menu())

    elif query.data.startswith('video_preset_'):
        preset_map = {
            'video_preset_of': "OF_WASH",
            'video_preset_tiktok': "TIKTOK_CLEAN",
            'video_preset_instagram': "IG_RAW_LOOK",
            'video_preset_youtube': "CINEMATIC_FADE"
        }
        context.user_data['video_batch_preset'] = preset_map[query.data]
        await query.edit_message_text("✅ Video Batch Preset set!", reply_markup=spoof_settings_menu())

    elif query.data == 'help':
        context.user_data['awaiting_support'] = True
        await query.edit_message_text(
            "📩 Send your message below and our team will reply via email.",
            reply_markup=back_button()
        )

    elif query.data == 'back_to_menu':
        context.user_data.pop('awaiting_support', None)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🔙 Back to Main Menu",
            reply_markup=main_menu()
        )

    else:
        print(f"[DEBUG] Unhandled callback: {query.data}")
        await query.edit_message_text(f"❌ Unknown action: {query.data}", reply_markup=back_button())

# ---------------- Files & Text ----------------

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_type = context.user_data.get('expected_file_type', None)
    user_id = update.effective_user.id
    if user_id not in verified_users:
        await update.message.reply_text("🔐 Please verify your license first with /verify <KEY>.")
        return
    if not file_type:
        await update.message.reply_text("❌ Please choose to send a video or image first.", reply_markup=main_menu())
        return

    file = update.message.document or update.message.video or update.message.photo[-1]
    file_id = file.file_id
    file_name = getattr(file, 'file_name', None) or f"{file_id}.jpg"
    
    # Handle Telegram's automatic GIF to MP4 conversion
    if file_type == 'gif' and update.message.video and not file_name:
        file_name = f"telegram_gif_{file_id}.gif.mp4"
    elif file_type == 'gif' and hasattr(file, 'mime_type') and file.mime_type == 'video/mp4':
        # This is likely a converted GIF
        base_name = getattr(file, 'file_name', f"gif_{file_id}")
        if not base_name.endswith('.gif.mp4'):
            file_name = f"{base_name}.gif.mp4"
    
    input_path = os.path.join(DOWNLOAD_DIR, file_name)

    new_file = await context.bot.get_file(file_id)
    await new_file.download_to_drive(input_path)

    # -------- Batch queue mode --------
    if file_type == 'batch':
        queue = context.user_data.setdefault('batch_paths', [])
        queue.append(input_path)
        await update.message.reply_text(
            f"✅ Queued: {os.path.basename(input_path)}\n"
            f"🧺 Queue size: {len(queue)}\n"
            f"▶️ Press *Start Batch* when ready.",
            parse_mode="Markdown"
        )
        return

    # -------- Single video --------
    if file_type == 'video':
        preset = context.user_data.get('selected_preset', "TIKTOK_CLEAN")
        await update.message.reply_text(f"🔧 Spoofing: {file_name}\n🎨 Mode: {preset}\n⚡ Engine: {'V2 Enhanced' if USE_V2_ENGINE else 'Legacy'}")

        if USE_V2_ENGINE:
            # Use V2 engine with enhanced quality and audio spoofing
            if preset == "IG_RAW_LOOK":
                se_v2.PRESET_MODE = "IG_REELS_SAFE"
                se_v2.FORGERY_PROFILE = "IG_ANDROID"
                se_v2.TRANSCODE_PROFILE = "IG_REELS"
                se_v2.STYLE_MORPH_PRESET = "IG_RAW_LOOK"
                se_v2.ENABLE_AUDIO_SPOOFING = True
            elif preset == "TIKTOK_CLEAN":
                se_v2.PRESET_MODE = "TIKTOK_SAFE"
                se_v2.FORGERY_PROFILE = "TIKTOK_IPHONE"
                se_v2.TRANSCODE_PROFILE = "TIKTOK_IOS"
                se_v2.STYLE_MORPH_PRESET = "TIKTOK_CLEAN"
                se_v2.ENABLE_AUDIO_SPOOFING = True  # CRITICAL for TikTok
            elif preset == "CINEMATIC_FADE":
                se_v2.PRESET_MODE = "YT_SHORTS_SAFE"
                se_v2.FORGERY_PROFILE = "CANON_PRO"
                se_v2.TRANSCODE_PROFILE = "YT_WEB"
                se_v2.STYLE_MORPH_PRESET = "CINEMATIC_FADE"
                se_v2.ENABLE_AUDIO_SPOOFING = True
            elif preset == "OF_WASH":
                se_v2.PRESET_MODE = "OF_WASH"
                se_v2.FORGERY_PROFILE = "OF_CREATOR"
                se_v2.TRANSCODE_PROFILE = "MOBILE_NATIVE"
                se_v2.STYLE_MORPH_PRESET = "IG_RAW_LOOK"
                se_v2.ENABLE_AUDIO_SPOOFING = True
            else:
                se_v2.PRESET_MODE = "TIKTOK_SAFE"
                se_v2.FORGERY_PROFILE = "TIKTOK_IPHONE"
                se_v2.TRANSCODE_PROFILE = "TIKTOK_IOS"
                se_v2.STYLE_MORPH_PRESET = "TIKTOK_CLEAN"
                se_v2.ENABLE_AUDIO_SPOOFING = True
            
            try:
                # Run V2 engine
                await asyncio.to_thread(se_v2.run_spoof_pipeline, input_path)
            except Exception as e:
                logging.error(f"V2 Engine error: {e}, falling back to legacy engine")
                await asyncio.to_thread(run_spoof_pipeline, input_path)
        else:
            # Use legacy engine
            se.ENABLE_WATERMARK_REMOVAL = False
            se.ENABLE_VISUAL_ECHO = False
            se.ENABLE_RESOLUTION_TWEAK = False
            se.ENABLE_FPS_JITTER = False
            se.FRAME_VARIANCE_STRENGTH = "soft"
            se.MOTION_PROFILE = "STABILIZED_GIMBAL"

            # Map preset -> engine globals
            if preset == "IG_RAW_LOOK":
                se.PRESET_MODE = "IG_REELS_SAFE"
                se.FORGERY_PROFILE = "IG_ANDROID"
                se.TRANSCODE_PROFILE = "IG_REELS"
                se.STYLE_MORPH_PRESET = "IG_RAW_LOOK"
                se.ENABLE_RESOLUTION_TWEAK = True
            elif preset == "TIKTOK_CLEAN":
                se.PRESET_MODE = "TIKTOK_SAFE"
                se.FORGERY_PROFILE = "TIKTOK_IPHONE"
                se.TRANSCODE_PROFILE = "TIKTOK_IOS"
                se.STYLE_MORPH_PRESET = "TIKTOK_CLEAN"
                se.ENABLE_RESOLUTION_TWEAK = True
                se.ENABLE_FPS_JITTER = True
                se.FRAME_VARIANCE_STRENGTH = "light"
            elif preset == "CINEMATIC_FADE":
                se.PRESET_MODE = "YT_SHORTS_SAFE"
                se.FORGERY_PROFILE = "CANON_PRO"
                se.TRANSCODE_PROFILE = "YT_WEB"
                se.STYLE_MORPH_PRESET = "CINEMATIC_FADE"
                se.ENABLE_RESOLUTION_TWEAK = True
                se.ENABLE_FPS_JITTER = False
                se.ENABLE_VISUAL_ECHO = False
                se.FRAME_VARIANCE_STRENGTH = "very_light"
            elif preset == "OF_WASH":
                se.PRESET_MODE = "OF_WASH"
                se.FORGERY_PROFILE = "OF_CREATOR"
                se.TRANSCODE_PROFILE = "MOBILE_NATIVE"
                se.STYLE_MORPH_PRESET = "IG_RAW_LOOK"
                se.ENABLE_WATERMARK_REMOVAL = True
                se.FRAME_VARIANCE_STRENGTH = "soft"
            else:
                se.PRESET_MODE = "TIKTOK_SAFE"
                se.FORGERY_PROFILE = "TIKTOK_IPHONE"
                se.TRANSCODE_PROFILE = "TIKTOK_IOS"
                se.STYLE_MORPH_PRESET = "TIKTOK_CLEAN"

            try:
                if hasattr(se, "apply_style_and_lut"):
                    se.apply_style_and_lut(se.STYLE_MORPH_PRESET)
            except Exception as e:
                print("[LUT ERROR]", e)

        try:
            # Run heavy pipeline off the event loop
            if not USE_V2_ENGINE:
                await asyncio.to_thread(run_spoof_pipeline, input_path)

            spoofed_files = glob.glob(os.path.join(OUTPUT_DIR, "spoofed_*_final_output.mp4"))
            if not spoofed_files:
                await update.message.reply_text("⚠️ Spoofing failed. No output file generated.", reply_markup=back_button())
                return

            latest_spoofed = max(spoofed_files, key=os.path.getctime)
            final_output = os.path.join(OUTPUT_DIR, f"spoofed_{file_name}")
            shutil.move(latest_spoofed, final_output)

            with open(final_output, "rb") as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=f"spoofed_{file_name}",
                    caption="✅ Spoof complete!",
                    reply_markup=back_button()
                )

            # 🔻 Deduct one credit
            ok, info = await deduct_credits_for_user(update.effective_user.id, 1)
            if ok:
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"💳 Credit consumed. Remaining: {info}")
                except Exception:
                    pass
            else:
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"[⚠️] Could not deduct credit: {info}")
                except Exception:
                    pass

        except Exception as e:
            logging.error(f"Error during spoofing: {e}")
            await update.message.reply_text("❌ Something went wrong while spoofing the video. Please try again.", reply_markup=back_button())

    # -------- Single photo --------
    elif file_type == 'photo':
        platform_sel = context.user_data.get('selected_photo_platform', "IG_THREADS")
        await update.message.reply_text(f"🔧 Spoofing photo for: {platform_sel}")
        try:
            output_path = batch_spoof_image(input_path, platform=platform_sel)
            with open(output_path, "rb") as f:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=f,
                    caption="✅ Photo spoof complete!",
                    reply_markup=back_button()
                )

            # 🔻 Deduct one credit
            ok, info = await deduct_credits_for_user(update.effective_user.id, 1)
            if ok:
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"💳 Credit consumed. Remaining: {info}")
                except Exception:
                    pass
            else:
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"[⚠️] Could not deduct credit: {info}")
                except Exception:
                    pass

        except Exception as e:
            logging.error(f"Error during photo spoofing: {e}")
            await update.message.reply_text("❌ Something went wrong while spoofing the photo. Please try again.", reply_markup=back_button())

    # -------- Photo Clone Spoofing --------
    elif file_type == 'photo_clone':
        platform_sel = context.user_data.get('selected_photo_platform', "IG_THREADS")
        clone_count = context.user_data.get('clone_count', 3)
        await update.message.reply_text(f"🎭 Creating {clone_count} unique clones for: {platform_sel}\n⏳ This may take a moment...")
        try:
            cloned_paths = await asyncio.to_thread(clone_spoof_image, input_path, platform_sel, clone_count)
            
            # Send all clones
            for i, clone_path in enumerate(cloned_paths):
                with open(clone_path, "rb") as f:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=f,
                        caption=f"✅ Clone {i+1}/{len(cloned_paths)} - {platform_sel}"
                    )
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🎉 Successfully created {len(cloned_paths)} unique clones!\n\nEach clone has different fingerprints and can be posted separately.",
                reply_markup=back_button()
            )

            # 🔻 Deduct credits (1 per clone)
            ok, info = await deduct_credits_for_user(update.effective_user.id, len(cloned_paths))
            if ok:
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"💳 Credits consumed: {len(cloned_paths)}. Remaining: {info}")
                except Exception:
                    pass
            else:
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"[⚠️] Could not deduct {len(cloned_paths)} credits: {info}")
                except Exception:
                    pass

        except Exception as e:
            logging.error(f"Error during photo cloning: {e}")
            await update.message.reply_text("❌ Something went wrong while cloning the photo. Please try again.", reply_markup=back_button())

    # -------- GIF Spoofing --------
    elif file_type == 'gif':
        platform = context.user_data.get('selected_gif_platform', "reddit")
        await update.message.reply_text(f"🎭 Spoofing GIF for {platform.upper()}...")
        try:
            # Check if Telegram converted GIF to MP4
            if input_path.endswith('.gif.mp4') or input_path.endswith('.mp4'):
                # Convert MP4 back to GIF first, then spoof it
                await update.message.reply_text("🔄 Converting Telegram MP4 back to GIF...")
                gif_path = await asyncio.to_thread(convert_video_to_gif, input_path, fps=15, width=400, platform="general")
                output_path = await asyncio.to_thread(spoof_gif_advanced, gif_path, platform, "medium", True)
            else:
                # Process as regular GIF
                output_path = await asyncio.to_thread(spoof_gif_advanced, input_path, platform, "medium", True)
            
            with open(output_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=f"spoofed_{os.path.basename(output_path)}",
                    caption="✅ GIF spoof complete!",
                    reply_markup=back_button()
                )
            
            # Deduct one credit
            ok, info = await deduct_credits_for_user(update.effective_user.id, 1)
            if ok:
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"💳 Credit consumed. Remaining: {info}")
                except Exception:
                    pass
                    
        except Exception as e:
            logging.error(f"Error during GIF spoofing: {e}")
            await update.message.reply_text("❌ GIF spoofing failed. Please try again.", reply_markup=back_button())

    # -------- Video to GIF Conversion --------
    elif file_type == 'video_for_gif':
        mode = context.user_data.get('gif_conversion_mode', 'vid2gif_full')
        await update.message.reply_text(f"🎬➡️🎭 Converting video to GIF...")
        try:
            if mode == 'vid2gif_full':
                output_path = await asyncio.to_thread(convert_video_to_gif, input_path, fps=15, width=400, platform="general")
            elif mode == 'vid2gif_moments':
                output_path = await asyncio.to_thread(convert_video_to_gif, input_path, fps=12, width=400, platform="general")
            else:  # vid2gif_segment - for now treat as full, can enhance later
                output_path = await asyncio.to_thread(convert_video_to_gif, input_path, fps=15, width=400, platform="general")
            
            with open(output_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=f"converted_{os.path.basename(output_path)}",
                    caption="✅ Video to GIF conversion complete!",
                    reply_markup=back_button()
                )
            
            # Deduct one credit
            ok, info = await deduct_credits_for_user(update.effective_user.id, 1)
            if ok:
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"💳 Credit consumed. Remaining: {info}")
                except Exception:
                    pass
                    
        except Exception as e:
            logging.error(f"Error during video to GIF conversion: {e}")
            await update.message.reply_text("❌ Video to GIF conversion failed. Please try again.", reply_markup=back_button())

    # -------- Frame Extraction --------
    elif file_type == 'video_for_frames':
        mode = context.user_data.get('frame_extraction_mode', 'frames_quick')
        await update.message.reply_text(f"📸 Extracting frames...")
        try:
            if mode == 'frames_quick':
                extracted_frames = await asyncio.to_thread(extract_frames_by_count, input_path, 10, "evenly_spaced")
            elif mode == 'frames_key':
                extracted_frames = await asyncio.to_thread(extract_key_frames, input_path, 0.3, 20)
            else:  # frames_custom, frames_interval - default to 15 frames evenly spaced
                extracted_frames = await asyncio.to_thread(extract_frames_by_count, input_path, 15, "evenly_spaced")
            
            # Send up to 10 frames as photos, rest as ZIP
            frames_sent = 0
            for frame_path in extracted_frames[:10]:
                try:
                    with open(frame_path, "rb") as f:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=f
                        )
                    frames_sent += 1
                except Exception as e:
                    logging.error(f"Failed to send frame {frame_path}: {e}")
            
            if len(extracted_frames) > 10:
                # Create ZIP for remaining frames
                zip_path = await asyncio.to_thread(create_bulk_output_zip, 
                    [{"status": "success", "frames": extracted_frames[10:]}], "frame_extraction")
                if zip_path:
                    with open(zip_path, "rb") as f:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=f,
                            filename=f"remaining_frames.zip",
                            caption=f"📦 {len(extracted_frames)-10} additional frames"
                        )
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Frame extraction complete! {len(extracted_frames)} frames extracted.",
                reply_markup=back_button()
            )
            
            # Deduct one credit
            ok, info = await deduct_credits_for_user(update.effective_user.id, 1)
            if ok:
                try:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"💳 Credit consumed. Remaining: {info}")
                except Exception:
                    pass
                    
        except Exception as e:
            logging.error(f"Error during frame extraction: {e}")
            await update.message.reply_text("❌ Frame extraction failed. Please try again.", reply_markup=back_button())

    # -------- Bulk Processing File Collection --------
    elif file_type in ['bulk_photos', 'bulk_videos', 'bulk_vid2gif', 'bulk_frames']:
        bulk_files = context.user_data.setdefault('bulk_files', [])
        bulk_files.append(input_path)
        await update.message.reply_text(
            f"✅ Added: {os.path.basename(input_path)}\n"
            f"📦 Bulk queue: {len(bulk_files)} files\n"
            f"💬 Type 'START' to begin bulk processing.",
            reply_markup=back_button()
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    if context.user_data.get('awaiting_license'):
        license_key = update.message.text.strip()
        hwid = generate_hwid()

        try:
            r = requests.post(
                f"{BASE_URL}/verify",
                json={"key": license_key, "hwid": hwid, "telegram_id": username},
                timeout=15
            )
            data = r.json()
            if r.status_code == 200 and data.get("valid") is True:
                verified_users[user_id] = license_key
                context.user_data.pop('awaiting_license', None)
                try:
                    with open("logo.png", "rb") as logo:
                        await update.message.reply_photo(logo)
                except Exception:
                    pass
                await update.message.reply_text(
                    f"✅ License activated!\n"
                    f"Tier: {data.get('tier','?')}\n"
                    f"Credits: {data.get('credits','?')}",
                    reply_markup=main_menu()
                )
            else:
                await update.message.reply_text(f"❌ Invalid license: {data.get('reason', 'Unknown error')}")
        except Exception as e:
            logging.error(f"Exception verifying license: {e}")
            await update.message.reply_text("❌ Server error verifying license.")
        return

    if context.user_data.get('awaiting_support'):
        user = update.effective_user.username or update.effective_user.full_name
        support_message = update.message.text.strip()

        success = send_support_email(user, support_message)
        context.user_data.pop('awaiting_support', None)

        if success:
            await update.message.reply_text("✅ Your message has been sent to our team.")
        else:
            await update.message.reply_text("❌ Failed to send message. Please try again later.")

        await update.message.reply_text("What would you like to do next?", reply_markup=main_menu())
        return

    # Handle bulk processing START command
    text = update.message.text.strip().upper()
    if text == "START":
        file_type = context.user_data.get('expected_file_type', '')
        bulk_files = context.user_data.get('bulk_files', [])
        
        if not bulk_files:
            await update.message.reply_text("📦 No files in bulk queue. Send files first.", reply_markup=back_button())
            return
            
        if file_type == 'bulk_photos':
            platform = context.user_data.get('bulk_photo_platform', 'IG_THREADS')
            await update.message.reply_text(f"📦🖼️ Starting bulk photo spoofing for {len(bulk_files)} files using {platform} mode...")
            try:
                result = await asyncio.to_thread(bulk_spoof_photos, bulk_files, platform, max_workers=2)
                successful = len([r for r in result['results'] if r['status'] == 'success'])
                
                # Send results
                for r in result['results'][:5]:  # Send first 5 results
                    if r['status'] == 'success' and os.path.exists(r['spoofed']):
                        with open(r['spoofed'], 'rb') as f:
                            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=f)
                
                # Create ZIP for all results
                if result.get('report_path'):
                    zip_path = await asyncio.to_thread(create_bulk_output_zip, result['results'], "bulk_photos")
                    if zip_path:
                        with open(zip_path, 'rb') as f:
                            await context.bot.send_document(
                                chat_id=update.effective_chat.id,
                                document=f,
                                filename="bulk_photos_spoofed.zip",
                                caption=f"📦 {successful}/{len(bulk_files)} photos spoofed successfully!"
                            )
                
                # Deduct credits
                if successful > 0:
                    ok, info = await deduct_credits_for_user(update.effective_user.id, successful)
                    if ok:
                        await context.bot.send_message(chat_id=update.effective_chat.id, 
                            text=f"💳 Credits consumed: {successful}. Remaining: {info}")
                        
            except Exception as e:
                logging.error(f"Bulk photo processing error: {e}")
                await update.message.reply_text("❌ Bulk photo processing failed.", reply_markup=back_button())
                
        elif file_type == 'bulk_videos':
            preset = context.user_data.get('bulk_video_preset', 'TIKTOK_CLEAN')
            await update.message.reply_text(f"📦🎥 Starting bulk video spoofing for {len(bulk_files)} files using {preset} mode...")
            try:
                result = await asyncio.to_thread(bulk_spoof_videos, bulk_files, preset, max_workers=1)
                successful = len([r for r in result['results'] if r['status'] == 'success'])
                
                # Send first few results
                for r in result['results'][:3]:
                    if r['status'] == 'success' and os.path.exists(r['spoofed']):
                        with open(r['spoofed'], 'rb') as f:
                            await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
                
                await context.bot.send_message(chat_id=update.effective_chat.id, 
                    text=f"✅ Bulk video spoofing complete: {successful}/{len(bulk_files)} successful",
                    reply_markup=back_button())
                
                # Deduct credits
                if successful > 0:
                    ok, info = await deduct_credits_for_user(update.effective_user.id, successful)
                    if ok:
                        await context.bot.send_message(chat_id=update.effective_chat.id, 
                            text=f"💳 Credits consumed: {successful}. Remaining: {info}")
                        
            except Exception as e:
                logging.error(f"Bulk video processing error: {e}")
                await update.message.reply_text("❌ Bulk video processing failed.", reply_markup=back_button())
                
        elif file_type == 'bulk_vid2gif':
            platform = context.user_data.get('bulk_gif_platform', 'general')
            await update.message.reply_text(f"📦🎭 Starting bulk video to GIF conversion for {len(bulk_files)} files using {platform} optimization...")
            try:
                result = await asyncio.to_thread(bulk_convert_to_gifs, bulk_files, platform, fps=15, width=400, max_workers=2)
                successful = len([r for r in result['results'] if r['status'] == 'success'])
                
                # Send first few GIFs
                for r in result['results'][:5]:
                    if r['status'] == 'success' and os.path.exists(r['gif']):
                        with open(r['gif'], 'rb') as f:
                            await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
                
                await context.bot.send_message(chat_id=update.effective_chat.id, 
                    text=f"✅ Bulk GIF conversion complete: {successful}/{len(bulk_files)} successful",
                    reply_markup=back_button())
                
                # Deduct credits
                if successful > 0:
                    ok, info = await deduct_credits_for_user(update.effective_user.id, successful)
                    if ok:
                        await context.bot.send_message(chat_id=update.effective_chat.id, 
                            text=f"💳 Credits consumed: {successful}. Remaining: {info}")
                        
            except Exception as e:
                logging.error(f"Bulk video to GIF error: {e}")
                await update.message.reply_text("❌ Bulk video to GIF failed.", reply_markup=back_button())
                
        elif file_type == 'bulk_frames':
            method = context.user_data.get('bulk_frame_method', 'evenly_spaced_10')
            if method == 'evenly_spaced_10':
                method_name, frame_count = "evenly_spaced", 10
            elif method == 'evenly_spaced_15':
                method_name, frame_count = "evenly_spaced", 15
            elif method == 'key_frames':
                method_name, frame_count = "key_frames", 20
            elif method == 'time_intervals':
                method_name, frame_count = "evenly_spaced", 12
            else:
                method_name, frame_count = "evenly_spaced", 10
                
            await update.message.reply_text(f"📦📸 Starting bulk frame extraction for {len(bulk_files)} files using {method_name} method ({frame_count} frames)...")
            try:
                if method_name == "key_frames":
                    # Use custom bulk function for key frames
                    result = await asyncio.to_thread(bulk_extract_frames_custom, bulk_files, method_name, frame_count, max_workers=2)
                else:
                    result = await asyncio.to_thread(bulk_extract_frames, bulk_files, method_name, frame_count, max_workers=2)
                successful = len([r for r in result['results'] if r['status'] == 'success'])
                total_frames = sum(r['count'] for r in result['results'] if r['status'] == 'success')
                
                # Create ZIP with all frames
                zip_path = await asyncio.to_thread(create_bulk_output_zip, result['results'], "bulk_frames")
                if zip_path:
                    with open(zip_path, 'rb') as f:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=f,
                            filename="bulk_extracted_frames.zip",
                            caption=f"📦 {total_frames} frames extracted from {successful}/{len(bulk_files)} videos!"
                        )
                
                # Deduct credits
                if successful > 0:
                    ok, info = await deduct_credits_for_user(update.effective_user.id, successful)
                    if ok:
                        await context.bot.send_message(chat_id=update.effective_chat.id, 
                            text=f"💳 Credits consumed: {successful}. Remaining: {info}")
                        
            except Exception as e:
                logging.error(f"Bulk frame extraction error: {e}")
                await update.message.reply_text("❌ Bulk frame extraction failed.", reply_markup=back_button())
        
        # Clear bulk files after processing
        context.user_data['bulk_files'] = []
        context.user_data['expected_file_type'] = None
        return

    await update.message.reply_text("❌ Please use the buttons or commands.")

# ---------------- Batch helper ----------------

def run_batch_spoof_pipeline(file_paths, context):
    output_files = []
    photo_preset = context.user_data.get('photo_batch_preset', "IG_THREADS")
    video_preset = context.user_data.get('video_batch_preset', "TIKTOK_CLEAN")

    for file_path in file_paths:
        try:
            ext = os.path.splitext(file_path)[-1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tif', '.tiff']:
                outp = batch_spoof_image(file_path, platform=photo_preset)
                output_files.append(outp)
            elif ext in ['.mp4', '.mov', '.mkv', '.avi']:
                # reset engine baseline
                se.ENABLE_WATERMARK_REMOVAL = False
                se.ENABLE_VISUAL_ECHO = False
                se.ENABLE_RESOLUTION_TWEAK = False
                se.ENABLE_FPS_JITTER = False
                se.FRAME_VARIANCE_STRENGTH = "soft"
                se.MOTION_PROFILE = "STABILIZED_GIMBAL"

                if video_preset == "IG_RAW_LOOK":
                    se.PRESET_MODE = "IG_REELS_SAFE"; se.FORGERY_PROFILE = "IG_ANDROID"; se.TRANSCODE_PROFILE = "IG_REELS"; se.STYLE_MORPH_PRESET = "IG_RAW_LOOK"; se.ENABLE_RESOLUTION_TWEAK = True
                elif video_preset == "TIKTOK_CLEAN":
                    se.PRESET_MODE = "TIKTOK_SAFE"; se.FORGERY_PROFILE = "TIKTOK_IPHONE"; se.TRANSCODE_PROFILE = "TIKTOK_IOS"; se.STYLE_MORPH_PRESET = "TIKTOK_CLEAN"; se.ENABLE_RESOLUTION_TWEAK = True; se.ENABLE_FPS_JITTER = True; se.FRAME_VARIANCE_STRENGTH = "light"
                elif video_preset == "CINEMATIC_FADE":
                    se.PRESET_MODE = "YT_SHORTS_SAFE"; se.FORGERY_PROFILE = "CANON_PRO"; se.TRANSCODE_PROFILE = "YT_WEB"; se.STYLE_MORPH_PRESET = "CINEMATIC_FADE"; se.ENABLE_RESOLUTION_TWEAK = True; se.ENABLE_FPS_JITTER = True; se.ENABLE_VISUAL_ECHO = True; se.FRAME_VARIANCE_STRENGTH = "light"
                elif video_preset == "OF_WASH":
                    se.PRESET_MODE = "OF_WASH"; se.FORGERY_PROFILE = "OF_CREATOR"; se.TRANSCODE_PROFILE = "MOBILE_NATIVE"; se.STYLE_MORPH_PRESET = "IG_RAW_LOOK"; se.ENABLE_WATERMARK_REMOVAL = True; se.FRAME_VARIANCE_STRENGTH = "soft"
                else:
                    se.PRESET_MODE = "TIKTOK_SAFE"; se.FORGERY_PROFILE = "TIKTOK_IPHONE"; se.TRANSCODE_PROFILE = "TIKTOK_IOS"; se.STYLE_MORPH_PRESET = "TIKTOK_CLEAN"

                try:
                    if hasattr(se, "apply_style_and_lut"):
                        se.apply_style_and_lut(se.STYLE_MORPH_PRESET)
                except Exception as e:
                    print("[LUT ERROR]", e)

                run_spoof_pipeline(file_path)
                spoofed_files = glob.glob(os.path.join(OUTPUT_DIR, "spoofed_*_final_output.mp4"))
                if spoofed_files:
                    latest_spoofed = max(spoofed_files, key=os.path.getctime)
                    final_output = os.path.join(OUTPUT_DIR, f"spoofed_{os.path.basename(file_path)}")
                    shutil.move(latest_spoofed, final_output)
                    output_files.append(final_output)
        except Exception as e:
            logging.error(f"Batch spoofing error for {file_path}: {e}")

    return output_files

# ---------------- Entrypoint ----------------

def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .read_timeout(120)
        .write_timeout(120)
        .connect_timeout(30)
        .get_updates_read_timeout(120)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CommandHandler("verify", verify))
    app.add_handler(CommandHandler("spoof", spoof))
    app.add_handler(CommandHandler("reset_hwid", reset_hwid))
    app.add_handler(CommandHandler("status", status))

    logging.info("SpectreSpoofer Assistant Bot running (live).")
    app.run_polling()

if __name__ == "__main__":
    main()
