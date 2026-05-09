from sqlalchemy.orm import Session
from api.models.dim_estudiante import DimEstudiante
from api.schemas.estudiante import EstudianteCreate

def get_estudiante(db: Session, id_estudiante: int):
    return db.query(DimEstudiante).filter(DimEstudiante.id_estudiante == id_estudiante).first()

def get_estudiantes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(DimEstudiante).offset(skip).limit(limit).all()

def create_estudiante(db: Session, estudiante: EstudianteCreate):
    db_estudiante = DimEstudiante(**estudiante.model_dump())
    db.add(db_estudiante)
    db.commit()
    db.refresh(db_estudiante)
    return db_estudiante