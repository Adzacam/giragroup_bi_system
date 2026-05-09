from pydantic import BaseModel

class EstudianteBase(BaseModel):
    nombre_completo: str
    codigo_estudiante: str

class EstudianteCreate(EstudianteBase):
    pass

class EstudianteResponse(EstudianteBase):
    id_estudiante: int

    class Config:
        from_attributes = True