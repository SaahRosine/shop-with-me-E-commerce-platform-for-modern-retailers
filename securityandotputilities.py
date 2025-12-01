import bcrypt
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import os

# --- Global Data Stores (Simulating Database) ---

# Stores user data: {email: {username, password_hash, quota_bytes, used_bytes, is_verified}}
# Initial quota is 2GB (2 * 1024 * 1024 * 1024 bytes)
TWO_GIGABYTES = 2147483648
USER_DATA_DB = {} 

# Temporary store for OTPs: {email: {otp: '123456', expiry: 123456789}}
OTP_CACHE = {} 
OTP_EXPIRY_SECONDS = 300 # 5 minutes

# --- Email Credentials (Using hardcoded placeholders for demonstration) ---
# IMPORTANT: Use a Gmail App Password if 2FA is enabled on the sender account.
SENDER_EMAIL = "sasbergson@gmail.com"
SENDER_PASSWORD = "tgnw azxw lfjr jsuz" 

# --- Security Functions ---

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """Checks a plaintext password against a stored bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- Utility Functions ---

def bytes_to_human(bytes_val):
    """Converts bytes to MB or GB for display."""
    if bytes_val >= 1024**3:
        return f"{round(bytes_val / (1024**3), 2)} GB"
    elif bytes_val >= 1024**2:
        return f"{round(bytes_val / (1024**2), 2)} MB"
    else:
        return f"{bytes_val} Bytes"

# --- OTP Functions ---

def generate_otp() -> str:
    """Generates a secure 6-digit OTP."""
    return str(random.randint(100000, 999999))

def send_otp_and_store(to_email: str) -> tuple[bool, str]:
    """Generates, stores, and sends the OTP."""
    otp = generate_otp()
    
    # Store OTP in cache
    expiry_time = time.time() + OTP_EXPIRY_SECONDS
    OTP_CACHE[to_email] = {'otp': otp, 'expiry': expiry_time}
    
    # In a real app, we wouldn't print the OTP! This is for demonstration.
    print(f"DEBUG: Stored OTP {otp} for {to_email} until {time.ctime(expiry_time)}")

    # Email configuration
    subject = "Your One-Time Password (OTP) for Cloud Access"
    body = f"Your OTP code is: {otp}\n\nThis code is valid for {OTP_EXPIRY_SECONDS/60} minutes."

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect and send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            return True, f"OTP sent to {to_email}. Check your inbox. It expires in 5 minutes."
    except Exception as e:
        print(f"ERROR: Failed to send email to {to_email}: {e}")
        # If email fails, remove the temporary OTP cache entry
        del OTP_CACHE[to_email] 
        return False, f"Email failed to send. Check server configuration/credentials. Error: {e}"

def verify_otp(email: str, otp_code: str) -> tuple[bool, str]:
    """Verifies the submitted OTP against the cache."""
    if email not in OTP_CACHE:
        return False, "OTP not requested or has expired. Please log in again."

    cached_otp_data = OTP_CACHE[email]
    
    if time.time() > cached_otp_data['expiry']:
        del OTP_CACHE[email]
        return False, "OTP has expired. Please request a new login."

    if otp_code == cached_otp_data['otp']:
        del OTP_CACHE[email] # OTP is single-use
        return True, "OTP verified successfully. You are now connected!"
    else:
        return False, "Invalid OTP code."