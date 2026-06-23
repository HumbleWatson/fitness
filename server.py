import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

DB_PATH = os.path.join(os.path.dirname(__file__), "fitness.db")
SECRET_KEY = secrets.token_hex(32)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            data TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, date)
        )
    """)
    conn.commit()
    conn.close()

init_db()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_token(token: str) -> Optional[int]:
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        user_id, exp, signature = parts
        exp_time = datetime.fromtimestamp(int(exp))
        if datetime.now() > exp_time:
            return None
        expected = hashlib.sha256(f"{user_id}:{exp}:{SECRET_KEY}".encode()).hexdigest()[:16]
        if signature != expected:
            return None
        return int(user_id)
    except:
        return None

def create_token(user_id: int) -> str:
    exp = int((datetime.now() + timedelta(days=30)).timestamp())
    signature = hashlib.sha256(f"{user_id}:{exp}:{SECRET_KEY}".encode()).hexdigest()[:16]
    return f"{user_id}:{exp}:{signature}"

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization.replace("Bearer ", "")
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="登录已过期")
    return user_id

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class SyncRequest(BaseModel):
    data: dict
    last_sync: Optional[str] = None

@app.post("/api/register")
def register(req: RegisterRequest):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (req.username, hash_password(req.password))
        )
        conn.commit()
        user = conn.execute("SELECT id FROM users WHERE username = ?", (req.username,)).fetchone()
        token = create_token(user["id"])
        return {"token": token, "username": req.username}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="用户名已存在")
    finally:
        conn.close()

@app.post("/api/login")
def login(req: LoginRequest):
    conn = get_db()
    user = conn.execute(
        "SELECT id FROM users WHERE username = ? AND password_hash = ?",
        (req.username, hash_password(req.password))
    ).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(user["id"])
    return {"token": token, "username": req.username}

@app.get("/api/records")
def get_records(user_id: int = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT date, data FROM records WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()
    result = {}
    for row in rows:
        result[row["date"]] = json.loads(row["data"])
    return {"data": result}

@app.post("/api/sync")
def sync_records(req: SyncRequest, user_id: int = Depends(get_current_user)):
    conn = get_db()
    for date, exercises in req.data.items():
        conn.execute(
            """INSERT INTO records (user_id, date, data, updated_at) 
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, date) 
               DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at""",
            (user_id, date, json.dumps(exercises), datetime.now().isoformat())
        )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/api/records/{date}")
def delete_record(date: str, user_id: int = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM records WHERE user_id = ? AND date = ?", (user_id, date))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/manifest.json")
def manifest():
    return FileResponse(os.path.join(os.path.dirname(__file__), "manifest.json"))

@app.get("/sw.js")
def service_worker():
    return FileResponse(os.path.join(os.path.dirname(__file__), "sw.js"))

app.mount("/", StaticFiles(directory=os.path.dirname(__file__), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    ssl_cert = os.path.join(os.path.dirname(__file__), "cert.pem")
    ssl_key = os.path.join(os.path.dirname(__file__), "key.pem")
    uvicorn.run(app, host="0.0.0.0", port=8080, ssl_certfile=ssl_cert, ssl_keyfile=ssl_key)
