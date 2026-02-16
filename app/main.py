from fastapi import FastAPI, Depends
from fastapi.params import Body, Header
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from .models import *
from .security import *
from .requestmodels import *

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    seed_defaults(db)
finally:
    db.close()

app = FastAPI()

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

        return {"message": "Login successful", "user_id": user.id, "session_token": session.session_token}
    return {"message": "Invalid username or password"}, 401

@app.post("/user")
def user_create(session_token: str = Body(...), user: User = Body(...), db: Session = Depends(get_db)):
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
        log(f"User with id \"{new_user.id}\", was created", request_user.id, db)
        return {"message": "Creation Successful"}, 201
    else:
        return {"message": "Invalid session"}, 401

@app.put("/user")
def user_update(session_token: str = Body(...), user_id: int = Body(...), user: User = Body(None), db: Session = Depends(get_db)):
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
        log(f"User with id \"{user_id}\", was updated", request_user.id, db)
        return {"message": "User updated successfully"}
    else:
        return {"message": "Invalid session"}, 401

@app.delete("/user")
def user_delete(session_token: str = Header(...), user_id: int = Header(...), db: Session = Depends(get_db)):
    request_user = validate_session(session_token, db)
    if request_user:
        if request_user.role.role != 'leder':
            return {"message": "Invalid Permissions"}, 403
        user_to_delete = db.query(Users).filter(Users.id == user_id).first()
        if not user_to_delete:
            return {"message": "User not found"}, 404
        db.delete(user_to_delete)
        db.commit()
        log(f"User with id \"{user_id}\", was deleted", request_user.id, db)
        return {"message": "User deleted successfully"}, 200
    else:
        return {"message": "Session token is required"}, 400

@app.get("/user")
def user_get(session_token: str = Header(None), user_id: int = Header(...), db: Session = Depends(get_db)):
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
    }}


@app.get("/users")
def users_get(session_token: str = Header(None), amount: int = Header(10), page: int = Header(1), db: Session = Depends(get_db)):
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
    return {"message": "Succesfully got users", "users": users_list}




def log(event: str, user_id: int, db: Session):
    new_log = Logs(
        event=event,
        user_id=user_id
    )
    db.add(new_log)
    db.commit()