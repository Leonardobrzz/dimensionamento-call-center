"""Simulação de eventos discretos de uma fila M/M/c (FCFS) para VALIDAR o Erlang C.

Se a fórmula estiver certa, o nível de serviço simulado tem que bater com o teórico.
É a mesma ideia de validar um modelo analítico com simulação em análise de desempenho.
"""
import heapq

import numpy as np
import pandas as pd

from erlang import asa, nivel_servico, trafego


def simular(chamadas_por_intervalo: float, tma: float, agentes: int, tempo_meta: float,
            n_chamadas: int = 200_000, intervalo: float = 1800, semente: int = 7):
    rng = np.random.default_rng(semente)
    taxa = chamadas_por_intervalo / intervalo          # chegadas por segundo
    chegadas = np.cumsum(rng.exponential(1 / taxa, n_chamadas))
    servicos = rng.exponential(tma, n_chamadas)

    livres = [0.0] * agentes                           # instante em que cada agente fica livre
    heapq.heapify(livres)
    esperas = np.empty(n_chamadas)
    for i in range(n_chamadas):
        prox_livre = heapq.heappop(livres)
        inicio = max(chegadas[i], prox_livre)
        esperas[i] = inicio - chegadas[i]
        heapq.heappush(livres, inicio + servicos[i])

    esperas = esperas[n_chamadas // 10:]               # descarta o aquecimento (warm-up)
    return (esperas <= tempo_meta).mean(), esperas.mean()


def validar(tempo_meta: float = 20) -> pd.DataFrame:
    casos = [(150, 300, 27), (150, 300, 28), (150, 300, 30),
             (300, 280, 50), (300, 280, 53), (60, 320, 13)]
    linhas = []
    for chamadas, tma, n in casos:
        a = trafego(chamadas, tma)
        ns_sim, asa_sim = simular(chamadas, tma, n, tempo_meta)
        linhas.append({
            "chamadas_30min": chamadas, "tma_seg": tma, "agentes": n,
            "trafego_erlangs": round(a, 2),
            "ns_erlang_c": round(nivel_servico(n, a, tma, tempo_meta), 4),
            "ns_simulado": round(ns_sim, 4),
            "asa_erlang_c": round(asa(n, a, tma), 2),
            "asa_simulado": round(asa_sim, 2),
        })
    return pd.DataFrame(linhas)


if __name__ == "__main__":
    print(validar().to_string(index=False))
