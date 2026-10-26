"""Gráficos em PNG (prontos para o post e para o README)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

from config import META_NS, PASTA_GRAFICOS, TEMPO_META_SEG
from erlang import nivel_servico, trafego

# Paleta: papéis fixos, nunca cicla
SUPERFICIE = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
GRADE = "#e6e5e0"
AZUL = "#2a78d6"      # modelo / plano Erlang C
LARANJA = "#eb6834"   # escala fixa
CINZA = "#9a998f"     # realizado

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE,
    "axes.edgecolor": GRADE, "axes.labelcolor": TEXTO_2, "text.color": TEXTO,
    "xtick.color": TEXTO_2, "ytick.color": TEXTO_2, "axes.grid": True,
    "grid.color": GRADE, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 11, "axes.titlesize": 14,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
})


def _salvar(fig, nome):
    PASTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(PASTA_GRAFICOS / nome, dpi=160)
    plt.close(fig)


def forecast_diario(diario: pd.DataFrame, metricas: pd.DataFrame):
    inicio = diario.loc[diario["periodo"] == "teste", "data"].min() - pd.Timedelta(weeks=6)
    d = diario[diario["data"] >= inicio]
    teste = d[d["periodo"] == "teste"]
    wape = metricas.iloc[0]["wape_diario"]
    wape_base = metricas.iloc[1]["wape_diario"]

    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(d["data"], d["chamadas_real"], color=CINZA, lw=2, label="Realizado")
    ax.plot(teste["data"], teste["chamadas_prev"], color=AZUL, lw=2, label="Previsto")
    ax.axvline(teste["data"].min(), color=TEXTO_2, lw=1, ls="--")
    ax.text(teste["data"].min(), ax.get_ylim()[1], "  início do teste", va="top",
            color=TEXTO_2, fontsize=10)
    pct = lambda v: f"{v:.1%}".replace(".", ",")
    ax.set_title(f"Previsão de volume diário: erro de {pct(wape)} (baseline: {pct(wape_base)})")
    ax.set_ylabel("Chamadas por dia")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
    ax.legend(loc="upper left", ncol=2)
    _salvar(fig, "1_forecast_diario.png")


def dia_exemplo(df: pd.DataFrame):
    # pega a segunda-feira (dia de pico) de maior volume no teste
    segundas = df[df["dia_semana"] == 0].groupby("data")["chamadas"].sum()
    dia = segundas.idxmax()
    d = df[df["data"] == dia]
    x = np.arange(len(d))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True,
                                   gridspec_kw={"height_ratios": [1, 1]})
    ax1.bar(x, d["chamadas"], color=CINZA, width=0.8, label="Realizado")
    ax1.plot(x, d["chamadas_prev"], color=AZUL, lw=2, marker="o", ms=4, label="Previsto")
    ax1.set_title(f"Um dia de pico ({dia:%d/%m/%Y}): volume e escala por intervalo de 30 min")
    ax1.set_ylabel("Chamadas")
    ax1.legend(loc="upper right", ncol=2)

    ax2.step(x, d["agentes_plano"], where="mid", color=AZUL, lw=2, label="Plano Erlang C")
    ax2.step(x, d["agentes_fixa"], where="mid", color=LARANJA, lw=2, label="Escala fixa (mesmas horas)")
    ax2.set_ylabel("Agentes logados")
    ax2.set_xticks(x[::2])
    ax2.set_xticklabels(d["hora"].iloc[::2], rotation=0)
    ax2.legend(loc="upper right", ncol=2)
    _salvar(fig, "2_dia_de_pico.png")


def ns_por_hora(df: pd.DataFrame):
    g = df.groupby("hora").apply(
        lambda t: pd.Series({
            "plano": (t["ns_plano"] * t["chamadas"]).sum() / t["chamadas"].sum(),
            "fixa": (t["ns_fixa"] * t["chamadas"]).sum() / t["chamadas"].sum()}),
        include_groups=False)
    x = np.arange(len(g))
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(x, g["plano"], color=AZUL, lw=2, marker="o", ms=5, label="Plano Erlang C")
    ax.plot(x, g["fixa"], color=LARANJA, lw=2, marker="o", ms=5, label="Escala fixa (mesmas horas)")
    ax.axhline(META_NS, color=TEXTO_2, lw=1, ls="--")
    ax.text(len(g) - 0.5, META_NS, f"meta {META_NS:.0%}/{TEMPO_META_SEG}s ", ha="right",
            va="bottom", color=TEXTO_2, fontsize=10)
    ax.set_xticks(x[::2])
    ax.set_xticklabels(g.index[::2])
    ax.set_ylim(0, 1.02)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_title("Nível de serviço realizado por horário (8 semanas de teste)")
    ax.set_ylabel("Nível de serviço")
    ax.legend(loc="center", bbox_to_anchor=(0.36, 0.6), ncol=2)
    _salvar(fig, "3_ns_por_horario.png")


def curva_erlang(chamadas=220, tma=300):
    a = trafego(chamadas, tma)
    ns_ag = np.arange(int(a) + 1, int(a) + 16)
    ns = [nivel_servico(n, a, tma, TEMPO_META_SEG) for n in ns_ag]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(ns_ag, ns, color=AZUL, lw=2, marker="o", ms=6)
    ax.axhline(META_NS, color=TEXTO_2, lw=1, ls="--")
    primeiro = next(n for n, v in zip(ns_ag, ns) if v >= META_NS)
    ax.annotate(f"{primeiro} agentes batem a meta",
                xy=(primeiro, nivel_servico(primeiro, a, tma, TEMPO_META_SEG)),
                xytext=(primeiro + 2, 0.45), color=TEXTO,
                arrowprops={"arrowstyle": "->", "color": TEXTO_2})
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_ylim(0, 1.02)
    ax.set_title(f"Erlang C: {chamadas} chamadas em 30 min, TMA {tma}s "
                 f"({a:.1f} Erlangs). Cada agente a mais rende menos")
    ax.set_xlabel("Agentes logados")
    ax.set_ylabel(f"Atendidas em até {TEMPO_META_SEG}s")
    _salvar(fig, "4_curva_erlang_c.png")


def gerar_todos(df, diario, metricas):
    forecast_diario(diario, metricas)
    dia_exemplo(df)
    ns_por_hora(df)
    curva_erlang()
