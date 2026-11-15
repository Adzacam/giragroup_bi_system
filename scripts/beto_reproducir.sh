#!/bin/bash
# Reproduce de punta a punta el ajuste fino de BETO SIN tocar pipeline/semantic/beto_local ni data/*.jsonl vigentes.
#   corpus (determinista, partición por persona) -> entrenamiento a directorio temporal
#   -> evaluación estricta y relajada en gold_510 y layouts_5 -> test.conll -> matriz de confusión.
# Uso: make beto-reproducir        (o)   BETO_SALIDA=/ruta/vacia bash scripts/beto_reproducir.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONHASHSEED=0 PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 BETO_INT8=0
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe
  elif [ -x .venv/bin/python ]; then PY=.venv/bin/python
  else PY=python; fi
fi
if [ -n "${BETO_SALIDA:-}" ]; then
  if [ -e "$BETO_SALIDA" ] && [ -n "$(ls -A "$BETO_SALIDA")" ]; then
    echo "BETO_SALIDA debe ser nuevo o vacío" >&2; exit 2
  fi
  mkdir -p "$BETO_SALIDA"
fi
SALIDA="${BETO_SALIDA:-$(mktemp -d)}"
case "$(cd "$SALIDA" && pwd)" in
  "$(pwd)"/pipeline/*|"$(pwd)"/data) echo "BETO_SALIDA no puede ser pipeline/ ni data/" >&2; exit 2;;
esac
mkdir -p "$SALIDA/corpus" "$SALIDA/modelo" "$SALIDA/eval"
echo "== Salida: $SALIDA"
echo "== 1/3 Corpus determinista"
"$PY" scripts/preparar_corpus_robusto.py --salida "$SALIDA/corpus" > "$SALIDA/corpus/log.txt"
echo "== 2/3 Entrenamiento CPU"
"$PY" scripts/entrenar_beto_robusto.py --datos "$SALIDA/corpus" --salida "$SALIDA/modelo"
echo "== 3/3 Evaluación estricta y relajada: gold_510, layouts_5, test.conll"
"$PY" scripts/evaluar_beto_checkpoint.py --modelo "$SALIDA/modelo" --gold "$SALIDA/corpus/test_gold_real.jsonl" --salida "$SALIDA/eval"
echo "== Listo. Resultados y matriz en $SALIDA/eval; hashes en modelo/training_info.json"
