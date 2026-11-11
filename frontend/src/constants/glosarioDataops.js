// Textos del glosario flotante del flujo DataOps (pasos ① a ④).
export const GLOSARIO_DATAOPS = {
  titulo: 'Cómo funciona el flujo de carga de datos',
  intro: 'Cada archivo que se carga pasa por cuatro pasos antes de llegar a los reportes. Aquí se explica cada término.',
  terminos: [
    ['Lote', 'Conjunto de archivos que se cargan y se procesan juntos. Un lote avanza por los cuatro pasos y se cierra al consolidarlo.'],
    ['① Ingesta', 'Se sube el archivo y el sistema revisa su estructura, su tipo (actas, cobranzas, admisiones) y que no esté repetido.'],
    ['② Texto plano', 'Cada fila del archivo se convierte en una oración ordenada que el modelo puede leer.'],
    ['Privacidad en el paso ②', 'El servidor oculta nombres, cédula, celular, correo, NIT, dirección y fecha de nacimiento antes de mostrar el texto. Los códigos que repiten la cédula también se protegen.'],
    ['③ Lectura de BETO', 'El modelo identifica estudiante, módulo, nota y montos en cada fila y calcula qué tan seguro está.'],
    ['④ Revisión humana', 'Una persona decide los casos en que el modelo no estuvo lo bastante seguro.'],
    ['Índice de confianza', 'Porcentaje de seguridad del modelo sobre cada registro, de 0 a 100.'],
    ['Umbral del 85 %', 'Valor fijo definido por la metodología. Con 85 % o más el registro entra directo; entre 60 % y 85 % entra marcado para revisión; por debajo queda en la bandeja.'],
    ['Consolidar', 'Guardar en el Data Warehouse los registros aprobados. Desde ese momento alimentan el CMI y los reportes.'],
    ['Data Warehouse', 'Base de datos institucional donde se guarda la información ya validada.'],
    ['Lote cerrado', 'Un lote consolidado queda de solo lectura. Para cargar archivos nuevos se inicia otro lote.'],
    ['Datos personales protegidos', 'La cédula de identidad se muestra siempre enmascarada (••••019). Solo el administrador y el auditor pueden revelarla, y cada consulta queda registrada.'],
  ],
};
