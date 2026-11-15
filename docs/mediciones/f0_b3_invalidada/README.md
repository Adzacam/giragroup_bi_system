# B-3 inicial invalidada por procedencia incompleta

La inferencia terminó y guardó spans sin texto, pero falló la serialización de numpy.int64 antes de persistir la metadata. La recuperación posterior reconstruyó seis filas, sin una ligadura criptográfica registrada antes de inferir. Estos archivos se conservan como evidencia provisional excluida; no reemplazan el nuevo resultado con sidecar f0_b3_procedencia.json.

Registro inicial: ../f0_b3_ejecucion.txt. Registro de recuperación: ../f0_b3_recuperacion.txt. La nueva inferencia válida no reutiliza estos resultados.
