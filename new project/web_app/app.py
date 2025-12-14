from flask import Flask, render_template, request, redirect, url_for, session
import grpc
import sys
import os

# --- 1. SETUP PATHS ---
# Allow importing from the parent folder (where user_service is)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. IMPORT GRPC MODULES ---
from user_service import user_pb2
from user_service import user_pb2_grpc

app = Flask(__name__)
app.secret_key = 'super-secret-key'

# --- 3. CONNECT TO GRPC SERVER ---
# This must match the server port (50051)
GRPC_SERVER_ADDRESS = 'localhost:50051'

def get_grpc_stub():
    channel = grpc.insecure_channel(GRPC_SERVER_ADDRESS)
    stub = user_pb2_grpc.UserServiceStub(channel)
    return stub

# --- 4. ROUTES ---

@app.route('/')
def home():
    # If user is already logged in, show dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ""
    if request.method == 'POST':
        action = request.form.get('action')
        email = request.form.get('email')
        
        stub = get_grpc_stub()

        if action == 'register':
            # Handle Registration (Enroll)
            name = request.form.get('name')
            password = request.form.get('password')
            try:
                response = stub.EnrollUser(user_pb2.EnrollUserRequest(
                    name=name, 
                    email=email, 
                    password=password
                ))
                if response.success:
                    message = "Registration successful! Please login."
                else:
                    message = f"Error: {response.message}"
            except grpc.RpcError as e:
                message = f"Server Error: {e.details()}"

        elif action == 'login_otp':
            # Step 1: Request OTP
            try:
                response = stub.RequestOTP(user_pb2.RequestOTPRequest(email=email))
                if response.success:
                    # Store email in session to verify later
                    session['temp_email'] = email
                    return render_template('login.html', step="verify_otp", message="OTP sent! Check server console.")
                else:
                    message = f"Error: {response.message}"
            except grpc.RpcError as e:
                message = f"Connection Failed. Is the server running on 50051? ({e.code()})"

        elif action == 'verify_otp':
            # Step 2: Verify OTP
            otp_code = request.form.get('otp')
            email = session.get('temp_email')
            
            try:
                response = stub.AuthenticateWithOTP(user_pb2.AuthenticateWithOTPRequest(
                    email=email, 
                    otp_code=otp_code
                ))
                if response.success:
                    # Login Success!
                    session['user_id'] = email # In real app, use real ID
                    session.pop('temp_email', None)
                    return redirect(url_for('dashboard'))
                else:
                    return render_template('login.html', step="verify_otp", message="Invalid OTP. Try again.")
            except grpc.RpcError as e:
                message = f"Server Error: {e.details()}"

    return render_template('login.html', step="login", message=message)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user_id']
    
    # Fetch profile data from gRPC
    stub = get_grpc_stub()
    try:
        response = stub.GetUserProfile(user_pb2.GetUserProfileRequest(user_id=user_email))
        
        # Calculate percentage for progress bar
        usage_percent = 0
        if response.storage_quota_bytes > 0:
            usage_percent = (response.storage_used_bytes / response.storage_quota_bytes) * 100
            
        return render_template('dashboard.html', user=response, usage_percent=usage_percent)
    except grpc.RpcError:
        return "Error loading profile. Is server running?"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=8080)