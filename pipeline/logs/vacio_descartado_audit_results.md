# Ingestion Pipeline: `vacio_descartado` Audit Report

This report provides a quantifiable breakdown of the 34,988 documents classified as `vacio_descartado` on the real GiraGroup corpus.

## Quantitative Breakdown

| Category | Count | Percentage | Avg. Length (Chars) | Avg. Length (Words) |
| :--- | :---: | :---: | :---: | :---: |
| **Real Empty** | 31,390 | 33.94% | 0.00 | 0.00 |
| **Admin Blank** | 2,976 | 3.22% | 1.84 | 1.02 |
| **Short Text** | 47,567 | 51.44% | 15.69 | 2.05 |
| **Ninguno Ninguna** | 9,921 | 10.73% | 6.70 | 1.00 |
| **Numeric Only** | 113 | 0.12% | 1.67 | 1.00 |
| **One Char** | 509 | 0.55% | 1.00 | 1.00 |
| **Total** | 92,476 | 100.00% | - | - |

## Category Details & Explanations

### 1. Real Empty
Total: 31,390 cels contain literal Excel empty/NaN cells or blank spacing. These are 100% correct to discard.

### 2. Administrative Blanks
Total: 2,976 cels contain standard filler expressions such as `N/A`, `-`, `.`, `sin respuesta` that hold no information. Discarding is 100% correct.
Samples found: ['..............................', '.................................', '...............', '...........', '......', '...................................................', '..........', '............', '....', 'N.A.', '.......', '.', '-----------------------', '--', '........................................']

### 3. Ninguno / Ninguna
Total: 9,921 cels contain 'ninguno', 'ninguna', or similar. **Note**: These are currently NOT in the default exclusion list (`_VALORES_VACIOS`). Let's inspect where they ended up.
Samples found: ['NADA', 'nada', 'NInguna', 'Nada', 'Ninguna', 'NInguno', 'ninguno', 'nINGUNO', 'NINGUNA', 'nADA']

### 4. Numeric Only
Total: 113 cels contain purely numeric sequences. These represent rating scores or CI values that got incorrectly written to a text column in Excel. Since they hold no text for NER extraction, they are correctly flagged as empty.
Samples found: ['78101773', '3', '10', '2132', '834', '0', '9167641125', '5', '4535', '4354', '4', '123456789', '23434', '2', '7']

### 5. One Character
Total: 509 cels contain a single letter or character (e.g. 'x', '?'). Correctly discarded as garbage.
Samples found: ['L', 'Y', ',', 'u', 'i', 'x', '…', 'M', 'A', 'G', '😌', 'n', '_', 'k', '✨']

### 6. Potential Short Text
Total: 47,567 cels contain 1-3 words of actual content. Let's verify what values are in this bucket to see if any valid answers are being discarded.
Samples: ['MONTERO BARRIO PORVENIR', 'SOPOCACHI/CHACO/1158', 'SANTA ROSA/"B"/2', 'TEMPORAL CALLE 12', 'ESTUDIANTE', 'lipoestructurasion', 'Tarija colon ,#617', 'información constante', 'ERICKA  MERIDA SIÑANI', 'la psicologia emocional', 'Muy  buena explicaión', 'Calle Ramón Clouzet', 'ahondar mas', 'Valdivieso 542', 'dinamicos', 'Mas actualiza', 'patologias duales', 'Programación python', 'dominio del tema', 'Datos maestros', 'planificacion', 'neuromarketing', 'ROXANA VILLALTA FERNÁNDEZ', 'Con más ejemplos', 'Dirección Empresarial', 'UNIVERSIDAD NACIONAL ECOLOGICA', 'SOPOCACHI, PLAZA ESPAÑA', 'Retroalimentacion', 'Anestesicos locales', 'GINECOLOGIA']