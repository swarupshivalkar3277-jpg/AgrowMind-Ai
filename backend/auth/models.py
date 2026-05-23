from datetime import datetime, timezone


def build_user_document(name: str, email: str, hashed_password: str, role: str = "farmer") -> dict:
    now = datetime.now(timezone.utc)
    return {
        "name": name,
        "email": email.lower(),
        "hashed_password": hashed_password,
        "role": role,
        "created_at": now,
        "updated_at": now,
    }


def user_public(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "farmer"),
    }
