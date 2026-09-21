import os
import sys
import bcrypt
from sqlalchemy.orm import Session
from core.database import SessionLocal, engine
from models.user import User

USERS = [
    {
        "username": "admin_general",
        "email": "admin.general@giragroup.bo",
        "role": "ADMIN",
        "password": "giragroup2026",
    },
    {
        "username": "auditor_dataops",
        "email": "auditor.dataops@giragroup.bo",
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
        "email": "analista.finanzas@giragroup.bo",
        "role": "ANALISTA_FINANCIERO",
        "password": "giragroup2026",
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
                    is_mfa_enabled=True,
                    failed_login_attempts=0,
                )
                db.add(new_user)
                print(f"[SEED] Created demo user: {u['email']} as {u['role']}")
            else:
                # Update role and password if needed
                existing.role = u["role"]
                existing.hashed_password = hash_password(u["password"])
                existing.is_active = True
                existing.is_mfa_enabled = True
                existing.failed_login_attempts = 0
                existing.locked_until = None
                print(f"[SEED] Updated demo user: {u['email']} as {u['role']}")
        db.commit()
        print("[SEED] All demo users verified in database.")
    except Exception as e:
        db.rollback()
        print(f"[SEED ERROR] Failed to seed users: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_default_users()
