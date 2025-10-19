# models.py
from typing import Tuple

# Global state variables
INITIAL_LENGTH = 50.0  # state variable for cable length

# NOTE: These variables are shared across the application.
CABLE_REMAINING = INITIAL_LENGTH
LAST_POSITION_ECI: Tuple[float, float] = (0.0, 0.0)

# Placeholder for modules not provided in the prompt
class circesoft_pb2:
    """Mock Protobuf class to represent the client status message."""
    class CurrentStatus:
        def __init__(self, **kwargs):
            self.reportedPosition = type('Pos', (object,), {'X_ECI': 0, 'Y_ECI': 0, 'Z_ECI': 0})
            self.reportedVelocity = type('Vel', (object,), {'Vx_ECI': 0, 'Vy_ECI': 0, 'Vz_ECI': 0})
            self.reportedHeading = 0
            self.reportedCableRemaining_m = 0
            self.reportedPercentBatteryRemaining = 0
            self.errorCode = 0
            self.cableDispenseStatus = 0
            self.cableDispenseCommand = 0
            self.SequenceNum = kwargs.get('SequenceNum', 0)
            self.isMoving = kwargs.get('isMoving', False)