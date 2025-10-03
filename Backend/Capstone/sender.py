from protos import circesoft_pb2

# Build a CurrentStatus protobuf from a key=value file
# Unknown keys are ignored; missing values default to 0/empty.

def build_client_status_from_file(path: str) -> bytes:
    fields = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            fields[k.strip()] = v.strip()

    msg = circesoft_pb2.CurrentStatus()

    # Position
    msg.reportedPosition.X_ECI = float(fields.get("X_ECI", 0.0))
    msg.reportedPosition.Y_ECI = float(fields.get("Y_ECI", 0.0))
    msg.reportedPosition.Z_ECI = float(fields.get("Z_ECI", 0.0))

    # Velocity
    msg.reportedVelocity.Vx_ECI = float(fields.get("Vx_ECI", 0.0))
    msg.reportedVelocity.Vy_ECI = float(fields.get("Vy_ECI", 0.0))
    msg.reportedVelocity.Vz_ECI = float(fields.get("Vz_ECI", 0.0))

    # Scalars
    msg.reportedHeading = float(fields.get("Heading", 0.0))
    msg.reportedCableRemaining_m = float(fields.get("cableRemaining_m", 0.0))
    msg.reportedPercentBatteryRemaining = float(fields.get("percentBatteryRemaining", 0.0))

    msg.errorCode = int(fields.get("errorCode", 0))
    msg.cableDispenseStatus = fields.get("cableDispenseStatus", "")
    msg.cableDispenseCommand = fields.get("cableDispenseCommand", "")
    msg.SequenceNum = int(fields.get("SequenceNum", 0))

    return msg.SerializeToString()

