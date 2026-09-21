import os
import sys
import psycopg2
import bcrypt

# Database connection settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "giragroup_db")
DB_USER = os.getenv("DB_USER", "giragroup_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "giragroup_password")

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

def seed():
    print(f"Connecting to database {DB_NAME} at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        
        # Ensure users table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL DEFAULT 'sistema',
                hashed_password VARCHAR(255) NOT NULL DEFAULT '$placeholder$',
                role VARCHAR(50) DEFAULT 'admin',
                email VARCHAR(150) UNIQUE NOT NULL DEFAULT 'admin@giragroup.com',
                phone VARCHAR(30),
                is_active BOOLEAN DEFAULT TRUE,
                is_mfa_enabled BOOLEAN DEFAULT TRUE,
                otp_code_hash VARCHAR(255),
                otp_expires_at TIMESTAMP WITH TIME ZONE,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP WITH TIME ZONE,
                created_by_id INTEGER REFERENCES public.users(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        for user_data in USERS:
            hashed = hash_password(user_data["password"])
            cur.execute("""
                INSERT INTO public.users (username, email, role, hashed_password, is_active, is_mfa_enabled, failed_login_attempts)
                VALUES (%s, %s, %s, %s, TRUE, TRUE, 0)
                ON CONFLICT (email) DO UPDATE 
                SET role = EXCLUDED.role,
                    hashed_password = EXCLUDED.hashed_password,
                    is_active = TRUE,
                    is_mfa_enabled = TRUE,
                    failed_login_attempts = 0,
                    locked_until = NULL;
            """, (user_data["username"], user_data["email"], user_data["role"], hashed))
            print(f"Seeded user: {user_data['email']} ({user_data['role']})")
            
        conn.commit()
        cur.close()
        conn.close()
        print("Seeding completed successfully!")
    except Exception as e:
        print(f"Error seeding users: {e}")
        sys.exit(1)

if __name__ == "__main__":
    seed()
