from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db

app = FastAPI(title="GiraGroup BI System")

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Intenta ejecutar un simple SELECT 1 en la base de datos
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected and responsive"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")