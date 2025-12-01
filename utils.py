import hashlib
import random
import time

# Simulated in-memory database
USER_DATA_DB = {}

# OTP temporary store
OTP_STORE = {}

# 2GB Storage Quota
TWO_GIGABYTES = 2 * 1024 * 1024 * 1024


# ------------------ SECURITY ------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def check_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


# ------------------ OTP SYSTEM ------------------

def send_otp_and_store(email: str):
    otp = str(random.randint(100000, 999999))
    OTP_STORE[email] = {
        'otp': otp,
        'timestamp': time.time()
    }
    print(f"[OTP] OTP for {email}: {otp} (simulated send)")
    return True, "OTP has been sent to your email (simulated)."


def verify_otp(email: str, otp: str):
    record = OTP_STORE.get(email)

    if not record:
        return False, "No OTP request found."

    if time.time() - record['timestamp'] > 300:  # 5 minutes validity
        return False, "OTP expired."

    if record['otp'] == otp:
        del OTP_STORE[email]
        return True, "OTP verification successful."

    return False, "Invalid OTP."


# ------------------ STORAGE ------------------

def bytes_to_human(num_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num_bytes < 1024:
            return f"{num_bytes:.2f}{unit}"
        num_bytes /= 1024
