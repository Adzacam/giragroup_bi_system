"""T-5: Recarga BD Techos.xlsx via gateway (/api/v1/dataops/upload-batch + confirm-dw-insert) y verifica la DW viva."""
import hashlib
import json
import subprocess
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://localhost"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def mint_admin_token() -> str:
    out = subprocess.check_output(
        [
            "docker",
            "exec",
            "giragroup_api",
            "python",
            "-c",
            "from core.security import create_access_token; print(create_access_token({'sub': 'admin_general', 'role': 'ADMIN'}))",
        ],
        text=True,
    )
    return out.strip().splitlines()[-1]


def psql_json(sql: str):
    out = subprocess.check_output(
        [
            "docker",
            "exec",
            "giragroup_db",
            "psql",
            "-U",
            "giragroup_user",
            "-d",
            "giragroup_db",
            "-t",
            "-A",
            "-c",
            f"SELECT coalesce(json_agg(t), '[]'::json) FROM ({sql}) t",
        ],
        text=True,
    )
    return json.loads(out.strip())


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--solo-verificar-lote", type=int, default=0)
    args = p.parse_args()

    dump_path = ROOT / "output/f3t/giragroup_db_pre_t5.dump"
    xlsx_path = ROOT / "uploads/data/BD Techos.xlsx"

    if args.solo_verificar_lote:
        id_lote = args.solo_verificar_lote
        up_json = {"omitido": True, "motivo": "verificacion post-recarga"}
        cons_json = {"omitido": True, "motivo": "verificacion post-recarga"}
    else:
        token = mint_admin_token()
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Subir BD Techos.xlsx al gateway
        with xlsx_path.open("rb") as fh:
            r_up = requests.post(
                f"{BASE_URL}/api/v1/dataops/upload-batch",
                headers=headers,
                files=[("files", (xlsx_path.name, fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
                data={"institucion": "GiraGroup", "periodo": "2024"},
                timeout=120,
            )
        r_up.raise_for_status()
        up_json = r_up.json()
        id_lote = up_json.get("id_lote")
        if not id_lote:
            raise RuntimeError(f"upload-batch no devolvio id_lote: {up_json}")

        # 2. Consolidar lote (sincrono)
        r_cons = requests.post(
            f"{BASE_URL}/api/v1/dataops/confirm-dw-insert",
            headers=headers,
            json={"id_lote": id_lote, "en_segundo_plano": False},
            timeout=300,
        )
        r_cons.raise_for_status()
        cons_json = r_cons.json()

    # 3. Verificar en la DW viva
    docs_lote = psql_json(f"SELECT id_documento, nombre_archivo, tipo_fuente, id_lote FROM dim_origen_documental WHERE id_lote = {int(id_lote)}")
    doc_ids = [d["id_documento"] for d in docs_lote]
    doc_in = ",".join(str(int(i)) for i in doc_ids)
    stg_doc = psql_json(f"SELECT tipo_entidad, motivo, count(*) FROM stg_entidad_no_resuelta WHERE id_documento IN ({doc_in}) GROUP BY tipo_entidad, motivo") if doc_ids else []
    stg_est_pend_total = psql_json("SELECT count(*) AS pendientes FROM stg_entidad_no_resuelta WHERE resuelto = false AND tipo_entidad = 'ESTUDIANTE'")
    conv_por_doc = psql_json("SELECT id_documento, count(*) AS filas FROM fact_techo_convenio GROUP BY id_documento ORDER BY id_documento")
    conv_total = psql_json("SELECT count(*) AS total FROM fact_techo_convenio")
    dups = psql_json(
        "SELECT clave_convenio, count(*) AS c "
        "FROM fact_techo_convenio GROUP BY clave_convenio HAVING count(*) > 1"
    )

    out = {
        "etiqueta": "F3T",
        "tarea": "T-5 (Borrado lote #3 y recarga completa de BD Techos.xlsx en DW viva)",
        "dump_previo": {
            "ruta": str(dump_path.relative_to(ROOT)),
            "sha256": sha256_file(dump_path),
            "bytes": dump_path.stat().st_size,
        },
        "nuevo_lote": {
            "id_lote": id_lote,
            "documentos": docs_lote,
            "upload_respuesta": up_json,
            "consolidacion_respuesta": cons_json,
        },
        "verificacion_dw_viva": {
            "stg_nuevo_doc": stg_doc,
            "stg_estudiante_pendientes_global": stg_est_pend_total[0]["pendientes"],
            "fact_techo_convenio_por_doc": conv_por_doc,
            "fact_techo_convenio_total": conv_total[0]["total"],
            "duplicados_convenio": dups,
            "cero_duplicados": len(dups) == 0,
        },
    }
    (ROOT / "docs/mediciones/f3t_lote3_viva.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"[OK] T-5 id_lote={id_lote} docs={doc_ids} total_convenios={conv_total[0]['total']} "
        f"dups={len(dups)} stg_nuevo={stg_doc}"
    )


if __name__ == "__main__":
    main()
