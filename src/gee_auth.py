"""
Módulo de inicialização e autenticação universal com o Google Earth Engine.
Suporta de forma transparente:
1. Google Colab: autenticação interativa nativa (ee.Authenticate / ee.Initialize) com suporte a projeto customizado do usuário.
2. Ambiente Local com Service Account (secrets/*.json).
3. Ambiente Local com credenciais de usuário (gcloud / ee.Authenticate).
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

    is_colab = "google.colab" in sys.modules

    # Tratamento do ID do projeto informado
    proj = project_id.strip() if (project_id and isinstance(project_id, str) and project_id.strip()) else None
    if proj and (proj.startswith("seu-projeto") or proj.lower() == "none"):
        proj = None

    # No Google Colab, não aplicar o fallback da Service Account local privada (evita erro 403 Forbidden)
    if not proj and not is_colab:
        proj = GEE_PROJECT_ID

    # 1. Fluxo Interativo Nativo no Google Colab
    if is_colab:
        init_kwargs = {"project": proj} if proj else {}
        try:
            ee.Initialize(**init_kwargs)
            _EE_INITIALIZED = True
            return True
        except Exception:
            print("Iniciando autenticacao interativa do Google Earth Engine no Colab...")
            ee.Authenticate()
            try:
                ee.Initialize(**init_kwargs)
                _EE_INITIALIZED = True
                return True
            except Exception as e:
                if not proj:
                    print(
                        "\nDica: O Google Earth Engine no Colab requer um Google Cloud Project associado a sua conta.\n"
                        "Defina a variavel GEE_PROJECT com o ID do seu projeto na celula acima\n"
                        "(ex: GEE_PROJECT = 'ee-seu-usuario' ou 'seu-projeto-gcp') e execute a celula novamente.\n"
                    )
                raise e

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
            ee.Initialize(credentials=credentials, project=proj or GEE_PROJECT_ID)
            _EE_INITIALIZED = True
            return True
        except Exception as e:
            print(f"Aviso: falha na autenticacao com Service Account ({e}). Tentando metodo padrao...")

    # 3. Fluxo Padrao / Interativo Local (gcloud auth ou ee.Authenticate)
    init_kwargs = {"project": proj} if proj else {}
    try:
        ee.Initialize(**init_kwargs)
        _EE_INITIALIZED = True
        return True
    except Exception:
        print("Sessao GEE nao encontrada. Abrindo navegador para autenticacao interativa...")
        ee.Authenticate()
        ee.Initialize(**init_kwargs)
        _EE_INITIALIZED = True
        return True

if __name__ == "__main__":
    print(f"Testando inicializacao GEE com projeto '{GEE_PROJECT_ID}'...")
    init_gee()
    print("Google Earth Engine inicializado com sucesso!")
