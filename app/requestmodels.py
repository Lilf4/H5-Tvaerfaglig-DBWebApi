from dataclasses import dataclass
from datetime import datetime, time

@dataclass
class User:
    name: str|None = None
    username: str|None = None
    password: str|None = None
    role_id: int = -1


@dataclass
class Schedule_Times:
    weekDay: int = -1
    startTime: time = None
    endTime: time = None
    user_id: int = -1
    inactive: bool = None

@dataclass
class Request:
    reason: str|None = None
    startDay: datetime = None
    endDay: datetime = None
    type_id: int = -1
    user_id: int = -1

@dataclass
class Process_Request:
    request_id: int = -1
    accepted: bool = None
    reason: str|None = None