import argparse
import itertools
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------------------------------
# Carga robusta del histórico
# ---------------------------------

def cargar_historico(csv_path: str) -> List[List[int]]:
    p = Path(csv_path)
    if not p.exists():
        return []
    try:
        df = pd.read_csv(p)
    except Exception:
        df = pd.read_csv(p, engine="python", on_bad_lines="skip")

    candidates = [
        ["num1", "num2", "num3", "num4", "num5"],
        ["num_1", "num_2", "num_3", "num_4", "num_5"],
        ["n1", "n2", "n3", "n4", "n5"],
    ]
    cols = None
    for cset in candidates:
        if all(c in df.columns for c in cset):
            cols = cset
            break

    if cols is None:
        numcols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(numcols) < 5:
            return []
        cols = numcols[:5]

    df_num = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    vals_raw = df_num.astype(int).values.tolist()

    vals: List[List[int]] = []
    for comb in vals_raw:
        s = sorted(comb)
        if len(s) == 5 and len(set(s)) == 5 and all(1 <= x <= 31 for x in s):
            vals.append(s)
    return vals


# ---------------------------------
# Stats y pesos
# ---------------------------------

def pesos_recencia(n: int, half_life: int) -> np.ndarray:
    if n <= 0:
        return np.array([])
    if half_life <= 0:
        return np.ones(n) / n
    ages = np.arange(n)
    w = 0.5 ** ((n - 1 - ages) / float(half_life))
    w = np.clip(w, 1e-12, None)
    return w / w.sum()


def stats_ponderadas(historico: List[List[int]], half_life: int):
    n = len(historico)
    if n == 0:
        return Counter(), Counter(), Counter(), {}

    w = pesos_recencia(n, half_life)
    fnum: Dict[int, float] = defaultdict(float)
    fpairs: Dict[Tuple[int, int], float] = defaultdict(float)
    ftrios: Dict[Tuple[int, int, int], float] = defaultdict(float)
    last_seen_idx: Dict[int, int] = {}

    for i, comb in enumerate(historico):
        wi = float(w[i])
        s = sorted(comb)
        for a in s:
            fnum[a] += wi
            last_seen_idx[a] = i
        for p in itertools.combinations(s, 2):
            fpairs[p] += wi
        for t in itertools.combinations(s, 3):
            ftrios[t] += wi

    return Counter(fnum), Counter(fpairs), Counter(ftrios), last_seen_idx


def rango_suma(historico: List[List[int]], p_low: int = 10, p_high: int = 90) -> Tuple[int, int, int]:
    if not historico:
        return 40, 120, 80
    s = np.array(historico).sum(axis=1)
    return int(np.percentile(s, p_low)), int(np.percentile(s, p_high)), int(np.mean(s))


def paridad_media(historico: List[List[int]]) -> Tuple[int, int]:
    if not historico:
        return 2, 3
    H_arr = np.array(historico)
    pares = np.sum(H_arr % 2 == 0, axis=1)
    mp = int(round(float(np.mean(pares))))
    return mp, 5 - mp


def consecutivos_max(comb: List[int]) -> int:
    s = sorted(comb)
    best = 1
    run = 1
    for a, b in zip(s, s[1:]):
        if b == a + 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def ultimo_sorteo(historico: List[List[int]]) -> set:
    return set(historico[-1]) if historico else set()


# ---------------------------------
# Reglas y scoring
# ---------------------------------

def cumple_reglas(
    comb: List[int],
    sum_range: Optional[Tuple[int, int]],
    target_parity: Tuple[int, int],
    max_consec: int,
    recent_cap_set: Optional[set] = None,
    recent_cap_max: int = 3,
) -> bool:
    s = sorted(comb)
    if len(s) != 5 or len(set(s)) != 5:
        return False
    if any(x < 1 or x > 31 for x in s):
        return False
    if sum_range:
        sm = sum(s)
        if not (sum_range[0] <= sm <= sum_range[1]):
            return False
    pares = sum(1 for x in s if x % 2 == 0)
    if abs(pares - target_parity[0]) > 1:
        return False
    if consecutivos_max(s) > max_consec:
        return False
    if recent_cap_set is not None and sum(1 for x in s if x in recent_cap_set) > recent_cap_max:
        return False
    return True


def normaliza_scores(d: Dict[int, float], universe: Iterable[int]) -> Dict[int, float]:
    vals = np.array([float(d.get(x, 0.0)) for x in universe], dtype=float)
    if vals.max() <= vals.min():
        return {x: 0.0 for x in universe}
    lo, hi = vals.min(), vals.max()
    return {x: float((d.get(x, 0.0) - lo) / (hi - lo)) for x in universe}


def construir_scores_numeros(
    historico: List[List[int]],
    half_life: int,
    recent_window: int,
) -> Dict[int, float]:
    U = list(range(1, 32))
    fnum_all, _, _, last_seen_idx = stats_ponderadas(historico, half_life)
    recent = historico[-recent_window:] if historico else []
    fnum_recent, _, _, _ = stats_ponderadas(recent, max(1, half_life // 2)) if recent else (Counter(), Counter(), Counter(), {})

    hot_all = normaliza_scores(fnum_all, U)
    hot_recent = normaliza_scores(fnum_recent, U)

    n = len(historico)
    gap_raw: Dict[int, float] = {}
    for x in U:
        idx = last_seen_idx.get(x)
        if idx is None:
            gap_raw[x] = float(n)
        else:
            gap_raw[x] = float((n - 1) - idx)
    gap = normaliza_scores(gap_raw, U)

    last = ultimo_sorteo(historico)

    scores: Dict[int, float] = {}
    for x in U:
        score = 0.55 * hot_all[x] + 0.25 * hot_recent[x] + 0.20 * gap[x]
        if x in last:
            score -= 0.08  # no perseguir demasiado el último resultado
        scores[x] = float(score)
    return scores


def score_combinacion(
    comb: List[int],
    num_score: Dict[int, float],
    pair_w: Counter,
    trio_w: Counter,
    historico: List[List[int]],
    target_sum: int,
    target_parity: Tuple[int, int],
) -> float:
    s = sorted(comb)
    score = sum(num_score.get(x, 0.0) for x in s)
    score += 0.85 * sum(pair_w.get(p, 0.0) for p in itertools.combinations(s, 2))
    score += 1.15 * sum(trio_w.get(t, 0.0) for t in itertools.combinations(s, 3))

    # Ajuste por suma y paridad razonables
    score -= abs(sum(s) - target_sum) / 70.0
    pares = sum(1 for x in s if x % 2 == 0)
    score -= 0.10 * abs(pares - target_parity[0])

    # Penaliza copiar un sorteo reciente entero o casi entero
    if historico:
        overlaps = [len(set(s) & set(h)) for h in historico[-8:]]
        max_ov = max(overlaps) if overlaps else 0
        if max_ov >= 4:
            score -= 0.80
        elif max_ov == 3:
            score -= 0.18
    return float(score)


def diversificar(preds: List[List[int]], nueva: List[int], max_overlap: int) -> bool:
    ns = set(nueva)
    return all(len(ns & set(p)) <= max_overlap for p in preds)


# ---------------------------------
# Generación eficiente de candidatos
# ---------------------------------

def weighted_choice_without_replacement(U: np.ndarray, W: np.ndarray, k: int, rng: np.random.Generator) -> List[int]:
    w = np.clip(W.astype(float), 1e-12, None)
    w = w / w.sum()
    return sorted(rng.choice(U, size=k, replace=False, p=w).tolist())


def generar_candidatos(
    historico: List[List[int]],
    panels: int = 8,
    seed: Optional[int] = None,
    half_life: int = 180,
    recent_window: int = 180,
    candidate_pool: int = 12000,
    max_consec: int = 2,
    max_overlap: int = 3,
):
    rng = np.random.default_rng(seed)
    U = np.arange(1, 32)

    if not historico:
        base = np.ones(len(U), dtype=float)
        pair_w, trio_w = Counter(), Counter()
        smin, smax, smed = 40, 120, 80
        parity_target = (2, 3)
        recent_cap_set = None
        scores = {int(x): 1.0 for x in U}
    else:
        scores = construir_scores_numeros(historico, half_life, recent_window)
        H_recent = historico[-recent_window:]
        _, pair_w, trio_w, _ = stats_ponderadas(H_recent, max(1, half_life // 2))
        base = np.array([scores[int(x)] for x in U], dtype=float)
        base = np.clip(base - base.min() + 1e-6, 1e-6, None)
        smin, smax, smed = rango_suma(historico, 10, 90)
        parity_target = paridad_media(historico)
        recent_cap_set = set().union(*[set(h) for h in historico[-3:]]) if len(historico) >= 3 else set().union(*[set(h) for h in historico])

    inverse = 1.0 / np.clip(base, 1e-8, None)
    inverse = inverse / inverse.sum()
    base = base / base.sum()

    def samp_hot():
        return weighted_choice_without_replacement(U, base, 5, rng)

    def samp_cold():
        return weighted_choice_without_replacement(U, inverse, 5, rng)

    def samp_mix(hot_k: int = 3):
        hot = weighted_choice_without_replacement(U, base, hot_k, rng)
        rem = np.array([x for x in U if x not in hot])
        rem_w = np.array([inverse[list(U).index(x)] for x in rem], dtype=float)
        rem_w = rem_w / rem_w.sum()
        cold = sorted(rng.choice(rem, size=5 - hot_k, replace=False, p=rem_w).tolist())
        return sorted(hot + cold)

    def samp_blend():
        # mezcla menos extrema para evitar paneles clónicos
        alpha = rng.uniform(0.25, 0.75)
        blend = alpha * base + (1 - alpha) * inverse
        blend = blend / blend.sum()
        return weighted_choice_without_replacement(U, blend, 5, rng)

    strategies = [
        ("hot", samp_hot),
        ("mix", lambda: samp_mix(3)),
        ("mix", lambda: samp_mix(2)),
        ("cold", samp_cold),
        ("blend", samp_blend),
    ]

    rules = dict(
        sum_range=(smin, smax),
        target_parity=parity_target,
        max_consec=max_consec,
        recent_cap_set=recent_cap_set,
        recent_cap_max=3,
    )

    scored: Dict[Tuple[int, ...], Tuple[float, str]] = {}

    for i in range(candidate_pool):
        strat_name, strat = strategies[i % len(strategies)]
        cand = strat()
        if not cumple_reglas(cand, **rules):
            continue
        key = tuple(cand)
        sc = score_combinacion(cand, scores, pair_w, trio_w, historico, smed, parity_target)
        prev = scored.get(key)
        if prev is None or sc > prev[0]:
            scored[key] = (sc, strat_name)

    # respaldo: enumeración parcial si el pool quedó corto
    if len(scored) < max(200, panels * 20):
        for comb in itertools.combinations(range(1, 32), 5):
            cand = list(comb)
            if not cumple_reglas(cand, **rules):
                continue
            sc = score_combinacion(cand, scores, pair_w, trio_w, historico, smed, parity_target)
            prev = scored.get(comb)
            if prev is None or sc > prev[0]:
                scored[comb] = (sc, "enum")

    ranked = sorted(((sc, list(comb), origin) for comb, (sc, origin) in scored.items()), key=lambda x: x[0], reverse=True)

    selected: List[List[int]] = []
    rows = []
    for sc, comb, origin in ranked:
        if diversificar(selected, comb, max_overlap=max_overlap):
            selected.append(comb)
            pares = sum(1 for x in comb if x % 2 == 0)
            rows.append({
                "panel": len(selected),
                "n1": comb[0], "n2": comb[1], "n3": comb[2], "n4": comb[3], "n5": comb[4],
                "score": round(sc, 6),
                "pares": pares,
                "impares": 5 - pares,
                "suma": sum(comb),
                "maxConsec": consecutivos_max(comb),
                "perfil": origin,
            })
            if len(selected) >= panels:
                break

    meta = {
        "panels": len(selected),
        "pick_size": 5,
        "half_life": half_life,
        "recent_window": recent_window,
        "candidate_pool": candidate_pool,
        "sum_range": (smin, smax),
        "target_sum": smed,
        "parity_target": parity_target,
        "max_consec": max_consec,
        "max_overlap": max_overlap,
    }
    return rows, meta


# ---------------------------------
# CLI
# ---------------------------------

def main():
    ap = argparse.ArgumentParser(description="Predicciones diversificadas para Loto Pool (5/31).")
    ap.add_argument("--csv", default="lotto_pool_historial.csv", help="Histórico CSV (num1..num5 o similares).")
    ap.add_argument("--panels", type=int, default=8, help="Cantidad de jugadas a emitir.")
    ap.add_argument("--seed", type=int, default=None, help="Semilla para reproducibilidad.")
    ap.add_argument("--half-life", type=int, default=180, help="Half-life de recencia (en sorteos).")
    ap.add_argument("--recent-window", type=int, default=180, help="Ventana reciente usada para pares/tríos.")
    ap.add_argument("--candidate-pool", type=int, default=12000, help="Cantidad de candidatos a explorar antes del ranking final.")
    ap.add_argument("--max-consec", type=int, default=2, help="Máximo de consecutivos permitidos.")
    ap.add_argument("--max-overlap", type=int, default=3, help="Solapamiento máximo entre jugadas finales.")
    ap.add_argument("--export", type=str, default="lottopool_top8.csv", help="CSV de salida.")
    args = ap.parse_args()

    historico = cargar_historico(args.csv)
    print(f"Histórico cargado: {len(historico)} sorteos válidos.")

    rows, meta = generar_candidatos(
        historico=historico,
        panels=args.panels,
        seed=args.seed,
        half_life=args.half_life,
        recent_window=args.recent_window,
        candidate_pool=args.candidate_pool,
        max_consec=args.max_consec,
        max_overlap=args.max_overlap,
    )

    print("\n🎯 Config usada:")
    for k, v in meta.items():
        print(f"- {k}: {v}")

    print(f"\n🟩 {len(rows)} jugadas priorizadas:")
    for r in rows:
        combo = [r[f"n{i}"] for i in range(1, 6)]
        print(f"{r['panel']:02d}. {combo} | score={r['score']:.4f} | perfil={r['perfil']} | pares={r['pares']} impares={r['impares']} | suma={r['suma']}")

    if args.export:
        pd.DataFrame(rows).to_csv(args.export, index=False, encoding="utf-8")
        print(f"\n💾 Exportado a: {args.export}")


if __name__ == "__main__":
    main()
