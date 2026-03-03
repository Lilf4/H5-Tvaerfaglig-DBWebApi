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
    weekDay: int|None = -1
    startTime: time|None = None
    endTime: time|None = None
    user_id: int|None = -1
    inactive: bool|None = None

@dataclass
class Request:
    reason: str|None = None
    startDay: datetime|None = None
    endDay: datetime|None = None
    type_id: int|None = -1
    user_id: int|None = -1

@dataclass
class Process_Request:
    request_id: int = -1
    accepted: bool = None
    reason: str|None = None