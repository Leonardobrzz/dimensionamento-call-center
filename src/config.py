"""Parâmetros do projeto. Mude aqui e rode `python main.py` de novo."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "data"
PASTA_SAIDA = RAIZ / "outputs"
PASTA_GRAFICOS = PASTA_SAIDA / "graficos"

# ---------------- Dados sintéticos ----------------
SEMENTE = 42
DATA_INICIO = "2025-01-01"
DATA_FIM = "2026-09-30"
HORA_ABERTURA = 7       # operação 07:00
HORA_FECHAMENTO = 22    # até 22:00 (último intervalo 21:30)
MINUTOS_INTERVALO = 30
VOLUME_DIARIO_BASE = 2600   # chamadas num dia útil "normal" no início da série
CRESCIMENTO_ANUAL = 0.08    # +8% ao ano
TMA_BASE_SEG = 300          # tempo médio de atendimento (segundos)

# ---------------- Forecast ----------------
SEMANAS_TESTE = 8           # últimas 8 semanas ficam de fora para avaliar o modelo
SEMANAS_CURVA_INTRADIA = 8  # janela usada para a curva intradiária

# ---------------- Erlang C / WFM ----------------
META_NS = 0.80              # nível de serviço: 80% ...
TEMPO_META_SEG = 20         # ... atendidas em até 20 segundos
OCUPACAO_MAXIMA = 0.85      # evita burnout: no máx. 85% de ocupação
MARGEM_SEGURANCA = 0.00     # ex.: 0.05 = dimensiona para previsão +5% (cobre erro de forecast)
SHRINKAGE = 0.30            # pausas, treinamento, absenteísmo
CUSTO_HORA_AGENTE = 28.0    # R$ por hora de agente escalado (ajuste à sua realidade)
