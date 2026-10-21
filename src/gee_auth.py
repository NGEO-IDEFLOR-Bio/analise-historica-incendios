"""
Módulo de inicialização e autenticação com o Google Earth Engine via Service Account.
"""
import sys
from pathlib import Path

# Garante raiz no path quando executado diretamente
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import ee
from google.oauth2.service_account import Credentials
from src.config import GEE_PROJECT_ID, GEE_CREDENTIALS_JSON

_EE_INITIALIZED = False

def init_gee(force: bool = False) -> bool:
    """Inicializa a sessão do Google Earth Engine com a Service Account configurada."""
    global _EE_INITIALIZED
    if _EE_INITIALIZED and not force:
        return True

    if not GEE_CREDENTIALS_JSON.exists():
        raise FileNotFoundError(
            f"Arquivo de credenciais GEE não encontrado em: {GEE_CREDENTIALS_JSON}\n"
            "Verifique o caminho no arquivo .env."
        )

    credentials = Credentials.from_service_account_file(
        str(GEE_CREDENTIALS_JSON),
        scopes=[
            "https://www.googleapis.com/auth/earthengine",
            "https://www.googleapis.com/auth/cloud-platform"
        ]
    )

    ee.Initialize(credentials=credentials, project=GEE_PROJECT_ID)
    _EE_INITIALIZED = True
    return True

if __name__ == "__main__":
    print(f"Tentando inicializar GEE com projeto '{GEE_PROJECT_ID}'...")
    init_gee()
    print("GEE inicializado com sucesso!")
