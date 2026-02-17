from dataclasses import dataclass
from datetime import datetime, time

@dataclass
class User:
    name: str = None
    username: str = None
    password: str = None
    role_id: int = -1


@dataclass
class Schedule_Times:
    weekDay: int = -1
    startTime: time = None
    endTime: time = None
    user_id: int = -1
    inactive: bool = False
