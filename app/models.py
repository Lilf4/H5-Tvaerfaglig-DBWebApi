from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from datetime import datetime, timedelta

class Base(DeclarativeBase):
	pass

class Roles(Base):
	__tablename__ = "roles"
	
	##Table Fields
	id: Mapped[int] = mapped_column(primary_key=True)
	role: Mapped[str] = mapped_column(String(50))
	users: Mapped[list["Users"]] = relationship(back_populates="role")

class Users(Base):
	__tablename__ = "users"

	##Table Fields
	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(255))
	role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
	role: Mapped["Roles"] = relationship(back_populates="users")
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now()
	)
	hashed_pass: Mapped[str] = mapped_column(String(255))

class Sessions(Base):
	__tablename__ = "sessions"
	
	id: Mapped[int] = mapped_column(primary_key=True)
	session_token: Mapped[str] = mapped_column(String(32))
	activeUntill: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		default=lambda: datetime.utcnow() + timedelta(days=1),
		server_default=text("NOW() + INTERVAL '1 day'")
	)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


  
class Scheduled_Times(Base):
	__tablename__ = "scheduled_times"

	id: Mapped[int] = mapped_column(primary_key=True)
	weekDay: Mapped[int] = mapped_column(Integer())
	startTime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
	duration: Mapped[int] = mapped_column(Integer())
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


	inactive: Mapped[bool] = mapped_column(Boolean())


class Worked_Times(Base):
	__tablename__ = "worked_times"

	id: Mapped[int] = mapped_column(primary_key=True)
	actualDate: Mapped[datetime] = mapped_column()
	weekDay: Mapped[int] = mapped_column(Integer())
	
	actualStart: Mapped[datetime] = mapped_column(DateTime(timezone=True))
	actualDuration: Mapped[int] = mapped_column(Integer())
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

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

class Request_Types(Base):
	__tablename__ = "request_types"

	id: Mapped[int] = mapped_column(primary_key=True)
	type_name: Mapped[str] = mapped_column(String(500))

class Requests(Base):
	__tablename__ = "requests"

	id: Mapped[int] = mapped_column(primary_key=True)
	reason: Mapped[str] = mapped_column(String(500))
	weekDay: Mapped[int] = mapped_column(Integer())
	startTime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
	duration: Mapped[int] = mapped_column(Integer())
	type_id: Mapped[int] = mapped_column(ForeignKey("request_types.id"))
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
	requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

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