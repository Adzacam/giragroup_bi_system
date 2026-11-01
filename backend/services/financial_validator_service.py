"""
backend/services/financial_validator_service.py
-----------------------------------------------
Motor de validación aritmética, contable y cambiaria del pipeline financiero:
- Sanitización de importes en bolivianos (BOB / Bs.) desde formatos heterogéneos:
  '1.500 Bs', 'Bs. 1,500.00', '1.500,50 BOB', '1500', '1,500.00'
- Verificación de consistencia contable:
  Saldo = Cuota - Monto Pagado
- Verificación de duplas Meta vs. Ejecutado:
  Cumplimiento = (Ejecutado / Meta) * 100
- Detección de anomalías de escala y monedas no institucionales.
"""

import re
import math
from typing import Any, Optional, Dict, Tuple


class FinancialTransactionValidator:
    """Validador aritmético y contable para transacciones financieras y metas."""

    PATRON_MONEDA_BOB = re.compile(r'\b(BS\.?|BOB|BOLIVIANOS?)\b', re.IGNORECASE)
    PATRON_MONEDA_USD = re.compile(r'(\$|USD|DOLARES?)', re.IGNORECASE)

    @classmethod
    def extraer_moneda(cls, valor_raw: Any, moneda_default: str = "BOB") -> Tuple[str, bool]:
        """
        Extrae la moneda de una cadena.
        Retorna (codigo_moneda, es_moneda_nacional).
        """
        if not valor_raw or not isinstance(valor_raw, str):
            return moneda_default, True

        texto = valor_raw.strip().upper()
        if cls.PATRON_MONEDA_USD.search(texto):
            return "USD", False
        if cls.PATRON_MONEDA_BOB.search(texto):
            return "BOB", True

        return moneda_default, True

    @classmethod
    def sanitizar_importe(cls, valor_raw: Any) -> Optional[float]:
        """
        Convierte cualquier formato de texto o número a float estándar limpio.
        
        Ejemplos:
        - 1500 ➔ 1500.0
        - "1.500 Bs" ➔ 1500.0
        - "Bs. 1.500,50" ➔ 1500.50
        - "1,500.00 BOB" ➔ 1500.00
        - "-250.00" ➔ -250.0
        - "(300)" ➔ -300.0
        - "N/A", "-", None ➔ None
        """
        if valor_raw is None:
            return None

        if isinstance(valor_raw, (int, float)):
            if math.isnan(valor_raw):
                return None
            return round(float(valor_raw), 2)

        texto = str(valor_raw).strip()
        if not texto or texto in {"-", "--", "N/A", "null", "None"}:
            return None

        # Detectar signo negativo por paréntesis, ej: (500) o -500
        es_negativo = False
        if texto.startswith("(") and texto.endswith(")"):
            es_negativo = True
            texto = texto[1:-1].strip()
        elif "-" in texto:
            es_negativo = True

        # Remover prefijos y sufijos de moneda explícitos (ej: 'Bs.', 'Bs', 'BOB', '$', 'USD')
        texto_norm = re.sub(r'(?i)\b(bs\.|bs|bob|usd|\$|bolivianos?)\b', '', texto)
        texto_norm = re.sub(r'[A-Za-z\$\s]', '', texto_norm).replace('-', '').strip()
        if not texto_norm:
            return None

        # Si quedó un punto inicial como '.500' y son 3 dígitos (ej: venía de 'Bs. 500')
        if texto_norm.startswith('.') and len(texto_norm) == 4 and texto_norm[1:].isdigit():
            texto_norm = texto_norm[1:]

        # Limpiar punto o coma trailing (ej: '1500.')
        if texto_norm.endswith('.') or texto_norm.endswith(','):
            texto_norm = texto_norm[:-1].strip()

        texto_limpio = texto_norm

        # Identificar separadores de miles y decimales
        # Casos:
        # 1. Tiene coma y punto:
        #    a) "1.500,50" -> punto es miles, coma es decimal
        #    b) "1,500.50" -> coma es miles, punto es decimal
        # 2. Solo tiene punto:
        #    a) "1.500" -> si son 3 dígitos después del punto, suele ser miles
        #    b) "1500.50" -> 2 dígitos, es decimal
        # 3. Solo tiene coma:
        #    a) "1,500" -> miles
        #    b) "1500,50" -> decimal
        if '.' in texto_limpio and ',' in texto_limpio:
            pos_punto = texto_limpio.rfind('.')
            pos_coma = texto_limpio.rfind(',')
            if pos_coma > pos_punto:
                # Formato europeo/latino: 1.500,50
                texto_limpio = texto_limpio.replace('.', '').replace(',', '.')
            else:
                # Formato anglosajón: 1,500.50
                texto_limpio = texto_limpio.replace(',', '')
        elif ',' in texto_limpio:
            partes = texto_limpio.split(',')
            if len(partes) == 2 and len(partes[1]) in {1, 2}:
                # Es decimal: 1500,50
                texto_limpio = partes[0].replace('.', '') + '.' + partes[1]
            elif len(partes) > 1 and all(len(p) == 3 for p in partes[1:]):
                # Es miles: 1,500 o 1,500,000
                texto_limpio = ''.join(partes)
            else:
                texto_limpio = texto_limpio.replace(',', '.')
        elif '.' in texto_limpio:
            partes = texto_limpio.split('.')
            if len(partes) == 2:
                if partes[0] == "":
                    texto_limpio = "0." + partes[1]
                elif len(partes[1]) == 3 and partes[0].isdigit() and int(partes[0]) > 0:
                    # Típico miles boliviano: 1.500 -> 1500
                    texto_limpio = partes[0] + partes[1]
            elif len(partes) > 2:
                # Múltiples puntos de miles: 1.500.000
                texto_limpio = ''.join(partes)

        try:
            val = float(texto_limpio)
            if es_negativo:
                val = -val
            return round(val, 2)
        except (ValueError, TypeError):
            return None

    @classmethod
    def validar_transaccion(
        cls,
        cuota: Any,
        pagado: Any,
        saldo: Any,
        moneda_raw: Any = "BOB",
        tolerancia: float = 0.05
    ) -> Dict[str, Any]:
        """
        Valida la coherencia contable de una transacción:
        Saldo = Cuota - Pagado
        """
        c_val = cls.sanitizar_importe(cuota)
        p_val = cls.sanitizar_importe(pagado)
        s_val = cls.sanitizar_importe(saldo)

        moneda, es_bob = cls.extraer_moneda(str(moneda_raw or "BOB"))

        errores = []
        advertencias = []

        if c_val is None:
            errores.append("Monto de Cuota no válido o ausente.")
        if p_val is None:
            errores.append("Monto Pagado no válido o ausente.")
        if s_val is None:
            errores.append("Monto de Saldo no válido o ausente.")

        if errores:
            return {
                "valido": False,
                "cuota": c_val,
                "pagado": p_val,
                "saldo_registrado": s_val,
                "saldo_calculado": None,
                "diferencia": None,
                "moneda": moneda,
                "cuadre_contable": False,
                "requiere_revision": True,
                "errores": errores,
                "advertencias": advertencias,
                "motivo": "Importes numéricos no válidos o faltantes."
            }

        # Validación de montos no negativos
        if c_val < 0 or p_val < 0:
            errores.append("Cuota o pago no pueden ser valores negativos.")
        if s_val < 0:
            advertencias.append("Saldo registrado negativo (posible pago en exceso o saldo a favor).")

        if not es_bob:
            advertencias.append(f"Moneda detectada '{moneda}' difiere de la moneda institucional (BOB/Bs).")

        # Regla contable: Saldo = Cuota - Pagado
        saldo_calculado = round(c_val - p_val, 2)
        diferencia = round(abs(saldo_calculado - s_val), 2)
        cuadre_correcto = diferencia <= tolerancia

        if not cuadre_correcto:
            errores.append(
                f"Inconsistencia contable detectada: Saldo registrado ({s_val:.2f} {moneda}) "
                f"difiere del saldo calculado Cuota - Pagado ({saldo_calculado:.2f} {moneda}) "
                f"por {diferencia:.2f} {moneda}."
            )

        requiere_revision = (len(errores) > 0)

        return {
            "valido": cuadre_correcto and (len(errores) == 0),
            "cuota": c_val,
            "pagado": p_val,
            "saldo_registrado": s_val,
            "saldo_calculado": saldo_calculado,
            "diferencia": diferencia,
            "moneda": moneda,
            "cuadre_contable": cuadre_correcto,
            "requiere_revision": requiere_revision,
            "errores": errores,
            "advertencias": advertencias,
            "motivo": "Transacción contablemente consistente." if cuadre_correcto and not errores else "; ".join(errores)
        }

    @classmethod
    def validar_meta_ejecutado(
        cls,
        meta: Any,
        ejecutado: Any,
        periodo: Optional[str] = None,
        categoria: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Valida y calcula métricas de cumplimiento entre Meta institucional y Ejecutado real:
        Cumplimiento = (Ejecutado / Meta) * 100
        """
        m_val = cls.sanitizar_importe(meta)
        e_val = cls.sanitizar_importe(ejecutado)

        errores = []
        advertencias = []

        if m_val is None:
            errores.append("Monto de Meta no válido o ausente.")
        if e_val is None:
            errores.append("Monto Ejecutado no válido o ausente.")

        if errores:
            return {
                "valido": False,
                "meta": m_val,
                "ejecutado": e_val,
                "cumplimiento_pct": 0.0,
                "brecha": None,
                "periodo": periodo,
                "categoria": categoria,
                "anomalia_detectada": True,
                "requiere_revision": True,
                "errores": errores,
                "advertencias": advertencias,
                "motivo": "Valores de meta o ejecutado no numéricos."
            }

        if m_val <= 0:
            errores.append("La meta presupuestaria debe ser mayor a cero.")
        if e_val < 0:
            errores.append("El monto ejecutado no puede ser negativo.")

        cumplimiento = round((e_val / m_val) * 100.0, 2) if m_val and m_val > 0 else 0.0
        brecha = round(m_val - e_val, 2) if m_val is not None else 0.0

        # Detección de anomalías de escala (ej. ejecutado > 250% de la meta o desproporción)
        anomalia = False
        if cumplimiento > 250.0:
            anomalia = True
            advertencias.append(
                f"Alerta de escala atípica: El ejecutado ({e_val:.2f}) supera el 250% de la meta ({m_val:.2f}) - {cumplimiento:.1f}%."
            )
        elif cumplimiento < 10.0 and m_val > 10000:
            advertencias.append(
                f"Bajo nivel de ejecución ({cumplimiento:.1f}%): Requiere seguimiento comercial/financiero."
            )

        requiere_revision = (len(errores) > 0) or anomalia

        return {
            "valido": (len(errores) == 0),
            "meta": m_val,
            "ejecutado": e_val,
            "cumplimiento_pct": cumplimiento,
            "brecha": brecha,
            "periodo": periodo,
            "categoria": categoria,
            "anomalia_detectada": anomalia,
            "requiere_revision": requiere_revision,
            "errores": errores,
            "advertencias": advertencias,
            "motivo": "Meta y ejecutado validados correctamente." if not errores else "; ".join(errores)
        }
