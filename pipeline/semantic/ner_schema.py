"""
pipeline/semantic/ner_schema.py
--------------------------------
Contratos y esquemas de datos tipados para el motor de inferencia NER (BETO)
en el sistema GiraGroup BI.

Cumple con el estándar de contrato:
{
    "entidad": valor,
    "tipo": tipo,
    "valor": valor,
    "start_char": start_char,
    "end_char": end_char,
    "score": score,
    "origen": origen
}
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional
from pipeline.config import UMBRAL_CONFIANZA_ALTO, UMBRAL_CONFIANZA_MEDIO


class TipoEntidad(str, Enum):
    ESTUDIANTE = "ESTUDIANTE"
    DOCENTE = "DOCENTE"
    PROGRAMA = "PROGRAMA"
    POS = "POS"
    MODULO = "MODULO"
    NOTA = "NOTA"
    MONTO = "MONTO"
    CI = "CI"
    FECHA = "FECHA"
    FACTURA = "FACTURA"
    OTRO = "OTRO"


class NivelConfianza(str, Enum):
    """
    Niveles probabilísticos estandarizados para GiraGroup BI (GIRA-42).
    ALTA: >= 0.85 (Aceptación directa)
    MEDIA: [0.60, 0.85) (Requiere revisión humana)
    BAJA: < 0.60 (Descarte o staging no resuelto)
    """
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAJA = "BAJA"



@dataclass
class EntidadExtraida:
    """
    Representa una entidad atómica extraída por el motor de inferencia NER o reglas de apoyo.
    """
    tipo: str
    valor: str
    start_char: int
    end_char: int
    score: float
    origen: str = "BETO_NER"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Asegurar tipos y normalizaciones básicas
        if isinstance(self.tipo, Enum):
            self.tipo = self.tipo.value
        else:
            self.tipo = str(self.tipo).strip().upper()
        self.valor = str(self.valor).strip()
        self.start_char = int(self.start_char)
        self.end_char = int(self.end_char)
        self.score = float(self.score)


    @property
    def entidad(self) -> str:
        """Alias retrocompatible para 'valor'."""
        return self.valor

    @property
    def longitud(self) -> int:
        return self.end_char - self.start_char

    @property
    def nivel_confianza(self) -> NivelConfianza:
        """Determina el nivel de confianza probabilístico formal según los umbrales de GiraGroup."""
        if self.score >= UMBRAL_CONFIANZA_ALTO:
            return NivelConfianza.ALTA
        elif self.score >= UMBRAL_CONFIANZA_MEDIO:
            return NivelConfianza.MEDIA
        else:
            return NivelConfianza.BAJA

    def es_confiable(self, umbral: float = UMBRAL_CONFIANZA_ALTO) -> bool:
        """Determina si la entidad supera el umbral de aceptación automática."""
        return self.score >= umbral

    def requiere_revision(self, umbral_alto: float = UMBRAL_CONFIANZA_ALTO, umbral_medio: float = UMBRAL_CONFIANZA_MEDIO) -> bool:
        """Retorna True si el score se ubica en el intervalo de duda [medio, alto)."""
        return umbral_medio <= self.score < umbral_alto

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario estándar con niveles de confianza y flag de revisión."""
        return {
            "entidad": self.valor,
            "tipo": self.tipo,
            "valor": self.valor,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "score": round(self.score, 4),
            "nivel_confianza": self.nivel_confianza.value,
            "requiere_revision": self.requiere_revision(),
            "origen": self.origen,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntidadExtraida":
        return cls(
            tipo=data.get("tipo", TipoEntidad.OTRO),
            valor=data.get("valor", data.get("entidad", "")),
            start_char=data.get("start_char", 0),
            end_char=data.get("end_char", 0),
            score=data.get("score", 0.0),
            origen=data.get("origen", "DESCONOCIDO"),
            metadata=data.get("metadata", {})
        )


@dataclass
class ResultadoInferenciaNER:
    """
    Resultado consolidado de inferencia para una oración o texto analizado.
    """
    texto: str
    entidades: List[EntidadExtraida] = field(default_factory=list)
    tiempo_inferencia_ms: float = 0.0
    modelo: str = "dccuchile/bert-base-spanish-wwm-cased"
    dispositivo: str = "cpu"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def obtener_por_tipo(self, tipo: str) -> List[EntidadExtraida]:
        """Filtra entidades por su tipo canónico."""
        tipo_normalizado = tipo.strip().upper()
        return [e for e in self.entidades if e.tipo == tipo_normalizado]

    def entidades_confiables(self, umbral: float = UMBRAL_CONFIANZA_ALTO) -> List[EntidadExtraida]:
        """Filtra solo las entidades con alta confianza probabilística."""
        return [e for e in self.entidades if e.es_confiable(umbral)]

    def entidades_por_nivel(self, nivel: Union[NivelConfianza, str]) -> List[EntidadExtraida]:
        """Filtra entidades que pertenezcan a un nivel específico (ALTA, MEDIA, BAJA)."""
        target = nivel.value if isinstance(nivel, NivelConfianza) else str(nivel).strip().upper()
        return [e for e in self.entidades if e.nivel_confianza.value == target]

    def entidades_que_requieren_revision(self) -> List[EntidadExtraida]:
        """Retorna las entidades con nivel de confianza MEDIA que ameritan verificación humana."""
        return [e for e in self.entidades if e.requiere_revision()]


    def to_dict(self) -> Dict[str, Any]:
        return {
            "texto": self.texto,
            "total_entidades": len(self.entidades),
            "entidades": [e.to_dict() for e in self.entidades],
            "tiempo_inferencia_ms": round(self.tiempo_inferencia_ms, 2),
            "modelo": self.modelo,
            "dispositivo": self.dispositivo,
            "metadata": self.metadata
        }
