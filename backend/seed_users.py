import os
import sys
import bcrypt
from sqlalchemy.orm import Session
from core.database import SessionLocal, engine
from models.user import User

USERS = [
    {
        "username": "admin_general",
        "email": "dazaadriano12@gmail.com",
        "role": "ADMIN",
        "password": "giragroup2026",
    },
    {
        "username": "auditor_dataops",
        "email": "dazaadrianoc@gmail.com",
        "role": "AUDITOR_CALIDAD",
        "password": "giragroup2026",
    },
    {
        "username": "dir_academica",
        "email": "direccion.academica@giragroup.bo",
        "role": "DIRECTOR_ACADEMICO",
        "password": "giragroup2026",
    },
    {
        "username": "analista_fin",
        "email": "dazwebos@gmail.com",
        "role": "ANALISTA_FINANCIERO",
        "password": "giragroup2026",
    },
    {
        "username": "analista_mkt",
        "email": "analista.marketing@giragroup.bo",
        "role": "ANALISTA_MARKETING",
        "password": "giragroup2026",
    },
    {
        "username": "loadtest_user",
        "email": "loadtest@giragroup.bo",
        "role": "ADMIN",
        "password": "giragroup2026",
        "is_mfa_enabled": False,
    },
]

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def seed_default_users():
    db: Session = SessionLocal()
    try:
        for u in USERS:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                new_user = User(
                    username=u["username"],
                    email=u["email"],
                    role=u["role"],
                    hashed_password=hash_password(u["password"]),
                    is_active=True,
                    is_mfa_enabled=u.get("is_mfa_enabled", True),
                    failed_login_attempts=0,
                )
                db.add(new_user)
                print(f"[SEED] Created demo user: {u['email']} as {u['role']}")
            else:
                print(f"[SEED] User already exists (password preserved): {u['email']}")
        db.commit()
        print("[SEED] All demo users verified in database.")
    except Exception as e:
        db.rollback()
        print(f"[SEED ERROR] Failed to seed users: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_default_users()
