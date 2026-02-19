import asyncio, random, string
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.params import Body, Header, Path
from sqlalchemy import delete
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from .models import *
from .security import *
from .requestmodels import *
from sqlalchemy import or_
Base.metadata.create_all(bind=engine)

LastCheckInCode: str = None
GenTime: datetime = None
MinBufferTime: int = 1
CurrCheckInCode: str = None

db = SessionLocal()
try:
    seed_defaults(db)
finally:
    db.close()



@asynccontextmanager
async def lifespan(app: FastAPI):
    async def periodic_cleanup():
        while True:
            db = SessionLocal()
            try:
                db.execute(
                    delete(Sessions).where(
                        Sessions.activeUntil < datetime.now(timezone.utc)
                    )
                )
                db.commit()
            finally:
                db.close()
            await asyncio.sleep(60)  #3600 every hour

    async def gen_check_in():
        while True:
            gen_check_in_code()
            await asyncio.sleep(60)  #3600 every hour
    task = asyncio.create_task(periodic_cleanup())
    task = asyncio.create_task(gen_check_in())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def validate_session(session_token: str, db: Session):
    session = db.query(Sessions).filter(Sessions.session_token == session_token).first()
    if session:
        if session.activeUntil.tzinfo is None:
            session.activeUntil = session.activeUntil.replace(tzinfo=timezone.utc)
        if session.activeUntil > datetime.now(timezone.utc):
            return session.user
        else:
            db.delete(session)
            return None
    else:
        return None

@app.get("/")
def read_root():
    return {"message": "API running"}

@app.post("/login")
def login(username: str = Body(...), password: str = Body(...), db: Session = Depends(get_db)):

    user = db.query(Users).filter(Users.username == username).first()
    if user and verify_password(password, user.hashed_pass):
        session = Sessions(user=user)
        db.add(session)
        db.commit()
        db.refresh(session)
        log(f"User logged in", user.id, db)

        return {"message": "Login successful", "user_id": user.id, "session_token": session.session_token}, 200
    return {"message": "Invalid username or password"}, 401

@app.post("/logout")
def logout(session_token: str = Header(...), db: Session = Depends(get_db)):
    session = db.query(Sessions).filter(Sessions.session_token == session_token).first()
    if session:
        log("User logged out", session.user.id, db)
        db.delete(session)
        db.commit()
        return {"message": "Successfully logged out"}, 200
    else:
        return {"message": "Invalid session token"}, 401

@app.post("/user")
def user_create(session_token: str = Header(...), user: User = Body(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if request_user:
        if request_user.role.role != 'leder':
            return {"message": "Invalid Permissions"}, 403
        new_user = Users(username=user.username, name=user.name, hashed_pass=get_password_hash(user.password), role_id=user.role_id)
        try:
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
        except Exception:
            return {"message": "User already exists"}, 400
        log(f"User with id \"{new_user.id}\" was created", request_user.id, db)
        return {"message": "Creation Successful"}, 201
    else:
        return {"message": "Invalid session"}, 401

@app.put("/user/{user_id}")
def user_update(session_token: str = Header(...), user_id: int = Path(...), user: User = Body(None), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if request_user:
        if request_user.role.role != 'leder' and request_user.id != user_id:
            return {"message": "Invalid Permissions"}, 403
        user_to_update = db.query(Users).filter(Users.id == user_id).first()
        if not user_to_update: return {"message": "Couldn't find user"}, 404
        if user.name:
            user_to_update.name = user.name
        if user.username:
            user_to_update.username = user.username
        if user.password:
            user_to_update.hashed_pass = get_password_hash(user.password)
        if user.role_id != -1 and request_user.role.role == 'leder':
            user_to_update.role_id = user.role_id
        db.commit()
        log(f"User with id \"{user_id}\" was updated", request_user.id, db)
        return {"message": "User updated successfully"}, 200
    else:
        return {"message": "Invalid session"}, 401

@app.delete("/user/{user_id}")
def user_delete(session_token: str = Header(...), user_id: int = Path(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if request_user:
        if request_user.role.role != 'leder':
            return {"message": "Invalid Permissions"}, 403
        user_to_delete = db.query(Users).filter(Users.id == user_id).first()
        if not user_to_delete:
            return {"message": "User not found"}, 404
        db.delete(user_to_delete)
        db.commit()
        log(f"User with id \"{user_id}\" was deleted", request_user.id, db)
        return {"message": "User deleted successfully"}, 200
    else:
        return {"message": "Session token is required"}, 400

@app.get("/user/{user_id}")
def user_get(session_token: str = Header(None), user_id: int = Path(...), db: Session = Depends(get_db)):
    request_user = None
    if session_token:
        request_user = validate_session(session_token, db)
    user_to_get = db.query(Users).filter(Users.id == user_id).first()
    if not user_to_get: return {"message": "User not found"}, 404
    return {"message": "Succesfully got user", "user": {
        "id": user_to_get.id, 
        "username": user_to_get.username, 
        "name": user_to_get.name if (request_user and (request_user.role.role == 'leder' or user_to_get.id == request_user.id)) else None,
        "role": user_to_get.role, 
    }}, 200


@app.get("/users/")
def users_get(session_token: str = Header(None), amount: int = 10, page: int = 1, db: Session = Depends(get_db)):
    request_user = None
    if session_token:
        request_user = validate_session(session_token, db)
    user_to_get = db.query(Users).offset((page - 1) * amount).limit(amount).all()
    if not user_to_get: return {"message": "User not found"}, 404
    users_list = [
        {
            "id": user.id, 
            "username": user.username, 
            "name": user.name if (request_user and (request_user.role.role == 'leder' or user.id == request_user.id)) else None,
            "role": user.role, 
        } for user in user_to_get]
    return {"message": "Succesfully got users", "users": users_list}, 200

@app.post("/scheduled_time")
def scheduled_time_create(session_token: str = Header(...), schedule: Schedule_Times = Body(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    if not request_user.role.role == 'leder': return {"message": "Invalid Permissions"}, 401
    new_schedule = Scheduled_Times(
        weekDay=schedule.weekDay,
        startTime=schedule.startTime,
        endTime=schedule.endTime,
        inactive=schedule.inactive,
        user_id=schedule.user_id,
    )
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    log(f"Schedule with id \"{new_schedule.id}\" was created", request_user.id, db)
    return {"message": "Successfully created schedule"}, 201

@app.get("/scheduled_time/{schedule_id}")
def schedule_time_get(session_token: str = Header(...), schedule_id: int = Path(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    schedule = db.query(Scheduled_Times).filter(Scheduled_Times.id == schedule_id).first()
    if not request_user: return {"message": "Invalid session"}, 400
    if not request_user.role.role == 'leder' and (not request_user.role.role == 'leder' and not request_user.id == schedule.user_id): return {"message": "Invalid Permissions"}, 401
    scheduled_time = db.query(Scheduled_Times).filter(Scheduled_Times.id == schedule_id).first()
    return {"message": "Succesfully got schedules", "schedules": scheduled_time}

@app.get("/scheduled_times/{user_id}")
def schedule_times_get(session_token: str = Header(...), user_id: int = Path(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    if not request_user.role.role == 'leder' and (not request_user.role.role == 'leder' and not request_user.id == user_id): return {"message": "Invalid Permissions"}, 401
    scheduled_times = db.query(Scheduled_Times).filter(Scheduled_Times.user_id == user_id).all()
    return {"message": "Succesfully got schedules", "schedules": scheduled_times}


@app.put("/scheduled_time/{schedule_id}")
def scheduled_time_update(session_token: str = Header(...), schedule_id: int = Path(...), schedule: Schedule_Times = Body(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    if not request_user.role.role == 'leder': return {"message": "Invalid Permissions"}, 401
    schedule_to_update = db.query(Scheduled_Times).filter(Scheduled_Times.id == schedule_id).first()
    if not schedule_to_update: return {"message": "Couldn't find schedule"}, 404
    if schedule.weekDay != -1: schedule_to_update.weekDay = schedule.weekDay
    if schedule.endTime: schedule_to_update.endTime = schedule.endTime
    if schedule.startTime: schedule_to_update.weekDay = schedule.weekDay
    if schedule.user_id != -1: schedule_to_update.user_id = schedule.user_id
    if schedule.inactive != None: schedule_to_update.inactive = schedule.inactive
    db.commit()
    log(f"Schedule with id \"{schedule_to_update.id}\" was updated", request_user.id, db)
    return {"Sucessfully updated schedule"}, 200

@app.delete("/scheduled_time/{schedule_id}")
def scheduled_time_delete(session_token: str = Header(...), schedule_id: int = Path(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    if not request_user.role.role == 'leder': return {"message": "Invalid Permissions"}, 401
    schedule_to_update = db.query(Scheduled_Times).filter(Scheduled_Times.id == schedule_id).first()
    if not schedule_to_update: return {"message": "Couldn't find schedule"}, 404
    log(f"Schedule with id \"{schedule_to_update.id}\" was deleted", request_user.id, db)
    db.delete(schedule_to_update)
    db.commit()
    return {"Sucessfully deleted schedule"}, 200

@app.post("/check_in_device/{device_name}")
def check_in_device_create(session_token: str = Header(...), device_name: str = Path(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    if not request_user.role.role == 'leder': return {"message": "Invalid Permissions"}, 401
    check_in_device = CheckinDeviceCode(name=device_name)
    db.add(check_in_device)
    log(f"Created device with id \"{check_in_device.id}\"", request_user.id, db)
    return {"message": "Succesfully created device"}, 201

@app.get("/check_in_device/{device_id}")
def check_in_device_get(session_token: str = Header(...), device_id: int = Path(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    if not request_user.role.role == 'leder': return {"message": "Invalid Permissions"}, 401
    check_in_device_to_get = db.query(CheckinDeviceCode).filter(CheckinDeviceCode.id == device_id).first()
    if not check_in_device_to_get: return {"message": "Device not found"}, 404
    return {"message": "Sucessfully got device", "device": check_in_device_to_get}, 200

@app.get("/check_in_devices")
def check_in_devices_get(session_token: str = Header(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    if not request_user.role.role == 'leder': return {"message": "Invalid Permissions"}, 401
    check_in_devices_to_get = db.query(CheckinDeviceCode).all()
    if not check_in_devices_to_get: return {"message": "No devices found"}, 404
    return {"message": "Sucessfully got devices", "device": check_in_devices_to_get}, 200

@app.delete("/check_in_device")
def check_in_device_delete(session_token: str = Header(...), device_id: int = Body(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    if not request_user.role.role == 'leder': return {"message": "Invalid Permissions"}, 401
    check_in_device_to_get = db.query(CheckinDeviceCode).filter(CheckinDeviceCode.id == device_id).first()
    if not check_in_device_to_get: return {"message": "Device not found"}, 404
    log(f"Device with id \"{check_in_device_to_get.id}\" was deleted", request_user.id, db)
    db.delete(check_in_device_to_get)
    db.commit()

@app.get("/check_in_code")
def check_out_code_get(device_code: str = Header(...), db: Session = Depends(get_db)):
    request_device = db.query(CheckinDeviceCode).filter(CheckinDeviceCode.code == device_code).first()
    if not request_device: return {"message": "Invalid device code"}, 400
    return {"message": "Sucessfully got check in code", "code": CurrCheckInCode}, 200

@app.post("/check_in_out")
def check_in(session_token: str = Header(...), check_in_code: str = Header(None), db: Session = Depends(get_db)):
    global LastCheckInCode, GenTime, CurrCheckInCode
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    if (check_in_code != CurrCheckInCode and not (check_in_code == LastCheckInCode and GenTime + timedelta(minutes=MinBufferTime) > datetime.now())):
        return {"message": "Invalid check in code"}, 400
    gen_check_in_code()
    gen_check_in_code()
    curr_work_time = db.query(Worked_Times).filter(
        (Worked_Times.user_id == request_user.id) & (Worked_Times.active == True)
    ).first()
    if not curr_work_time:
        new_work_time = Worked_Times(
            actualDate=datetime.now(),
            weekDay=datetime.now().weekday() + 1,
            actualStart=datetime.now().time(),
            actualEnd=None,
            user_id=request_user.id,
            note="",
            active=True
        )
        log(f"User has checked in", request_user.id, db)
        db.add(new_work_time)
        db.commit()
        return {"message": "Sucessfully checked in"}
    else:
        log(f"User has checked out", request_user.id, db)
        curr_work_time.actualEnd = datetime.now().time()
        curr_work_time.active=False
        db.commit()
        return {"message": "Sucessfully checked out"}

def gen_check_in_code():
    length = 16
    global LastCheckInCode, GenTime, CurrCheckInCode
    new_code = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    LastCheckInCode = CurrCheckInCode
    GenTime = datetime.now()
    CurrCheckInCode = new_code

@app.post("/request")
def request_create(session_token: str = Header(...), request: Request = Body(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    new_request = Requests(
        startDay=request.startDay,
        endDay=request.endDay,
        reason=request.reason,
        type_id=request.type_id,
        user_id=request.user_id,
        requested_by=request_user.id
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    log(f"Request with id \"{new_request.id}\" has been created", request_user.id, db)
    return {"message": "request sucessfully created"}, 201

@app.delete("/request/{request_id}")
def request_delete(session_token: str = Header(...), request_id: int = Path(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    request_to_delete = db.query(Requests).filter(Requests.id == request_id).first()
    if not request_to_delete: return {"message": "Couldn't find request"}, 404
    if not request_user.role.role == 'leder':
        if (not request_user.role.role == 'leder' and not request_user.id == request_to_delete.requested_by): 
            if (not request_user.role.role == 'leder' and not request_user.id == request_to_delete.user_id):
                return {"message": "Invalid Permissions"}, 401
    processed_request = db.query(Processed_Requests).filter(Processed_Requests.request_id == request_to_delete.id).first()
    if processed_request: return {"message": "Can't delete processed request"}, 405
    log(f"Request with id \"{request_to_delete.id}\" has been deleted", request_user.id, db)
    db.delete(request_to_delete)
    db.commit()
    return {"message": "Successfully deleted request"}, 200

@app.get("/request/{request_id}&{get_processed}")
def request_get(session_token: str = Header(...), request_id: int = Path(...), get_processed: bool = Path(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    request_to_get = None
    if get_processed:
        request_to_get = db.query(Requests).outerjoin(Processed_Requests).filter(Requests.id == request_id).first()
    else:
        request_to_get = db.query(Requests).outerjoin(Processed_Requests).filter((Processed_Requests.id.is_(None)) & Requests.id == request_id).first()
    if not request_to_get: return {"message": "Couldn't find request"}, 404
    if not request_user.role.role == 'leder':
        if (not request_user.role.role == 'leder' and not request_user.id == request_to_get.requested_by): 
            if (not request_user.role.role == 'leder' and not request_user.id == request_to_get.user_id):
                return {"message": "Invalid Permissions"}, 401
    return {"message": "Successfully got request", "request": request_to_get}, 200

@app.get("/requests/{user_id}&{get_processed}")
def user_requests_get(session_token: str = Header(...), user_id: int = Path(...), get_processed: bool = Path(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    requests_to_get = None
    if get_processed:
        requests_to_get = db.query(Requests).outerjoin(Processed_Requests).filter((Requests.user_id == user_id) & or_(or_(Requests.user_id == request_user.id, Requests.requested_by == request_user.id), request_user.role.role == 'leder')).all()
    else:
        requests_to_get = db.query(Requests).outerjoin(Processed_Requests).filter((Processed_Requests.id.is_(None)) & (Requests.user_id == user_id) & or_(or_(Requests.user_id == request_user.id, Requests.requested_by == request_user.id), request_user.role.role == 'leder')).all()
    if not requests_to_get: return {"message": "Couldn't find request"}, 404
    return {"message": "Successfully got requests", "requests": requests_to_get}, 200
    

@app.get("/requests/{get_processed}")
def requests_get(session_token: str = Header(...), get_processed: bool = Path(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    requests_to_get = None
    if get_processed:
        requests_to_get = db.query(Requests).outerjoin(Processed_Requests).filter(or_(or_(Requests.user_id == request_user.id, Requests.requested_by == request_user.id), request_user.role.role == 'leder')).all()
    else:
        requests_to_get = db.query(Requests).outerjoin(Processed_Requests).filter(Processed_Requests.id.is_(None) & or_(or_(Requests.user_id == request_user.id, Requests.requested_by == request_user.id), request_user.role.role == 'leder')).all()
    if not requests_to_get: return {"message": "Couldn't find request"}, 404

    return {"message": "Successfully got request", "request": requests_to_get}, 200
    

@app.post("/process_request")
def process_request(session_token: str = Header(...), process_request: Process_Request = Body(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    if not request_user.role.role == 'leder': return {"message": "Invalid Permissions"}, 401
    process_request_check = db.query(Processed_Requests).filter(Processed_Requests.request_id == process_request.request_id).first()
    if process_request_check: return {"message": "Cannot process already processed request"}, 400 
    processed_request = Processed_Requests(
        request_id=process_request.request_id,
        accepted=process_request.accepted,
        reason=process_request.reason,
        admin_id=request_user.id
    )
    db.add(processed_request)
    db.commit()
    db.refresh(processed_request)
    log(f"Request with id \"{processed_request}\" has been processed", request_user.id, db)
    return {"message": "Successfully processed request"}, 201

@app.get("/roles")
def roles_get(session_token: str = Header(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    roles = db.query(Roles).all()
    return {"message": "Successfully got roles", "roles": roles}, 200

@app.get("/request_types")
def request_types_get(session_token: str = Header(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if not request_user: return {"message": "Invalid session"}, 400
    request_types = db.query(Request_Types).all()
    return {"message": "Successfully got request types", "request_types": request_types}, 200

def log(event: str, user_id: int, db: Session):
    new_log = Logs(
        event=event,
        user_id=user_id
    )
    db.add(new_log)
    db.commit()