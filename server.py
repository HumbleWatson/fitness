import os
import json
import sqlite3
import hashlib
import secrets
import requests as http_requests
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

DB_PATH = os.path.join(os.path.dirname(__file__), "fitness.db")
SECRET_FILE = os.path.join(os.path.dirname(__file__), ".secret")
if os.path.exists(SECRET_FILE):
    with open(SECRET_FILE) as f:
        SECRET_KEY = f.read().strip()
    if not SECRET_KEY:
        SECRET_KEY = secrets.token_hex(32)
        with open(SECRET_FILE, "w") as f:
            f.write(SECRET_KEY)
else:
    SECRET_KEY = secrets.token_hex(32)
    with open(SECRET_FILE, "w") as f:
        f.write(SECRET_KEY)

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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS diet_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            meals TEXT NOT NULL DEFAULT '[]',
            raw_text TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, date)
        )
    """)
    conn.commit()
    conn.close()

init_db()

def migrate_profile():
    conn = get_db()
    for col in ["height", "weight", "goal"]:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
        except:
            pass
    conn.commit()
    conn.close()

migrate_profile()

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

class ProfileRequest(BaseModel):
    height: Optional[float] = None
    weight: Optional[float] = None
    goal: Optional[str] = None

class DietRequest(BaseModel):
    meals: str = "[]"
    raw_text: str = ""

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

@app.get("/api/profile")
def get_profile(user_id: int = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT height, weight, goal FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return {"height": row["height"], "weight": row["weight"], "goal": row["goal"]}

@app.put("/api/profile")
def update_profile(req: ProfileRequest, user_id: int = Depends(get_current_user)):
    conn = get_db()
    updates = {}
    if req.height is not None: updates["height"] = req.height
    if req.weight is not None: updates["weight"] = req.weight
    if req.goal is not None: updates["goal"] = req.goal
    if updates:
        sets = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE users SET {sets} WHERE id=?", list(updates.values()) + [user_id])
        conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/diet/{date}")
def get_diet(date: str, user_id: int = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute(
        "SELECT meals, raw_text FROM diet_records WHERE user_id=? AND date=?",
        (user_id, date)
    ).fetchone()
    conn.close()
    if row:
        return {"date": date, "meals": json.loads(row["meals"]), "raw_text": row["raw_text"]}
    return {"date": date, "meals": [], "raw_text": ""}

@app.put("/api/diet/{date}")
def save_diet(date: str, req: DietRequest, user_id: int = Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        """INSERT INTO diet_records (user_id, date, meals, raw_text, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_id, date)
           DO UPDATE SET meals=excluded.meals, raw_text=excluded.raw_text, updated_at=excluded.updated_at""",
        (user_id, date, req.meals, req.raw_text, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

AI_BASE = "http://localhost:20128/v1/chat/completions"
AI_MODEL = "auto/best-fast"

SYSTEM_PROMPTS = {
    "parse": "你是一个营养分析助手。用户会输入食物名称和份量，请返回JSON数组，每项包含 name(中文名), weight_g(克), calories(千卡), protein_g, fat_g, carbs_g。只返回JSON，不要其他文字。如果无法识别某食物，返回 {\"unknown\": true, \"name\": \"...\"}。",
    "analyze": "你是一个健身与营养顾问。根据用户的饮食数据和身体数据，给出分析和建议，包括：热量是否达标、碳蛋脂比例是否合理、改进建议。语气专业但友好，200字以内。",
    "chat": "你是一个健身与营养顾问，回答用户关于训练、饮食、恢复等全部健身话题的问题。基于科学依据给出建议，语气友好专业。"
}

class AIRequest(BaseModel):
    messages: list

@app.post("/api/diet/{action}")
def diet_ai(action: str, req: AIRequest, user_id: int = Depends(get_current_user)):
    if action not in SYSTEM_PROMPTS:
        raise HTTPException(status_code=404)
    system_prompt = SYSTEM_PROMPTS[action]
    payload = {
        "model": AI_MODEL,
        "messages": [{"role": "system", "content": system_prompt}] + req.messages,
        "temperature": 0.7
    }
    try:
        resp = http_requests.post(AI_BASE, json=payload, timeout=30)
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用: {str(e)}")

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
    uvicorn.run(app, host="127.0.0.1", port=8080, ssl_certfile=ssl_cert, ssl_keyfile=ssl_key)
