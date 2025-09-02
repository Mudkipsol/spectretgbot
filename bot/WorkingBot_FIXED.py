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

from photo_spoofer import batch_spoof_image
from spoof_engine import run_spoof_pipeline
import spoof_engine as se  # used to set runtime globals for the engine

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
        [InlineKeyboardButton("🎥 Send Video", callback_data='send_video')],
        [InlineKeyboardButton("🖼️ Photo Spoofer", callback_data='photo_spoofer')],
        [InlineKeyboardButton("📦 Batch Spoof", callback_data='batch_spoof')],
        [InlineKeyboardButton("⚙️ Spoof Settings", callback_data='spoof_settings')],
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
        [InlineKeyboardButton("👽 Reddit Mode", callback_data='photo_reddit')]
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
        await query.edit_message_text("❌ Unknown action.", reply_markup=back_button())

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
        await update.message.reply_text(f"🔧 Spoofing: {file_name}\n🔧 Mode: {preset}")

        # Reset baseline runtime flags in engine
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
            se.ENABLE_FPS_JITTER = True
            se.ENABLE_VISUAL_ECHO = True
            se.FRAME_VARIANCE_STRENGTH = "light"
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
