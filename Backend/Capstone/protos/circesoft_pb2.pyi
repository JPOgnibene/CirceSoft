from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CurrentStatus(_message.Message):
    __slots__ = ["SequenceNum", "cableDispenseCommand", "cableDispenseStatus", "errorCode", "reportedCableRemaining_m", "reportedHeading", "reportedPercentBatteryRemaining", "reportedPosition", "reportedVelocity"]
    CABLEDISPENSECOMMAND_FIELD_NUMBER: _ClassVar[int]
    CABLEDISPENSESTATUS_FIELD_NUMBER: _ClassVar[int]
    ERRORCODE_FIELD_NUMBER: _ClassVar[int]
    REPORTEDCABLEREMAINING_M_FIELD_NUMBER: _ClassVar[int]
    REPORTEDHEADING_FIELD_NUMBER: _ClassVar[int]
    REPORTEDPERCENTBATTERYREMAINING_FIELD_NUMBER: _ClassVar[int]
    REPORTEDPOSITION_FIELD_NUMBER: _ClassVar[int]
    REPORTEDVELOCITY_FIELD_NUMBER: _ClassVar[int]
    SEQUENCENUM_FIELD_NUMBER: _ClassVar[int]
    SequenceNum: int
    cableDispenseCommand: str
    cableDispenseStatus: str
    errorCode: int
    reportedCableRemaining_m: float
    reportedHeading: float
    reportedPercentBatteryRemaining: float
    reportedPosition: PositionECI
    reportedVelocity: VelocityECI
    def __init__(self, reportedPosition: _Optional[_Union[PositionECI, _Mapping]] = ..., reportedVelocity: _Optional[_Union[VelocityECI, _Mapping]] = ..., reportedHeading: _Optional[float] = ..., reportedCableRemaining_m: _Optional[float] = ..., reportedPercentBatteryRemaining: _Optional[float] = ..., errorCode: _Optional[int] = ..., cableDispenseStatus: _Optional[str] = ..., cableDispenseCommand: _Optional[str] = ..., SequenceNum: _Optional[int] = ...) -> None: ...

class PositionECI(_message.Message):
    __slots__ = ["X_ECI", "Y_ECI", "Z_ECI"]
    X_ECI: float
    X_ECI_FIELD_NUMBER: _ClassVar[int]
    Y_ECI: float
    Y_ECI_FIELD_NUMBER: _ClassVar[int]
    Z_ECI: float
    Z_ECI_FIELD_NUMBER: _ClassVar[int]
    def __init__(self, X_ECI: _Optional[float] = ..., Y_ECI: _Optional[float] = ..., Z_ECI: _Optional[float] = ...) -> None: ...

class VelocityECI(_message.Message):
    __slots__ = ["Vx_ECI", "Vy_ECI", "Vz_ECI"]
    VX_ECI_FIELD_NUMBER: _ClassVar[int]
    VY_ECI_FIELD_NUMBER: _ClassVar[int]
    VZ_ECI_FIELD_NUMBER: _ClassVar[int]
    Vx_ECI: float
    Vy_ECI: float
    Vz_ECI: float
    def __init__(self, Vx_ECI: _Optional[float] = ..., Vy_ECI: _Optional[float] = ..., Vz_ECI: _Optional[float] = ...) -> None: ...
