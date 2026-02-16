from dataclasses import dataclass

@dataclass
class User:
    name: str = None
    username: str = None
    password: str = None
    role_id: int = -1