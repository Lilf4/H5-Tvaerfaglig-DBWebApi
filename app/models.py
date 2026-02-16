import random 
import string
from datetime import timezone
from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime, func, Date, Time, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timedelta
from .database import Base
from .security import *

class Roles(Base):
	__tablename__ = "roles"
	
	##Table Fields
	id: Mapped[int] = mapped_column(primary_key=True)
	role: Mapped[str] = mapped_column(String(50), unique=True)
	users: Mapped[list["Users"]] = relationship(back_populates="role")

class Users(Base):
	__tablename__ = "users"

	##Table Fields
	id: Mapped[int] = mapped_column(primary_key=True)
	username: Mapped[str] = mapped_column(String(32), unique=True)
	name: Mapped[str] = mapped_column(String(255))
	role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	hashed_pass: Mapped[str] = mapped_column(String(255))

	role: Mapped["Roles"] = relationship(back_populates="users")
	sessions: Mapped[list["Sessions"]] = relationship(back_populates="user", cascade="all, delete-orphan")
	scheduled_times: Mapped[list["Scheduled_Times"]] = relationship(back_populates="user")
	worked_times: Mapped[list["Worked_Times"]] = relationship(back_populates="user")
	logs: Mapped[list["Logs"]] = relationship(back_populates="user")

	requests: Mapped[list["Requests"]] = relationship(
		back_populates="user",
		foreign_keys="Requests.user_id"
	)

	requested_requests: Mapped[list["Requests"]] = relationship(
		back_populates="requester",
		foreign_keys="Requests.requested_by"
	)

	processed_requests: Mapped[list["Processed_Requests"]] = relationship(
		back_populates="admin",
		foreign_keys="Processed_Requests.admin_id"
	)

class Sessions(Base):
	__tablename__ = "sessions"
	
	id: Mapped[int] = mapped_column(primary_key=True)
	session_token: Mapped[str] = mapped_column(String(32), default=lambda: ''.join(random.choices(string.ascii_letters + string.digits, k=32)))
	activeUntil: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		default=lambda: datetime.now(timezone.utc) + timedelta(days=1),
		nullable=False
	)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
	user: Mapped["Users"] = relationship(back_populates="sessions")


  
class Scheduled_Times(Base):
	__tablename__ = "scheduled_times"

	id: Mapped[int] = mapped_column(primary_key=True)
	weekDay: Mapped[int] = mapped_column(Integer())
	startTime: Mapped[datetime.time] = mapped_column(Time())
	duration: Mapped[int] = mapped_column(Integer())
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
	user: Mapped["Users"] = relationship(back_populates="scheduled_times")

	inactive: Mapped[bool] = mapped_column(Boolean())


class Worked_Times(Base):
	__tablename__ = "worked_times"

	id: Mapped[int] = mapped_column(primary_key=True)
	actualDate: Mapped[datetime.date] = mapped_column(Date())
	weekDay: Mapped[int] = mapped_column(Integer())
	
	actualStart: Mapped[datetime.time] = mapped_column(Time())
	actualDuration: Mapped[int] = mapped_column(Integer())
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
	user: Mapped["Users"] = relationship(back_populates="worked_times")

	note: Mapped[str] = mapped_column(String(500))

class Logs(Base):
	__tablename__ = "logs"

	id: Mapped[int] = mapped_column(primary_key=True)
	event: Mapped[str] = mapped_column(String(500))
	time: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now()
	)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
	user: Mapped["Users"] = relationship(back_populates="logs")

class Request_Types(Base):
	__tablename__ = "request_types"

	id: Mapped[int] = mapped_column(primary_key=True)
	type_name: Mapped[str] = mapped_column(String(500), unique=True)
	requests: Mapped[list["Requests"]] = relationship(back_populates="type")

class Requests(Base):
	__tablename__ = "requests"

	id: Mapped[int] = mapped_column(primary_key=True)
	reason: Mapped[str] = mapped_column(String(500))
	weekDay: Mapped[int] = mapped_column(Integer())
	startTime: Mapped[datetime.time] = mapped_column(Time())
	duration: Mapped[int] = mapped_column(Integer())
	type_id: Mapped[int] = mapped_column(ForeignKey("request_types.id"))
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
	requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
	type: Mapped["Request_Types"] = relationship(back_populates="requests")

	user: Mapped["Users"] = relationship(
		back_populates="requests",
		foreign_keys=[user_id]
	)

	requester: Mapped["Users"] = relationship(
		back_populates="requested_requests",
		foreign_keys=[requested_by]
	)

	processed_request: Mapped["Processed_Requests"] = relationship(
		back_populates="request",
		uselist=False
	)
	

class Processed_Requests(Base):
	__tablename__ = "processed_requests"

	id: Mapped[int] = mapped_column(primary_key=True)

	request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
	accepted: Mapped[bool] = mapped_column(Boolean())
	reason: Mapped[str] = mapped_column(String(500))
	processed_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now()
	)
	admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

	request: Mapped["Requests"] = relationship(back_populates="processed_request")

	admin: Mapped["Users"] = relationship(
		back_populates="processed_requests",
		foreign_keys=[admin_id]
	)


def seed_defaults(session):
	# Roles
	existing_roles = session.execute(select(Roles)).scalars().all()
	if not existing_roles:
		session.add_all([
			Roles(role="leder"),
			Roles(role="medarbejder"),
		])
	session.commit()

	# Request Types
	existing_types = session.execute(select(Request_Types)).scalars().all()
	if not existing_types:
		session.add_all([
			Request_Types(type_name="ferie"),
			Request_Types(type_name="sygdom"),
			Request_Types(type_name="overtid"),
		])
	session.commit()
	
	existing_users = session.execute(select(Users)).scalars().all()
	if not existing_users:
		role_leder = session.execute(select(Roles).where(Roles.role == "leder")).scalars().first()

		session.add_all([
			Users(username="Admin", name="Admin", role=role_leder, hashed_pass=get_password_hash("1234"))
		])

	session.commit()