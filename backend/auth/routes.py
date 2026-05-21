from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError

from auth.deps import get_current_user
from auth.models import build_user_document, user_public
from auth.schemas import TokenResponse, UserLogin, UserRegister, UserResponse
from auth.utils import create_access_token, hash_password, verify_password
from database.mongodb import db

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    email = user.email.lower()

    try:
        existing = await db.users.find_one({"email": email})
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable. Check the backend MONGO_URL and MongoDB network access.",
        ) from exc

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user_data = build_user_document(
        name=user.name,
        email=email,
        hashed_password=hash_password(user.password),
        role=user.role,
    )
    try:
        result = await db.users.insert_one(user_data)
        created = await db.users.find_one({"_id": result.inserted_id})
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable. Check the backend MONGO_URL and MongoDB network access.",
        ) from exc

    return user_public(created)


@router.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    email = user.email.lower()

    try:
        db_user = await db.users.find_one({"email": email})
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable. Check the backend MONGO_URL and MongoDB network access.",
        ) from exc

    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    try:
        token = create_access_token({
            "sub": str(db_user["_id"]),
            "email": db_user["email"],
            "role": db_user.get("role", "user"),
        })
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET_KEY is missing on the backend host.",
        ) from exc

    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
async def logout():
    return {"message": "Logged out. Remove the token on the client."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return user_public(current_user)
