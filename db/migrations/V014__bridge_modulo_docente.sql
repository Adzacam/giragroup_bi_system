-- ==============================================================================
-- Migración V014: bridge_modulo_docente
--
-- Qué docente dictó cada módulo (POS-XXXX-MNN), cargado desde hojas de asignación (MODULOS).
-- Atribuye notas y evaluaciones al docente cuando la fila no lo nombra. Idempotente.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.bridge_modulo_docente (
    id_asignacion SERIAL PRIMARY KEY,
    id_modulo INTEGER NOT NULL REFERENCES public.dim_modulo(id_modulo) ON DELETE CASCADE,
    id_docente INTEGER NOT NULL REFERENCES public.dim_docente(id_docente) ON DELETE CASCADE,
    id_documento INTEGER REFERENCES public.dim_origen_documental(id_documento) ON DELETE SET NULL,
    tipo_docente VARCHAR(30),
    grado_academico VARCHAR(50),
    horas_modulo NUMERIC(6, 2),
    pago_docente NUMERIC(12, 2),
    fecha_inicio DATE,
    fecha_fin DATE,
    CONSTRAINT uq_bridge_modulo_docente UNIQUE (id_modulo, id_docente)
);
CREATE INDEX IF NOT EXISTS idx_bridge_mod_doc_modulo ON public.bridge_modulo_docente (id_modulo);
CREATE INDEX IF NOT EXISTS idx_bridge_mod_doc_docente ON public.bridge_modulo_docente (id_docente);
