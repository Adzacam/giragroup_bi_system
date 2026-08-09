# POS Suffix Length Distribution Analysis

This document presents the detailed counts and length distributions of POS suffixes across all 5 master sheets in the GiraGroup real corpus.

## Distribution by Source Table

| Source Master Sheet | Unique POS Suffixes | Suffix Lengths Distribution |
| :--- | :---: | :--- |
| ARCA -> ACTAS DE NOTAS | 475 | Len 4: 475 |
| ARCA -> MODULOS | 381 | Len 4: 381 |
| ARCA -> PROGRMAS  DE BAJA | 1 | Len 4: 1 |
| Planificacion -> Centralizado_Mensual | 117 | Len 4: 117 |
| TBL_INSCRITOS -> TBL_INSCRITOS | 961 | Len 4: 14967 |
| **GLOBAL UNIQUE** | 1,004 | Len 4: 1004 |

## Suffix Length Details
- **Length 4** (Total: 1004): Samples: ['5589', '5971', '5522', '5472', '5906', '6141', '4553', '5791', '5184', '5987', '5832', '5673', '4881', '4562', '5592']

## Design Decisions & Verification Conclusion

- **Regex Range Validation**: The current standard regex matches `POS-[a-zA-Z0-9]{2,4}`.
- **Actual Data Observation**: The distribution shows that 100% of standard POS suffixes are exactly **4 characters** in the real corpus (and **3 characters** in the test corpus).
- **Conclusion**: The range `{2,4}` covers 100% of both real and test POS suffixes.
- **Fallback Action Rule**: If a master POS suffix with length 5+ is ever encountered:
  - The pipeline will log a `WARNING` during loading: `[FK_CHECKER] Valid POS suffix outside standard length range found: {pos}`.
  - To ensure no data loss, the pipeline will expand the regex range dynamically in memory or log it as a configuration warning for manual schema review.