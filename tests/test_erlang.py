"""Testes do Erlang C. Rode com:  python -m pytest  (ou: python tests/test_erlang.py)"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from erlang import agentes_necessarios, erlang_c, escalados, nivel_servico, trafego  # noqa: E402


def test_valor_classico_de_livro():
    # 10 Erlangs com 12 agentes: P(espera) = 0,4494 (valor tabelado)
    assert math.isclose(erlang_c(12, 10), 0.4494, abs_tol=1e-4)


def test_trafego():
    # 120 chamadas de 300 s em 30 min = 20 Erlangs
    assert trafego(120, 300, 1800) == 20


def test_fila_instavel():
    assert erlang_c(10, 10) == 1.0
    assert nivel_servico(9, 10, 300, 20) == 0.0


def test_mais_agentes_melhora_ns():
    a, tma = trafego(150, 300), 300
    ns = [nivel_servico(n, a, tma, 20) for n in range(26, 40)]
    assert all(x < y for x, y in zip(ns, ns[1:]))


def test_agentes_necessarios_e_o_minimo():
    n = agentes_necessarios(150, 300, 0.80, 20)
    a = trafego(150, 300)
    assert nivel_servico(n, a, 300, 20) >= 0.80
    assert nivel_servico(n - 1, a, 300, 20) < 0.80


def test_ocupacao_maxima_e_respeitada():
    n = agentes_necessarios(600, 300, 0.80, 20, ocupacao_max=0.85)
    assert trafego(600, 300) / n <= 0.85


def test_shrinkage():
    assert escalados(21, 0.30) == 30
    assert escalados(0, 0.30) == 0


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_"):
            f()
            print(f"ok  {nome}")
