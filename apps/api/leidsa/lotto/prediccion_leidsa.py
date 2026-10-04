# predicciones_leidsa.py
import argparse
import random
from collections import Counter, defaultdict
import itertools
import math
import sys
from typing import List, Tuple, Optional

import numpy as np
import pandas as pd


# --------------------------
# CARGA Y PREPROCESAMIENTO
# --------------------------
def cargar_datos(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # Soportar CSV con columnas ['fecha','n1'..'n6'] o ['num1'..'num6']
    posibles = [
        ['num1','num2','num3','num4','num5','num6'],
        ['n1','n2','n3','n4','n5','n6'],
    ]
    num_cols = None
    for cols in posibles:
        if all(c in df.columns for c in cols):
            num_cols = cols
            break
    if num_cols is None:
        raise ValueError("No encuentro columnas de números. Esperaba num1..num6 o n1..n6.")

    df = df.dropna(subset=num_cols)
    df = df[num_cols].astype(int)
    # quita filas con duplicados dentro del mismo sorteo (por si hay basura)
    df = df[df.apply(lambda r: len(set(r.values.tolist())) == 6, axis=1)]
    df["numeros"] = df.values.tolist()
    return df[["numeros"]].reset_index(drop=True)


def universo_desde_hist(historico: List[List[int]]) -> List[int]:
    # Universo deducido del histórico (robusto a cambios)
    return sorted(set(itertools.chain.from_iterable(historico)))


# --------------------------
# PESOS POR RECENCIA
# --------------------------
def pesos_recencia(n: int, half_life_draws: int) -> np.ndarray:
    """
    Devuelve un vector de pesos para n sorteos, con decaimiento exponencial.
    half_life_draws = cuántos sorteos tardan en "valer la mitad".
    """
    if n == 0:
        return np.array([])
    if half_life_draws <= 0:
        # sin decaimiento => todos iguales
        return np.ones(n, dtype=float)
    # age 0 = sorteo más reciente
    ages = np.arange(n-1, -1, -1)  # viejo -> reciente (opcional)
    # Queremos peso mayor para recientes: usemos ages crecientes desde antiguo.
    ages = np.arange(n)            # 0 antiguo, n-1 reciente
    # peso = 0.5 ** (age / half_life)
    w = 0.5 ** ( (n-1 - ages) / half_life_draws )
    return w / w.sum()


def frecuencias_ponderadas(historico: List[List[int]], half_life_draws: int):
    """
    Cuenta números, pares, tríos con pesos por recencia.
    """
    n = len(historico)
    w = pesos_recencia(n, half_life_draws)
    # Si half_life_draws==0, todos iguales
    if n == 0:
        return Counter(), Counter(), Counter()
    freq_num = defaultdict(float)
    freq_pair = defaultdict(float)
    freq_trio = defaultdict(float)
    for i, comb in enumerate(historico):
        wi = w[i]
        for a in comb:
            freq_num[a] += wi
        for p in itertools.combinations(sorted(comb), 2):
            freq_pair[p] += wi
        for t in itertools.combinations(sorted(comb), 3):
            freq_trio[t] += wi
    return Counter(freq_num), Counter(freq_pair), Counter(freq_trio)


# --------------------------
# ESTADÍSTICAS DE SUMA, PARIDAD
# --------------------------
def rango_sumatoria(historico: List[List[int]], p_low=20, p_high=80) -> Tuple[int,int,int]:
    sumas = [sum(f) for f in historico if len(f) == 6]
    if not sumas:
        return 21, 245, 120
    s = np.array(sumas)
    return int(np.percentile(s, p_low)), int(np.percentile(s, p_high)), int(np.mean(s))


def conteo_paridad(comb: List[int]) -> Tuple[int,int]:
    pares = sum(1 for n in comb if n % 2 == 0)
    return pares, len(comb) - pares


def consecutivos_max(comb: List[int]) -> int:
    c = 1
    best = 1
    for a, b in zip(sorted(comb), sorted(comb)[1:]):
        if b == a + 1:
            c += 1
            best = max(best, c)
        else:
            c = 1
    return best


# --------------------------
# MUESTREO PONDERADO
# --------------------------
def weighted_sample_without_replacement(universe: List[int], weights: np.ndarray, k: int, rng: np.random.Generator):
    # seguridad numérica
    w = np.clip(weights, 1e-12, None)
    w = w / w.sum()
    return sorted(rng.choice(universe, size=k, replace=False, p=w).tolist())


def invertir_pesos(weights: np.ndarray) -> np.ndarray:
    # Ponderar "fríos": mayor peso a los con menos prob.
    inv = 1.0 / np.clip(weights, 1e-9, None)
    return inv / inv.sum()


# --------------------------
# REGLAS / CONSTRAINTS
# --------------------------
def cumple_reglas(
    comb: List[int],
    sum_range: Optional[Tuple[int,int]]=None,
    parity: Optional[Tuple[int,int]]=None,
    max_consec: Optional[int]=None,
) -> bool:
    if sum_range is not None:
        s = sum(comb)
        if not (sum_range[0] <= s <= sum_range[1]):
            return False
    if parity is not None:
        p = conteo_paridad(comb)
        if p != parity:
            return False
    if max_consec is not None:
        if consecutivos_max(comb) > max_consec:
            return False
    return True


def generar_con_reglas(
    sampler_fn,
    intentos: int,
    rules_kwargs: dict,
    rng: np.random.Generator,
):
    for _ in range(intentos):
        comb = sampler_fn()
        if cumple_reglas(comb, **rules_kwargs):
            return comb
    # fallback: sin reglas (no bloquearse)
    return sampler_fn()


# --------------------------
# SCORING POR PARES/TRÍOS
# --------------------------
def score_por_bloques(comb: List[int], pair_w: Counter, trio_w: Counter, alpha=1.0, beta=2.0) -> float:
    s = 0.0
    for p in itertools.combinations(sorted(comb), 2):
        s += alpha * pair_w.get(p, 0.0)
    for t in itertools.combinations(sorted(comb), 3):
        s += beta * trio_w.get(t, 0.0)
    return s


def buscar_mejor_de_n(
    n_candidatos: int,
    sampler_fn,
    pair_w: Counter,
    trio_w: Counter,
    rules_kwargs: dict,
    rng: np.random.Generator,
    alpha=1.0,
    beta=2.0,
):
    mejor = None
    mejor_s = -1e9
    for _ in range(n_candidatos):
        c = sampler_fn()
        if not cumple_reglas(c, **rules_kwargs):
            continue
        s = score_por_bloques(c, pair_w, trio_w, alpha, beta)
        if s > mejor_s:
            mejor_s = s
            mejor = c
    return mejor if mejor is not None else sampler_fn()


# --------------------------
# DIVERSIFICACIÓN ENTRE JUGADAS
# --------------------------
def overlap(a: List[int], b: List[int]) -> int:
    return len(set(a) & set(b))


def diversificar(preds: List[List[int]], nueva: List[int], max_overlap: int) -> bool:
    return all(overlap(p, nueva) <= max_overlap for p in preds)


# --------------------------
# ESTRATEGIAS
# --------------------------
def estrategias_prediccion(
    historico: List[List[int]],
    universe: List[int],
    num_weights: np.ndarray,
    pair_w: Counter,
    trio_w: Counter,
    sum_range: Tuple[int,int],
    rng: np.random.Generator,
    recent_window: int,
    rules_kwargs: dict,
):
    preds = []

    W = num_weights
    U = universe
    k = 6

    # 1) Súper calientes (ponderado por recencia)
    def sampler_hot():
        return weighted_sample_without_replacement(U, W, k, rng)
    preds.append(("🔥 Súper calientes", generar_con_reglas(sampler_hot, 5000, rules_kwargs, rng)))

    # 2) Súper fríos (inverso de los pesos)
    Winv = invertir_pesos(W)
    def sampler_cold():
        return weighted_sample_without_replacement(U, Winv, k, rng)
    preds.append(("🧊 Súper fríos", generar_con_reglas(sampler_cold, 5000, rules_kwargs, rng)))

    # 3) Mix hot/cold (4+2)
    def sampler_mix():
        hot = weighted_sample_without_replacement(U, W, 4, rng)
        # recalcular frío sobre universo restante
        rem = [x for x in U if x not in hot]
        if not rem:
            return sorted(hot)
        wrem = np.array([Winv[U.index(x)] for x in rem], dtype=float)
        cold2 = sorted(rng.choice(rem, size=2, replace=False, p=wrem / wrem.sum()).tolist())
        return sorted(hot + cold2)
    preds.append(("🥶 Mezcla fríos/calientes", generar_con_reglas(sampler_mix, 5000, rules_kwargs, rng)))

    # 4) Pares/Tríos famosos (busca la mejor de N)
    def sampler_uniforme():
        return sorted(rng.choice(U, size=k, replace=False).tolist())
    mejor = buscar_mejor_de_n(8000, sampler_uniforme, pair_w, trio_w, rules_kwargs, rng, alpha=1.0, beta=2.5)
    preds.append(("👫 Pares/tríos famosos", mejor))

    # 5) Balance altos/bajos (3 y 3 vs mediana)
    med = int(np.median(U))
    bajos = [x for x in U if x <= med]
    altos = [x for x in U if x > med]
    wb = np.array([W[U.index(x)] for x in bajos], dtype=float)
    wa = np.array([W[U.index(x)] for x in altos], dtype=float)
    def sampler_bal():
        a = sorted(rng.choice(bajos, size=3, replace=False, p=wb / wb.sum()).tolist())
        b = sorted(rng.choice(altos, size=3, replace=False, p=wa / wa.sum()).tolist())
        return sorted(a + b)
    preds.append(("🧬 Balanceada altos/bajos", generar_con_reglas(sampler_bal, 5000, rules_kwargs, rng)))

    # 6) Tendencia reciente (solo últimas R jugadas)
    R = max(1, min(recent_window, len(historico)))
    recientes = historico[-R:]
    freq_r, _, _ = frecuencias_ponderadas(recientes, half_life_draws=max(1, R//2))
    Wr = np.array([freq_r.get(x, 0.0) for x in U], dtype=float)
    if Wr.sum() == 0:
        Wr = np.ones_like(Wr)
    def sampler_recent():
        return weighted_sample_without_replacement(U, Wr, k, rng)
    preds.append(("🧠 Tendencia reciente", generar_con_reglas(sampler_recent, 5000, rules_kwargs, rng)))

    # 7) Top-N random
    N = min(30, len(U))
    top_idx = np.argsort(W)[::-1][:N]
    topN = [U[i] for i in top_idx]
    def sampler_topN():
        return sorted(rng.choice(topN, size=k, replace=False).tolist())
    preds.append(("🎲 Top 30 random", generar_con_reglas(sampler_topN, 5000, rules_kwargs, rng)))

    # 8) Outlier/bizarro (3 fríos + 3 al azar del top)
    cold_idx = np.argsort(W)[:max(3, min(16, len(U)//3))]
    frios = [U[i] for i in cold_idx]
    def sampler_outlier():
        c3 = sorted(rng.choice(frios, size=3, replace=False).tolist())
        t3 = sorted(rng.choice(topN, size=3, replace=False).tolist())
        return sorted(c3 + t3)
    preds.append(("👽 Outlier/bizarro", generar_con_reglas(sampler_outlier, 5000, rules_kwargs, rng)))

    return preds


# --------------------------
# MAIN
# --------------------------
def main():
    ap = argparse.ArgumentParser(description="Generador de combinaciones (estilo análisis) para Loto (6 números).")
    ap.add_argument("--csv", default="loto_leidsa.csv", help="Ruta al histórico CSV (con columnas num1..num6 o n1..n6).")
    ap.add_argument("--preds", type=int, default=8, help="Cantidad de predicciones a generar.")
    ap.add_argument("--seed", type=int, default=None, help="Semilla para reproducibilidad.")
    ap.add_argument("--half_life", type=int, default=16, help="Half-life en número de sorteos (ponderación por recencia).")
    ap.add_argument("--recent_window", type=int, default=12, help="Cuántos sorteos considerar para 'tendencia reciente'.")
    ap.add_argument("--sum_p_low", type=int, default=20, help="Percentil bajo para filtro de suma.")
    ap.add_argument("--sum_p_high", type=int, default=80, help="Percentil alto para filtro de suma.")
    ap.add_argument("--parity", type=str, default=None, help="Paridad exacta 'pares,impares' (ej: '3,3').")
    ap.add_argument("--max_consec", type=int, default=2, help="Máximo de consecutivos permitidos (ej: 2).")
    ap.add_argument("--max_overlap", type=int, default=4, help="Máximo solapamiento permitido entre jugadas (0..6).")
    ap.add_argument("--export", type=str, default=None, help="Ruta para exportar predicciones en CSV.")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)

    df = cargar_datos(args.csv)
    historico = df["numeros"].tolist()
    if len(historico) < 10:
        print("⚠️ Histórico demasiado corto. Carga más datos.")
        sys.exit(1)

    U = universo_desde_hist(historico)

    # Pesos por recencia para NÚMEROS, pares y tríos
    freq_num, pair_w, trio_w = frecuencias_ponderadas(historico, args.half_life)
    W = np.array([freq_num.get(x, 0.0) for x in U], dtype=float)
    if W.sum() == 0:
        W = np.ones_like(W)
    W = W / W.sum()

    # Rango típico de suma
    smin, smax, smed = rango_sumatoria(historico, args.sum_p_low, args.sum_p_high)

    parity_tuple = None
    if args.parity:
        try:
            p, q = args.parity.split(",")
            parity_tuple = (int(p), int(q))
        except Exception:
            print("Paridad inválida. Usa formato 'pares,impares', ej: 3,3")
            sys.exit(1)

    rules_kwargs = dict(
        sum_range=(smin, smax),
        parity=parity_tuple,
        max_consec=args.max_consec,
    )

    # Generar estrategias base (8)
    base_preds = estrategias_prediccion(
        historico, U, W, pair_w, trio_w, (smin, smax), rng, args.recent_window, rules_kwargs
    )

    # Si piden menos, recortamos; si piden más, rellenamos con variantes “mejores por score”
    preds = []
    for desc, comb in base_preds:
        if len(preds) >= args.preds:
            break
        # aplicar diversificación
        if diversificar([c for _, c in preds], comb, args.max_overlap):
            preds.append((desc, comb))

    # Relleno (si faltan)
    while len(preds) < args.preds:
        # tomar mejores por score desde muestreo uniforme
        c = buscar_mejor_de_n(
            4000,
            lambda: sorted(rng.choice(U, size=6, replace=False).tolist()),
            pair_w,
            trio_w,
            rules_kwargs,
            rng,
            alpha=1.0,
            beta=2.0
        )
        if diversificar([x for _, x in preds], c, args.max_overlap):
            preds.append(("⭐ Relleno optimizado", c))

    # SALIDA BONITA
    print("\n🎲 ANALISIS DE LOTTO (estilo data):")
    print(f"- Universo inferido: {min(U)}..{max(U)} (tamaño {len(U)})")
    print(f"- Half-life: {args.half_life} sorteos | Ventana reciente: {args.recent_window}")
    print(f"- Rango de suma típico (p{args.sum_p_low}-{args.sum_p_high}): {smin}-{smax} (media aprox: {smed})")
    if parity_tuple:
        print(f"- Paridad forzada: pares={parity_tuple[0]}, impares={parity_tuple[1]}")
    print(f"- Máximo consecutivos: {args.max_consec} | Diversificación (max overlap): {args.max_overlap}")

    print(f"\n🟩 {len(preds)} Predicciones generadas:")
    for i, (desc, nums) in enumerate(preds, 1):
        pares, impares = conteo_paridad(nums)
        print(f"{i:02d}. {desc:>20} -> {nums} | suma={sum(nums)} | P/I={pares}/{impares} | maxConsec={consecutivos_max(nums)}")

    if args.export:
        out = pd.DataFrame(
            [{"estrategia": d, "n1": c[0], "n2": c[1], "n3": c[2], "n4": c[3], "n5": c[4], "n6": c[5]} for d, c in preds]
        )
        out.to_csv(args.export, index=False, encoding="utf-8")
        print(f"\n💾 Exportado a: {args.export}")

    # Recordatorio ético/pragmático
    print("\n🔎 Nota: esto NO aumenta probabilidades reales; es solo un generador con reglas/ponderaciones.")
    print("   Si quieres evaluar vs. azar puro, te puedo armar un backtest rápido (simulación) 😉")


if __name__ == "__main__":
    main()
