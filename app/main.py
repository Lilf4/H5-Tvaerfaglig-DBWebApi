from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from .models import *
from .password import *

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

@app.post("/login")
def login():
    pass

@app.post("/user")
def user_create():
    pass

@app.put("/user")
def user_update():
    pass

@app.delete("/user")
def user_delete():
	pass

@app.get("/user")
def user_get():
	pass