import cloud_system_pb2 as pb


def create_empty_quota_response(email):
    return pb.QuotaResponse(
        email=email,
        total_quota_bytes=0,
        used_storage_bytes=0,
        percentage_used=0.0
    )


def create_calc_error_response(msg):
    return pb.CalculationResponse(result=0.0, message=msg)


def create_file_transfer_response(success, message, new_used_bytes=0):
    return pb.FileTransferResponse(
        success=success,
        message=message,
        new_used_bytes=new_used_bytes
    )
