-- CAT-L0: Inventario reproducible del catálogo de módulos e instituciones (sin PII)
-- Uso: docker compose exec -T db psql -U giragroup_user -d giragroup_db -f - --csv < scripts/auditoria_dw/cat_inventario.sql > docs/mediciones/cat_l0_inventario.csv

WITH clasificado AS (
    SELECT
        id_modulo,
        pos_code,
        CASE
            WHEN pos_code LIKE 'POS-%' THEN 'POS'
            WHEN pos_code IS NOT NULL AND pos_code != 'MOD-GEN' THEN 'OTRO_CODIGO'
            WHEN TRIM(nombre_modulo) ~ '^\d{4}-\d{2}-\d{2}' THEN 'MOD_GEN_FECHA'
            WHEN TRIM(nombre_modulo) ~ '^\d+(\.\d+)?$' THEN 'MOD_GEN_NUMERO'
            WHEN UPPER(TRIM(nombre_modulo)) IN ('SI', 'SÍ', 'NO', 'N/A', 'NA', '-', '--', 'NINGUNO', 'NINGUNA', 'SIN DATO', 'NULL', 'NONE', '.')
                 OR LENGTH(TRIM(nombre_modulo)) <= 3 THEN 'MOD_GEN_CENTINELA'
            WHEN id_modulo IN (1224, 4318, 1380, 1439, 1502) THEN 'MOD_GEN_DC3_CANDIDATO'
            WHEN UPPER(TRIM(nombre_modulo)) ~ '^(LIC\.?|ING\.?|DR\.?|DRA\.?|MSC\.?|ABOGAD|INGENIER|M[EÉ]DIC|ARQUITECT|ECONOMIST|CONTADOR|ADMINISTRADOR|FARMAC[EÉ]UTIC|BIOQU[IÍ]MIC|PSIC[OÓ]LOG|ODONT[OÓ]LOG|ENFERMER|T[EÉ]CNICO|PROFESOR|DOCENTE)' THEN 'MOD_GEN_PROFESION_TITULO'
            ELSE 'MOD_GEN_CARRERA_CARGO'
        END AS clase,
        (programa IS NULL OR TRIM(programa) = '' OR LOWER(TRIM(programa)) = 'sin dato') AS sin_programa
    FROM dim_modulo
)
SELECT
    'dim_modulo' AS tabla,
    clase,
    COUNT(*) AS n,
    COUNT(*) FILTER (WHERE sin_programa) AS sin_programa,
    MIN(id_modulo) AS min_id,
    MAX(id_modulo) AS max_id
FROM clasificado
GROUP BY clase
ORDER BY n DESC;
