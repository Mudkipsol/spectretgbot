
import sqlite3
import os
from datetime import datetime, timedelta

# Path to the shared license database
DB_PATH = os.getenv("SPECTRE_LICENSE_DB", "spectre_license_db.sqlite")

def connect_db():
    return sqlite3.connect(DB_PATH)

def validate_license(license_key, machine_id=None, telegram_username=None):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT license_type, spoof_count, max_spoofs, machine_id, telegram_username, is_active FROM licenses WHERE license_key = ?", (license_key,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False, "License key not found."

    license_type, spoof_count, max_spoofs, stored_machine_id, stored_username, is_active = row

    if not is_active:
        return False, "License is inactive or expired."

    if stored_machine_id and machine_id and stored_machine_id != machine_id:
        return False, "License machine mismatch."

    if telegram_username:
        if not stored_username:
            # Bind Telegram username on first use
            cursor = connect_db().cursor()
            cursor.execute("UPDATE licenses SET telegram_username = ? WHERE license_key = ?", (telegram_username, license_key))
            cursor.connection.commit()
        elif stored_username != telegram_username:
            return False, "License Telegram mismatch."

    if max_spoofs is not None and spoof_count >= max_spoofs:
        return False, "Spoof limit reached."

    return True, license_type

def increment_spoof_count(license_key):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE licenses SET spoof_count = spoof_count + 1 WHERE license_key = ?", (license_key,))
    conn.commit()
    conn.close()

def create_trial_key(machine_id, telegram_username):
    import uuid
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM licenses WHERE machine_id = ? OR telegram_username = ?", (machine_id, telegram_username))
    if cursor.fetchone():
        conn.close()
        return None, "Trial already claimed."

    license_key = f"TRIAL-{uuid.uuid4().hex[:8].upper()}"
    cursor.execute("""
        INSERT INTO licenses (license_key, license_type, spoof_count, max_spoofs, machine_id, telegram_username)
        VALUES (?, 'trial', 0, 5, ?, ?)
    """, (license_key, machine_id, telegram_username))

    conn.commit()
    conn.close()
    return license_key, "Trial license created."

def upgrade_license(license_key, license_type, max_spoofs=None):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE licenses SET license_type = ?, max_spoofs = ?, is_active = 1 WHERE license_key = ?", (license_type, max_spoofs, license_key))
    conn.commit()
    conn.close()
