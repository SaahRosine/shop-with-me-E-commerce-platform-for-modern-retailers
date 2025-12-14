import grpc
from concurrent import futures
import time
import uuid
import sys
import os

# Fix import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import generated gRPC code
from user_service import user_pb2
from user_service import user_pb2_grpc

# --- IN-MEMORY DATABASE ---
USERS_DB = {} 
OTP_DB = {}

class UserService(user_pb2_grpc.UserServiceServicer):

    def EnrollUser(self, request, context):
        if request.email in USERS_DB:
            return user_pb2.EnrollUserResponse(success=False, message="User already exists.")
        
        new_user_id = str(uuid.uuid4())
        USERS_DB[request.email] = {
            "id": new_user_id,
            "password": request.password,
            "name": request.name,
            "storage_used": 0,
            "storage_limit": 50 * 1024 * 1024 * 1024  # 50 GB
        }
        print(f"User enrolled: {request.email} | ID: {new_user_id}")
        return user_pb2.EnrollUserResponse(success=True, message="Enrollment successful.", user_id=new_user_id)

    def RequestOTP(self, request, context):
        email = request.email
        if email not in USERS_DB:
            return user_pb2.RequestOTPResponse(success=False, message="Email not registered.")
        
        otp_code = "123456" # Fixed OTP for demo
        OTP_DB[email] = otp_code
        print(f"--- OTP Generated for {email}: {otp_code} ---")
        return user_pb2.RequestOTPResponse(success=True, message="OTP sent to console.")

    def AuthenticateWithOTP(self, request, context):
        email = request.email
        if OTP_DB.get(email) == request.otp_code:
            del OTP_DB[email]
            return user_pb2.AuthenticateWithOTPResponse(success=True, message="Authentication successful.", auth_token=f"jwt-token-{email}")
        return user_pb2.AuthenticateWithOTPResponse(success=False, message="Invalid OTP.")

    def GetUserProfile(self, request, context):
        # Always return a dummy profile for the dashboard demo
        return user_pb2.GetUserProfileResponse(
            user_id=request.user_id,
            name="Newbie Dev",
            email="test.newbie@example.com",
            storage_used_bytes=0,
            storage_quota_bytes=53687091200 # 50GB
        )

def serve():
    # THE CORRECT PORT IS HERE:
    port = '50051'
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    server.add_insecure_port('[::]:' + port)
    server.start()
    print(f"🚀 User Service listening on port {port}...")
    try:
        while True: time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()