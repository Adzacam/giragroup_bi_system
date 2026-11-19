// Textos del glosario flotante del CMI, por pestaña.
export const GLOSARIO_CMI = {
  scorecard: {
    titulo: 'Cómo leer el Cuadro de Mando Integral',
    intro: 'El scorecard consolida el desempeño institucional en cuatro perspectivas estratégicas con metas y semáforos unificados.',
    terminos: [
      ['Índice global', 'Promedio ponderado de las perspectivas activas (0 a 100). En meta = 100, en alerta = 60, crítico = 20.'],
      ['Mapa estratégico', 'Relación causa → efecto desde Aprendizaje y Crecimiento hasta la perspectiva Financiera.'],
      ['Semáforo', 'Verde (en meta), Ámbar (en alerta) y Rojo (crítico) según los umbrales configurados para cada indicador.'],
      ['Variación (Δ)', 'Diferencia respecto a la gestión inmediatamente anterior.'],
    ],
  },
  prediccion: {
    titulo: 'Cómo leer la analítica predictiva',
    intro: 'Las proyecciones se calculan con los datos ya consolidados en el sistema y se actualizan al cargar nuevas fuentes.',
    terminos: [
      ['Holt-Winters amortiguado', 'Modelo que proyecta con la tendencia y la estacionalidad anual de la serie. "Amortiguado" significa que la tendencia pierde fuerza con los meses, así que la curva se aplana en lugar de crecer sin límite.'],
      ['Banda de confianza 95 %', 'Rango en el que se espera que caiga el valor real. Cuanto más ancha, más incierta es la proyección.'],
      ['Horizonte', 'Cantidad de meses hacia adelante que se proyectan (de 1 a 6).'],
      ['MAPE', 'Error porcentual medio al comparar el modelo con los últimos meses reales. Menos de 20 % se considera una buena precisión.'],
      ['RMSE', 'Error promedio del modelo expresado en la misma unidad de la serie (estudiantes o bolivianos).'],
      ['CAGR', 'Crecimiento anual compuesto: cuánto creció o decreció la serie por año en promedio.'],
      ['Matriz de viabilidad', 'Recomendación por programa (abrir nueva versión, continuar o reestructurar) según su demanda reciente y su crecimiento.'],
    ],
  },
  configuracion: {
    titulo: 'Cómo configurar los indicadores',
    intro: 'Aquí se ajusta cómo se evalúa cada indicador. Los cambios se reflejan en la web y en Power BI al actualizar.',
    terminos: [
      ['Meta', 'Valor que la dirección quiere alcanzar. Sin meta, el indicador se muestra como informativo y no puntúa.'],
      ['Sentido', '"Más es mejor" o "Menos es mejor". Define cómo se compara el valor con la meta.'],
      ['Umbral verde y ámbar', 'Límites del semáforo: en meta (verde), en alerta (ámbar) y crítico (rojo) cuando no llega al ámbar.'],
      ['Peso', 'Importancia relativa dentro de su perspectiva. Los pesos de las perspectivas activas deberían sumar 100 %.'],
      ['Activo', 'Un indicador desactivado deja de mostrarse y de puntuar, pero conserva su historial.'],
      ['Editar o quitar', 'Puedes cambiar meta, umbrales, peso y estado de cada indicador, y desactivar los que no necesites.'],
      ['Agregar un indicador nuevo', 'Un indicador nuevo necesita una fórmula de cálculo sobre los datos consolidados, por lo que se solicita al equipo de datos; una vez creado, aparece aquí para configurarlo.'],
    ],
  },
  powerbi: {
    titulo: 'Cómo usar el informe en Power BI Desktop',
    intro: 'El archivo .pbix conecta directamente con el esquema analítico de sólo lectura para exploración avanzada.',
    terminos: [
      ['Versión vigente', 'Archivo .pbix oficial que descargan los roles autorizados.'],
      ['Restaurar versión', 'Permite volver a marcar una versión anterior como vigente sin perder el historial.'],
      ['Eliminar versión', 'Borra versiones históricas (> v1) que ya no se necesiten. La versión base v1 permanece protegida.'],
    ],
  },
};
