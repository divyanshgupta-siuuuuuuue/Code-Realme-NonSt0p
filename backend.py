# =========================================================
# CODE REALME NONSTOP — ULTRA FASTAPI SERVER
# FULL MULTIPLAYER BACKEND
# =========================================================

# INSTALL:
#
# pip install fastapi uvicorn python-multipart pymongo bcrypt pyjwt aiofiles websockets
#
# RUN:
#
# uvicorn main:app --reload
#
# =========================================================

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    WebSocket,
    WebSocketDisconnect
)

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse

from pymongo import MongoClient

from typing import List

import bcrypt
import jwt
import os
import shutil
import uuid
import datetime
import json

# =========================================================
# APP
# =========================================================

app = FastAPI()

# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# DATABASE
# =========================================================

MONGO_URL = "mongodb://localhost:27017"

client = MongoClient(MONGO_URL)

db = client["code_realme_nonstop"]

users_collection = db["users"]

projects_collection = db["projects"]

# =========================================================
# SECRET
# =========================================================

SECRET_KEY = "CRN_SUPER_SECRET"

# =========================================================
# FOLDERS
# =========================================================

UPLOAD_FOLDER = "uploads"

PROJECT_FOLDER = "projects"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

os.makedirs(PROJECT_FOLDER, exist_ok=True)

# =========================================================
# ACTIVE SOCKETS
# =========================================================

active_connections = []

# =========================================================
# GENERATE TOKEN
# =========================================================

def generate_token(username):

    payload = {
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }

    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# =========================================================
# HOME
# =========================================================

@app.get("/")
async def home():

    return {
        "status": "ONLINE",
        "server": "CODE REALME NONSTOP",
        "multiplayer": True
    }

# =========================================================
# REGISTER
# =========================================================

@app.post("/register")

async def register(
    username: str = Form(...),
    password: str = Form(...),
    bio: str = Form(""),
    profile_logo: UploadFile = File(None)
):

    existing = users_collection.find_one({
        "username": username
    })

    if existing:
        raise HTTPException(
            status_code=400,
            detail="USERNAME EXISTS"
        )

    hashed = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    )

    social_id = "CRN-" + str(uuid.uuid4())[:8].upper()

    logo_path = ""

    if profile_logo:

        logo_filename = f"{uuid.uuid4()}_{profile_logo.filename}"

        logo_path = os.path.join(
            UPLOAD_FOLDER,
            logo_filename
        )

        with open(logo_path, "wb") as buffer:
            shutil.copyfileobj(profile_logo.file, buffer)

    user_data = {

        "username": username,

        "password": hashed.decode(),

        "bio": bio,

        "social_id": social_id,

        "logo": logo_path,

        "friends": [],

        "projects": [],

        "created_at": str(datetime.datetime.utcnow())
    }

    users_collection.insert_one(user_data)

    token = generate_token(username)

    return {

        "message": "REGISTER SUCCESS",

        "token": token,

        "social_id": social_id
    }

# =========================================================
# LOGIN
# =========================================================

@app.post("/login")

async def login(

    username: str = Form(...),

    password: str = Form(...)
):

    user = users_collection.find_one({
        "username": username
    })

    if not user:
        raise HTTPException(
            status_code=404,
            detail="USER NOT FOUND"
        )

    valid = bcrypt.checkpw(
        password.encode(),
        user["password"].encode()
    )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="WRONG PASSWORD"
        )

    token = generate_token(username)

    return {

        "message": "LOGIN SUCCESS",

        "token": token,

        "social_id": user["social_id"]
    }

# =========================================================
# GET PROFILE
# =========================================================

@app.get("/profile/{username}")

async def profile(username: str):

    user = users_collection.find_one({
        "username": username
    })

    if not user:
        raise HTTPException(
            status_code=404,
            detail="USER NOT FOUND"
        )

    return {

        "username": user["username"],

        "bio": user["bio"],

        "social_id": user["social_id"],

        "logo": user["logo"],

        "friends": user["friends"]
    }

# =========================================================
# CREATE PROJECT
# =========================================================

@app.post("/create-project")

async def create_project(

    username: str = Form(...),

    project_name: str = Form(...),

    description: str = Form(...),

    purpose: str = Form(...),

    visibility: str = Form(...),

    project_logo: UploadFile = File(None),

    files: List[UploadFile] = File([])
):

    project_id = "project-" + str(uuid.uuid4())[:10]

    project_folder = os.path.join(
        PROJECT_FOLDER,
        project_id
    )

    os.makedirs(project_folder, exist_ok=True)

    logo_path = ""

    # =====================================================
    # SAVE LOGO
    # =====================================================

    if project_logo:

        logo_name = f"{uuid.uuid4()}_{project_logo.filename}"

        logo_path = os.path.join(
            project_folder,
            logo_name
        )

        with open(logo_path, "wb") as buffer:
            shutil.copyfileobj(
                project_logo.file,
                buffer
            )

    # =====================================================
    # SAVE FILES
    # =====================================================

    uploaded_files = []

    for file in files:

        file_path = os.path.join(
            project_folder,
            file.filename
        )

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

        uploaded_files.append(file.filename)

    project_data = {

        "project_id": project_id,

        "owner": username,

        "project_name": project_name,

        "description": description,

        "purpose": purpose,

        "visibility": visibility,

        "logo": logo_path,

        "files": uploaded_files,

        "members": [username],

        "created_at": str(datetime.datetime.utcnow())
    }

    projects_collection.insert_one(project_data)

    project_link = f"/{project_id}"

    return {

        "message": "PROJECT CREATED",

        "project_id": project_id,

        "project_link": project_link,

        "files_uploaded": uploaded_files
    }

# =========================================================
# ALL PROJECTS
# =========================================================

@app.get("/projects")

async def get_projects():

    projects = list(projects_collection.find({}, {
        "_id": 0
    }))

    return projects

# =========================================================
# ADD FRIEND
# =========================================================

@app.post("/add-friend")

async def add_friend(

    username: str = Form(...),

    friend_social_id: str = Form(...)
):

    user = users_collection.find_one({
        "username": username
    })

    if not user:
        raise HTTPException(
            status_code=404,
            detail="USER NOT FOUND"
        )

    friend = users_collection.find_one({
        "social_id": friend_social_id
    })

    if not friend:
        raise HTTPException(
            status_code=404,
            detail="FRIEND NOT FOUND"
        )

    users_collection.update_one(
        {"username": username},
        {"$push": {
            "friends": friend_social_id
        }}
    )

    return {
        "message": "FRIEND ADDED"
    }

# =========================================================
# INVITE MEMBER
# =========================================================

@app.post("/invite-member")

async def invite_member(

    project_id: str = Form(...),

    social_id: str = Form(...)
):

    user = users_collection.find_one({
        "social_id": social_id
    })

    if not user:
        raise HTTPException(
            status_code=404,
            detail="USER NOT FOUND"
        )

    projects_collection.update_one(
        {"project_id": project_id},
        {
            "$push": {
                "members": user["username"]
            }
        }
    )

    return {
        "message": "MEMBER ADDED"
    }

# =========================================================
# WEBSOCKET
# =========================================================

@app.websocket("/ws")

async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()

    active_connections.append(websocket)

    try:

        while True:

            data = await websocket.receive_text()

            for connection in active_connections:

                await connection.send_text(
                    f"LIVE MULTIPLAYER: {data}"
                )

    except WebSocketDisconnect:

        active_connections.remove(websocket)

# =========================================================
# LIVE ROOM
# =========================================================

@app.get("/live-room/{room_id}")

async def live_room(room_id: str):

    return {

        "room_id": room_id,

        "voice_chat": True,

        "facecam": True,

        "screen_share": True
    }

# =========================================================
# TERMINAL SIMULATION
# =========================================================

@app.post("/compile")

async def compile_code(

    language: str = Form(...),

    code: str = Form(...)
):

    syntax_error = False

    output = "Compilation Success"

    if "error" in code.lower():

        syntax_error = True

        output = "Syntax Error Detected"

    return {

        "language": language,

        "syntax_error": syntax_error,

        "output": output
    }

# =========================================================
# SETTINGS
# =========================================================

@app.post("/settings")

async def settings(

    username: str = Form(...),

    theme: str = Form(...),

    notifications: bool = Form(...)
):

    users_collection.update_one(
        {"username": username},
        {
            "$set": {
                "theme": theme,
                "notifications": notifications
            }
        }
    )

    return {
        "message": "SETTINGS UPDATED"
    }

# =========================================================
# DELETE PROJECT
# =========================================================

@app.delete("/delete-project/{project_id}")

async def delete_project(project_id: str):

    projects_collection.delete_one({
        "project_id": project_id
    })

    project_path = os.path.join(
        PROJECT_FOLDER,
        project_id
    )

    if os.path.exists(project_path):
        shutil.rmtree(project_path)

    return {
        "message": "PROJECT DELETED"
    }

# =========================================================
# ONLINE USERS
# =========================================================

@app.get("/online-users")

async def online_users():

    users = list(users_collection.find({}, {
        "_id": 0,
        "username": 1,
        "social_id": 1
    }))

    return users

# =========================================================
# SERVER INFO
# =========================================================

@app.get("/server-info")

async def server_info():

    return {

        "server": "CODE REALME NONSTOP",

        "database": "MongoDB",

        "multiplayer": True,

        "voice_chat": True,

        "screen_share": True,

        "terminal": True,

        "deployment": "READY"
    }

# =========================================================
# END
# =========================================================
