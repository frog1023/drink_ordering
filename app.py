import io
import json
import os
import secrets
import sqlite3
import logging
from pathlib import Path
from urllib.parse import quote

import qrcode
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from openai import OpenAI
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
MENU = json.loads((ROOT / "menu.json").read_text(encoding="utf-8"))
ITEMS = {x["id"]: x for x in MENU["items"]}
DB = ROOT / "orders.sqlite3"
app = FastAPI(title="主題餐飲 AI Agent")

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

with db() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, table_no TEXT, items TEXT, total INTEGER, note TEXT, status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP)")

class Chat(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[dict[str, str]] = Field(default_factory=list)

class Line(BaseModel):
    id: str
    quantity: int = Field(ge=1, le=20)
    sugar: str
    ice: str

class Order(BaseModel):
    table_no: str = Field(min_length=1, max_length=20)
    items: list[Line] = Field(min_length=1, max_length=30)
    note: str = Field(default="", max_length=300)

class Status(BaseModel):
    status: str

@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT / "index.html").read_text(encoding="utf-8")

@app.get("/admin", response_class=HTMLResponse)
def admin():
    return (ROOT / "admin.html").read_text(encoding="utf-8")

@app.get("/api/menu")
def menu():
    return MENU

@app.post("/api/chat")
def chat(request: Chat):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(503, "請先在 .env 設定 OPENAI_API_KEY")
    prior = [{"role": t["role"], "content": t["content"][:1000]} for t in request.history[-8:] if t.get("role") in ("user", "assistant") and isinstance(t.get("content"), str)]
    instruction = ("你是繁體中文飲料店點餐助手。只依以下菜單推薦，不能虛構菜色、價格、過敏安全或已送單。未知過敏資訊請找店員確認。你無法操作購物車；推薦後請顧客點選畫面上的飲料選項，不要詢問是否由你代為加入。顧客要下單時請他操作購物車。菜單：" + json.dumps(MENU, ensure_ascii=False))
    try:
        result = OpenAI(api_key=key, timeout=20).responses.create(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), instructions=instruction, input=prior + [{"role":"user","content":request.message}], max_output_tokens=350, store=False)
        return {"reply":result.output_text}
    except Exception:
        logging.exception("AI chat request failed")
        raise HTTPException(502, "AI 暫時無法回應，請找店員協助")

@app.post("/api/orders", status_code=201)
def order(request: Order):
    if not request.table_no.strip():
        raise HTTPException(422, "請填桌號")
    selected = []
    for line in request.items:
        if line.id not in ITEMS:
            raise HTTPException(422, "未知餐點")
        if line.sugar not in ("無糖", "1分糖", "3分糖", "5分糖", "8分糖") or line.ice not in ("35%冰", "去冰五顆冰", "完全去冰", "溫", "熱"):
            raise HTTPException(422, "甜度或冰量不正確")
        selected.append({"id":line.id,"name":ITEMS[line.id]["name"],"quantity":line.quantity,"unit_price":ITEMS[line.id]["price"],"sugar":line.sugar,"ice":line.ice})
    total = sum(x["unit_price"] * x["quantity"] for x in selected)
    with db() as conn:
        cursor = conn.execute("INSERT INTO orders(table_no,items,total,note) VALUES(?,?,?,?)", (request.table_no.strip(),json.dumps(selected,ensure_ascii=False),total,request.note.strip()))
        number = cursor.lastrowid
    return {"id":number,"total":total,"status":"pending"}

def guard(token):
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected or not secrets.compare_digest(token or "", expected):
        raise HTTPException(401, "未授權")

@app.get("/api/admin/orders")
def orders(x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    with db() as conn:
        rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100").fetchall()
    return [{**dict(row),"items":json.loads(row["items"])} for row in rows]

@app.patch("/api/admin/orders/{number}")
def status(number: int, request: Status, x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    if request.status not in {"pending","accepted","completed","cancelled"}:
        raise HTTPException(422, "不支援的狀態")
    with db() as conn:
        cursor = conn.execute("UPDATE orders SET status=? WHERE id=?", (request.status,number))
        if not cursor.rowcount:
            raise HTTPException(404, "訂單不存在")
    return {"id":number,"status":request.status}

@app.get("/qr")
def qr(table: str = "A1"):
    if len(table)>20:
        raise HTTPException(422, "桌號太長")
    url = os.getenv("PUBLIC_BASE_URL","http://127.0.0.1:8000").rstrip("/") + "/"
    output=io.BytesIO()
    qrcode.make(url).save(output,format="PNG")
    output.seek(0)
    return StreamingResponse(output,media_type="image/png")
