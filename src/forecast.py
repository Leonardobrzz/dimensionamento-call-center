"""Previsão de volume por intervalo de 30 min, no padrão de mercado de WFM:

1. Prevê o VOLUME DIÁRIO com Holt-Winters (tendência amortecida + sazonalidade semanal).
   Feriados são "limpos" do treino e depois recebem um fator próprio.
2. Distribui o volume do dia pelos intervalos com a CURVA INTRADIÁRIA
   (participação média de cada intervalo por dia da semana, últimas N semanas).
3. Compara com um BASELINE ingênuo: "mesmo intervalo da semana passada".
"""
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from config import PASTA_DADOS, SEMANAS_CURVA_INTRADIA, SEMANAS_TESTE


def carregar() -> tuple[pd.DataFrame, set]:
    df = pd.read_csv(PASTA_DADOS / "historico_chamadas.csv", parse_dates=["data_hora"])
    df["data"] = df["data_hora"].dt.normalize()
    df["hora"] = df["data_hora"].dt.strftime("%H:%M")
    df["dia_semana"] = df["data_hora"].dt.dayofweek
    feriados = set(pd.to_datetime(pd.read_csv(PASTA_DADOS / "feriados.csv")["data"]))
    return df, feriados


def wape(real, previsto) -> float:
    """Weighted Absolute Percentage Error: erro total / volume total."""
    real, previsto = np.asarray(real, float), np.asarray(previsto, float)
    return np.abs(real - previsto).sum() / real.sum()


def bias(real, previsto) -> float:
    real, previsto = np.asarray(real, float), np.asarray(previsto, float)
    return (previsto - real).sum() / real.sum()


def prever(df: pd.DataFrame, feriados: set):
    diario = df.groupby("data")["chamadas"].sum().asfreq("D")
    corte = diario.index[-1] - pd.Timedelta(weeks=SEMANAS_TESTE)
    treino, teste = diario[diario.index <= corte], diario[diario.index > corte]

    # --- 1. Volume diário -------------------------------------------------
    eh_feriado = treino.index.isin(feriados)
    treino_limpo = treino.copy().astype(float)
    treino_limpo[eh_feriado] = np.nan
    # preenche feriado com o mesmo dia da semana anterior/seguinte
    vizinhos = pd.concat([treino_limpo.shift(7), treino_limpo.shift(-7)], axis=1).mean(axis=1)
    treino_limpo = treino_limpo.fillna(vizinhos).bfill().ffill()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        modelo = ExponentialSmoothing(treino_limpo, trend="add", damped_trend=True,
                                      seasonal="mul", seasonal_periods=7).fit()
    prev_diaria = modelo.forecast(len(teste))
    prev_diaria.index = teste.index

    # fator de feriado aprendido no treino: real / ajustado do modelo
    ajustado = modelo.fittedvalues
    fator_feriado = (treino[eh_feriado] / ajustado[eh_feriado]).median()
    prev_diaria[prev_diaria.index.isin(feriados)] *= fator_feriado

    # --- 2. Curva intradiária ---------------------------------------------
    inicio_janela = corte - pd.Timedelta(weeks=SEMANAS_CURVA_INTRADIA)
    janela = df[(df["data"] > inicio_janela) & (df["data"] <= corte)
                & ~df["data"].isin(feriados)].copy()
    janela["participacao"] = janela["chamadas"] / janela.groupby("data")["chamadas"].transform("sum")
    curva = janela.groupby(["dia_semana", "hora"])["participacao"].mean()
    curva = curva / curva.groupby(level=0).transform("sum")  # cada dia soma 100%
    tma_curva = janela.groupby(["dia_semana", "hora"])["tma_seg"].mean()

    teste_int = df[df["data"] > corte].copy()
    chave = pd.MultiIndex.from_arrays([teste_int["dia_semana"], teste_int["hora"]])
    teste_int["chamadas_prev"] = (teste_int["data"].map(prev_diaria).values
                                  * curva.reindex(chave).values)
    teste_int["tma_prev"] = tma_curva.reindex(chave).values

    # --- 3. Baseline: mesmo intervalo, semana passada ----------------------
    semana_passada = df.set_index("data_hora")["chamadas"]
    teste_int["chamadas_baseline"] = semana_passada.reindex(
        teste_int["data_hora"] - pd.Timedelta(weeks=1)).values

    # --- Métricas ----------------------------------------------------------
    baseline_diario = teste_int.groupby("data")["chamadas_baseline"].sum()
    metricas = pd.DataFrame([
        {"modelo": "Holt-Winters + curva intradiária",
         "wape_diario": wape(teste, prev_diaria), "bias_diario": bias(teste, prev_diaria),
         "wape_intervalo": wape(teste_int["chamadas"], teste_int["chamadas_prev"])},
        {"modelo": "Baseline (semana passada)",
         "wape_diario": wape(teste, baseline_diario), "bias_diario": bias(teste, baseline_diario),
         "wape_intervalo": wape(teste_int["chamadas"], teste_int["chamadas_baseline"])},
    ])

    diario_out = pd.DataFrame({
        "data": diario.index, "chamadas_real": diario.values,
        "chamadas_prev": prev_diaria.reindex(diario.index).values,
        "ajuste_modelo": ajustado.reindex(diario.index).values,
        "periodo": np.where(diario.index > corte, "teste", "treino"),
        "feriado": diario.index.isin(feriados),
    })
    return teste_int, diario_out, metricas, curva.reset_index()
