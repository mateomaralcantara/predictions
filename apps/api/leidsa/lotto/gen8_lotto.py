# gen8_lotto.py
import argparse, itertools
from collections import Counter, defaultdict
from typing import List, Tuple, Optional, Dict

import numpy as np
import pandas as pd

# ----------------------- Carga histórico -----------------------
def cargar_historico(csv_path: str) -> List[List[int]]:
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return []
    cols_ok = None

    # Preferencias típicas (6 base)
    cand_sets = [
        [f"n{i}" for i in range(1,7)],
        [f"num{i}" for i in range(1,7)],
        [f"num_{i}" for i in range(1,7)],
    ]
    for cs in cand_sets:
        if all(c in df.columns for c in cs):
            cols_ok = cs
            break

    # Si no, intenta detectar 6 primeras columnas numéricas y descartar 'mas'/'super_mas'
    if cols_ok is None:
        cols_num = []
        for c in df.columns:
            name = str(c).strip().lower()
            if name in ("mas","super_mas","supermas"):
                continue
            if pd.api.types.is_numeric_dtype(df[c]) or pd.to_numeric(df[c], errors="coerce").notna().any():
                cols_num.append(c)
        if len(cols_num) >= 6:
            cols_ok = cols_num[:6]

    if cols_ok is None:
        return []

    # Filtra filas válidas: 6 enteros únicos en 1..40
    vals = []
    sub = df[cols_ok].apply(pd.to_numeric, errors="coerce").dropna()
    for _, r in sub.iterrows():
        comb = [int(x) for x in r.values.tolist()]
        if len(comb) == 6 and len(set(comb)) == 6 and all(1 <= x <= 40 for x in comb):
            vals.append(comb)
    return vals

# ----------------------- Stats / pesos -----------------------
def pesos_recencia(n: int, half_life: int) -> np.ndarray:
    if n <= 0: return np.array([])
    if half_life <= 0: return np.ones(n) / n
    ages = np.arange(n)  # 0 antiguo -> n-1 reciente
    w = 0.5 ** ((n - 1 - ages) / float(half_life))
    w = np.clip(w, 1e-12, None)
    return w / w.sum()

def frecuencias_ponderadas(h: List[List[int]], half_life: int):
    n = len(h)
    if n == 0:
        return Counter(), Counter(), Counter()
    w = pesos_recencia(n, half_life)
    fnum: Dict[int,float] = defaultdict(float)
    fpairs: Dict[Tuple[int,int],float] = defaultdict(float)
    ftrios: Dict[Tuple[int,int,int],float] = defaultdict(float)
    for i, comb in enumerate(h):
        wi = float(w[i])
        s = sorted(comb)
        for a in s: fnum[a] += wi
        for p in itertools.combinations(s, 2): fpairs[p] += wi
        for t in itertools.combinations(s, 3): ftrios[t] += wi
    return Counter(fnum), Counter(fpairs), Counter(ftrios)

def rango_sumatoria(h: List[List[int]], p_low=20, p_high=80):
    if not h: return 21, 245, 120
    s = np.array([sum(c) for c in h])
    return int(np.percentile(s, p_low)), int(np.percentile(s, p_high)), int(np.mean(s))

def consecutivos_max(comb: List[int]) -> int:
    s = sorted(comb); best = 1; run = 1
    for a,b in zip(s, s[1:]):
        if b == a+1: run += 1; best = max(best, run)
        else: run = 1
    return best

def conteo_paridad(comb: List[int]) -> Tuple[int,int]:
    pares = sum(1 for x in comb if x % 2 == 0)
    return pares, 6 - pares

# ----------------------- Reglas & muestreos -----------------------
def cumple_reglas(comb, sum_range, parity_allowed, max_consec) -> bool:
    s = sum(comb)
    if not (sum_range[0] <= s <= sum_range[1]): return False
    if consecutivos_max(comb) > max_consec: return False
    if parity_allowed and (conteo_paridad(comb) not in parity_allowed): return False
    return True

def weighted_sample(U, W, k, rng):
    w = np.clip(W, 1e-12, None); w = w / w.sum()
    return sorted(rng.choice(U, size=k, replace=False, p=w).tolist())

def invert_weights(W):
    inv = 1.0 / np.clip(W, 1e-9, None)
    return inv / inv.sum()

def score_bloques(comb, pair_w, trio_w, a=1.0, b=2.0):
    s = 0.0; sc = sorted(comb)
    for p in itertools.combinations(sc, 2): s += a*pair_w.get(p, 0.0)
    for t in itertools.combinations(sc, 3): s += b*trio_w.get(t, 0.0)
    return s

def mejor_de_n(n_cands, sampler, rules, pair_w, trio_w, rng, a=1.0, b=2.0):
    best, bestS = None, -1e18
    for _ in range(n_cands):
        c = sampler()
        if not cumple_reglas(c, **rules): continue
        S = score_bloques(c, pair_w, trio_w, a, b)
        if S > bestS: best, bestS = c, S
    return best if best else sampler()

def diversificar(preds, nueva, max_overlap=3) -> bool:
    return all(len(set(p) & set(nueva)) <= max_overlap for p in preds)

# ----------------------- Generación (8 jugadas) -----------------------
def generar_8(historico: List[List[int]],
              half_life=20,
              sum_percentiles=(20,80),
              max_consec=2,
              parity_allowed=[(3,3),(4,2),(2,4)],
              seed: Optional[int]=None):
    rng = np.random.default_rng(seed)
    U = list(range(1, 41))

    fnum, pair_w, trio_w = frecuencias_ponderadas(historico, half_life) if historico else (Counter(),Counter(),Counter())
    W = np.array([fnum.get(x, 0.0) for x in U], dtype=float)
    if W.sum() == 0: W = np.ones(len(U))/len(U)
    else: W = W / W.sum()

    smin, smax, _ = rango_sumatoria(historico, *sum_percentiles)
    rules = dict(sum_range=(smin, smax), parity_allowed=parity_allowed, max_consec=max_consec)

    Winv = invert_weights(W)
    def samp_hot():  return weighted_sample(U, W, 6, rng)
    def samp_cold(): return weighted_sample(U, Winv, 6, rng)
    def samp_mix():
        hot = weighted_sample(U, W, 4, rng)
        rem = [x for x in U if x not in hot]
        wrem = np.array([Winv[U.index(x)] for x in rem], dtype=float)
        wrem = wrem / wrem.sum()
        cold2 = sorted(rng.choice(rem, size=2, replace=False, p=wrem).tolist())
        return sorted(hot + cold2)

    preds = []

    # 1–2: calientes (mejor de N)
    for _ in range(2):
        cand = mejor_de_n(4000, samp_hot, rules, pair_w, trio_w, rng, a=1.0, b=2.0)
        if diversificar(preds, cand, 3): preds.append(cand)

    # 3–4: fríos (mejor de N suave)
    for _ in range(2):
        cand = mejor_de_n(3500, samp_cold, rules, pair_w, trio_w, rng, a=0.8, b=1.6)
        if diversificar(preds, cand, 3): preds.append(cand)

    # 5–6: mix 4/2
    for _ in range(2):
        cand = mejor_de_n(3500, samp_mix, rules, pair_w, trio_w, rng, a=1.0, b=2.0)
        if diversificar(preds, cand, 3): preds.append(cand)

    # 7: bucket altos/bajos 3–3 (respecto a mediana 20)
    def samp_bal():
        bajos = [x for x in U if x <= 20]; altos = [x for x in U if x > 20]
        wb = np.array([W[U.index(x)] for x in bajos]); wb = wb/wb.sum() if wb.sum()>0 else np.ones(len(bajos))/len(bajos)
        wa = np.array([W[U.index(x)] for x in altos]); wa = wa/wa.sum() if wa.sum()>0 else np.ones(len(altos))/len(altos)
        a = sorted(np.random.default_rng(rng.integers(1, 1<<31)).choice(bajos, 3, replace=False, p=wb).tolist())
        b = sorted(np.random.default_rng(rng.integers(1, 1<<31)).choice(altos, 3, replace=False, p=wa).tolist())
        return sorted(a+b)
    cand = mejor_de_n(3000, samp_bal, rules, pair_w, trio_w, rng, a=1.0, b=2.0)
    if diversificar(preds, cand, 3): preds.append(cand)

    # 8: “best of best” desde hot puro
    cand = mejor_de_n(7000, samp_hot, rules, pair_w, trio_w, rng, a=1.0, b=2.3)
    if diversificar(preds, cand, 3): preds.append(cand)

    return preds, (smin, smax)

# ----------------------- CLI -----------------------
def main():
    ap = argparse.ArgumentParser(description="Genera 8 combinaciones 'con heurística' para Loto (6/40).")
    ap.add_argument("--csv", default="loto_leidsa.csv", help="Histórico (si existe; si no, usa 1..40 uniforme).")
    ap.add_argument("--seed", type=int, default=None, help="Semilla para reproducibilidad.")
    ap.add_argument("--half-life", type=int, default=20, help="Half-life de recencia (en sorteos).")
    ap.add_argument("--export", type=str, default=None, help="CSV de salida con las 8 jugadas.")
    args = ap.parse_args()

    hist = cargar_historico(args.csv)
    preds, sum_range = generar_8(hist, half_life=args.half_life, seed=args.seed)

    print(f"\n🎯 Config: half-life={args.half_life} | sum_range≈{sum_range[0]}..{sum_range[1]}")
    print(f"🟩 8 combinaciones sugeridas:")
    for i, c in enumerate(preds, 1):
        pares, impares = conteo_paridad(c)
        print(f"{i:02d}. {c} | suma={sum(c)} | P/I={pares}/{impares} | maxConsec={consecutivos_max(c)}")

    if args.export:
        out = pd.DataFrame([{"n1":c[0],"n2":c[1],"n3":c[2],"n4":c[3],"n5":c[4],"n6":c[5]} for c in preds])
        out.to_csv(args.export, index=False, encoding="utf-8")
        print(f"\n💾 Exportado a: {args.export}")

    print("\n⚠️ Real talk: en un sorteo justo ninguna combinación tiene ventaja real. Esto solo organiza el caos con reglas y diversidad.")

if __name__ == "__main__":
    main()
