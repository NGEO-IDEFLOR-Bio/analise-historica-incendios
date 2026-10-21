"""
Módulo de acesso e manipulação das Unidades de Conservação do IDEFLOR-Bio.
"""
from typing import Optional, List, Dict, Any
import json
import pandas as pd
from src.config import GEOJSON_UCS, CSV_METADATA_UCS, SIGLAS_GERENCIAS

class UCDatabase:
    """Gerenciador de dados das Unidades de Conservação."""
    
    def __init__(self):
        self._df: Optional[pd.DataFrame] = None
        self._geojson: Optional[Dict[str, Any]] = None

    @property
    def df(self) -> pd.DataFrame:
        """Retorna o DataFrame tabular de metadados das UCs."""
        if self._df is None:
            if not CSV_METADATA_UCS.exists():
                raise FileNotFoundError(f"Arquivo de metadados não encontrado em: {CSV_METADATA_UCS}")
            self._df = pd.read_csv(CSV_METADATA_UCS, encoding="utf-8-sig")
            self._df["sigla_gerencia"] = self._df["gerencia"].map(SIGLAS_GERENCIAS).fillna(self._df["gerencia"])
        return self._df

    @property
    def geojson(self) -> Dict[str, Any]:
        """Retorna a estrutura GeoJSON com os polígonos das UCs."""
        if self._geojson is None:
            if not GEOJSON_UCS.exists():
                raise FileNotFoundError(f"Arquivo GeoJSON não encontrado em: {GEOJSON_UCS}")
            with open(GEOJSON_UCS, "r", encoding="utf-8") as f:
                self._geojson = json.load(f)
        return self._geojson

    def get_uc(self, uc_id: int) -> Optional[Dict[str, Any]]:
        """Busca os metadados de uma UC pelo ID numérico."""
        res = self.df[self.df["id"] == uc_id]
        if res.empty:
            return None
        return res.iloc[0].to_dict()

    def get_by_gerencia(self, gerencia_ou_sigla: str) -> pd.DataFrame:
        """Filtra UCs por nome completo da gerência ou por sigla (ex: 'GRB', 'GRX')."""
        sigla_busca = gerencia_ou_sigla.strip().upper()
        return self.df[
            (self.df["gerencia"].str.upper().str.contains(sigla_busca)) |
            (self.df["sigla_gerencia"].str.upper() == sigla_busca)
        ].copy()

    def get_by_grupo(self, grupo: str) -> pd.DataFrame:
        """Filtra UCs por grupo SNUC ('Proteção Integral' ou 'Uso Sustentável')."""
        return self.df[self.df["grupo"].str.lower() == grupo.strip().lower()].copy()

    def get_geometry_by_id(self, uc_id: int) -> Optional[Dict[str, Any]]:
        """Retorna a geometria (GeoJSON feature) de uma UC específica."""
        for feat in self.geojson.get("features", []):
            if feat.get("properties", {}).get("id") == uc_id:
                return feat
        return None

    def summary_gerencias(self) -> pd.DataFrame:
        """Retorna resumo estatístico agrupado por Gerência Regional."""
        return self.df.groupby(["gerencia", "sigla_gerencia"]).agg(
            total_ucs=("id", "count"),
            area_ha_total=("area_ha", "sum"),
            area_km2_total=("area_km2", "sum"),
            ano_criacao_primeira=("ano_criacao", "min"),
            ano_criacao_ultima=("ano_criacao", "max")
        ).reset_index().sort_values(by="area_ha_total", ascending=False)
