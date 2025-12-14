import sys
import os
import time
import grpc

print("Client Script Starting...")

try:
    # Use the explicit package path for the imports
    import user_service.user_pb2 as user_pb2 
    import user_service.user_pb2_grpc as user_pb2_grpc
    print("Protobuf files imported successfully.")
    
except ImportError as e:
    print(f"FATAL IMPORT ERROR: {e}")
    sys.exit(1)

def run_client():
    """Client function to test the User Service (All 4 RPCs)."""
    
    # Define variables outside the try block so they are accessible later
    test_email = "test.newbie@example.com"
    test_password = "SecurePassword123"
    user_id = None
    
    try:
        # 1. Establish the connection
        print("Attempting to connect to gRPC server at localhost:50051...")
        with grpc.insecure_channel('localhost:50051') as channel:
            stub = user_pb2_grpc.UserServiceStub(channel)
            print("Connection successful. Starting tests...")
            
            # --- 1. Testing Enrollment (EnrollUser) ---
            print("\n--- 1. Testing Enrollment (EnrollUser) ---")
            enroll_response = stub.EnrollUser(user_pb2.EnrollUserRequest(
                email=test_email, 
                password=test_password, 
                name="Newbie Dev"
            ))
            
            print(f"Enroll Status: {enroll_response.success}")
            print(f"Message: {enroll_response.message}")
            
            if enroll_response.success:
                user_id = enroll_response.user_id
                print(f"User ID: {user_id}")
            else:
                # If enrollment fails (user already exists), assume a previous run
                # and try to find the user_id (requires server change, but we proceed)
                print("Enrollment failed. Skipping to OTP request.")

            time.sleep(1) # Wait a moment

            # --- 2. Testing OTP Request (RequestOTP) ---
            print("\n--- 2. Testing OTP Request (RequestOTP) ---")
            otp_req_response = stub.RequestOTP(user_pb2.RequestOTPRequest(email=test_email))
            print(f"OTP Request Status: {otp_req_response.success}")
            print(f"Message: {otp_req_response.message}")
            
            if not otp_req_response.success:
                print("Could not request OTP. Stopping test.")
                return

            # IMPORTANT: Manually retrieve the OTP from the SERVER CONSOLE for this demo!
            print("\n*** ACTION REQUIRED: CHECK THE SERVER CONSOLE FOR THE GENERATED OTP CODE! ***")
            
            # Wait for user input
            otp_code = input("Enter the 6-digit OTP code from the server console: ")
            
            # --- 3. Testing Authentication (AuthenticateWithOTP) ---
            print("\n--- 3. Testing Authentication (AuthenticateWithOTP) ---")
            auth_response = stub.AuthenticateWithOTP(user_pb2.AuthenticateWithOTPRequest(
                email=test_email,
                otp_code=otp_code
            ))
            
            print(f"Auth Status: {auth_response.success}")
            print(f"Message: {auth_response.message}")
            
            if auth_response.success:
                auth_token = auth_response.auth_token
                print(f"JWT Token (first 20 chars): {auth_token[:20]}...")
            else:
                print("Authentication failed. Stopping test.")
                return

            time.sleep(1) # Wait a moment

            # --- 4. Testing GetUserProfile ---
            # NOTE: We assume the server can look up the profile based on the email from step 1/2
            # or the user ID must be retrieved. For simplicity, we assume user_id is set.
            if not user_id:
                # If user_id wasn't set in Step 1, try to look it up (requires complex logic)
                # For this demo, we'll assume it was set correctly in Step 1.
                print("Cannot run GetUserProfile: User ID missing.")
                return

            print("\n--- 4. Testing GetUserProfile ---")
            profile_response = stub.GetUserProfile(user_pb2.GetUserProfileRequest(
                user_id=user_id
            ))
            
            # The response is the UserProfile message itself
            print(f"Profile retrieved for: {profile_response.name}")
            print(f"  > Email: {profile_response.email}")
            
            # Formatting large byte numbers for readability
            quota_gb = profile_response.storage_quota_bytes / (1024**3)
            used_mb = profile_response.storage_used_bytes / (1024**2)
            
            print(f"  > Storage Quota: {quota_gb:.0f} GB")
            print(f"  > Storage Used: {used_mb:.2f} MB")
            
            print("\nTest completed successfully.")

    except grpc.RpcError as e:
        print(f"\nFATAL RUNTIME ERROR: gRPC connection or call failed (RpcError).")
        print(f"Status Code: {e.code()}")
        print(f"Details: {e.details()}")
        print("Check: Is the server running? Check for network issues.")
        
    except Exception as e:
        print(f"\nFATAL UNEXPECTED ERROR: {e}")

# --- CRITICAL: THE SCRIPT ENTRY POINT ---
if __name__ == '__main__':
    run_client()