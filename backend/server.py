from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import io
import logging
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any

import jwt
import bcrypt
import pandas as pd
from bson import ObjectId
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File
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
    created_at: str = Field(default_factory=now_iso)


class QuestionBody(BaseModel):
    category_id: Optional[str] = None
    type: str
    text: str
    options: List[str] = []
    correct_answer: Optional[str] = None
    weight: float = 1.0


class Package(BaseModel):
    id: str = Field(default_factory=new_id)
    title: str
    description: Optional[str] = ""
    category_id: Optional[str] = None
    question_ids: List[str] = []
    scoring_method: str = "percentage"  # percentage | weighted
    shuffle_questions: bool = False
    shuffle_options: bool = False
    created_at: str = Field(default_factory=now_iso)


class PackageBody(BaseModel):
    title: str
    description: Optional[str] = ""
    category_id: Optional[str] = None
    question_ids: List[str] = []
    scoring_method: str = "percentage"
    shuffle_questions: bool = False
    shuffle_options: bool = False


class Session(BaseModel):
    id: str = Field(default_factory=new_id)
    title: str
    package_id: str
    start_time: str
    end_time: str
    duration_minutes: int = 60
    kkm: float = 75.0
    class_ids: List[str] = []
    created_at: str = Field(default_factory=now_iso)


class SessionBody(BaseModel):
    title: str
    package_id: str
    start_time: str
    end_time: str
    duration_minutes: int = 60
    kkm: float = 75.0
    class_ids: List[str] = []


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
    pkgs = await db.packages.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for p in pkgs:
        p["question_count"] = len(p.get("question_ids", []))
    return pkgs


@api_router.get("/packages/{pid}")
async def get_package(pid: str, user: dict = Depends(require_roles("admin", "guru"))):
    p = await db.packages.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Paket tidak ditemukan")
    return p


@api_router.post("/packages")
async def create_package(body: PackageBody, user: dict = Depends(require_roles("admin", "guru"))):
    pkg = Package(**body.model_dump())
    await db.packages.insert_one(pkg.model_dump())
    return pkg.model_dump()


@api_router.put("/packages/{pid}")
async def update_package(pid: str, body: PackageBody, user: dict = Depends(require_roles("admin", "guru"))):
    await db.packages.update_one({"id": pid}, {"$set": body.model_dump()})
    return await db.packages.find_one({"id": pid}, {"_id": 0})


@api_router.delete("/packages/{pid}")
async def delete_package(pid: str, user: dict = Depends(require_roles("admin", "guru"))):
    await db.packages.delete_one({"id": pid})
    return {"ok": True}


# ------------------------------------------------------------------ SESSIONS
async def enrich_session(s: dict) -> dict:
    pkg = await db.packages.find_one({"id": s["package_id"]}, {"_id": 0})
    s["package_title"] = pkg["title"] if pkg else "-"
    s["question_count"] = len(pkg.get("question_ids", [])) if pkg else 0
    now = datetime.now(timezone.utc)
    start = datetime.fromisoformat(s["start_time"])
    end = datetime.fromisoformat(s["end_time"])
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
            att = await db.attempts.find_one({"session_id": s["id"], "student_id": user["id"]}, {"_id": 0})
            s["attempt_status"] = att["status"] if att else None
            visible.append(s)
        return visible
    else:
        for s in sessions:
            classes = await db.classes.find({"id": {"$in": s.get("class_ids", [])}}, {"_id": 0, "name": 1}).to_list(100)
            s["class_names"] = [c["name"] for c in classes]
    return sessions


@api_router.post("/sessions")
async def create_session(body: SessionBody, user: dict = Depends(require_roles("admin", "guru"))):
    ses = Session(**body.model_dump())
    await db.sessions.insert_one(ses.model_dump())
    return ses.model_dump()


@api_router.put("/sessions/{sid}")
async def update_session(sid: str, body: SessionBody, user: dict = Depends(require_roles("admin", "guru"))):
    await db.sessions.update_one({"id": sid}, {"$set": body.model_dump()})
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
        "options": opts, "weight": q.get("weight", 1.0),
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

    attempt = await db.attempts.find_one({"session_id": body.session_id, "student_id": user["id"]}, {"_id": 0})
    if attempt and attempt["status"] != "berlangsung":
        raise HTTPException(status_code=400, detail="Anda sudah mengerjakan sesi ini")

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
        }
        await db.attempts.insert_one(dict(attempt))

    order_ids = attempt.get("question_order") or list(pkg.get("question_ids", []))
    option_perm = attempt.get("option_perm", {})
    display = [sanitize_question(qmap[qid], option_perm.get(qid)) for qid in order_ids if qid in qmap]

    return {
        "attempt_id": attempt["id"],
        "session": {"id": session["id"], "title": session["title"],
                    "duration_minutes": session["duration_minutes"], "end_time": session["end_time"]},
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
    score = None if needs_grading else (round(earned / total_possible * 100, 2) if total_possible else 0.0)
    return details, needs_grading, score, round(earned, 2), round(total_possible, 2)


@api_router.post("/exam/submit")
async def submit_exam(body: SubmitBody, user: dict = Depends(require_roles("siswa"))):
    attempt = await db.attempts.find_one({"session_id": body.session_id, "student_id": user["id"]}, {"_id": 0})
    if not attempt:
        raise HTTPException(status_code=404, detail="Percobaan tidak ditemukan")
    if attempt["status"] != "berlangsung":
        raise HTTPException(status_code=400, detail="Sesi sudah dikumpulkan")
    pkg = await db.packages.find_one({"id": attempt["package_id"]}, {"_id": 0})
    qlist = await db.questions.find({"id": {"$in": pkg.get("question_ids", [])}}, {"_id": 0}).to_list(2000)
    qmap = {q["id"]: q for q in qlist}
    # Convert shuffled option indices back to original indices for pg questions
    perm_map = attempt.get("option_perm", {})
    canonical = {}
    for qid, ans in body.answers.items():
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
    return {"status": update["status"], "score": score, "needs_grading": needs_grading}


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
                         "correct_answer": q.get("correct_answer")})
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
    "type,text,option_a,option_b,option_c,option_d,correct,weight,category\n"
    "pg,Berapa hasil 5 + 3?,6,7,8,9,C,1,Matematika\n"
    "truefalse,Matahari terbit dari timur.,,,,,benar,1,IPA\n"
    "essay,Jelaskan proses fotosintesis.,,,,,,2,IPA\n"
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
    letter_idx = {"a": "0", "b": "1", "c": "2", "d": "3"}
    for i, row in df.iterrows():
        rownum = i + 2
        try:
            qtype = str(row.get("type", "")).strip().lower()
            text = str(row.get("text", "")).strip()
            if not text or text.lower() == "nan" or qtype not in ("pg", "truefalse", "essay"):
                errors.append(f"Baris {rownum}: tipe/teks tidak valid")
                continue
            # category
            cat_name = str(row.get("category", "")).strip()
            cat_id = None
            if cat_name and cat_name.lower() != "nan":
                key = cat_name.lower()
                if key not in cat_by_name:
                    nc = Category(name=cat_name)
                    await db.categories.insert_one(nc.model_dump())
                    cat_by_name[key] = nc.id
                cat_id = cat_by_name[key]
            weight = 1.0
            try:
                wv = str(row.get("weight", "") or "").strip()
                weight = float(wv) if wv and wv.lower() != "nan" else 1.0
            except (ValueError, TypeError):
                weight = 1.0
            if weight != weight:  # NaN guard
                weight = 1.0

            options, correct = [], None
            if qtype == "pg":
                for col in ("option_a", "option_b", "option_c", "option_d"):
                    v = row.get(col, "")
                    v = "" if (v is None or str(v).lower() == "nan") else str(v).strip()
                    if v:
                        options.append(v)
                raw_c = str(row.get("correct", "")).strip().lower()
                if raw_c in letter_idx:
                    correct = letter_idx[raw_c]
                elif raw_c.isdigit():
                    correct = raw_c
                else:
                    errors.append(f"Baris {rownum}: kunci PG tidak valid")
                    continue
            elif qtype == "truefalse":
                raw_c = str(row.get("correct", "")).strip().lower()
                correct = "true" if raw_c in ("true", "benar", "b", "1") else "false"

            ques = Question(category_id=cat_id, type=qtype, text=text,
                            options=options, correct_answer=correct, weight=weight)
            await db.questions.insert_one(ques.model_dump())
            imported += 1
        except Exception as e:
            errors.append(f"Baris {rownum}: {e}")

    return {"imported": imported, "errors": errors}


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



# ------------------------------------------------------------------ DASHBOARD
@api_router.get("/dashboard/stats")
async def dashboard_stats(user: dict = Depends(require_roles("admin", "guru"))):
    students = await db.users.count_documents({"role": "siswa"})
    teachers = await db.users.count_documents({"role": "guru"})
    questions = await db.questions.count_documents({})
    packages = await db.packages.count_documents({})
    sessions = await db.sessions.count_documents({})
    attempts = await db.attempts.find({"status": "selesai"}, {"_id": 0, "score": 1}).to_list(5000)
    scores = [a["score"] for a in attempts if a.get("score") is not None]
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    pending = await db.attempts.count_documents({"status": "menunggu_koreksi"})
    return {"students": students, "teachers": teachers, "questions": questions,
            "packages": packages, "sessions": sessions, "avg_score": avg,
            "completed_attempts": len(scores), "pending_grading": pending}


# ------------------------------------------------------------------ startup
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
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
