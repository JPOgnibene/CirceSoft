from protos import circesoft_pb2

# Parse protobuf bytes into a CurrentStatus message.
# Returns a CurrentStatus object; callers can read fields directly.

def handle_client_message(data: bytes) -> circesoft_pb2.CurrentStatus:
    msg = circesoft_pb2.CurrentStatus()
    msg.ParseFromString(data)
    return msg
