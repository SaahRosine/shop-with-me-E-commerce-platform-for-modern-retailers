import grpc
from concurrent import futures
import time

import utils
import cloud_system_pb2 as pb
import cloud_system_pb2_grpc as pb_grpc
from cloud_system import (
    create_empty_quota_response,
    create_calc_error_response,
    create_file_transfer_response
)

_ONE_DAY_IN_SECONDS = 60 * 60 * 24
SERVER_PORT = '[::]:50051'



class EnrollmentServicer(pb_grpc.EnrollmentServiceServicer):

    def Enroll(self, request, context):
        if request.email in utils.USER_DATA_DB:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            return pb.GeneralResponse(False, "Email already registered.")

        if not request.email or not request.password:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return pb.GeneralResponse(False, "Email and password required.")

        utils.USER_DATA_DB[request.email] = {
            'username': request.username,
            'password_hash': utils.hash_password(request.password),
            'quota_bytes': utils.TWO_GIGABYTES,
            'used_bytes': 0,
            'is_verified': False
        }

        print(f"[ENROLL] {request.email} registered.")
        return pb.GeneralResponse(True, "Enrollment successful.")



class UserServicer(pb_grpc.UserServiceServicer):

    def Login(self, request, context):
        user = utils.USER_DATA_DB.get(request.email)

        if not user or not utils.check_password(request.password, user['password_hash']):
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            return pb.GeneralResponse(False, "Invalid credentials.")

        success, message = utils.send_otp_and_store(request.email)
        return pb.GeneralResponse(success, message)

    def VerifyOTP(self, request, context):
        success, message = utils.verify_otp(request.email, request.otp)

        if success:
            utils.USER_DATA_DB[request.email]['is_verified'] = True
            return pb.GeneralResponse(True, message)

        context.set_code(grpc.StatusCode.UNAUTHENTICATED)
        return pb.GeneralResponse(False, message)



class StorageServicer(pb_grpc.StorageServiceServicer):

    def _auth(self, email, context):
        user = utils.USER_DATA_DB.get(email)
        if not user or not user['is_verified']:
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            return None
        return user

    def CheckQuota(self, request, context):
        user = self._auth(request.email, context)
        if not user:
            return create_empty_quota_response(request.email)

        used = user['used_bytes']
        total = user['quota_bytes']
        percentage = (used / total) * 100

        return pb.QuotaResponse(
            email=request.email,
            total_quota_bytes=total,
            used_storage_bytes=used,
            percentage_used=percentage
        )

    def SimulateFileUpload(self, request, context):
        user = self._auth(request.email, context)
        if not user:
            return create_file_transfer_response(False, "Authentication required.")

        if user['used_bytes'] + request.file_size_bytes > user['quota_bytes']:
            context.set_code(grpc.StatusCode.RESOURCE_EXHAUSTED)
            return create_file_transfer_response(False, "Quota exceeded.", user['used_bytes'])

        user['used_bytes'] += request.file_size_bytes

        return create_file_transfer_response(
            True,
            "Upload successful",
            user['used_bytes']
        )

    def SimulateFileDownload(self, request, context):
        user = self._auth(request.email, context)
        if not user:
            return create_file_transfer_response(False, "Authentication required.")

        return create_file_transfer_response(
            True,
            "Download successful",
            user['used_bytes']
        )



class CalculatorServicer(pb_grpc.CalculatorServiceServicer):

    def Calculate(self, request, context):
        user = utils.USER_DATA_DB.get(request.email)

        if not user or not user['is_verified']:
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            return create_calc_error_response("Authentication required.")

        n1, n2 = request.number1, request.number2
        op = request.operation.upper()

        if op == "ADD":
            result = n1 + n2
        elif op == "SUB":
            result = n1 - n2
        elif op == "MUL":
            result = n1 * n2
        elif op == "DIV":
            if n2 == 0:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                return create_calc_error_response("Division by zero.")
            result = n1 / n2
        else:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return create_calc_error_response("Invalid operation.")

        return pb.CalculationResponse(result=result, message="Success")



def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    pb_grpc.add_EnrollmentServiceServicer_to_server(EnrollmentServicer(), server)
    pb_grpc.add_UserServiceServicer_to_server(UserServicer(), server)
    pb_grpc.add_StorageServiceServicer_to_server(StorageServicer(), server)
    pb_grpc.add_CalculatorServiceServicer_to_server(CalculatorServicer(), server)

    server.add_insecure_port(SERVER_PORT)
    server.start()
    print(" Cloud Server Running on port 50051")

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)
        print(" Server stopped.")


if __name__ == "__main__":
    serve()
