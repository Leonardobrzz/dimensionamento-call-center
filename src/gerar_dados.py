"""Gera um histórico sintético (mas realista) de chamadas de uma central de atendimento.

Cada linha = um intervalo de 30 minutos com:
- chamadas recebidas (processo de Poisson com taxa variável)
- TMA (tempo médio de atendimento, em segundos)

Padrões embutidos, iguais aos de uma operação real:
- sazonalidade semanal (segunda é o pico, domingo é o vale)
- sazonalidade intradiária com dois picos (manhã e começo da tarde)
- efeito início de mês (vencimento de boletos / faturas)
- feriados nacionais com volume bem menor
- tendência de crescimento da base de clientes
"""
import numpy as np
import pandas as pd

from config import (CRESCIMENTO_ANUAL, DATA_FIM, DATA_INICIO, HORA_ABERTURA,
                    HORA_FECHAMENTO, MINUTOS_INTERVALO, PASTA_DADOS, SEMENTE,
                    TMA_BASE_SEG, VOLUME_DIARIO_BASE)

# Feriados nacionais (fixos + móveis) no período
FERIADOS = pd.to_datetime([
    "2025-01-01", "2025-03-03", "2025-03-04", "2025-04-18", "2025-04-21",
    "2025-05-01", "2025-06-19", "2025-09-07", "2025-10-12", "2025-11-02",
    "2025-11-15", "2025-11-20", "2025-12-25",
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03", "2026-04-21",
    "2026-05-01", "2026-06-04", "2026-09-07",
])

FATOR_DIA_SEMANA = {0: 1.18, 1: 1.05, 2: 1.00, 3: 0.97, 4: 0.92, 5: 0.55, 6: 0.30}


def curva_intradiaria(horas: np.ndarray, dia_semana: int) -> np.ndarray:
    """Formato do dia: pico ~10h, pico menor ~15h, cauda à noite."""
    pico_manha = np.exp(-((horas - 10.0) ** 2) / (2 * 1.6 ** 2))
    pico_tarde = 0.80 * np.exp(-((horas - 15.0) ** 2) / (2 * 1.9 ** 2))
    noite = 0.25 * np.exp(-((horas - 19.5) ** 2) / (2 * 1.5 ** 2))
    curva = 0.08 + pico_manha + pico_tarde + noite
    if dia_semana >= 5:  # fim de semana: dia mais "achatado" e mais tarde
        curva = 0.15 + np.exp(-((horas - 11.5) ** 2) / (2 * 2.5 ** 2))
    return curva / curva.sum()


def gerar() -> pd.DataFrame:
    rng = np.random.default_rng(SEMENTE)
    dias = pd.date_range(DATA_INICIO, DATA_FIM, freq="D")
    n_intervalos = int((HORA_FECHAMENTO - HORA_ABERTURA) * 60 / MINUTOS_INTERVALO)
    horas = HORA_ABERTURA + (np.arange(n_intervalos) + 0.5) * MINUTOS_INTERVALO / 60

    linhas = []
    for dia in dias:
        anos = (dia - dias[0]).days / 365.25
        tendencia = (1 + CRESCIMENTO_ANUAL) ** anos
        fator_semana = FATOR_DIA_SEMANA[dia.dayofweek]
        fator_mes = 1.0 + 0.18 * np.exp(-(dia.day - 6) ** 2 / 8)  # pico perto do dia 5-7
        fator_sazonal = 1.0 + 0.06 * np.cos(2 * np.pi * (dia.dayofyear - 20) / 365.25)
        fator_feriado = 0.28 if dia in FERIADOS else 1.0
        ruido_dia = rng.lognormal(0, 0.06)  # dias "atípicos" sem motivo aparente

        volume_esperado = (VOLUME_DIARIO_BASE * tendencia * fator_semana * fator_mes
                           * fator_sazonal * fator_feriado * ruido_dia)
        taxas = volume_esperado * curva_intradiaria(horas, dia.dayofweek)
        chamadas = rng.poisson(taxas)

        # TMA: maior de manhã (casos complexos), menor à noite, com ruído
        tma = (TMA_BASE_SEG * (1.08 - 0.012 * (horas - HORA_ABERTURA))
               * rng.normal(1, 0.05, n_intervalos))

        for i in range(n_intervalos):
            inicio = dia + pd.Timedelta(minutes=HORA_ABERTURA * 60 + i * MINUTOS_INTERVALO)
            linhas.append((inicio, int(chamadas[i]), round(float(tma[i]), 1)))

    df = pd.DataFrame(linhas, columns=["data_hora", "chamadas", "tma_seg"])
    return df


def main() -> pd.DataFrame:
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    df = gerar()
    caminho = PASTA_DADOS / "historico_chamadas.csv"
    df.to_csv(caminho, index=False)
    feriados = pd.DataFrame({"data": FERIADOS.date})
    feriados.to_csv(PASTA_DADOS / "feriados.csv", index=False)
    print(f"[dados] {len(df):,} intervalos | {df['chamadas'].sum():,} chamadas -> {caminho.name}")
    return df


if __name__ == "__main__":
    main()
