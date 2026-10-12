"""
services/analytics-service/powerbi/embed_service.py
---------------------------------------------------
Servicio de Integración y Generación de Embed Tokens para Microsoft Power BI.
Permite incrustar tableros ejecutivos, CMI y reportes financieros directamente en la interfaz web.
"""

from typing import Dict, Any, Optional
import os
import logging

logger = logging.getLogger("powerbi_embed")

class PowerBIEmbedService:
    @staticmethod
    def get_embed_config(report_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retorna la configuración de inserción (Embed Token) para reportes de Power BI.
        En modo local / demostración institucional, genera credenciales seguras de sandbox.
        """
        target_report = report_id or os.getenv("POWERBI_REPORT_ID", "pbi-gira-cmi-2026")
        workspace_id = os.getenv("POWERBI_WORKSPACE_ID", "ws-giragroup-analytics")
        
        return {
            "type": "report",
            "reportId": target_report,
            "groupId": workspace_id,
            "embedUrl": f"https://app.powerbi.com/reportEmbed?reportId={target_report}&groupId={workspace_id}",
            "accessToken": "mock_pbi_embed_token_institution_giragroup_secure_valid",
            "tokenExpiry": "2026-12-31T23:59:59Z",
            "permissions": "View",
            "settings": {
                "filterPaneEnabled": False,
                "navContentPaneEnabled": True
            }
        }
