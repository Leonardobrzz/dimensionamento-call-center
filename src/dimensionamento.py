"""Transforma a previsão em escala de agentes (Erlang C) e compara dois cenários
avaliando ambos contra o volume e o TMA que REALMENTE aconteceram:

- Plano Erlang C: agentes por intervalo, calculados sobre a previsão.
- Escala fixa: as MESMAS horas-agente do dia, mas distribuídas por igual em todos
  os intervalos (prática comum quando não há WFM).

A pergunta que o projeto responde: "só redistribuindo as mesmas horas, quanto o
nível de serviço melhora?"
"""
import math

import numpy as np
import pandas as pd

from config import (CUSTO_HORA_AGENTE, MARGEM_SEGURANCA, META_NS, MINUTOS_INTERVALO, OCUPACAO_MAXIMA,
                    SHRINKAGE, TEMPO_META_SEG)
from erlang import agentes_necessarios, asa, escalados, nivel_servico, trafego

INTERVALO_SEG = MINUTOS_INTERVALO * 60
HORAS_POR_INTERVALO = MINUTOS_INTERVALO / 60


def _avaliar(linha, col_agentes):
    """NS, ASA e ocupação de uma escala diante do que realmente aconteceu."""
    n = int(linha[col_agentes])
    a = trafego(linha["chamadas"], linha["tma_seg"], INTERVALO_SEG)
    ns = nivel_servico(n, a, linha["tma_seg"], TEMPO_META_SEG)
    espera = asa(n, a, linha["tma_seg"])
    ocup = min(a / n, 1.0) if n > 0 else (1.0 if a > 0 else 0.0)
    return ns, (espera if math.isfinite(espera) else np.nan), ocup


def dimensionar(teste: pd.DataFrame) -> pd.DataFrame:
    df = teste.copy()
    df["trafego_prev_erl"] = df["chamadas_prev"] * df["tma_prev"] / INTERVALO_SEG
    df["agentes_plano"] = [
        agentes_necessarios(c, t, META_NS, TEMPO_META_SEG, OCUPACAO_MAXIMA, INTERVALO_SEG)
        for c, t in zip(df["chamadas_prev"] * (1 + MARGEM_SEGURANCA), df["tma_prev"])]
    df["escalados_plano"] = df["agentes_plano"].apply(lambda n: escalados(n, SHRINKAGE))

    # Escala fixa com as mesmas horas-agente logadas por dia
    media_dia = df.groupby("data")["agentes_plano"].transform("mean")
    df["agentes_fixa"] = np.round(media_dia).astype(int)
    df["escalados_fixa"] = df["agentes_fixa"].apply(lambda n: escalados(n, SHRINKAGE))

    for cenario in ("plano", "fixa"):
        res = df.apply(lambda l: _avaliar(l, f"agentes_{cenario}"), axis=1, result_type="expand")
        df[[f"ns_{cenario}", f"asa_{cenario}", f"ocupacao_{cenario}"]] = res.values
        df[f"bateu_meta_{cenario}"] = df[f"ns_{cenario}"] >= META_NS
    return df


def resumo(df: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for cenario, nome in (("plano", "Plano Erlang C"), ("fixa", "Escala fixa (mesmas horas)")):
        peso = df["chamadas"]
        horas = df[f"agentes_{cenario}"].sum() * HORAS_POR_INTERVALO
        horas_escala = df[f"escalados_{cenario}"].sum() * HORAS_POR_INTERVALO
        estavel = df[f"asa_{cenario}"].notna()  # fora isso, agentes <= tráfego: fila explode
        linhas.append({
            "cenario": nome,
            "ns_ponderado": (df[f"ns_{cenario}"] * peso).sum() / peso.sum(),
            "pct_intervalos_na_meta": df[f"bateu_meta_{cenario}"].mean(),
            "pct_intervalos_em_colapso": 1 - estavel.mean(),
            "asa_medio_seg_estaveis": ((df.loc[estavel, f"asa_{cenario}"] * peso[estavel]).sum()
                                       / peso[estavel].sum()),
            "ocupacao_media": (df[f"ocupacao_{cenario}"] * peso).sum() / peso.sum(),
            "horas_agente_logadas": horas,
            "horas_agente_escaladas": horas_escala,
            "custo_estimado_rs": horas_escala * CUSTO_HORA_AGENTE,
        })
    return pd.DataFrame(linhas)
