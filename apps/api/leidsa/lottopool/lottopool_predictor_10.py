# lottopool_predictor_20.py
# 20 jugadas "con cabeza" para Loto Pool (5 de 31)
# ⚠️ No sube odds reales. Solo heurísticas + reglas + diversidad.

import argparse, itertools, sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Tuple, Optional, Dict

import numpy as np
import pandas as pd

# ----------------------------
# Carga robusta del histórico
# ----------------------------
def cargar_historico(csv_path: str) -> List[List[int]]:
    p = Path(csv_path)
    if not p.exists():
        return []
    try:
        df = pd.read_csv(p)
    except Exception:
        # tolerante a líneas chuecas
        df = pd.read_csv(p, engine="python", on_bad_lines="skip")

    # columnas típicas
    candidates = [
        ["num1","num2","num3","num4","num5"],
        ["num_1","num_2","num_3","num_4","num_5"],
        ["n1","n2","n3","n4","n5"],
    ]
    cols = None
    for cset in candidates:
        if all(c in df.columns for c in cset):
            cols = cset; break
    if cols is None:
        # fallback: primeras 5 columnas numéricas
        numcols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(numcols) < 5:
            return []
        cols = numcols[:5]

    # [ACTUALIZACIÓN] Reemplazo de iterrows() por operaciones vectorizadas (más rápido)
    df_num = df[cols].apply(pd.to_numeric, errors='coerce').dropna()
    vals_raw = df_num.astype(int).values.tolist()
    
    vals = []
    # Validación rápida en Python
    for comb in vals_raw:
        try:
            if len(comb) == 5 and len(set(comb)) == 5 and all(1 <= x <= 31 for x in comb):
                vals.append(comb)
        except Exception:
            continue
    return vals

# ----------------------------
# Ponderaciones y stats
# ----------------------------
def pesos_recencia(n: int, half_life: int) -> np.ndarray:
    if n <= 0: return np.array([])
    if half_life <= 0: return np.ones(n) / n
    ages = np.arange(n)  # 0 antiguo -> n-1 reciente
    w = 0.5 ** ((n - 1 - ages) / float(half_life))
    w = np.clip(w, 1e-12, None)
    return w / w.sum()

def frecuencias_ponderadas(historico: List[List[int]], half_life: int):
    n = len(historico)
    if n == 0:
        return Counter(), Counter(), Counter()
    w = pesos_recencia(n, half_life)
    fnum: Dict[int,float] = defaultdict(float)
    fpairs: Dict[Tuple[int,int],float] = defaultdict(float)
    ftrios: Dict[Tuple[int,int,int],float] = defaultdict(float)
    for i, comb in enumerate(historico):
        wi = float(w[i])
        s = sorted(comb)
        for a in s: fnum[a] += wi
        # Para k=5 (Loto Pool), los tríos son computacionalmente baratos y valiosos
        for p in itertools.combinations(s, 2): fpairs[p] += wi
        for t in itertools.combinations(s, 3): ftrios[t] += wi
    return Counter(fnum), Counter(fpairs), Counter(ftrios)

def rango_suma(historico: List[List[int]], p_low=10, p_high=90) -> Tuple[int,int,int]:
    if not historico:
        # aproximado (uniforme 1..31, k=5)
        return 40, 120, 80
        
    # [ACTUALIZACIÓN] Vectorización con Numpy
    s = np.array(historico).sum(axis=1) # Suma por filas
    
    return int(np.percentile(s, p_low)), int(np.percentile(s, p_high)), int(np.mean(s))

def paridad_media(historico: List[List[int]]) -> Tuple[float,float]:
    if not historico: return 2.5, 2.5
    
    # [ACTUALIZACIÓN] Vectorización con Numpy
    H_arr = np.array(historico)
    pares = np.sum(H_arr % 2 == 0, axis=1) # Contar pares por fila
    
    mp = float(np.mean(pares))
    return mp, 5.0 - mp

def consecutivos_max(comb: List[int]) -> int:
    s = sorted(comb); best = 1; run = 1
    for a,b in zip(s, s[1:]):
        if b == a+1: run += 1; best = max(best, run)
        else: run = 1
    return best

# ----------------------------
# Samplers y reglas
# ----------------------------
def weighted_sample(U, W, k, rng):
    w = np.clip(W, 1e-12, None)
    w = w / w.sum()
    return sorted(rng.choice(U, size=k, replace=False, p=w).tolist())

def invert_weights(W):
    inv = 1.0 / np.clip(W, 1e-9, None)
    return inv / inv.sum()

def cumple_reglas(
    comb: List[int],
    sum_range: Optional[Tuple[int,int]],
    target_parity: Tuple[int,int],
    max_consec: int
) -> bool:
    if sum_range:
        s = sum(comb)
        if not (sum_range[0] <= s <= sum_range[1]): return False
    pares = sum(1 for x in comb if x % 2 == 0)
    # tolerancia ±1 sobre paridad target
    if abs(pares - target_parity[0]) > 1: return False
    if consecutivos_max(comb) > max_consec: return False
    return True

def score_bloques(comb, pair_w, trio_w, a=1.0, b=2.0):
    s = sorted(comb); S = 0.0
    for p in itertools.combinations(s, 2): S += a*pair_w.get(p, 0.0)
    for t in itertools.combinations(s, 3): S += b*trio_w.get(t, 0.0)
    return S

def mejor_de_n(n_cands, sampler, rules_kwargs, pair_w, trio_w, rng, a=1.0, b=2.0):
    best, bestS = None, -1e18
    for _ in range(n_cands):
        c = sampler()
        if not cumple_reglas(c, **rules_kwargs): continue
        S = score_bloques(c, pair_w, trio_w, a, b)
        if S > bestS: best, bestS = c, S
    return best if best else sampler()

def diversificar(preds: List[List[int]], nueva: List[int], max_overlap: int) -> bool:
    return all(len(set(p) & set(nueva)) <= max_overlap for p in preds)

# ----------------------------
# Generación principal (20 jugadas)
# ----------------------------
def generar_20(
    historico: List[List[int]],
    k=5, panels=20, seed=None,
    half_life=180, recent_window=400,
    max_consec=2, max_overlap=2
):
    rng = np.random.default_rng(seed)
    U = list(range(1, 32))

    # Pesos por recencia
    fnum_all, pair_w_all, trio_w_all = frecuencias_ponderadas(historico, half_life) if historico else (Counter(),Counter(),Counter())
    W = np.array([fnum_all.get(x, 0.0) for x in U], dtype=float)
    if W.sum() == 0: W = np.ones(len(U))/len(U)
    else: W = W / W.sum()

    # Ventana reciente para pares/tríos
    H_recent = historico[-recent_window:] if historico else []
    _, pair_w, trio_w = frecuencias_ponderadas(H_recent, max(1, half_life//2)) if H_recent else (Counter(),Counter(),Counter())

    # Suma y paridad target
    smin, smax, smed = rango_suma(historico, 10, 90)
    mp, mi = paridad_media(historico)
    p_target = int(round(mp))  # ej. ~2–3
    parity_target = (p_target, k - p_target)

    rules = dict(sum_range=(smin, smax), target_parity=parity_target, max_consec=max_consec)

    Winv = invert_weights(W)

    def samp_hot(): return weighted_sample(U, W, k, rng)
    def samp_cold(): return weighted_sample(U, Winv, k, rng)
    def samp_mix():
        # 3 hot + 2 cold aprox
        hot_k = 3; cold_k = k - hot_k
        hot = weighted_sample(U, W, hot_k, rng)
        rem = [x for x in U if x not in hot]
        wrem = np.array([Winv[U.index(x)] for x in rem], dtype=float)
        wrem = wrem / wrem.sum()
        cold = sorted(rng.choice(rem, size=cold_k, replace=False, p=wrem).tolist())
        return sorted(hot + cold)

    preds: List[List[int]] = []
    strat_cycle = ["hot","cold","mix","best"]
    tries = 0
    while len(preds) < panels and tries < panels * 40:
        strat = strat_cycle[len(preds) % len(strat_cycle)]
        if strat == "hot":
            cand = mejor_de_n(3000, samp_hot, rules, pair_w, trio_w, rng, a=1.0, b=2.0)
        elif strat == "cold":
            cand = mejor_de_n(3000, samp_cold, rules, pair_w, trio_w, rng, a=0.8, b=1.6)
        elif strat == "mix":
            cand = mejor_de_n(3000, samp_mix, rules, pair_w, trio_w, rng, a=1.0, b=2.0)
        else:  # best (busca por score directo desde hot)
            cand = mejor_de_n(5000, samp_hot, rules, pair_w, trio_w, rng, a=1.0, b=2.2)

        if cumple_reglas(cand, **rules) and diversificar(preds, cand, max_overlap):
            preds.append(cand)
        tries += 1

    meta = dict(
        panels=len(preds), pick_size=k, half_life=half_life, recent_window=recent_window,
        sum_range=(smin, smax), parity_target=parity_target,
        max_consec=max_consec, max_overlap=max_overlap
    )
    return preds, meta

# ----------------------------
# Backtest opcional
# ----------------------------
def backtest_hits(preds: List[List[int]], historico: List[List[int]], draws: int = 200) -> pd.DataFrame:
    if not historico or not preds: return pd.DataFrame()
    H = historico[-min(draws, len(historico)):]
    rows = []
    for i, p in enumerate(preds, 1):
        for j, d in enumerate(reversed(H), 1):
            rows.append({"panel": i, "draw": j, "hits": len(set(p) & set(d))})
    df = pd.DataFrame(rows)
    return df.groupby("panel")["hits"].agg(["mean","max","std"]).reset_index()

# ----------------------------
# CLI
# ----------------------------
def main():
    ap = argparse.ArgumentParser(description="20 predicciones para Loto Pool (5/31) con heurísticas y diversidad.")
    ap.add_argument("--csv", default="lotto_pool_historial.csv", help="Histórico (num1..num5 o similares).")
    ap.add_argument("--seed", type=int, default=None, help="Semilla para reproducibilidad.")
    ap.add_argument("--half-life", type=int, default=180, help="Half-life de recencia (en sorteos).")
    ap.add_argument("--recent-window", type=int, default=400, help="Ventana reciente para pares/tríos.")
    ap.add_argument("--max-consec", type=int, default=2, help="Máximo de consecutivos permitidos.")
    ap.add_argument("--max-overlap", type=int, default=2, help="Solapamiento máx entre jugadas (0..5).")
    ap.add_argument("--export", type=str, default="lottopool_predicciones.csv", help="Salida CSV con las 20 jugadas.")
    ap.add_argument("--backtest", type=int, default=0, help="Evalúa hits vs últimos N sorteos (0=off).")
    args = ap.parse_args()

    print("Cargando histórico...")
    historico = cargar_historico(args.csv)
    print(f"Histórico cargado: {len(historico)} sorteos válidos.")
    
    print("Generando paneles...")
    preds, meta = generar_20(historico,
                             k=5, panels=20, seed=args.seed,
                             half_life=args.half_life, recent_window=args.recent_window,
                             max_consec=args.max_consec, max_overlap=args.max_overlap)

    print("\n🎯 Config usada:")
    for k_, v_ in meta.items(): print(f"- {k_}: {v_}")

    print(f"\n🟩 {len(preds)} jugadas:")
    for i, c in enumerate(preds, 1):
        pares = sum(1 for x in c if x % 2 == 0)
        print(f"{i:02d}. {sorted(c)} | pares={pares} impares={5-pares} | sum={sum(c)} | maxConsec={consecutivos_max(c)}")

    if args.export:
        out = pd.DataFrame([{"panel": i, **{f"n{j+1}": c[j] for j in range(len(c))}} for i, c in enumerate(preds, 1)])
        out.to_csv(args.export, index=False, encoding="utf-8")
        print(f"\n💾 Exportado a: {args.export}")

    if args.backtest and historico:
        df = backtest_hits(preds, historico, draws=args.backtest)
        if not df.empty:
            print("\n📊 Backtest (hits por panel) vs últimos", args.backtest, "sorteos:")
            print(df.to_string(index=False))

if __name__ == "__main__":
    main()