from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import io
import hmac
import logging
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any

import jwt
import bcrypt
import requests
import pandas as pd
from bson import ObjectId
from fastapi import (FastAPI, APIRouter, HTTPException, Depends, Request, Response,
                     UploadFile, File, BackgroundTasks, Header, Query)
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

# ------------------------------------------------------------------ DB setup
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

JWT_ALGORITHM = "HS256"

# ------------------------------------------------------------------ object storage
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "cbt-ujian"
_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key, "Content-Type": content_type},
                        data=data, timeout=120)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                            headers={"X-Storage-Key": key, "Content-Type": content_type},
                            data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")



def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


# ------------------------------------------------------------------ helpers
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id, "email": email, "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_dt(value) -> datetime:
    """Parse an ISO datetime string and always return a timezone-aware UTC datetime.

    Datetimes coming from the browser (e.g. <input type="datetime-local">) have no
    timezone suffix; those are treated as UTC so they can safely be compared with
    datetime.now(timezone.utc).
    """
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


def clean_user(u: dict) -> dict:
    u = dict(u)
    u["id"] = str(u.pop("_id"))
    u.pop("password_hash", None)
    return u


# ------------------------------------------------------------------ auth dep
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return clean_user(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_roles(*roles):
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Akses ditolak")
        return user
    return checker


# ------------------------------------------------------------------ models
class LoginBody(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str  # siswa | guru | admin
    identifier: Optional[str] = None  # NISN / NIP


class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    identifier: Optional[str] = None


class Category(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    description: Optional[str] = ""
    created_at: str = Field(default_factory=now_iso)


class CategoryBody(BaseModel):
    name: str
    description: Optional[str] = ""


class Question(BaseModel):
    id: str = Field(default_factory=new_id)
    category_id: Optional[str] = None
    type: str  # pg | truefalse | essay
    text: str
    options: List[str] = []          # for pg
    correct_answer: Optional[str] = None  # index string for pg, "true"/"false" for tf
    weight: float = 1.0
    image_path: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)


class QuestionBody(BaseModel):
    category_id: Optional[str] = None
    type: str
    text: str
    options: List[str] = []
    correct_answer: Optional[str] = None
    weight: float = 1.0
    image_path: Optional[str] = None


class Package(BaseModel):
    id: str = Field(default_factory=new_id)
    title: str
    description: Optional[str] = ""
    category_id: Optional[str] = None
    question_ids: List[str] = []
    scoring_method: str = "percentage"  # percentage | weighted
    shuffle_questions: bool = False
    shuffle_options: bool = False
    min_score: float = 0.0
    rounding: str = "2desimal"  # 2desimal | 1desimal | bulat
    easy_min: Optional[float] = None
    medium_min: Optional[float] = None
    created_by: Optional[str] = None
    is_public: bool = False
    created_at: str = Field(default_factory=now_iso)


class PackageBody(BaseModel):
    title: str
    description: Optional[str] = ""
    category_id: Optional[str] = None
    question_ids: List[str] = []
    scoring_method: str = "percentage"
    shuffle_questions: bool = False
    shuffle_options: bool = False
    min_score: float = 0.0
    rounding: str = "2desimal"
    easy_min: Optional[float] = None
    medium_min: Optional[float] = None
    is_public: bool = False


SCORE_POLICIES = ("tertinggi", "terakhir", "rata")


class Session(BaseModel):
    id: str = Field(default_factory=new_id)
    title: str
    package_id: str
    start_time: str
    end_time: str
    duration_minutes: int = 60
    kkm: float = 75.0
    class_ids: List[str] = []
    announcement: Optional[str] = ""
    max_attempts: int = 1               # berapa kali siswa boleh mengerjakan
    score_policy: str = "tertinggi"     # tertinggi | terakhir | rata
    created_at: str = Field(default_factory=now_iso)


class SessionBody(BaseModel):
    title: str
    package_id: str
    start_time: str
    end_time: str
    duration_minutes: int = 60
    kkm: float = 75.0
    class_ids: List[str] = []
    announcement: Optional[str] = ""
    max_attempts: int = 1
    score_policy: str = "tertinggi"


class SchoolClass(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    description: Optional[str] = ""
    student_ids: List[str] = []
    created_at: str = Field(default_factory=now_iso)


class ClassBody(BaseModel):
    name: str
    description: Optional[str] = ""
    student_ids: List[str] = []


class DifficultyBody(BaseModel):
    easy_min: float = 70.0
    medium_min: float = 40.0


class SchoolBody(BaseModel):
    name: str = ""
    address: str = ""
    logo_path: Optional[str] = None
    theme_color: Optional[str] = None


class StartAttemptBody(BaseModel):
    session_id: str


class SubmitBody(BaseModel):
    session_id: str
    answers: dict  # {question_id: answer}


class GradeEssayBody(BaseModel):
    scores: dict  # {question_id: points_earned}


# ------------------------------------------------------------------ AUTH routes
def set_auth_cookie(response: Response, token: str):
    response.set_cookie(key="access_token", value=token, httponly=True,
                        secure=True, samesite="none", max_age=604800, path="/")


@api_router.post("/auth/login")
async def login(body: LoginBody, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email atau password salah")
    token = create_access_token(str(user["_id"]), email, user["role"])
    set_auth_cookie(response, token)
    return {"token": token, "user": clean_user(user)}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@api_router.post("/auth/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


# ------------------------------------------------------------------ ACCOUNTS (admin)
@api_router.get("/users")
async def list_users(role: Optional[str] = None, user: dict = Depends(require_roles("admin", "guru"))):
    q = {}
    if role:
        q["role"] = role
    users = await db.users.find(q).sort("created_at", -1).to_list(1000)
    return [clean_user(u) for u in users]


@api_router.post("/users")
async def create_user(body: UserCreate, user: dict = Depends(require_roles("admin"))):
    if body.role not in ("siswa", "guru", "admin"):
        raise HTTPException(status_code=400, detail="Role tidak valid")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    doc = {
        "email": email, "password_hash": hash_password(body.password),
        "name": body.name, "role": body.role, "identifier": body.identifier or "",
        "created_at": now_iso(),
    }
    res = await db.users.insert_one(doc)
    doc["_id"] = res.inserted_id
    return clean_user(doc)


@api_router.put("/users/{user_id}")
async def update_user(user_id: str, body: UserUpdate, user: dict = Depends(require_roles("admin"))):
    update = {}
    if body.name is not None:
        update["name"] = body.name
    if body.role is not None:
        update["role"] = body.role
    if body.identifier is not None:
        update["identifier"] = body.identifier
    if body.password:
        update["password_hash"] = hash_password(body.password)
    if update:
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update})
    u = await db.users.find_one({"_id": ObjectId(user_id)})
    return clean_user(u)


@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_roles("admin"))):
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"ok": True}


# ------------------------------------------------------------------ CATEGORIES
@api_router.get("/categories")
async def list_categories(user: dict = Depends(get_current_user)):
    return await db.categories.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api_router.post("/categories")
async def create_category(body: CategoryBody, user: dict = Depends(require_roles("admin", "guru"))):
    cat = Category(**body.model_dump())
    await db.categories.insert_one(cat.model_dump())
    return cat.model_dump()


@api_router.put("/categories/{cid}")
async def update_category(cid: str, body: CategoryBody, user: dict = Depends(require_roles("admin", "guru"))):
    await db.categories.update_one({"id": cid}, {"$set": body.model_dump()})
    return await db.categories.find_one({"id": cid}, {"_id": 0})


@api_router.delete("/categories/{cid}")
async def delete_category(cid: str, user: dict = Depends(require_roles("admin", "guru"))):
    await db.categories.delete_one({"id": cid})
    return {"ok": True}


# ------------------------------------------------------------------ QUESTIONS
@api_router.get("/questions")
async def list_questions(category_id: Optional[str] = None, user: dict = Depends(require_roles("admin", "guru"))):
    q = {}
    if category_id:
        q["category_id"] = category_id
    return await db.questions.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)


@api_router.post("/questions")
async def create_question(body: QuestionBody, user: dict = Depends(require_roles("admin", "guru"))):
    ques = Question(**body.model_dump())
    await db.questions.insert_one(ques.model_dump())
    return ques.model_dump()


@api_router.put("/questions/{qid}")
async def update_question(qid: str, body: QuestionBody, user: dict = Depends(require_roles("admin", "guru"))):
    await db.questions.update_one({"id": qid}, {"$set": body.model_dump()})
    return await db.questions.find_one({"id": qid}, {"_id": 0})


@api_router.delete("/questions/{qid}")
async def delete_question(qid: str, user: dict = Depends(require_roles("admin", "guru"))):
    await db.questions.delete_one({"id": qid})
    return {"ok": True}


# ------------------------------------------------------------------ PACKAGES
@api_router.get("/packages")
async def list_packages(user: dict = Depends(require_roles("admin", "guru"))):
    if user["role"] == "admin":
        q = {}
    else:
        q = {"$or": [{"created_by": user["id"]}, {"is_public": True},
                     {"created_by": None}, {"created_by": {"$exists": False}}]}
    pkgs = await db.packages.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    owner_ids = {p.get("created_by") for p in pkgs if p.get("created_by")}
    owners = {}
    if owner_ids:
        docs = await db.users.find({"_id": {"$in": [ObjectId(o) for o in owner_ids]}}).to_list(2000)
        owners = {str(d["_id"]): d["name"] for d in docs}
    for p in pkgs:
        p["question_count"] = len(p.get("question_ids", []))
        p["owner_name"] = owners.get(p.get("created_by"), "—")
        p["is_owner"] = user["role"] == "admin" or not p.get("created_by") or p.get("created_by") == user["id"]
    return pkgs


@api_router.get("/packages/{pid}")
async def get_package(pid: str, user: dict = Depends(require_roles("admin", "guru"))):
    p = await db.packages.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Paket tidak ditemukan")
    return p


def _check_pkg_thresholds(body: "PackageBody"):
    if body.easy_min is not None or body.medium_min is not None:
        if body.easy_min is None or body.medium_min is None:
            raise HTTPException(status_code=400, detail="Ambang Mudah & Sedang harus diisi keduanya")
        if not (0 <= body.medium_min < body.easy_min <= 100):
            raise HTTPException(status_code=400, detail="Harus 0 ≤ Sedang < Mudah ≤ 100")


@api_router.post("/packages")
async def create_package(body: PackageBody, user: dict = Depends(require_roles("admin", "guru"))):
    _check_pkg_thresholds(body)
    data = body.model_dump()
    data["created_by"] = user["id"]
    pkg = Package(**data)
    await db.packages.insert_one(pkg.model_dump())
    return pkg.model_dump()


@api_router.put("/packages/{pid}")
async def update_package(pid: str, body: PackageBody, user: dict = Depends(require_roles("admin", "guru"))):
    _check_pkg_thresholds(body)
    existing = await db.packages.find_one({"id": pid}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Paket tidak ditemukan")
    if user["role"] != "admin" and existing.get("created_by") and existing["created_by"] != user["id"]:
        raise HTTPException(status_code=403, detail="Hanya pemilik yang dapat mengubah paket ini")
    await db.packages.update_one({"id": pid}, {"$set": body.model_dump()})
    return await db.packages.find_one({"id": pid}, {"_id": 0})


@api_router.delete("/packages/{pid}")
async def delete_package(pid: str, user: dict = Depends(require_roles("admin", "guru"))):
    existing = await db.packages.find_one({"id": pid}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Paket tidak ditemukan")
    if user["role"] != "admin" and existing.get("created_by") and existing["created_by"] != user["id"]:
        raise HTTPException(status_code=403, detail="Hanya pemilik yang dapat menghapus paket ini")
    await db.packages.delete_one({"id": pid})
    return {"ok": True}


@api_router.post("/packages/{pid}/duplicate")
async def duplicate_package(pid: str, user: dict = Depends(require_roles("admin", "guru"))):
    src = await db.packages.find_one({"id": pid}, {"_id": 0})
    if not src:
        raise HTTPException(status_code=404, detail="Paket tidak ditemukan")
    if (user["role"] != "admin" and src.get("created_by")
            and src["created_by"] != user["id"] and not src.get("is_public")):
        raise HTTPException(status_code=403, detail="Paket ini tidak dapat disalin")
    new = Package(
        title=f"{src.get('title', 'Paket')} (Salinan)", description=src.get("description", ""),
        category_id=src.get("category_id"), question_ids=src.get("question_ids", []),
        scoring_method=src.get("scoring_method", "percentage"),
        shuffle_questions=src.get("shuffle_questions", False),
        shuffle_options=src.get("shuffle_options", False),
        min_score=src.get("min_score", 0), rounding=src.get("rounding", "2desimal"),
        easy_min=src.get("easy_min"), medium_min=src.get("medium_min"),
        created_by=user["id"], is_public=False,
    )
    await db.packages.insert_one(new.model_dump())
    return new.model_dump()


# ------------------------------------------------------------------ SESSIONS
def normalize_session_times(data: dict) -> dict:
    """Store session schedule as timezone-aware UTC ISO strings.

    The browser sends naive strings from <input type="datetime-local">; normalizing on
    write keeps every later comparison (status, timer, auto-submit) unambiguous.
    """
    for field in ("start_time", "end_time"):
        if data.get(field):
            data[field] = parse_dt(data[field]).isoformat()
    try:
        data["max_attempts"] = max(1, int(data.get("max_attempts") or 1))
    except (TypeError, ValueError):
        data["max_attempts"] = 1
    if data.get("score_policy") not in SCORE_POLICIES:
        data["score_policy"] = "tertinggi"
    return data


# ------------------------------------------------------------------ ATTEMPTS (retake support)
FINISHED = {"$in": ["selesai", "menunggu_koreksi"]}
COUNTED_ONLY = {"counted": {"$ne": False}}  # legacy attempts (no field) still count


STATUS_ID = {
    "berlangsung": "Berlangsung",
    "menunggu_koreksi": "Menunggu Koreksi",
    "selesai": "Selesai",
}


def fmt_local(iso: str, tz_hours: int = 7) -> str:
    """Format an ISO timestamp for Indonesian reports (default WIB / UTC+7)."""
    try:
        dt = parse_dt(iso) + timedelta(hours=tz_hours)
    except Exception:
        return str(iso or "-")
    bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    return f"{dt.day:02d} {bulan[dt.month - 1]} {dt.year} {dt.hour:02d}:{dt.minute:02d} WIB"


def att_score(a: dict):
    """Score used for grades/ranking: effective_score honours the session score policy."""
    val = a.get("effective_score")
    return a.get("score") if val is None else val


async def recount_attempts(session_id: str, student_id: str) -> None:
    """Mark exactly one attempt of a student as the counted one, per session policy.

    - tertinggi : attempt with the highest score counts
    - terakhir  : the most recent submission counts
    - rata      : most recent submission counts, carrying the average of all attempts
    """
    attempts = await db.attempts.find(
        {"session_id": session_id, "student_id": student_id, "status": {"$ne": "berlangsung"}},
        {"_id": 0, "id": 1, "score": 1, "submitted_at": 1},
    ).to_list(200)
    if not attempts:
        return
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0, "score_policy": 1})
    policy = (session or {}).get("score_policy") or "tertinggi"
    ordered = sorted(attempts, key=lambda a: a.get("submitted_at") or "")
    scored = [a for a in ordered if a.get("score") is not None]

    if policy == "terakhir":
        chosen, effective = ordered[-1], None
    elif policy == "rata":
        chosen = ordered[-1]
        effective = round(sum(a["score"] for a in scored) / len(scored), 2) if scored else None
    else:  # tertinggi
        chosen = max(scored, key=lambda a: a["score"]) if scored else ordered[-1]
        effective = None

    for a in ordered:
        is_chosen = a["id"] == chosen["id"]
        await db.attempts.update_one({"id": a["id"]}, {"$set": {
            "counted": is_chosen,
            "effective_score": effective if is_chosen else None,
            "score_policy": policy,
        }})


async def enrich_session(s: dict) -> dict:
    pkg = await db.packages.find_one({"id": s["package_id"]}, {"_id": 0})
    s["package_title"] = pkg["title"] if pkg else "-"
    s["question_count"] = len(pkg.get("question_ids", [])) if pkg else 0
    now = datetime.now(timezone.utc)
    start = parse_dt(s["start_time"])
    end = parse_dt(s["end_time"])
    if now < start:
        s["status"] = "akan_datang"
    elif now > end:
        s["status"] = "selesai"
    else:
        s["status"] = "berlangsung"
    return s


@api_router.get("/sessions")
async def list_sessions(user: dict = Depends(get_current_user)):
    sessions = await db.sessions.find({}, {"_id": 0}).sort("start_time", -1).to_list(1000)
    for s in sessions:
        await enrich_session(s)
    if user["role"] == "siswa":
        my_classes = await db.classes.find({"student_ids": user["id"]}, {"_id": 0, "id": 1}).to_list(1000)
        my_class_ids = {c["id"] for c in my_classes}
        visible = []
        for s in sessions:
            targets = s.get("class_ids") or []
            if targets and not (set(targets) & my_class_ids):
                continue
            att = await db.attempts.find_one(
                {"session_id": s["id"], "student_id": user["id"], "status": "berlangsung"}, {"_id": 0})
            finished = await db.attempts.count_documents(
                {"session_id": s["id"], "student_id": user["id"], "status": {"$ne": "berlangsung"}})
            max_att = int(s.get("max_attempts") or 1)
            s["attempt_status"] = att["status"] if att else ("selesai" if finished else None)
            s["attempts_used"] = finished
            s["max_attempts"] = max_att
            s["attempts_left"] = max(0, max_att - finished)
            s["has_ongoing"] = bool(att)
            s["score_policy"] = s.get("score_policy") or "tertinggi"
            visible.append(s)
        return visible
    else:
        for s in sessions:
            classes = await db.classes.find({"id": {"$in": s.get("class_ids", [])}}, {"_id": 0, "name": 1}).to_list(100)
            s["class_names"] = [c["name"] for c in classes]
    return sessions


@api_router.post("/sessions")
async def create_session(body: SessionBody, user: dict = Depends(require_roles("admin", "guru"))):
    data = normalize_session_times(body.model_dump())
    ses = Session(**data)
    await db.sessions.insert_one(ses.model_dump())
    return ses.model_dump()


@api_router.put("/sessions/{sid}")
async def update_session(sid: str, body: SessionBody, user: dict = Depends(require_roles("admin", "guru"))):
    data = normalize_session_times(body.model_dump())
    prev = await db.sessions.find_one({"id": sid}, {"_id": 0, "score_policy": 1})
    await db.sessions.update_one({"id": sid}, {"$set": data})
    if (prev or {}).get("score_policy") != data.get("score_policy"):
        # policy changed -> re-decide which attempt counts for every participant
        students = await db.attempts.distinct("student_id", {"session_id": sid})
        for st in students:
            await recount_attempts(sid, st)
    return await db.sessions.find_one({"id": sid}, {"_id": 0})


@api_router.delete("/sessions/{sid}")
async def delete_session(sid: str, user: dict = Depends(require_roles("admin", "guru"))):
    await db.sessions.delete_one({"id": sid})
    return {"ok": True}


# ------------------------------------------------------------------ EXAM (student)
def sanitize_question(q: dict, perm: Optional[List[int]] = None) -> dict:
    opts = q.get("options", [])
    if perm and q["type"] == "pg":
        opts = [opts[i] for i in perm if i < len(opts)]
    return {
        "id": q["id"], "type": q["type"], "text": q["text"],
        "options": opts, "weight": q.get("weight", 1.0), "image_path": q.get("image_path"),
    }


@api_router.post("/exam/start")
async def start_exam(body: StartAttemptBody, user: dict = Depends(require_roles("siswa"))):
    session = await db.sessions.find_one({"id": body.session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    await enrich_session(session)
    if session["status"] == "akan_datang":
        raise HTTPException(status_code=400, detail="Sesi belum dimulai")
    if session["status"] == "selesai":
        raise HTTPException(status_code=400, detail="Sesi sudah berakhir")

    attempt = await db.attempts.find_one(
        {"session_id": body.session_id, "student_id": user["id"], "status": "berlangsung"}, {"_id": 0})
    finished = await db.attempts.count_documents(
        {"session_id": body.session_id, "student_id": user["id"], "status": {"$ne": "berlangsung"}})
    max_attempts = int(session.get("max_attempts") or 1)
    if not attempt and finished >= max_attempts:
        detail = ("Anda sudah mengerjakan sesi ini" if max_attempts == 1 else
                  f"Batas percobaan tercapai ({finished}/{max_attempts})")
        raise HTTPException(status_code=400, detail=detail)

    pkg = await db.packages.find_one({"id": session["package_id"]}, {"_id": 0})
    questions = await db.questions.find({"id": {"$in": pkg.get("question_ids", [])}}, {"_id": 0}).to_list(2000)
    qmap = {q["id"]: q for q in questions}

    if not attempt:
        order_ids = list(pkg.get("question_ids", []))
        if pkg.get("shuffle_questions"):
            random.shuffle(order_ids)
        option_perm = {}
        if pkg.get("shuffle_options"):
            for q in questions:
                if q["type"] == "pg" and q.get("options"):
                    idxs = list(range(len(q["options"])))
                    random.shuffle(idxs)
                    option_perm[q["id"]] = idxs
        attempt = {
            "id": new_id(), "session_id": body.session_id, "student_id": user["id"],
            "student_name": user["name"], "student_identifier": user.get("identifier", ""),
            "package_id": session["package_id"], "answers": {}, "status": "berlangsung",
            "score": None, "started_at": now_iso(), "submitted_at": None,
            "needs_grading": False, "question_order": order_ids, "option_perm": option_perm,
            "attempt_number": finished + 1, "counted": False, "effective_score": None,
        }
        await db.attempts.insert_one(dict(attempt))

    order_ids = attempt.get("question_order") or list(pkg.get("question_ids", []))
    option_perm = attempt.get("option_perm", {})
    display = [sanitize_question(qmap[qid], option_perm.get(qid)) for qid in order_ids if qid in qmap]

    return {
        "attempt_id": attempt["id"],
        "session": {"id": session["id"], "title": session["title"],
                    "duration_minutes": session["duration_minutes"], "end_time": session["end_time"],
                    "max_attempts": max_attempts, "score_policy": session.get("score_policy", "tertinggi")},
        "attempt_number": attempt.get("attempt_number", 1),
        "attempts_left": max(0, max_attempts - finished - (0 if attempt.get("submitted_at") else 1)),
        "started_at": attempt["started_at"],
        "answers": attempt.get("answers", {}),
        "questions": display,
    }


def compute_grade(pkg: dict, questions: dict, answers: dict, essay_scores: dict = None):
    """Returns (details, needs_grading, score_or_none)."""
    essay_scores = essay_scores or {}
    weighted = pkg.get("scoring_method") == "weighted"
    details = []
    total_possible = 0.0
    earned = 0.0
    needs_grading = False
    for qid in pkg.get("question_ids", []):
        q = questions.get(qid)
        if not q:
            continue
        w = q.get("weight", 1.0) if weighted else 1.0
        total_possible += w
        ans = answers.get(qid)
        d = {"question_id": qid, "answer": ans, "type": q["type"],
             "points_possible": w, "points_earned": 0.0, "is_correct": None}
        if q["type"] in ("pg", "truefalse"):
            correct = (ans is not None) and (str(ans) == str(q.get("correct_answer")))
            d["is_correct"] = correct
            d["points_earned"] = w if correct else 0.0
            d["correct_answer"] = q.get("correct_answer")
        else:  # essay
            if qid in essay_scores and essay_scores[qid] is not None:
                pts = max(0.0, min(float(essay_scores[qid]), w))
                d["points_earned"] = pts
                d["is_correct"] = None
            else:
                d["needs_grading"] = True
                needs_grading = True
        earned += d["points_earned"]
        details.append(d)
    if needs_grading:
        score = None
    elif not total_possible:
        score = 0.0
    else:
        raw = earned / total_possible * 100
        rounding = pkg.get("rounding", "2desimal")
        if rounding == "bulat":
            raw = round(raw)
        elif rounding == "1desimal":
            raw = round(raw, 1)
        else:
            raw = round(raw, 2)
        min_score = float(pkg.get("min_score", 0) or 0)
        score = max(raw, min_score)
        if rounding == "bulat":
            score = round(score)
        elif rounding == "1desimal":
            score = round(score, 1)
        else:
            score = round(score, 2)
    return details, needs_grading, score, round(earned, 2), round(total_possible, 2)


async def finalize_attempt(attempt: dict, answers: dict) -> dict:
    """Convert shuffled indices, grade, and persist. Shared by submit + auto-submit."""
    pkg = await db.packages.find_one({"id": attempt["package_id"]}, {"_id": 0})
    qlist = await db.questions.find({"id": {"$in": pkg.get("question_ids", [])}}, {"_id": 0}).to_list(2000)
    qmap = {q["id"]: q for q in qlist}
    perm_map = attempt.get("option_perm", {})
    canonical = {}
    for qid, ans in (answers or {}).items():
        q = qmap.get(qid)
        if q and q.get("type") == "pg" and qid in perm_map and ans not in (None, ""):
            try:
                canonical[qid] = str(perm_map[qid][int(ans)])
            except (ValueError, IndexError, TypeError):
                canonical[qid] = ans
        else:
            canonical[qid] = ans
    details, needs_grading, score, earned, total = compute_grade(pkg, qmap, canonical)
    update = {
        "answers": canonical, "details": details, "needs_grading": needs_grading,
        "score": score, "earned": earned, "total_possible": total,
        "status": "menunggu_koreksi" if needs_grading else "selesai",
        "submitted_at": now_iso(),
    }
    await db.attempts.update_one({"id": attempt["id"]}, {"$set": update})
    await recount_attempts(attempt["session_id"], attempt["student_id"])
    return update


@api_router.post("/exam/submit")
async def submit_exam(body: SubmitBody, user: dict = Depends(require_roles("siswa"))):
    attempt = await db.attempts.find_one(
        {"session_id": body.session_id, "student_id": user["id"], "status": "berlangsung"}, {"_id": 0})
    if not attempt:
        raise HTTPException(status_code=404, detail="Percobaan tidak ditemukan")
    update = await finalize_attempt(attempt, body.answers)
    return {"status": update["status"], "score": update["score"],
            "needs_grading": update["needs_grading"], "attempt_number": attempt.get("attempt_number", 1)}


@api_router.post("/exam/save/{session_id}")
async def save_progress(session_id: str, body: dict, user: dict = Depends(require_roles("siswa"))):
    await db.attempts.update_one(
        {"session_id": session_id, "student_id": user["id"], "status": "berlangsung"},
        {"$set": {"answers": body.get("answers", {})}})
    return {"ok": True}


# ------------------------------------------------------------------ RESULTS
@api_router.get("/results/session/{session_id}")
async def results_by_session(session_id: str, user: dict = Depends(require_roles("admin", "guru"))):
    attempts = await db.attempts.find({"session_id": session_id}, {"_id": 0}).to_list(2000)
    attempts.sort(key=lambda a: (a.get("student_name", "").lower(), a.get("attempt_number", 1)))
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    return {"session": session, "attempts": attempts}


@api_router.get("/results/me")
async def my_results(user: dict = Depends(require_roles("siswa"))):
    attempts = await db.attempts.find(
        {"student_id": user["id"], "status": {"$ne": "berlangsung"}}, {"_id": 0}
    ).sort("submitted_at", -1).to_list(1000)
    for a in attempts:
        s = await db.sessions.find_one({"id": a["session_id"]}, {"_id": 0})
        a["session_title"] = s["title"] if s else "-"
        a["kkm"] = s.get("kkm", 75) if s else 75
        a["max_attempts"] = int(s.get("max_attempts") or 1) if s else 1
        a["score_policy"] = (s.get("score_policy") if s else None) or "tertinggi"
        a["final_score"] = att_score(a)
    return attempts


@api_router.get("/results/detail/{attempt_id}")
async def result_detail(attempt_id: str, user: dict = Depends(get_current_user)):
    attempt = await db.attempts.find_one({"id": attempt_id}, {"_id": 0})
    if not attempt:
        raise HTTPException(status_code=404, detail="Tidak ditemukan")
    if user["role"] == "siswa" and attempt["student_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    pkg = await db.packages.find_one({"id": attempt["package_id"]}, {"_id": 0})
    qlist = await db.questions.find({"id": {"$in": pkg.get("question_ids", [])}}, {"_id": 0}).to_list(2000)
    qmap = {q["id"]: q for q in qlist}
    session = await db.sessions.find_one({"id": attempt["session_id"]}, {"_id": 0})
    enriched = []
    for d in attempt.get("details", []):
        q = qmap.get(d["question_id"], {})
        enriched.append({**d, "text": q.get("text"), "options": q.get("options", []),
                         "correct_answer": q.get("correct_answer"), "image_path": q.get("image_path")})
    attempt["details"] = enriched
    attempt["session_title"] = session["title"] if session else "-"
    attempt["scoring_method"] = pkg.get("scoring_method")
    return attempt


@api_router.post("/results/grade/{attempt_id}")
async def grade_essay(attempt_id: str, body: GradeEssayBody, user: dict = Depends(require_roles("admin", "guru"))):
    attempt = await db.attempts.find_one({"id": attempt_id}, {"_id": 0})
    if not attempt:
        raise HTTPException(status_code=404, detail="Tidak ditemukan")
    pkg = await db.packages.find_one({"id": attempt["package_id"]}, {"_id": 0})
    qlist = await db.questions.find({"id": {"$in": pkg.get("question_ids", [])}}, {"_id": 0}).to_list(2000)
    qmap = {q["id"]: q for q in qlist}
    details, needs_grading, score, earned, total = compute_grade(
        pkg, qmap, attempt.get("answers", {}), body.scores)
    await db.attempts.update_one({"id": attempt_id}, {"$set": {
        "details": details, "needs_grading": needs_grading, "score": score,
        "earned": earned, "total_possible": total,
        "status": "menunggu_koreksi" if needs_grading else "selesai",
    }})
    await recount_attempts(attempt["session_id"], attempt["student_id"])
    return {"score": score, "needs_grading": needs_grading}


# ------------------------------------------------------------------ CLASSES
async def enrich_class(c: dict) -> dict:
    c["student_count"] = len(c.get("student_ids", []))
    return c


@api_router.get("/classes")
async def list_classes(user: dict = Depends(require_roles("admin", "guru"))):
    items = await db.classes.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for c in items:
        await enrich_class(c)
    return items


@api_router.post("/classes")
async def create_class(body: ClassBody, user: dict = Depends(require_roles("admin", "guru"))):
    cls = SchoolClass(**body.model_dump())
    await db.classes.insert_one(cls.model_dump())
    return await enrich_class(cls.model_dump())


@api_router.put("/classes/{cid}")
async def update_class(cid: str, body: ClassBody, user: dict = Depends(require_roles("admin", "guru"))):
    await db.classes.update_one({"id": cid}, {"$set": body.model_dump()})
    c = await db.classes.find_one({"id": cid}, {"_id": 0})
    return await enrich_class(c)


@api_router.delete("/classes/{cid}")
async def delete_class(cid: str, user: dict = Depends(require_roles("admin", "guru"))):
    await db.classes.delete_one({"id": cid})
    return {"ok": True}


# ------------------------------------------------------------------ QUESTION IMPORT
IMPORT_TEMPLATE = (
    "type,text,option_a,option_b,option_c,option_d,option_e,correct,weight,category,image_url\n"
    "pg,Berapa hasil 5 + 3?,6,7,8,9,10,C,1,Matematika,\n"
    "pg,Ibu kota Provinsi Jawa Barat adalah ...,Bandung,Semarang,Surabaya,Medan,Bogor,A,1,IPS,\n"
    "truefalse,Matahari terbit dari timur.,,,,,,benar,1,IPA,\n"
    "essay,Jelaskan proses fotosintesis.,,,,,,,2,IPA,\n"
    "pg,Perhatikan gambar berikut.,A,B,C,D,E,A,1,IPA,https://contoh.com/gambar.png\n"
)


@api_router.get("/questions/import-template")
async def import_template(user: dict = Depends(require_roles("admin", "guru"))):
    return StreamingResponse(
        io.BytesIO(IMPORT_TEMPLATE.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=template_soal.csv"},
    )


@api_router.post("/questions/import")
async def import_questions(file: UploadFile = File(...), user: dict = Depends(require_roles("admin", "guru"))):
    raw = await file.read()
    name = (file.filename or "").lower()
    try:
        if name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(raw), dtype=str)
        else:
            df = pd.read_csv(io.BytesIO(raw), dtype=str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca file: {e}")

    df.columns = [str(c).strip().lower() for c in df.columns]
    cats = await db.categories.find({}, {"_id": 0}).to_list(1000)
    cat_by_name = {c["name"].strip().lower(): c["id"] for c in cats}

    imported = 0
    errors = []
    letter_idx = {"a": "0", "b": "1", "c": "2", "d": "3", "e": "4"}
    OPT_ALIASES = [
        ("option_a", "opsi_a", "pilihan_a", "jawaban_a", "a"),
        ("option_b", "opsi_b", "pilihan_b", "jawaban_b", "b"),
        ("option_c", "opsi_c", "pilihan_c", "jawaban_c", "c"),
        ("option_d", "opsi_d", "pilihan_d", "jawaban_d", "d"),
        ("option_e", "opsi_e", "pilihan_e", "jawaban_e", "e"),
    ]
    TYPE_ALIASES = {
        "pg": "pg", "pilihan ganda": "pg", "pilihan_ganda": "pg", "multiple choice": "pg", "mc": "pg",
        "truefalse": "truefalse", "true/false": "truefalse", "benar/salah": "truefalse",
        "benar salah": "truefalse", "bs": "truefalse", "b/s": "truefalse",
        "essay": "essay", "esai": "essay", "uraian": "essay", "isian": "essay",
    }
    for i, row in df.iterrows():
        rownum = i + 2
        try:
            text = _cell(row, "text", "soal", "pertanyaan", "butir_soal", "butir soal", "uraian", "deskripsi")
            options_raw = [_cell(row, *aliases) for aliases in OPT_ALIASES]
            raw_c = _cell(row, "correct", "kunci", "kunci_jawaban", "kunci jawaban",
                          "jawaban", "jawaban_benar", "key").lower()

            qtype = TYPE_ALIASES.get(_cell(row, "type", "tipe", "jenis", "jenis_soal",
                                           "tipe_soal", "bentuk").lower(), None)
            if not qtype:  # tebak tipe soal bila kolom tipe tidak ada
                if any(options_raw):
                    qtype = "pg"
                elif raw_c in ("benar", "salah", "true", "false", "b", "s"):
                    qtype = "truefalse"
                else:
                    qtype = "essay"
            if not text:
                errors.append(f"Baris {rownum}: teks soal kosong")
                continue

            cat_name = _cell(row, "category", "kategori", "mapel", "mata_pelajaran",
                             "mata pelajaran", "materi", "pelajaran")
            cat_id = None
            if cat_name:
                key = cat_name.lower()
                if key not in cat_by_name:
                    nc = Category(name=cat_name)
                    await db.categories.insert_one(nc.model_dump())
                    cat_by_name[key] = nc.id
                cat_id = cat_by_name[key]
            weight = 1.0
            try:
                wv = _cell(row, "weight", "bobot", "skor", "poin", "point")
                weight = float(str(wv).replace(",", ".")) if wv else 1.0
            except (ValueError, TypeError):
                weight = 1.0
            if weight != weight or weight <= 0:  # NaN / invalid guard
                weight = 1.0

            options, correct = [], None
            if qtype == "pg":
                options = [v for v in options_raw if v]
                if len(options) < 2:
                    errors.append(f"Baris {rownum}: soal PG butuh minimal 2 opsi")
                    continue
                if raw_c in letter_idx:
                    correct = letter_idx[raw_c]
                elif raw_c.isdigit():
                    correct = raw_c
                else:
                    # kunci bisa berisi teks jawabannya, cocokkan dengan opsi
                    match = next((str(i) for i, o in enumerate(options) if o.lower() == raw_c), None)
                    if match is None:
                        errors.append(f"Baris {rownum}: kunci PG '{raw_c or '(kosong)'}' tidak valid (pakai A–E)")
                        continue
                    correct = match
                if int(correct) >= len(options):
                    errors.append(f"Baris {rownum}: kunci '{raw_c.upper()}' menunjuk opsi yang kosong")
                    continue
            elif qtype == "truefalse":
                correct = "true" if raw_c in ("true", "benar", "b", "1", "ya", "y") else "false"

            image_path = None
            img_url = _cell(row, "image_url", "gambar", "url_gambar", "link_gambar", "image")
            if img_url and img_url.startswith("http"):
                image_path = await fetch_image_to_storage(img_url, user["id"])

            ques = Question(category_id=cat_id, type=qtype, text=text,
                            options=options, correct_answer=correct, weight=weight,
                            image_path=image_path)
            await db.questions.insert_one(ques.model_dump())
            imported += 1
        except Exception as e:
            errors.append(f"Baris {rownum}: {e}")

    return {"imported": imported, "errors": errors}


# ------------------------------------------------------------------ USER IMPORT (Excel/CSV)
USER_IMPORT_TEMPLATE = (
    "nama,email,password,role,identifier,kelas\n"
    "Ani Siswa,ani@sekolah.id,siswa123,siswa,1001,Kelas X-A\n"
    "Budi Siswa,budi@sekolah.id,siswa123,siswa,1002,Kelas X-A\n"
    "Pak Rudi,rudi@sekolah.id,guru123,guru,G-01,\n"
)

ROLE_ALIASES = {
    "siswa": "siswa", "murid": "siswa", "student": "siswa",
    "guru": "guru", "teacher": "guru", "pengajar": "guru",
    "admin": "admin", "administrator": "admin",
}


@api_router.get("/users/import-template")
async def user_import_template(user: dict = Depends(require_roles("admin"))):
    return StreamingResponse(
        io.BytesIO(USER_IMPORT_TEMPLATE.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=template_akun.csv"},
    )


def _cell(row, *keys, default=""):
    """Read the first present column among aliases, tolerating NaN/blank cells."""
    for k in keys:
        if k in row:
            v = row.get(k)
            if v is None:
                continue
            s = str(v).strip()
            if s and s.lower() != "nan":
                return s
    return default


@api_router.post("/users/import")
async def import_users(file: UploadFile = File(...), user: dict = Depends(require_roles("admin"))):
    raw = await file.read()
    name = (file.filename or "").lower()
    try:
        if name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(raw), dtype=str)
        else:
            df = pd.read_csv(io.BytesIO(raw), dtype=str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca file: {e}")

    df.columns = [str(c).strip().lower() for c in df.columns]
    imported, updated, errors, notes = 0, 0, [], []
    classes = await db.classes.find({}, {"_id": 0}).to_list(1000)
    cls_by_name = {c["name"].strip().lower(): c for c in classes}
    class_members = {c["id"]: set(c.get("student_ids", [])) for c in classes}
    touched_classes = set()

    for i, row in df.iterrows():
        rownum = i + 2
        try:
            full_name = _cell(row, "nama", "name", "nama_lengkap", "nama lengkap", "nama_siswa", "nama siswa")
            email = _cell(row, "email", "e-mail", "surel", "email_siswa").lower()
            password = _cell(row, "password", "kata_sandi", "sandi", "kata sandi")
            role_raw = _cell(row, "role", "peran", "jabatan", default="siswa").lower()
            identifier = _cell(row, "identifier", "nis", "nisn", "nip", "nisn/nip", "no_induk", "no induk")
            class_name = _cell(row, "kelas", "class", "rombel", "kelas_siswa", "rombongan_belajar")
            if not full_name:
                errors.append(f"Baris {rownum}: nama wajib diisi")
                continue
            role = ROLE_ALIASES.get(role_raw)
            if not role:
                errors.append(f"Baris {rownum}: role '{role_raw}' tidak dikenal (siswa/guru/admin)")
                continue
            if not email:
                # buat email otomatis dari NISN supaya daftar siswa tanpa email tetap bisa diimpor
                if identifier and role == "siswa":
                    email = f"{identifier}@siswa.sekolah.id"
                    notes.append(f"Baris {rownum}: email dibuat otomatis → {email}")
                else:
                    errors.append(f"Baris {rownum}: email wajib diisi")
                    continue
            if "@" not in email or " " in email:
                errors.append(f"Baris {rownum}: email '{email}' tidak valid")
                continue

            existing = await db.users.find_one({"email": email})
            if existing:
                patch = {"name": full_name, "role": role, "identifier": identifier}
                if password:
                    patch["password_hash"] = hash_password(password)
                await db.users.update_one({"email": email}, {"$set": patch})
                user_id = str(existing["_id"])
                updated += 1
            else:
                if not password:
                    password = identifier or ("siswa123" if role == "siswa" else "guru123")
                    notes.append(f"Baris {rownum}: password default '{password}' dipakai untuk {email}")
                res = await db.users.insert_one({
                    "email": email, "password_hash": hash_password(password),
                    "name": full_name, "role": role, "identifier": identifier,
                    "created_at": now_iso(),
                })
                user_id = str(res.inserted_id)
                imported += 1

            # masukkan siswa ke kelas (kelas dibuat otomatis bila belum ada)
            if class_name and role == "siswa":
                key = class_name.lower()
                cls = cls_by_name.get(key)
                if not cls:
                    new_cls = SchoolClass(name=class_name)
                    await db.classes.insert_one(new_cls.model_dump())
                    cls = new_cls.model_dump()
                    cls_by_name[key] = cls
                    class_members[cls["id"]] = set()
                    notes.append(f"Kelas '{class_name}' dibuat otomatis")
                if user_id not in class_members[cls["id"]]:
                    class_members[cls["id"]].add(user_id)
                    touched_classes.add(cls["id"])
        except Exception as e:
            errors.append(f"Baris {rownum}: {e}")

    for cid in touched_classes:
        await db.classes.update_one({"id": cid}, {"$set": {"student_ids": sorted(class_members[cid])}})

    return {"imported": imported, "updated": updated, "errors": errors, "notes": notes}


# ------------------------------------------------------------------ RESULT PDF
@api_router.get("/results/detail/{attempt_id}/pdf")
async def result_pdf(attempt_id: str, user: dict = Depends(get_current_user)):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    attempt = await db.attempts.find_one({"id": attempt_id}, {"_id": 0})
    if not attempt:
        raise HTTPException(status_code=404, detail="Tidak ditemukan")
    if user["role"] == "siswa" and attempt["student_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Akses ditolak")

    pkg = await db.packages.find_one({"id": attempt["package_id"]}, {"_id": 0})
    qlist = await db.questions.find({"id": {"$in": pkg.get("question_ids", [])}}, {"_id": 0}).to_list(2000)
    qmap = {q["id"]: q for q in qlist}
    session = await db.sessions.find_one({"id": attempt["session_id"]}, {"_id": 0})
    kkm = session.get("kkm", 75) if session else 75

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm)
    styles = getSampleStyleSheet()
    green = colors.HexColor("#1e3a30")
    terra = colors.HexColor("#c0563f")
    h = ParagraphStyle("h", parent=styles["Title"], textColor=green, fontSize=18, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=styles["Normal"], textColor=colors.grey, fontSize=9)
    label = ParagraphStyle("lbl", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    val = ParagraphStyle("val", parent=styles["Normal"], fontSize=11)

    elems = []
    elems.append(Paragraph("KARTU HASIL UJIAN", h))
    elems.append(Paragraph("Computer Based Test", sub))
    elems.append(Spacer(1, 10 * mm))

    passed = attempt.get("score") is not None and attempt["score"] >= kkm
    score_txt = str(attempt["score"]) if attempt.get("score") is not None else "Menunggu Koreksi"
    info = [
        ["Nama Siswa", attempt.get("student_name", "-"), "Nilai Akhir", score_txt],
        ["NISN / NIP", attempt.get("student_identifier") or "-", "KKM", str(kkm)],
        ["Sesi Ujian", session["title"] if session else "-", "Status",
         "LULUS" if passed else ("BELUM LULUS" if attempt.get("score") is not None else "-")],
        ["Metode Nilai", "Berbobot" if pkg.get("scoring_method") == "weighted" else "Persentase",
         "Poin", f"{attempt.get('earned', 0)}/{attempt.get('total_possible', 0)}"],
    ]
    t = Table(info, colWidths=[32 * mm, 60 * mm, 28 * mm, 46 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
        ("TEXTCOLOR", (3, 0), (3, 0), terra if not passed else green),
        ("FONTNAME", (3, 0), (3, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0d8")),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 8 * mm))

    elems.append(Paragraph("Rincian Jawaban", ParagraphStyle("s2", parent=styles["Heading2"], textColor=green, fontSize=12)))
    elems.append(Spacer(1, 3 * mm))

    rows = [["No", "Soal", "Tipe", "Poin", "Hasil"]]
    tlabel = {"pg": "PG", "truefalse": "B/S", "essay": "Esai"}
    for i, d in enumerate(attempt.get("details", [])):
        q = qmap.get(d["question_id"], {})
        qtext = (q.get("text") or "")[:70] + ("..." if len(q.get("text") or "") > 70 else "")
        if d.get("type") == "essay":
            res = "Menunggu" if d.get("needs_grading") else "Dinilai"
        else:
            res = "Benar" if d.get("is_correct") else "Salah"
        rows.append([str(i + 1), Paragraph(qtext, ParagraphStyle("c", fontSize=8)),
                     tlabel.get(d.get("type"), "-"),
                     f"{d.get('points_earned', 0)}/{d.get('points_possible', 0)}", res])
    dt = Table(rows, colWidths=[10 * mm, 92 * mm, 16 * mm, 22 * mm, 22 * mm], repeatRows=1)
    dt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), green),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f6f0")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0d8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems.append(dt)
    elems.append(Spacer(1, 10 * mm))
    elems.append(Paragraph(f"Dicetak pada {datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M UTC')}", sub))

    doc.build(elems)
    buf.seek(0)
    fname = f"hasil-{attempt.get('student_name', 'siswa')}.pdf".replace(" ", "_")
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={fname}"})



# ------------------------------------------------------------------ IMAGE UPLOAD
ALLOWED_IMG = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
               "webp": "image/webp", "gif": "image/gif"}


async def fetch_image_to_storage(url: str, user_id: str) -> Optional[str]:
    """Download an image from a URL and store it. Returns storage path or None."""
    try:
        resp = requests.get(url, timeout=20, stream=True,
                            headers={"User-Agent": "Mozilla/5.0 (compatible; CBT-Ujian/1.0)"})
        resp.raise_for_status()
        data = resp.content
        if len(data) > 5 * 1024 * 1024:
            return None
        ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}.get(ct)
        if not ext:
            ext = url.rsplit(".", 1)[-1].lower().split("?")[0]
            if ext not in ALLOWED_IMG:
                return None
            ct = ALLOWED_IMG[ext]
        path = f"{APP_NAME}/questions/{user_id}/{new_id()}.{ext}"
        result = put_object(path, data, ct)
        await db.files.insert_one({
            "id": new_id(), "storage_path": result["path"], "original_filename": url,
            "content_type": ct, "size": result.get("size"), "is_deleted": False,
            "created_at": now_iso(),
        })
        return result["path"]
    except Exception:
        return None


@api_router.post("/uploads/image")
async def upload_image(file: UploadFile = File(...), user: dict = Depends(require_roles("admin", "guru"))):
    fname = file.filename or ""
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if ext not in ALLOWED_IMG:
        raise HTTPException(status_code=400, detail="Format harus png/jpg/webp/gif")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran gambar maksimal 5MB")
    ct = ALLOWED_IMG[ext]
    path = f"{APP_NAME}/questions/{user['id']}/{new_id()}.{ext}"
    try:
        result = put_object(path, data, ct)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengunggah gambar: {e}")
    await db.files.insert_one({
        "id": new_id(), "storage_path": result["path"], "original_filename": fname,
        "content_type": ct, "size": result.get("size"), "is_deleted": False,
        "created_at": now_iso(),
    })
    return {"path": result["path"]}


@api_router.get("/files/{path:path}")
async def get_file(path: str, authorization: Optional[str] = Header(None), auth: Optional[str] = Query(None)):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif auth:
        token = auth
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    try:
        data, content_type = get_object(path)
    except Exception:
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    return Response(content=data, media_type=record.get("content_type", content_type))


# ------------------------------------------------------------------ STUDENT REPORT PDF
@api_router.get("/report/student/{student_id}/pdf")
async def student_report_pdf(student_id: str, user: dict = Depends(get_current_user)):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart

    if student_id == "me":
        student_id = user["id"]
    if user["role"] == "siswa" and student_id != user["id"]:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    stu = await db.users.find_one({"_id": ObjectId(student_id)})
    if not stu:
        raise HTTPException(status_code=404, detail="Siswa tidak ditemukan")

    attempts = await db.attempts.find(
        {"student_id": student_id, "status": {"$ne": "berlangsung"}, **COUNTED_ONLY}, {"_id": 0}
    ).sort("submitted_at", 1).to_list(2000)
    pkgs = await db.packages.find({}, {"_id": 0, "id": 1, "category_id": 1}).to_list(2000)
    pkg_cat = {p["id"]: p.get("category_id") for p in pkgs}
    cats = await db.categories.find({}, {"_id": 0}).to_list(1000)
    cat_name = {c["id"]: c["name"] for c in cats}

    rows_data = []
    scores = []
    labels = []
    for a in attempts:
        s = await db.sessions.find_one({"id": a["session_id"]}, {"_id": 0})
        subj = cat_name.get(pkg_cat.get(a.get("package_id")), "Umum")
        kkm = s.get("kkm", 75) if s else 75
        sc = att_score(a)
        status = "Lulus" if (sc is not None and sc >= kkm) else ("Belum Lulus" if sc is not None else "Menunggu")
        rows_data.append([s["title"] if s else "-", subj, str(sc) if sc is not None else "-", str(kkm), status])
        if sc is not None:
            scores.append(sc)
            labels.append((s["title"] if s else "-")[:10])

    green = colors.HexColor("#1e3a30")
    terra = colors.HexColor("#c0563f")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=18 * mm, rightMargin=18 * mm)
    styles = getSampleStyleSheet()
    sub = ParagraphStyle("sub", parent=styles["Normal"], textColor=colors.grey, fontSize=9)
    elems = await _school_kop(styles, green, sub)
    elems += [Paragraph("RAPOR HASIL BELAJAR SISWA", ParagraphStyle("h", parent=styles["Title"], textColor=green, fontSize=18, spaceAfter=2)),
             Paragraph("Computer Based Test", sub), Spacer(1, 8 * mm)]

    avg = round(sum(scores) / len(scores), 1) if scores else 0
    info = [["Nama Siswa", stu["name"], "Rata-rata", str(avg)],
            ["NISN / NIP", stu.get("identifier", "") or "-", "Total Ujian", str(len(scores))]]
    t = Table(info, colWidths=[32 * mm, 62 * mm, 30 * mm, 42 * mm])
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                           ("TEXTCOLOR", (2, 0), (2, -1), colors.grey), ("FONTNAME", (3, 0), (3, 0), "Helvetica-Bold"),
                           ("TEXTCOLOR", (3, 0), (3, 0), green), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0d8"))]))
    elems += [t, Spacer(1, 8 * mm)]

    if scores:
        elems.append(Paragraph("Grafik Perkembangan Nilai", ParagraphStyle("s2", parent=styles["Heading2"], textColor=green, fontSize=12)))
        d = Drawing(460, 190)
        bc = VerticalBarChart()
        bc.x, bc.y, bc.height, bc.width = 30, 20, 150, 420
        bc.data = [scores]
        bc.categoryAxis.categoryNames = labels
        bc.categoryAxis.labels.fontSize = 6
        bc.categoryAxis.labels.angle = 30
        bc.categoryAxis.labels.dy = -6
        bc.valueAxis.valueMin, bc.valueAxis.valueMax, bc.valueAxis.valueStep = 0, 100, 20
        bc.bars[0].fillColor = green
        d.add(bc)
        elems += [d, Spacer(1, 6 * mm)]

    elems.append(Paragraph("Rincian Nilai", ParagraphStyle("s3", parent=styles["Heading2"], textColor=green, fontSize=12)))
    trows = [["Sesi Ujian", "Mapel", "Nilai", "KKM", "Status"]] + (rows_data or [["Belum ada ujian", "-", "-", "-", "-"]])
    dt = Table(trows, colWidths=[70 * mm, 40 * mm, 20 * mm, 18 * mm, 26 * mm], repeatRows=1)
    dt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), green), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f6f0")]),
                            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0d8")),
                            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    elems += [dt, Spacer(1, 10 * mm),
              Paragraph(f"Dicetak pada {datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M UTC')}", sub)]
    doc.build(elems)
    buf.seek(0)
    fname = f"rapor-{stu['name']}.pdf".replace(" ", "_")
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={fname}"})


# ------------------------------------------------------------------ CLASS REPORT PDF (bulk)
@api_router.get("/report/class/{class_id}/pdf")
async def class_report_pdf(class_id: str, user: dict = Depends(require_roles("admin", "guru"))):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart

    cls = await db.classes.find_one({"id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    sids = cls.get("student_ids", [])
    students = []
    if sids:
        docs = await db.users.find({"_id": {"$in": [ObjectId(s) for s in sids]}}).to_list(2000)
        students = sorted(docs, key=lambda u: u["name"].lower())
    pkgs = await db.packages.find({}, {"_id": 0, "id": 1, "category_id": 1}).to_list(2000)
    pkg_cat = {p["id"]: p.get("category_id") for p in pkgs}
    cats = await db.categories.find({}, {"_id": 0}).to_list(1000)
    cat_name = {c["id"]: c["name"] for c in cats}

    green = colors.HexColor("#1e3a30")
    styles = getSampleStyleSheet()
    sub = ParagraphStyle("sub", parent=styles["Normal"], textColor=colors.grey, fontSize=9)
    name_style = ParagraphStyle("nm", parent=styles["Heading1"], textColor=green, fontSize=15)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm)
    elems = await _school_kop(styles, green, sub)
    elems += [Paragraph(f"RAPOR KELAS {cls['name'].upper()}", ParagraphStyle("h", parent=styles["Title"], textColor=green, fontSize=18, spaceAfter=2)),
             Paragraph(f"{len(students)} siswa · Computer Based Test", sub), Spacer(1, 8 * mm)]
    if not students:
        elems.append(Paragraph("Belum ada siswa di kelas ini.", styles["Normal"]))

    for i, stu in enumerate(students):
        if i > 0:
            elems.append(PageBreak())
        sid = str(stu["_id"])
        attempts = await db.attempts.find({"student_id": sid, "status": {"$ne": "berlangsung"}, **COUNTED_ONLY}, {"_id": 0}).sort("submitted_at", 1).to_list(2000)
        rows_data, scores, labels = [], [], []
        for a in attempts:
            s = await db.sessions.find_one({"id": a["session_id"]}, {"_id": 0})
            subj = cat_name.get(pkg_cat.get(a.get("package_id")), "Umum")
            kkm = s.get("kkm", 75) if s else 75
            sc = att_score(a)
            status = "Lulus" if (sc is not None and sc >= kkm) else ("Belum Lulus" if sc is not None else "Menunggu")
            rows_data.append([s["title"] if s else "-", subj, str(sc) if sc is not None else "-", str(kkm), status])
            if sc is not None:
                scores.append(sc)
                labels.append((s["title"] if s else "-")[:10])
        elems.append(Paragraph(f"Rapor: {stu['name']}", name_style))
        avg = round(sum(scores) / len(scores), 1) if scores else 0
        info = [["Nama", stu["name"], "Rata-rata", str(avg)],
                ["NISN/NIP", stu.get("identifier", "") or "-", "Total Ujian", str(len(scores))]]
        t = Table(info, colWidths=[28 * mm, 64 * mm, 28 * mm, 42 * mm])
        t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                               ("TEXTCOLOR", (2, 0), (2, -1), colors.grey), ("FONTNAME", (3, 0), (3, 0), "Helvetica-Bold"),
                               ("TEXTCOLOR", (3, 0), (3, 0), green), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0d8"))]))
        elems += [t, Spacer(1, 5 * mm)]
        if scores:
            d = Drawing(460, 170)
            bc = VerticalBarChart()
            bc.x, bc.y, bc.height, bc.width = 30, 15, 135, 420
            bc.data = [scores]
            bc.categoryAxis.categoryNames = labels
            bc.categoryAxis.labels.fontSize = 6
            bc.categoryAxis.labels.angle = 30
            bc.categoryAxis.labels.dy = -6
            bc.valueAxis.valueMin, bc.valueAxis.valueMax, bc.valueAxis.valueStep = 0, 100, 20
            bc.bars[0].fillColor = green
            d.add(bc)
            elems += [d, Spacer(1, 4 * mm)]
        trows = [["Sesi Ujian", "Mapel", "Nilai", "KKM", "Status"]] + (rows_data or [["Belum ada ujian", "-", "-", "-", "-"]])
        dt = Table(trows, colWidths=[70 * mm, 40 * mm, 20 * mm, 18 * mm, 26 * mm], repeatRows=1)
        dt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), green), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                ("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f6f0")]),
                                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0d8")),
                                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        elems.append(dt)

    doc.build(elems)
    buf.seek(0)
    fname = f"rapor-kelas-{cls['name']}.pdf".replace(" ", "_")
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={fname}"})


# ------------------------------------------------------------------ AUTO-SUBMIT (cron)
async def run_auto_submit():
    now = datetime.now(timezone.utc)
    attempts = await db.attempts.find({"status": "berlangsung"}, {"_id": 0}).to_list(5000)
    count = 0
    for att in attempts:
        session = await db.sessions.find_one({"id": att["session_id"]}, {"_id": 0})
        if not session:
            continue
        try:
            end = parse_dt(session["end_time"])
            started = parse_dt(att["started_at"])
        except Exception:
            continue
        deadline = min(end, started + timedelta(minutes=session.get("duration_minutes", 60)))
        if now >= deadline:
            await finalize_attempt(att, att.get("answers", {}))
            count += 1
    logging.getLogger(__name__).info(f"Auto-submit finalized {count} attempt(s)")
    return count


@api_router.post("/cron/auto-submit")
async def cron_auto_submit(request: Request, background: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not secret or not hmac.compare_digest(token, secret):
        raise HTTPException(status_code=401, detail="Unauthorized")
    background.add_task(run_auto_submit)
    return {"accepted": True}


# ------------------------------------------------------------------ ITEM ANALYTICS
@api_router.get("/analytics/session/{session_id}")
async def analytics_session(session_id: str, user: dict = Depends(require_roles("admin", "guru"))):
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    pkg = await db.packages.find_one({"id": session["package_id"]}, {"_id": 0})
    qlist = await db.questions.find({"id": {"$in": pkg.get("question_ids", [])}}, {"_id": 0}).to_list(2000)
    qmap = {q["id"]: q for q in qlist}
    settings = await db.settings.find_one({"key": "difficulty"}, {"_id": 0})
    pkg_easy = pkg.get("easy_min")
    pkg_med = pkg.get("medium_min")
    if pkg_easy is not None and pkg_med is not None:
        easy_min, medium_min, source = pkg_easy, pkg_med, "paket"
    else:
        easy_min = settings.get("easy_min", 70) if settings else 70
        medium_min = settings.get("medium_min", 40) if settings else 40
        source = "global"
    attempts = await db.attempts.find(
        {"session_id": session_id, "status": {"$in": ["selesai", "menunggu_koreksi"]}}, {"_id": 0}
    ).to_list(5000)

    items = []
    for qid in pkg.get("question_ids", []):
        q = qmap.get(qid)
        if not q:
            continue
        total = answered = correct_count = 0
        pts_earned = pts_possible = 0.0
        for att in attempts:
            det = next((d for d in att.get("details", []) if d["question_id"] == qid), None)
            if not det:
                continue
            total += 1
            if det.get("answer") not in (None, ""):
                answered += 1
            if q["type"] in ("pg", "truefalse"):
                if det.get("is_correct"):
                    correct_count += 1
            else:
                pts_earned += det.get("points_earned", 0) or 0
                pts_possible += det.get("points_possible", 0) or 0
        if q["type"] in ("pg", "truefalse"):
            p = (correct_count / total) if total else 0
        else:
            p = (pts_earned / pts_possible) if pts_possible else 0
        pct = round(p * 100, 1)
        difficulty = "Mudah" if pct >= easy_min else ("Sedang" if pct >= medium_min else "Sulit")
        items.append({
            "question_id": qid, "text": q["text"], "type": q["type"],
            "total": total, "answered": answered,
            "correct": correct_count if q["type"] in ("pg", "truefalse") else None,
            "percent_correct": pct, "difficulty": difficulty,
        })
    return {"session_title": session["title"], "participants": len(attempts),
            "items": items, "thresholds": {"easy_min": easy_min, "medium_min": medium_min, "source": source}}


# ------------------------------------------------------------------ CLASS GRADE EXPORT (Excel)
@api_router.get("/export/class/{class_id}/xlsx")
async def export_class_grades(class_id: str, user: dict = Depends(require_roles("admin", "guru"))):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    cls = await db.classes.find_one({"id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    sids = cls.get("student_ids", [])
    students = []
    if sids:
        docs = await db.users.find({"_id": {"$in": [ObjectId(s) for s in sids]}}).to_list(2000)
        students = sorted([clean_user(u) for u in docs], key=lambda x: x["name"].lower())
    sessions = await db.sessions.find(
        {"$or": [{"class_ids": class_id}, {"class_ids": {"$size": 0}}, {"class_ids": {"$exists": False}}]},
        {"_id": 0}
    ).sort("start_time", 1).to_list(1000)

    wb = Workbook()
    ws = wb.active
    ws.title = "Rekap Nilai"
    ws.append([f"REKAP NILAI - {cls['name']}"])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(4, 4 + len(sessions)))
    ws["A1"].font = Font(bold=True, size=14, color="1E3A30")
    header = ["No", "Nama Siswa", "NISN/NIP"] + [s["title"] for s in sessions] + ["Rata-rata"]
    ws.append(header)
    green = PatternFill("solid", fgColor="1E3A30")
    thin = Side(style="thin", color="D9D9CF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for cell in ws[2]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = green
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    for i, st in enumerate(students):
        row = [i + 1, st["name"], st.get("identifier", "")]
        scores = []
        for s in sessions:
            att = await db.attempts.find_one(
                {"session_id": s["id"], "student_id": st["id"], "status": {"$ne": "berlangsung"}, **COUNTED_ONLY},
                {"_id": 0})
            val = att_score(att) if att else None
            row.append(val if val is not None else "-")
            if val is not None:
                scores.append(val)
        row.append(round(sum(scores) / len(scores), 1) if scores else "-")
        ws.append(row)
        for cell in ws[ws.max_row]:
            cell.border = border
            if cell.column > 3:
                cell.alignment = Alignment(horizontal="center")

    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 16
    from openpyxl.utils import get_column_letter
    for idx in range(4, 4 + len(sessions) + 1):
        ws.column_dimensions[get_column_letter(idx)].width = 16

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = f"rekap-nilai-{cls['name']}.xlsx".replace(" ", "_")
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"})


# ------------------------------------------------------------------ EXAM CARDS (Kartu Peserta)
def _sized_logo(logo_path, mm_size):
    from reportlab.platypus import Image
    from reportlab.lib.units import mm
    try:
        if not logo_path:
            return None
        data, _ = get_object(logo_path)
        return Image(io.BytesIO(data), width=mm_size * mm, height=mm_size * mm)
    except Exception:
        return None


@api_router.get("/cards/class/{class_id}/pdf")
async def exam_cards_pdf(class_id: str, session_id: Optional[str] = None,
                         user: dict = Depends(require_roles("admin", "guru"))):
    """Kartu peserta ujian per kelas: nama, NISN, kelas, akun, dan daftar sesi.

    4 kartu per halaman A4 (2x2) dengan garis potong, siap dicetak & digunting.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    cls = await db.classes.find_one({"id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    sids = cls.get("student_ids", [])
    students = []
    if sids:
        docs = await db.users.find({"_id": {"$in": [ObjectId(s) for s in sids]}}).to_list(2000)
        students = sorted(docs, key=lambda u: u["name"].lower())

    query = {"$or": [{"class_ids": class_id}, {"class_ids": {"$size": 0}}, {"class_ids": {"$exists": False}}]}
    if session_id:
        query = {"id": session_id}
    sessions = await db.sessions.find(query, {"_id": 0}).sort("start_time", 1).to_list(1000)
    pkg_titles = {}
    for s in sessions:
        pkg = await db.packages.find_one({"id": s["package_id"]}, {"_id": 0, "title": 1})
        pkg_titles[s["id"]] = pkg["title"] if pkg else "-"
    school = await db.settings.find_one({"key": "school"}, {"_id": 0}) or {}

    green = colors.HexColor("#1e3a30")
    terra = colors.HexColor("#c0563f")
    grey = colors.HexColor("#7a7a70")
    lightline = colors.HexColor("#d9d9cf")

    styles = getSampleStyleSheet()
    st_school = ParagraphStyle("cs", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5,
                               textColor=green, leading=10)
    st_addr = ParagraphStyle("ca", parent=styles["Normal"], fontSize=6.5, textColor=grey, leading=8)
    st_title = ParagraphStyle("ct", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5,
                              textColor=colors.white, alignment=1, leading=12)
    st_label = ParagraphStyle("cl", parent=styles["Normal"], fontSize=6.5, textColor=grey, leading=8)
    st_value = ParagraphStyle("cv", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9,
                              textColor=colors.black, leading=11)
    st_small = ParagraphStyle("csm", parent=styles["Normal"], fontSize=6, textColor=grey, leading=7.5)
    st_sess = ParagraphStyle("cse", parent=styles["Normal"], fontSize=6.5, leading=8.5)

    CARD_W = 88 * mm

    def build_card(stu):
        head_txt = []
        if school.get("name"):
            head_txt.append(Paragraph(school["name"].upper(), st_school))
        if school.get("address"):
            head_txt.append(Paragraph(school["address"], st_addr))
        if not head_txt:
            head_txt.append(Paragraph("CBT UJIAN ONLINE", st_school))
        logo = _sized_logo(school.get("logo_path"), 12)
        if logo:
            head = Table([[logo, head_txt]], colWidths=[14 * mm, CARD_W - 22 * mm])
            head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                      ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                                      ("TOPPADDING", (0, 0), (-1, -1), 0),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        else:
            head = Table([[head_txt]], colWidths=[CARD_W - 8 * mm])
            head.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                      ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))

        band = Table([[Paragraph("KARTU PESERTA UJIAN", st_title)]], colWidths=[CARD_W - 8 * mm])
        band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), green),
                                  ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))

        ident = Table([
            [Paragraph("Nama Peserta", st_label), Paragraph("NISN / NIP", st_label)],
            [Paragraph(stu["name"], st_value), Paragraph(stu.get("identifier") or "-", st_value)],
            [Paragraph("Kelas", st_label), Paragraph("Akun Login", st_label)],
            [Paragraph(cls["name"], st_value), Paragraph(stu.get("email", "-"), st_sess)],
        ], colWidths=[(CARD_W - 8 * mm) * 0.52, (CARD_W - 8 * mm) * 0.48])
        ident.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))

        rows = [[Paragraph("<b>Sesi Ujian</b>", st_sess), Paragraph("<b>Jadwal</b>", st_sess),
                 Paragraph("<b>Durasi</b>", st_sess)]]
        for s in sessions[:5]:
            rows.append([
                Paragraph(f"{s['title']}<br/><font size=5 color='#7a7a70'>{pkg_titles.get(s['id'], '-')}</font>", st_sess),
                Paragraph(fmt_local(s["start_time"]).replace(" WIB", ""), st_sess),
                Paragraph(f"{s.get('duration_minutes', 0)}'", st_sess),
            ])
        if len(sessions) > 5:
            rows.append([Paragraph(f"+{len(sessions) - 5} sesi lainnya", st_small), "", ""])
        if not sessions:
            rows.append([Paragraph("Belum ada sesi terjadwal", st_small), "", ""])
        w = CARD_W - 8 * mm
        sess_t = Table(rows, colWidths=[w * 0.5, w * 0.36, w * 0.14])
        sess_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f1ea")),
            ("TEXTCOLOR", (0, 0), (-1, 0), green),
            ("GRID", (0, 0), (-1, -1), 0.25, lightline),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))

        foot = Table([[Paragraph("Kartu ini wajib dibawa saat ujian.", st_small),
                       Paragraph("Tanda tangan peserta<br/><br/>__________________", st_small)]],
                     colWidths=[w * 0.55, w * 0.45])
        foot.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                  ("TOPPADDING", (0, 0), (-1, -1), 2), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                  ("ALIGN", (1, 0), (1, 0), "RIGHT")]))

        inner = [head, Spacer(1, 3), band, Spacer(1, 3), ident, Spacer(1, 3), sess_t, Spacer(1, 2), foot]
        card = Table([[inner]], colWidths=[CARD_W], rowHeights=[68 * mm])
        card.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, green),
            ("LINEBEFORE", (0, 0), (0, 0), 2.5, terra),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ]))
        return card

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=12 * mm, bottomMargin=12 * mm,
                            leftMargin=10 * mm, rightMargin=10 * mm,
                            title=f"Kartu Peserta {cls['name']}")
    elems = []
    if not students:
        elems.append(Paragraph(f"Belum ada siswa di kelas {cls['name']}.", styles["Normal"]))
    else:
        pairs = [students[i:i + 2] for i in range(0, len(students), 2)]
        for pi, pair in enumerate(pairs):
            cards = [build_card(s) for s in pair]
            if len(cards) == 1:
                cards.append("")
            grid = Table([cards], colWidths=[CARD_W, CARD_W])
            grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                      ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                                      ("TOPPADDING", (0, 0), (-1, -1), 0),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm)]))
            elems.append(KeepTogether(grid))
    doc.build(elems)
    buf.seek(0)
    fname = f"kartu-peserta-{cls['name']}.pdf".replace(" ", "_").replace("/", "-")
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={fname}"})


# ------------------------------------------------------------------ SESSION RESULT EXPORT (Excel)
@api_router.get("/export/session/{session_id}/xlsx")
async def export_session_results(session_id: str, user: dict = Depends(require_roles("admin", "guru"))):
    """Rekap nilai satu sesi ujian dalam Excel bertema, siap cetak/arsip."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    await enrich_session(session)
    pkg = await db.packages.find_one({"id": session["package_id"]}, {"_id": 0}) or {}
    school = await db.settings.find_one({"key": "school"}, {"_id": 0}) or {}
    classes = await db.classes.find({}, {"_id": 0}).to_list(1000)
    cls_by_student = {}
    for c in classes:
        for sid in c.get("student_ids", []):
            cls_by_student.setdefault(sid, []).append(c["name"])

    attempts = await db.attempts.find({"session_id": session_id}, {"_id": 0}).to_list(5000)
    attempts.sort(key=lambda a: (a.get("student_name", "").lower(), a.get("attempt_number", 1)))
    max_att = int(session.get("max_attempts") or 1)
    kkm = float(session.get("kkm", 75) or 75)
    policy = session.get("score_policy") or "tertinggi"
    policy_label = {"tertinggi": "Nilai tertinggi", "terakhir": "Nilai percobaan terakhir",
                    "rata": "Rata-rata semua percobaan"}.get(policy, policy)

    GREEN, TERRA, LIGHT = "1E3A30", "C0563F", "F1F1EA"
    thin = Side(style="thin", color="D9D9CF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Rekap Nilai"
    ws.sheet_view.showGridLines = False
    ncols = 10 if max_att > 1 else 8
    last_col = get_column_letter(ncols)

    def band(row, text, size=14, color=GREEN, bold=True, fill=None, height=None):
        ws.merge_cells(f"A{row}:{last_col}{row}")
        c = ws[f"A{row}"]
        c.value = text
        c.font = Font(bold=bold, size=size, color="FFFFFF" if fill else color)
        c.alignment = Alignment(horizontal="center", vertical="center")
        if fill:
            c.fill = PatternFill("solid", fgColor=fill)
        if height:
            ws.row_dimensions[row].height = height

    r = 1
    if school.get("name"):
        band(r, school["name"].upper(), size=14, height=22); r += 1
    if school.get("address"):
        band(r, school["address"], size=9, bold=False, color="7A7A70"); r += 1
    band(r, "REKAP NILAI UJIAN", size=15, fill=GREEN, height=26); r += 1
    band(r, session["title"], size=11, bold=False, color=TERRA); r += 2

    meta = [
        ("Paket Soal", pkg.get("title", "-"), "Jumlah Soal", len(pkg.get("question_ids", []))),
        ("Jadwal", f"{fmt_local(session['start_time'])} s/d {fmt_local(session['end_time'])}",
         "Durasi", f"{session.get('duration_minutes', 0)} menit"),
        ("KKM", kkm, "Maks Percobaan", f"{max_att}x" + (f" · {policy_label}" if max_att > 1 else "")),
    ]
    for label1, val1, label2, val2 in meta:
        ws.cell(row=r, column=1, value=label1).font = Font(bold=True, size=9, color="7A7A70")
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=max(2, ncols - 4))
        ws.cell(row=r, column=2, value=val1).font = Font(size=9)
        ws.cell(row=r, column=ncols - 3, value=label2).font = Font(bold=True, size=9, color="7A7A70")
        ws.merge_cells(start_row=r, start_column=ncols - 2, end_row=r, end_column=ncols)
        ws.cell(row=r, column=ncols - 2, value=val2).font = Font(size=9)
        r += 1
    r += 1

    header = ["No", "Nama Siswa", "NISN / NIP", "Kelas"]
    if max_att > 1:
        header += ["Percobaan", "Dipakai"]
    header += ["Status", "Nilai", "KKM", "Keterangan"]
    header_row = r
    for i, h in enumerate(header, start=1):
        c = ws.cell(row=header_row, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF", size=10)
        c.fill = PatternFill("solid", fgColor=GREEN)
        c.alignment = center
        c.border = border
    ws.row_dimensions[header_row].height = 24
    r += 1

    counted_scores, passed = [], 0
    no = 0
    for a in attempts:
        is_counted = a.get("counted") is not False
        sc = att_score(a)
        if is_counted:
            no += 1
            if sc is not None:
                counted_scores.append(sc)
                if sc >= kkm:
                    passed += 1
        note = "Menunggu koreksi" if sc is None else ("Lulus" if sc >= kkm else "Belum Lulus")
        row = [no if is_counted else "", a.get("student_name", "-"), a.get("student_identifier") or "-",
               ", ".join(cls_by_student.get(a.get("student_id"), [])) or "-"]
        if max_att > 1:
            row += [a.get("attempt_number", 1), "Ya" if is_counted else "-"]
        row += [STATUS_ID.get(a.get("status"), a.get("status")), sc if sc is not None else "-", kkm, note]
        ws.append(row)
        rr = ws.max_row
        for i in range(1, ncols + 1):
            c = ws.cell(row=rr, column=i)
            c.border = border
            c.font = Font(size=10, color="000000" if is_counted else "8A8A80")
            if i != 2:
                c.alignment = center
        if rr % 2 == 0:
            for i in range(1, ncols + 1):
                if not ws.cell(row=rr, column=i).fill.fgColor.rgb or ws.cell(row=rr, column=i).fill.patternType is None:
                    ws.cell(row=rr, column=i).fill = PatternFill("solid", fgColor=LIGHT)
        nilai_cell = ws.cell(row=rr, column=ncols - 2)
        if sc is not None:
            nilai_cell.font = Font(bold=True, size=10, color=GREEN if sc >= kkm else TERRA)
        note_cell = ws.cell(row=rr, column=ncols)
        if sc is not None:
            note_cell.font = Font(size=10, color=GREEN if sc >= kkm else TERRA)

    if not attempts:
        ws.append(["-"] * ncols)
        ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=ncols)
        c = ws.cell(row=ws.max_row, column=1, value="Belum ada peserta yang mengumpulkan.")
        c.alignment = center
        c.font = Font(size=10, italic=True, color="8A8A80")

    # Ringkasan
    sr = ws.max_row + 2
    avg = round(sum(counted_scores) / len(counted_scores), 2) if counted_scores else "-"
    summary = [
        ("Jumlah Peserta", no),
        ("Sudah Dinilai", len(counted_scores)),
        ("Rata-rata Nilai", avg),
        ("Nilai Tertinggi", max(counted_scores) if counted_scores else "-"),
        ("Nilai Terendah", min(counted_scores) if counted_scores else "-"),
        ("Tuntas (≥ KKM)", f"{passed} siswa" + (f" · {round(passed / no * 100)}%" if no else "")),
        ("Belum Tuntas", f"{max(0, len(counted_scores) - passed)} siswa"),
    ]
    ws.merge_cells(start_row=sr, start_column=1, end_row=sr, end_column=3)
    hc = ws.cell(row=sr, column=1, value="RINGKASAN")
    hc.font = Font(bold=True, size=10, color="FFFFFF")
    hc.fill = PatternFill("solid", fgColor=GREEN)
    hc.alignment = Alignment(horizontal="center")
    for i, (label, val) in enumerate(summary, start=1):
        lc = ws.cell(row=sr + i, column=1, value=label)
        lc.font = Font(size=10, color="7A7A70")
        lc.border = border
        ws.merge_cells(start_row=sr + i, start_column=2, end_row=sr + i, end_column=3)
        vc = ws.cell(row=sr + i, column=2, value=val)
        vc.font = Font(bold=True, size=10, color=GREEN)
        vc.border = border
        ws.cell(row=sr + i, column=3).border = border

    foot = sr + len(summary) + 2
    ws.merge_cells(start_row=foot, start_column=1, end_row=foot, end_column=ncols)
    fc = ws.cell(row=foot, column=1,
                 value=f"Dicetak {fmt_local(now_iso())} · CBT Ujian Online")
    fc.font = Font(size=8, italic=True, color="9A9A90")

    widths = {"A": 6, "B": 28, "C": 16, "D": 16}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    for idx in range(5, ncols + 1):
        ws.column_dimensions[get_column_letter(idx)].width = 14
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = f"rekap-nilai-{session['title']}.xlsx".replace(" ", "_").replace("/", "-")
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"})


# ------------------------------------------------------------------ DASHBOARD
@api_router.get("/dashboard/stats")
async def dashboard_stats(user: dict = Depends(require_roles("admin", "guru"))):
    students = await db.users.count_documents({"role": "siswa"})
    teachers = await db.users.count_documents({"role": "guru"})
    questions = await db.questions.count_documents({})
    packages = await db.packages.count_documents({})
    sessions = await db.sessions.count_documents({})
    attempts = await db.attempts.find({"status": "selesai", **COUNTED_ONLY},
                                      {"_id": 0, "score": 1, "effective_score": 1}).to_list(5000)
    scores = [att_score(a) for a in attempts if att_score(a) is not None]
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    pending = await db.attempts.count_documents({"status": "menunggu_koreksi"})
    return {"students": students, "teachers": teachers, "questions": questions,
            "packages": packages, "sessions": sessions, "avg_score": avg,
            "completed_attempts": len(scores), "pending_grading": pending}


# ------------------------------------------------------------------ CLASS ANALYTICS
@api_router.get("/analytics/classes")
async def analytics_classes(user: dict = Depends(require_roles("admin", "guru"))):
    classes = await db.classes.find({}, {"_id": 0}).to_list(1000)
    result = []
    for c in classes:
        sids = c.get("student_ids", [])
        avg = 0
        completed = 0
        if sids:
            attempts = await db.attempts.find(
                {"student_id": {"$in": sids}, "status": "selesai", **COUNTED_ONLY},
                {"_id": 0, "score": 1, "effective_score": 1}).to_list(5000)
            scores = [att_score(a) for a in attempts if att_score(a) is not None]
            avg = round(sum(scores) / len(scores), 1) if scores else 0
            completed = len(scores)
        result.append({"class_id": c["id"], "name": c["name"], "avg_score": avg,
                       "completed": completed, "students": len(sids)})
    sessions = await db.sessions.find({}, {"_id": 0}).sort("start_time", 1).to_list(1000)
    trend = []
    for s in sessions:
        atts = await db.attempts.find({"session_id": s["id"], "status": "selesai", **COUNTED_ONLY},
                                      {"_id": 0, "score": 1, "effective_score": 1}).to_list(5000)
        sc = [att_score(a) for a in atts if att_score(a) is not None]
        if sc:
            trend.append({"session": s["title"][:18], "avg": round(sum(sc) / len(sc), 1)})
    return {"classes": result, "trend": trend}


# ------------------------------------------------------------------ SUBJECT STATS
@api_router.get("/analytics/subjects")
async def analytics_subjects(user: dict = Depends(require_roles("admin", "guru"))):
    cats = await db.categories.find({}, {"_id": 0}).to_list(1000)
    pkgs = await db.packages.find({}, {"_id": 0, "id": 1, "category_id": 1}).to_list(2000)
    pkg_cat = {p["id"]: p.get("category_id") for p in pkgs}
    atts = await db.attempts.find({"status": "selesai", **COUNTED_ONLY},
                                  {"_id": 0, "score": 1, "effective_score": 1, "package_id": 1}).to_list(20000)
    agg = {}
    for a in atts:
        if att_score(a) is None:
            continue
        agg.setdefault(pkg_cat.get(a.get("package_id")), []).append(att_score(a))
    result = []
    for c in cats:
        sc = agg.get(c["id"], [])
        result.append({"category_id": c["id"], "name": c["name"],
                       "avg_score": round(sum(sc) / len(sc), 1) if sc else 0, "attempts": len(sc)})
    uncat = agg.get(None, [])
    if uncat:
        result.append({"category_id": None, "name": "Umum",
                       "avg_score": round(sum(uncat) / len(uncat), 1), "attempts": len(uncat)})
    result.sort(key=lambda r: -r["avg_score"])
    return result


# ------------------------------------------------------------------ NOTIFICATIONS
@api_router.get("/notifications")
async def notifications(user: dict = Depends(require_roles("siswa"))):
    my_classes = await db.classes.find({"student_ids": user["id"]}, {"_id": 0, "id": 1}).to_list(1000)
    my_class_ids = {c["id"] for c in my_classes}
    sessions = await db.sessions.find({}, {"_id": 0}).to_list(1000)
    now = datetime.now(timezone.utc)
    notes = []
    for s in sessions:
        targets = s.get("class_ids") or []
        if targets and not (set(targets) & my_class_ids):
            continue
        try:
            start = parse_dt(s["start_time"])
            end = parse_dt(s["end_time"])
        except Exception:
            continue
        att = await db.attempts.find_one({"session_id": s["id"], "student_id": user["id"]}, {"_id": 0, "status": 1})
        done = att and att["status"] != "berlangsung"
        if s.get("announcement"):
            notes.append({"id": f"{s['id']}-ann", "type": "info", "title": s["title"],
                          "message": s["announcement"], "time": s["start_time"]})
        if not done:
            if now < start:
                notes.append({"id": f"{s['id']}-open", "type": "upcoming", "title": s["title"],
                              "message": "Ujian akan segera dibuka.", "time": s["start_time"]})
            elif now <= end:
                notes.append({"id": f"{s['id']}-live", "type": "live", "title": s["title"],
                              "message": "Ujian sedang berlangsung — segera kerjakan.", "time": s["start_time"]})
    notes.sort(key=lambda n: n["time"], reverse=True)
    return notes


# ------------------------------------------------------------------ SCHOOL SETTINGS
@api_router.get("/settings/school")
async def get_school(user: dict = Depends(get_current_user)):
    doc = await db.settings.find_one({"key": "school"}, {"_id": 0}) or {}
    return {"name": doc.get("name", ""), "address": doc.get("address", ""),
            "logo_path": doc.get("logo_path"), "theme_color": doc.get("theme_color")}


@api_router.put("/settings/school")
async def set_school(body: SchoolBody, user: dict = Depends(require_roles("admin"))):
    """Patch identitas sekolah — field yang tidak dikirim tidak menghapus data lama."""
    current = await db.settings.find_one({"key": "school"}, {"_id": 0}) or {}
    data = body.model_dump()
    merged = {"key": "school", "name": data.get("name") or "", "address": data.get("address") or "",
              "logo_path": data.get("logo_path")}
    # theme_color is optional in some clients; keep the stored value when it is omitted
    merged["theme_color"] = data.get("theme_color") or current.get("theme_color")
    await db.settings.update_one({"key": "school"}, {"$set": merged}, upsert=True)
    merged.pop("key", None)
    return merged


def _logo_flowable(logo_path):
    from reportlab.platypus import Image
    from reportlab.lib.units import mm
    try:
        if not logo_path:
            return None
        data, _ = get_object(logo_path)
        return Image(io.BytesIO(data), width=18 * mm, height=18 * mm)
    except Exception:
        return None


async def _school_kop(styles, green, sub):
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    school = await db.settings.find_one({"key": "school"}, {"_id": 0}) or {}
    if not (school.get("name") or school.get("logo_path")):
        return []
    txt = []
    if school.get("name"):
        txt.append(Paragraph(school["name"], ParagraphStyle("sn", parent=styles["Title"], textColor=green, fontSize=15, spaceAfter=0)))
    if school.get("address"):
        txt.append(Paragraph(school["address"], sub))
    logo = _logo_flowable(school.get("logo_path"))
    if logo:
        t = Table([[logo, txt]], colWidths=[22 * 2.83, None])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
        head = [t]
    else:
        head = txt
    from reportlab.lib import colors
    line = Table([[""]], colWidths=[520 * 0.35])
    return head + [Spacer(1, 6)]


# ------------------------------------------------------------------ DIFFICULTY SETTINGS
@api_router.get("/settings/difficulty")
async def get_difficulty(user: dict = Depends(require_roles("admin", "guru"))):
    doc = await db.settings.find_one({"key": "difficulty"}, {"_id": 0})
    if not doc:
        return {"easy_min": 70, "medium_min": 40}
    return {"easy_min": doc.get("easy_min", 70), "medium_min": doc.get("medium_min", 40)}


@api_router.put("/settings/difficulty")
async def set_difficulty(body: DifficultyBody, user: dict = Depends(require_roles("admin", "guru"))):
    easy = max(1.0, min(100.0, float(body.easy_min)))
    medium = max(0.0, min(99.0, float(body.medium_min)))
    if medium >= easy:
        raise HTTPException(status_code=400, detail="Ambang 'Sedang' harus lebih kecil dari 'Mudah'")
    await db.settings.update_one(
        {"key": "difficulty"},
        {"$set": {"key": "difficulty", "easy_min": easy, "medium_min": medium}},
        upsert=True)
    return {"easy_min": easy, "medium_min": medium}


# ------------------------------------------------------------------ LEADERBOARD
async def compute_class_leaderboard(cls: dict, category_id: str = None) -> list:
    sids = cls.get("student_ids", [])
    if not sids:
        return []
    pkg_ids = None
    if category_id:
        pkgs = await db.packages.find({"category_id": category_id}, {"_id": 0, "id": 1}).to_list(2000)
        pkg_ids = {p["id"] for p in pkgs}
    docs = await db.users.find({"_id": {"$in": [ObjectId(s) for s in sids]}}).to_list(2000)
    rows = []
    for u in docs:
        uid = str(u["_id"])
        atts = await db.attempts.find({"student_id": uid, "status": "selesai", **COUNTED_ONLY},
                                      {"_id": 0, "score": 1, "effective_score": 1, "package_id": 1}).to_list(5000)
        scores = [att_score(a) for a in atts
                  if att_score(a) is not None and (pkg_ids is None or a.get("package_id") in pkg_ids)]
        rows.append({
            "student_id": uid, "name": u["name"], "identifier": u.get("identifier", ""),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "completed": len(scores),
        })
    rows.sort(key=lambda r: (-r["avg_score"], r["name"].lower()))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows


@api_router.get("/leaderboard/class/{class_id}")
async def leaderboard_class(class_id: str, user: dict = Depends(require_roles("admin", "guru"))):
    cls = await db.classes.find_one({"id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    return {"class_name": cls["name"], "rows": await compute_class_leaderboard(cls)}


@api_router.get("/leaderboard/me")
async def leaderboard_me(category_id: Optional[str] = None, user: dict = Depends(require_roles("siswa"))):
    classes = await db.classes.find({"student_ids": user["id"]}, {"_id": 0}).to_list(1000)
    out = []
    for c in classes:
        out.append({"class_id": c["id"], "class_name": c["name"],
                    "rows": await compute_class_leaderboard(c, category_id)})
    return out


async def compute_global_leaderboard(start=None, end=None, category_id=None):
    students = await db.users.find({"role": "siswa"}).to_list(5000)
    classes = await db.classes.find({}, {"_id": 0}).to_list(1000)
    cls_by_student = {}
    for c in classes:
        for sid in c.get("student_ids", []):
            cls_by_student.setdefault(sid, []).append(c["name"])
    pkg_ids = None
    if category_id:
        pkgs = await db.packages.find({"category_id": category_id}, {"_id": 0, "id": 1}).to_list(2000)
        pkg_ids = {p["id"] for p in pkgs}
    rows = []
    for u in students:
        uid = str(u["_id"])
        atts = await db.attempts.find(
            {"student_id": uid, "status": "selesai", **COUNTED_ONLY},
            {"_id": 0, "score": 1, "effective_score": 1, "submitted_at": 1, "package_id": 1}).to_list(5000)
        scores = []
        for a in atts:
            if att_score(a) is None:
                continue
            if pkg_ids is not None and a.get("package_id") not in pkg_ids:
                continue
            st = (a.get("submitted_at") or "")[:10]
            if start and (not st or st < start):
                continue
            if end and (not st or st > end):
                continue
            scores.append(att_score(a))
        rows.append({
            "student_id": uid, "name": u["name"], "identifier": u.get("identifier", ""),
            "classes": cls_by_student.get(uid, []),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "completed": len(scores),
        })
    rows.sort(key=lambda r: (-r["avg_score"], r["name"].lower()))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows


@api_router.get("/leaderboard/global")
async def leaderboard_global(start: Optional[str] = None, end: Optional[str] = None,
                             category_id: Optional[str] = None,
                             user: dict = Depends(get_current_user)):
    rows = await compute_global_leaderboard(start, end, category_id)
    return {"rows": rows}


@api_router.get("/export/leaderboard/xlsx")
async def export_leaderboard(start: Optional[str] = None, end: Optional[str] = None,
                             category_id: Optional[str] = None,
                             user: dict = Depends(require_roles("admin", "guru"))):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    rows = await compute_global_leaderboard(start, end, category_id)
    cat_name = "Semua Mapel"
    if category_id:
        cat = await db.categories.find_one({"id": category_id}, {"_id": 0, "name": 1})
        cat_name = cat["name"] if cat else category_id
    period = f"{start or '...'} s/d {end or '...'}" if (start or end) else "Semua waktu"

    wb = Workbook()
    ws = wb.active
    ws.title = "Peringkat Angkatan"
    ws.append(["PERINGKAT ANGKATAN"])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
    ws["A1"].font = Font(bold=True, size=14, color="1E3A30")
    ws.append([f"Mapel: {cat_name}", "", f"Periode: {period}"])
    ws.append([])
    header = ["Peringkat", "Nama Siswa", "NISN/NIP", "Kelas", "Ujian Selesai", "Rata-rata"]
    ws.append(header)
    green = PatternFill("solid", fgColor="1E3A30")
    thin = Side(style="thin", color="D9D9CF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hrow = ws.max_row
    for cell in ws[hrow]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = green
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
    for r in rows:
        ws.append([r["rank"], r["name"], r.get("identifier", ""), ", ".join(r.get("classes", [])),
                   r["completed"], r["avg_score"]])
        for cell in ws[ws.max_row]:
            cell.border = border
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 12
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=peringkat-angkatan.xlsx"})


# ------------------------------------------------------------------ startup
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    # Migrate any legacy session schedules stored without timezone info to UTC-aware ISO
    try:
        migrated = 0
        for s in await db.sessions.find({}, {"_id": 0, "id": 1, "start_time": 1, "end_time": 1}).to_list(5000):
            patch = {}
            for field in ("start_time", "end_time"):
                raw = s.get(field)
                if raw and isinstance(raw, str) and not (raw.endswith("Z") or "+" in raw[10:] or "-" in raw[10:]):
                    patch[field] = parse_dt(raw).isoformat()
            if patch:
                await db.sessions.update_one({"id": s["id"]}, {"$set": patch})
                migrated += 1
        if migrated:
            logging.getLogger(__name__).info(f"Normalized schedule of {migrated} session(s) to UTC")
    except Exception as e:
        logging.getLogger(__name__).error(f"Session time migration failed: {e}")
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logging.getLogger(__name__).error(f"Storage init failed: {e}")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "email": admin_email, "password_hash": hash_password(admin_password),
            "name": "Administrator", "role": "admin", "identifier": "",
            "created_at": now_iso(),
        })
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email},
                                  {"$set": {"password_hash": hash_password(admin_password)}})


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
