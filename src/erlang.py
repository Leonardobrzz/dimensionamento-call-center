"""Erlang C: o modelo clássico de filas (M/M/c) usado em Workforce Management.

Notação:
    chamadas  -> chamadas no intervalo
    tma       -> tempo médio de atendimento (s)
    intervalo -> duração do intervalo (s), ex.: 1800 para 30 min
    A         -> tráfego em Erlangs = chamadas * tma / intervalo
    n         -> número de agentes atendendo

Fórmulas:
    Erlang B (recursiva, numericamente estável):
        B(0) = 1
        B(k) = A*B(k-1) / (k + A*B(k-1))
    Erlang C (prob. de a chamada esperar), válida para n > A:
        C = n*B(n) / (n - A*(1 - B(n)))
    Nível de serviço (atendidas em até T segundos):
        NS = 1 - C * exp(-(n - A) * T / tma)
    Tempo médio de espera (ASA):
        ASA = C * tma / (n - A)
    Ocupação:
        rho = A / n
"""
import math


def trafego(chamadas: float, tma: float, intervalo: float = 1800) -> float:
    return chamadas * tma / intervalo


def erlang_b(n: int, a: float) -> float:
    b = 1.0
    for k in range(1, n + 1):
        b = a * b / (k + a * b)
    return b


def erlang_c(n: int, a: float) -> float:
    """Probabilidade de uma chamada ter que esperar na fila."""
    if a <= 0:
        return 0.0
    if n <= a:
        return 1.0  # fila instável: cresce sem parar
    b = erlang_b(n, a)
    return n * b / (n - a * (1 - b))


def nivel_servico(n: int, a: float, tma: float, tempo_meta: float) -> float:
    if a <= 0:
        return 1.0
    if n <= a:
        return 0.0
    return 1 - erlang_c(n, a) * math.exp(-(n - a) * tempo_meta / tma)


def asa(n: int, a: float, tma: float) -> float:
    """Average Speed of Answer: espera média (s)."""
    if a <= 0:
        return 0.0
    if n <= a:
        return math.inf
    return erlang_c(n, a) * tma / (n - a)


def agentes_necessarios(chamadas: float, tma: float, meta_ns: float, tempo_meta: float,
                        ocupacao_max: float = 1.0, intervalo: float = 1800) -> int:
    """Menor número de agentes que bate a meta de NS sem passar da ocupação máxima."""
    a = trafego(chamadas, tma, intervalo)
    if a <= 0:
        return 0
    n = max(1, math.ceil(a / ocupacao_max))
    while nivel_servico(n, a, tma, tempo_meta) < meta_ns:
        n += 1
    return n


def escalados(agentes: int, shrinkage: float) -> int:
    """Quantos precisam estar na escala para sobrar `agentes` logados de fato."""
    # round() evita erro de ponto flutuante: 21 / 0.7 = 30.000000000000004
    return math.ceil(round(agentes / (1 - shrinkage), 9)) if agentes > 0 else 0
