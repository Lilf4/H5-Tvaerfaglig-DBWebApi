from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from .models import *

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

@app.get("/")
def read_root():
    return {"message": "API running"}

#pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")