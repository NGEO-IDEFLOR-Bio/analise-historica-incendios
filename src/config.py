"""
Configurações globais, caminhos e constantes do projeto.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Raiz do projeto
ROOT_DIR = Path(__file__).resolve().parent.parent

# Carregar variáveis de ambiente do .env
ENV_FILE = ROOT_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

# Diretórios de Dados
DATA_DIR = ROOT_DIR / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_PROCESSED = DATA_DIR / "processed"
DATA_OUTPUT = DATA_DIR / "output"

# Diretórios de Código e Documentação
SRC_DIR = ROOT_DIR / "src"
DOCS_DIR = ROOT_DIR / "docs"
NOTEBOOKS_DIR = ROOT_DIR / "notebooks"

# Garantir existência de pastas
DATA_RAW.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)

# Arquivos de Referência
GEOJSON_UCS = DATA_RAW / "shapes_de_todas_as_unidades_com_gerencia.geojson"
CSV_METADATA_UCS = DATA_PROCESSED / "ucs_ideflor_bio.csv"
JSON_METADATA_UCS = DATA_PROCESSED / "ucs_ideflor_bio.json"

# Credenciais GEE
GEE_PROJECT_ID = os.getenv("GEE_PROJECT_ID", "sentinel-landsat-download")
GEE_CREDENTIALS_JSON_REL = os.getenv("GEE_CREDENTIALS_JSON", "secrets/sentinel-landsat-download-c9ec6de8d78c.json")
GEE_CREDENTIALS_JSON = ROOT_DIR / GEE_CREDENTIALS_JSON_REL

# Assets GEE MapBiomas Fogo Coleção 3 (Brasil 1985-2023)
ASSET_MAPBIOMAS_FOGO_ANUAL = "projects/mapbiomas-public/assets/brazil/fire/collection3/mapbiomas_fire_collection3_annual_burned_coverage_v1"
ASSET_MAPBIOMAS_FOGO_MENSAL = "projects/mapbiomas-public/assets/brazil/fire/collection3/mapbiomas_fire_collection3_monthly_burned_coverage_v1"

# CRS de referência
CRS_ORIGINAL = "EPSG:4674"  # SIRGAS 2000
CRS_WEB = "EPSG:4326"       # WGS 84
CRS_ALBERS_BRASIL = "EPSG:5880"  # Projeção de área equivalente

# Siglas simplificadas para gráficos
SIGLAS_GERENCIAS = {
    "GERÊNCIA REGIONAL DE BELÉM (GRB)": "GRB",
    "GERÊNCIA REGIONAL DO NORDESTE (GRNE)": "GRNE",
    "GERÊNCIA REGIONAL DO MARAJÓ (GRM)": "GRM",
    "GERÊNCIA REGIONAL DE TUCURUÍ (GRTUC)": "GRTUC",
    "GERÊNCIA REGIONAL DO ARAGUAIA (GRA)": "GRA",
    "GERÊNCIA REGIONAL DO XINGU (GRX)": "GRX",
    "GERÊNCIA REGIONAL DA CALHA NORTE I (GRCN-I)": "GRCN-I",
    "GERÊNCIA REGIONAL DA CALHA NORTE II (GRCN-II)": "GRCN-II",
    "GERÊNCIA REGIONAL DA CALHA NORTE III (GRCN-III)": "GRCN-III",
}
