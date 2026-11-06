# scripts/patch_fuente_resolucion.py
import re

with open("pipeline/semantic/ner_schema.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add fuente_resolucion field to EntidadExtraida
if "fuente_resolucion: Optional[str] = None" not in text:
    old_fields = """    origen: str = "BETO_NER"
    metadata: Dict[str, Any] = field(default_factory=dict)"""
    new_fields = """    origen: str = "BETO_NER"
    metadata: Dict[str, Any] = field(default_factory=dict)
    fuente_resolucion: Optional[str] = None"""
    text = text.replace(old_fields, new_fields)

# 2. Add fuente_resolucion fallback in __post_init__
if "if self.fuente_resolucion is None:" not in text:
    old_init = """        self.score = float(self.score)"""
    new_init = """        self.score = float(self.score)

        if self.fuente_resolucion is None:
            if "fuente_resolucion" in self.metadata:
                self.fuente_resolucion = self.metadata["fuente_resolucion"]
            elif self.origen in ("BETO_NER", "BETO"):
                self.fuente_resolucion = "BETO"
            elif "CI" in self.origen:
                self.fuente_resolucion = "CI_EXACTA"
            elif "ENCABEZADO" in self.origen:
                self.fuente_resolucion = "ENCABEZADO"
            elif "FUZZY" in self.origen:
                self.fuente_resolucion = "FUZZY"
            elif "REGEX" in self.origen or "PATRON" in self.origen:
                self.fuente_resolucion = "REGEX"
            else:
                self.fuente_resolucion = "BETO" """
    text = text.replace(old_init, new_init, 1)

# 3. Add fuente_resolucion in to_dict
if '"fuente_resolucion": self.fuente_resolucion,' not in text:
    old_dict = """            "origen": self.origen,
            "metadata": self.metadata"""
    new_dict = """            "origen": self.origen,
            "fuente_resolucion": self.fuente_resolucion,
            "metadata": self.metadata"""
    text = text.replace(old_dict, new_dict)

# 4. Add fuente_resolucion in from_dict
if 'fuente_resolucion=data.get("fuente_resolucion"' not in text:
    old_from = """            metadata=data.get("metadata", {})
        )"""
    new_from = """            metadata=data.get("metadata", {}),
            fuente_resolucion=data.get("fuente_resolucion", None)
        )"""
    text = text.replace(old_from, new_from)

with open("pipeline/semantic/ner_schema.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Patch applied to ner_schema.py!")
