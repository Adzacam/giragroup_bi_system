from .dim_tiempo import DimTiempo
from .dim_estudiante import DimEstudiante
from .dim_docente import DimDocente
from .dim_modulo import DimModulo
from .dim_origen import DimOrigenDocumental
from .dim_categoria_financiera import DimCategoriaFinanciera
from .user import User
from .notification import Notification
from .staging_registro import StagingRegistroCrudo
from .log_pipeline import LogPipelineIngesta
from .log_auditoria_nlp import LogAuditoriaNlp
from .fact_rendimiento import FactRendimientoAcademico
from .fact_financiero import FactSituacionFinanciera
from .fact_cobranzas import FactCobranzasProyectadas
from .fact_evaluacion import FactEvaluacionDocente
from .fact_marketing import FactMarketing
from .fact_rentabilidad import FactRentabilidad
from .dim_meta import DimMeta
from .fact_forecast import FactForecast
from .staging_entidad import StagingEntidadNoResuelta
from .catalogos import (
    CatEscuela,
    CatTipoPrograma,
    CatModalidad,
    CatPrograma,
    CatDocente,
    CatModulo,
    CatEstadoAcademico,
    CatEstadoReprobado,
    CatEstadoArca,
    CatTipoCartera,
    RefMetasGestion,
    CatEtiquetaClasificacion,
    CatMapeoColumna,
    CatGuiaTextoPlano,
)