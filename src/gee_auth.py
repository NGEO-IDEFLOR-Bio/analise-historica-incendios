"""
Módulo de inicialização e autenticação universal com o Google Earth Engine.
Suporta de forma transparente:
1. Google Colab: autenticação interativa nativa (ee.Authenticate / ee.Initialize)
2. Ambiente Local com Service Account (secrets/*.json)
3. Ambiente Local com credenciais de usuário (gcloud / ee.Authenticate)
"""
import sys
from pathlib import Path
from typing import Optional

# Garante raiz no path quando executado diretamente
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import ee
from google.oauth2.service_account import Credentials
from src.config import GEE_PROJECT_ID, GEE_CREDENTIALS_JSON

_EE_INITIALIZED = False

def init_gee(project_id: Optional[str] = None, force: bool = False) -> bool:
    """
    Inicializa a sessão do Google Earth Engine de forma universal e adaptativa:
    - Se estiver no Google Colab, executa o fluxo interativo do navegador com 1 clique.
    - Se houver arquivo de Service Account configurado e existente, utiliza-o diretamente.
    - Caso contrário, utiliza autenticação interativa ou sessão ativa do usuário.
    """
    global _EE_INITIALIZED
    if _EE_INITIALIZED and not force:
        return True

    proj = project_id or GEE_PROJECT_ID
    is_colab = "google.colab" in sys.modules

    # 1. Fluxo Interativo Nativo no Google Colab
    if is_colab:
        try:
            ee.Initialize(project=proj)
            _EE_INITIALIZED = True
            return True
        except Exception:
            print("Iniciando autenticação interativa do Google Earth Engine no Colab...")
            ee.Authenticate()
            ee.Initialize(project=proj)
            _EE_INITIALIZED = True
            return True

    # 2. Fluxo via Service Account (Ambiente Local com chave privada)
    if GEE_CREDENTIALS_JSON.exists():
        try:
            credentials = Credentials.from_service_account_file(
                str(GEE_CREDENTIALS_JSON),
                scopes=[
                    "https://www.googleapis.com/auth/earthengine",
                    "https://www.googleapis.com/auth/cloud-platform"
                ]
            )
            ee.Initialize(credentials=credentials, project=proj)
            _EE_INITIALIZED = True
            return True
        except Exception as e:
            print(f"Aviso: falha na autenticação com Service Account ({e}). Tentando método padrão...")

    # 3. Fluxo Padrão / Interativo Local (gcloud auth ou ee.Authenticate)
    try:
        ee.Initialize(project=proj)
        _EE_INITIALIZED = True
        return True
    except Exception:
        print("Sessão GEE não encontrada. Abrindo navegador para autenticação interativa...")
        ee.Authenticate()
        ee.Initialize(project=proj)
        _EE_INITIALIZED = True
        return True

if __name__ == "__main__":
    print(f"Testando inicialização GEE com projeto '{GEE_PROJECT_ID}'...")
    init_gee()
    print("Google Earth Engine inicializado com sucesso!")
