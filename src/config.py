"""
Configuracoes globais, caminhos e constantes do projeto.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Raiz do projeto
ROOT_DIR = Path(__file__).resolve().parent.parent

# Carregar variaveis de ambiente do .env
ENV_FILE = ROOT_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

# Diretorios de Dados
DATA_DIR = ROOT_DIR / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_PROCESSED = DATA_DIR / "processed"
DATA_CARTOGRAFIA = DATA_PROCESSED / "cartografia"
DATA_OUTPUT = DATA_DIR / "output"

# Diretorios de Codigo e Documentacao
SRC_DIR = ROOT_DIR / "src"
DOCS_DIR = ROOT_DIR / "docs"
NOTEBOOKS_DIR = ROOT_DIR / "notebooks"

# Garantir existencia de pastas
DATA_RAW.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
DATA_CARTOGRAFIA.mkdir(parents=True, exist_ok=True)
DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)

# Arquivos de Referencia de UCs
GEOJSON_UCS = DATA_RAW / "shapes_de_todas_as_unidades_com_gerencia.geojson"
CSV_METADATA_UCS = DATA_PROCESSED / "ucs_ideflor_bio.csv"
JSON_METADATA_UCS = DATA_PROCESSED / "ucs_ideflor_bio.json"

# Camadas Cartograficas de Contexto
GEOJSON_AMERICA_DO_SUL = DATA_RAW / "america-do-sul.geojson"
GEOJSON_BRASIL_UFS = DATA_RAW / "brasil-ufs.geojson"
GEOJSON_PARA = DATA_RAW / "pará.geojson"
GEOJSON_AMERICA_DO_SUL_SIMP = DATA_CARTOGRAFIA / "america_do_sul_simplificado.geojson"
GEOJSON_BRASIL_UFS_SIMP = DATA_CARTOGRAFIA / "brasil_ufs_simplificado.geojson"

# Credenciais GEE
GEE_PROJECT_ID = os.getenv("GEE_PROJECT_ID", "sentinel-landsat-download")
GEE_CREDENTIALS_JSON_REL = os.getenv("GEE_CREDENTIALS_JSON", "secrets/sentinel-landsat-download-c9ec6de8d78c.json")
GEE_CREDENTIALS_JSON = ROOT_DIR / GEE_CREDENTIALS_JSON_REL

# Assets GEE MapBiomas Fogo Colecao 3 (Brasil 1985 a 2023)
ASSET_MAPBIOMAS_FOGO_ANUAL = "projects/mapbiomas-public/assets/brazil/fire/collection3/mapbiomas_fire_collection3_annual_burned_coverage_v1"
ASSET_MAPBIOMAS_FOGO_MENSAL = "projects/mapbiomas-public/assets/brazil/fire/collection3/mapbiomas_fire_collection3_monthly_burned_coverage_v1"

# CRS de referencia
CRS_ORIGINAL = "EPSG:4674"  # SIRGAS 2000
CRS_WEB = "EPSG:4326"       # WGS 84
CRS_ALBERS_BRASIL = "EPSG:5880"  # Projecao de area equivalente

# Siglas simplificadas para graficos
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
