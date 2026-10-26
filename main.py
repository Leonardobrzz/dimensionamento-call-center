"""Roda o projeto inteiro: dados -> forecast -> Erlang C -> cenários -> gráficos -> CSVs.

Uso:
    python main.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd  # noqa: E402

import gerar_dados  # noqa: E402
import graficos  # noqa: E402
from config import PASTA_SAIDA  # noqa: E402
from dimensionamento import dimensionar, resumo  # noqa: E402
from forecast import carregar, prever  # noqa: E402
from simulacao import validar  # noqa: E402

# CSV no padrão brasileiro: abre direto no Excel e no Power BI em pt-BR
CSV_BR = {"sep": ";", "decimal": ",", "index": False, "encoding": "utf-8-sig"}


def main():
    t0 = time.time()
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

    print("1/5 Gerando histórico de chamadas...")
    gerar_dados.main()

    print("2/5 Treinando previsão e avaliando nas últimas semanas...")
    df, feriados = carregar()
    teste, diario, metricas, curva = prever(df, feriados)

    print("3/5 Dimensionando com Erlang C e comparando cenários...")
    plano = dimensionar(teste)
    tabela = resumo(plano)

    print("4/5 Validando Erlang C com simulação de eventos discretos...")
    validacao = validar()

    print("5/5 Gerando gráficos e arquivos para o Power BI...")
    graficos.gerar_todos(plano, diario, metricas)

    colunas = ["data_hora", "data", "hora", "dia_semana", "chamadas", "chamadas_prev",
               "chamadas_baseline", "tma_seg", "tma_prev", "trafego_prev_erl",
               "agentes_plano", "escalados_plano", "ns_plano", "asa_plano", "ocupacao_plano",
               "bateu_meta_plano", "agentes_fixa", "escalados_fixa", "ns_fixa", "asa_fixa",
               "ocupacao_fixa", "bateu_meta_fixa"]
    plano[colunas].round({c: 4 for c in colunas if plano[c].dtype.kind == "f"}).to_csv(PASTA_SAIDA / "fato_intervalos.csv", **CSV_BR)
    diario.round({"chamadas_prev": 1, "ajuste_modelo": 1}).to_csv(PASTA_SAIDA / "fato_diario.csv", **CSV_BR)
    metricas.round(4).to_csv(PASTA_SAIDA / "metricas_forecast.csv", **CSV_BR)
    tabela.round(4).to_csv(PASTA_SAIDA / "resumo_cenarios.csv", **CSV_BR)
    validacao.to_csv(PASTA_SAIDA / "validacao_simulacao.csv", **CSV_BR)
    curva.round(5).to_csv(PASTA_SAIDA / "curva_intradiaria.csv", **CSV_BR)

    # ---------------- Resumo no terminal ----------------
    pd.set_option("display.width", 140)
    print("\n=== Previsão (últimas 8 semanas) ===")
    m = metricas.copy()
    for c in ("wape_diario", "bias_diario", "wape_intervalo"):
        m[c] = m[c].map("{:.1%}".format)
    print(m.to_string(index=False))

    print("\n=== Cenários avaliados contra o que realmente aconteceu ===")
    r = tabela.copy()
    for c in ("ns_ponderado", "pct_intervalos_na_meta", "pct_intervalos_em_colapso", "ocupacao_media"):
        r[c] = r[c].map("{:.1%}".format)
    r["asa_medio_seg_estaveis"] = r["asa_medio_seg_estaveis"].map("{:.1f}".format)
    for c in ("horas_agente_logadas", "horas_agente_escaladas"):
        r[c] = r[c].map("{:,.0f}".format)
    r["custo_estimado_rs"] = r["custo_estimado_rs"].map("R$ {:,.0f}".format)
    print(r.T.to_string(header=False))

    print("\n=== Erlang C x simulação (deve bater) ===")
    print(validacao.to_string(index=False))
    print(f"\nPronto em {time.time() - t0:.0f}s. Veja a pasta outputs/")


if __name__ == "__main__":
    main()
