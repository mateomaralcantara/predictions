
# superkino_predictor_v4.py
# Predictor heurístico Super Kino.
# Ajustes v4:
# - Carga CSV robusta aunque el archivo venga malformado.
# - Soporta encabezados fecha,num_1..num_20 y también archivos viejos con n1..n20.
# - Ignora filas dañadas sin romper el proceso.
#
# Requisitos:
#   pip install numpy pandas
#
# Uso:
#   python superkino_predictor_v4.py --csv superkino_historico_limpio.csv --panels 8 --pick-size 10
#   python superkino_predictor_v4.py --export jugadas.csv
from __future__ import annotations

import argparse
import csv
import itertools
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd


def _parse_date(raw: str):
    raw = (raw or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except Exception:
            continue
    return None


def _load_loose_rows(csv_path: str) -> pd.DataFrame:
    p = Path(csv_path)
    if not p.exists():
        return pd.DataFrame(columns=["fecha"] + [f"num_{i}" for i in range(1, 21)])

    rows = []
    with p.open("r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        for i, row in enumerate(r, start=1):
            if not row:
                continue
            if i == 1:
                continue
            d = _parse_date(row[0]) if row else None
            if d is None:
                continue
            nums = []
            for cell in row[1:]:
                cell = (cell or "").strip()
                if cell.isdigit():
                    nums.append(int(cell))
            seen = set()
            clean = []
            for n in nums:
                if 1 <= n <= 80 and n not in seen:
                    clean.append(n)
                    seen.add(n)
                if len(clean) == 20:
                    break
            if len(clean) == 20:
                rows.append([d.isoformat()] + clean)

    cols = ["fecha"] + [f"num_{i}" for i in range(1, 21)]
    if not rows:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(rows, columns=cols)
    df = df.drop_duplicates(subset=["fecha"], keep="last").sort_values("fecha").reset_index(drop=True)
    return df


def cargar_historico(csv_path: str) -> List[List[int]]:
    df = _load_loose_rows(csv_path)
    if df.empty:
        return []
    cols = [f"num_{i}" for i in range(1, 21)]
    vals: List[List[int]] = []
    for comb in df[cols].astype(int).values.tolist():
        if len(comb) != 20:
            continue
        if any(x < 1 or x > 80 for x in comb):
            continue
        if len(set(comb)) != 20:
            continue
        vals.append(comb)
    return vals


def pesos_recencia(n: int, half_life: int) -> np.ndarray:
    if n <= 0:
        return np.array([], dtype=np.float64)
    if half_life <= 0:
        w = np.ones(n, dtype=np.float64)
        return w / w.sum()
    ages = np.arange(n, dtype=np.float64)
    w = 0.5 ** ((n - 1 - ages) / float(half_life))
    w = np.clip(w, 1e-12, None)
    return w / w.sum()


def frecuencias_ponderadas(historico: List[List[int]], half_life: int, calc_pairs: bool = True):
    n = len(historico)
    if n == 0:
        return Counter(), Counter()
    w = pesos_recencia(n, half_life)
    fnum: Dict[int, float] = defaultdict(float)
    fpairs: Dict[Tuple[int, int], float] = defaultdict(float)
    for i, comb in enumerate(historico):
        wi = float(w[i])
        s = sorted(comb)
        for a in s:
            fnum[a] += wi
        if calc_pairs:
            for p in itertools.combinations(s, 2):
                fpairs[p] += wi
    return Counter(fnum), Counter(fpairs)


def distrib_buckets(historico: List[List[int]], nbuckets: int = 8) -> np.ndarray:
    if not historico:
        return np.array([20.0 / nbuckets] * nbuckets, dtype=np.float64)
    H = np.asarray(historico, dtype=np.int16)
    b = (H - 1) // 10
    n = H.shape[0]
    counts = np.zeros((n, nbuckets), dtype=np.int16)
    rows = np.repeat(np.arange(n, dtype=np.int32), H.shape[1])
    cols = b.reshape(-1).astype(np.int32)
    np.add.at(counts, (rows, cols), 1)
    return counts.mean(axis=0).astype(np.float64)


def distrib_paridad(historico: List[List[int]]) -> Tuple[float, float]:
    if not historico:
        return 10.0, 10.0
    H = np.asarray(historico, dtype=np.int16)
    pares = (H % 2 == 0).sum(axis=1)
    mp = float(np.mean(pares))
    return mp, 20.0 - mp


def consecutivos_max_sorted(sorted_arr: np.ndarray) -> int:
    if sorted_arr.size <= 1:
        return int(sorted_arr.size)
    dif = np.diff(sorted_arr)
    best = run = 1
    for d in dif:
        if d == 1:
            run += 1
            if run > best:
                best = run
        else:
            run = 1
    return best


def cumple_reglas_fast(comb_sorted: np.ndarray, target_even: int, parity_tol: int, max_consec: int,
                       target_bucket_counts: Optional[np.ndarray], bucket_tol: int, min_spread: int) -> bool:
    even = int((comb_sorted % 2 == 0).sum())
    if abs(even - target_even) > parity_tol:
        return False
    if max_consec >= 1 and consecutivos_max_sorted(comb_sorted) > max_consec:
        return False
    if min_spread > 0 and int(comb_sorted[-1] - comb_sorted[0]) < min_spread:
        return False
    if target_bucket_counts is not None:
        b = (comb_sorted - 1) // 10
        counts = np.bincount(b, minlength=8).astype(np.int16)
        if np.any(np.abs(counts - target_bucket_counts) > bucket_tol):
            return False
    return True


def build_pair_matrix(pair_w: Counter) -> np.ndarray:
    M = np.zeros((81, 81), dtype=np.float32)
    for (a, b), v in pair_w.items():
        if 1 <= a <= 80 and 1 <= b <= 80 and a != b:
            if a < b:
                M[a, b] = float(v)
            else:
                M[b, a] = float(v)
    return M


def score_pairs_mat(sorted_nums: np.ndarray, pair_mat: np.ndarray, alpha: float) -> float:
    if alpha == 0.0:
        return 0.0
    S = 0.0
    k = int(sorted_nums.size)
    for i in range(k - 1):
        ai = int(sorted_nums[i])
        for j in range(i + 1, k):
            S += float(pair_mat[ai, int(sorted_nums[j])])
    return alpha * S


def score_numbers(sorted_idx: np.ndarray, W: np.ndarray, alpha: float) -> float:
    if alpha == 0.0:
        return 0.0
    return alpha * float(np.take(W, sorted_idx).sum())


def score_spread(sorted_nums: np.ndarray, alpha: float) -> float:
    if alpha == 0.0:
        return 0.0
    sp = float(sorted_nums[-1] - sorted_nums[0]) / 79.0
    return alpha * sp


def es_sample_idx(weights: np.ndarray, k: int, rng: np.random.Generator, pool_idx: Optional[np.ndarray] = None) -> np.ndarray:
    if pool_idx is None:
        pool_idx = np.arange(weights.size, dtype=np.int16)
    w = np.clip(weights[pool_idx].astype(np.float64, copy=False), 1e-12, None)
    u = rng.random(pool_idx.size)
    keys = u ** (1.0 / w)
    chosen = pool_idx[np.argpartition(keys, -k)[-k:]]
    chosen.sort()
    return chosen


def invert_weights(W: np.ndarray) -> np.ndarray:
    inv = 1.0 / np.clip(W.astype(np.float64, copy=False), 1e-9, None)
    inv = inv / inv.sum()
    return inv.astype(np.float64, copy=False)


def mejor_de_n(n_cands: int, sampler_idx, rules_kwargs: dict, pair_mat: np.ndarray, W: np.ndarray,
               rng: np.random.Generator, k: int, alpha_pairs: float, alpha_num: float, alpha_spread: float) -> List[int]:
    best = None
    bestS = -1e18
    for _ in range(n_cands):
        idx = sampler_idx()
        nums = (idx + 1).astype(np.int16, copy=False)
        nums.sort()
        if not cumple_reglas_fast(nums, **rules_kwargs):
            continue
        S = 0.0
        S += score_pairs_mat(nums, pair_mat, alpha=alpha_pairs)
        S += score_numbers(np.sort(idx), W, alpha=alpha_num)
        S += score_spread(nums, alpha=alpha_spread)
        if S > bestS:
            bestS = S
            best = nums.copy()
    if best is not None:
        return best.tolist()
    for _ in range(800):
        idx = sampler_idx()
        nums = (idx + 1).astype(np.int16, copy=False)
        nums.sort()
        if cumple_reglas_fast(nums, **rules_kwargs):
            return nums.tolist()
    idx = sampler_idx()
    nums = (idx + 1).astype(np.int16, copy=False)
    nums.sort()
    return nums.tolist()


def diversificar_sets(pred_sets: List[set], nueva: List[int], max_overlap: int) -> bool:
    s = set(nueva)
    return all(len(ps & s) <= max_overlap for ps in pred_sets)


def generar_panels(historico: List[List[int]], panels: int = 8, k: int = 10, seed: Optional[int] = None,
                   half_life: int = 120, recent_window: int = 300, max_consec: int = 2, max_overlap: int = 7,
                   n_cands: int = 5000, alpha_pairs: float = 1.0, alpha_num: float = 0.35,
                   alpha_spread: float = 0.15, min_spread: Optional[int] = None):
    rng = np.random.default_rng(seed)
    fnum, _ = frecuencias_ponderadas(historico, half_life, calc_pairs=False) if historico else (Counter(), Counter())
    W = np.array([float(fnum.get(i, 0.0)) for i in range(1, 81)], dtype=np.float64)
    W = np.ones(80, dtype=np.float64) / 80.0 if W.sum() <= 0 else W / W.sum()
    Winv = invert_weights(W)
    H_recent = historico[-recent_window:] if historico else []
    _, pair_w = frecuencias_ponderadas(H_recent, max(1, half_life // 2), calc_pairs=True) if H_recent else (Counter(), Counter())
    pair_mat = build_pair_matrix(pair_w)

    means = distrib_buckets(historico, nbuckets=8)
    target_bucket_counts = np.floor(means * (k / 20.0)).astype(np.int16)
    while int(target_bucket_counts.sum()) < k:
        resid = (means * (k / 20.0)) - target_bucket_counts.astype(np.float64)
        target_bucket_counts[int(np.argmax(resid))] += 1
    while int(target_bucket_counts.sum()) > k:
        target_bucket_counts[int(np.argmax(target_bucket_counts))] -= 1

    mp, _ = distrib_paridad(historico)
    target_even = int(round(mp * (k / 20.0)))
    if min_spread is None:
        min_spread = int(round(2.5 * k + 10))

    all_idx = np.arange(80, dtype=np.int16)

    def samp_hot_idx(): return es_sample_idx(W, k, rng)
    def samp_cold_idx(): return es_sample_idx(Winv, k, rng)

    def samp_mix_idx():
        hot_k = max(1, int(round(k * 0.7)))
        cold_k = k - hot_k
        hot = es_sample_idx(W, hot_k, rng)
        if cold_k <= 0:
            return hot
        mask = np.ones(80, dtype=bool)
        mask[hot] = False
        rem = all_idx[mask]
        if rem.size == 0:
            return hot
        cold = es_sample_idx(Winv, cold_k, rng, pool_idx=rem)
        out = np.concatenate([hot, cold])
        out = np.unique(out)
        if out.size < k:
            missing = k - int(out.size)
            pool = all_idx[~np.isin(all_idx, out)]
            if pool.size > 0:
                extra = rng.choice(pool, size=min(missing, int(pool.size)), replace=False)
                out = np.concatenate([out, extra.astype(np.int16)])
        out.sort()
        return out[:k]

    def samp_bucket_idx():
        selected = np.zeros(80, dtype=bool)
        picks: List[int] = []
        for b in range(8):
            t = int(target_bucket_counts[b])
            if t <= 0:
                continue
            lo, hi = b * 10, b * 10 + 10
            pool = np.arange(lo, hi, dtype=np.int16)
            pool = pool[~selected[pool]]
            if pool.size == 0:
                continue
            chosen = es_sample_idx(W, min(t, int(pool.size)), rng, pool_idx=pool)
            selected[chosen] = True
            picks.extend(chosen.tolist())
        if len(picks) < k:
            pool = all_idx[~selected]
            if pool.size > 0:
                extra = rng.choice(pool, size=min(k - len(picks), int(pool.size)), replace=False)
                picks.extend(extra.astype(int).tolist())
        arr = np.array(picks[:k], dtype=np.int16)
        arr.sort()
        return arr

    def samp_random_idx():
        return rng.choice(all_idx, size=k, replace=False).astype(np.int16)

    strategies = [("hot", samp_hot_idx), ("cold", samp_cold_idx), ("mix", samp_mix_idx), ("bucket", samp_bucket_idx), ("best", samp_hot_idx)]
    strat_order = [n for n, _ in strategies]
    strat_map = {n: fn for n, fn in strategies}
    relax_steps = [
        dict(parity_tol=2, bucket_tol=1, consec=max_consec, overlap=max_overlap),
        dict(parity_tol=2, bucket_tol=2, consec=max_consec, overlap=min(k, max_overlap + 1)),
        dict(parity_tol=3, bucket_tol=2, consec=max_consec + 1, overlap=min(k, max_overlap + 2)),
        dict(parity_tol=3, bucket_tol=3, consec=max_consec + 1, overlap=min(k, max_overlap + 3)),
        dict(parity_tol=4, bucket_tol=4, consec=max_consec + 2, overlap=k),
    ]

    preds, pred_sets = [], []
    for rel in relax_steps:
        rules = dict(target_even=target_even, parity_tol=int(rel["parity_tol"]), max_consec=int(rel["consec"]),
                     target_bucket_counts=target_bucket_counts, bucket_tol=int(rel["bucket_tol"]), min_spread=int(min_spread))
        overlap_now = int(rel["overlap"])
        tries, max_tries = 0, max(800, panels * 200)
        while len(preds) < panels and tries < max_tries:
            name = strat_order[len(preds) % len(strat_order)]
            cand = mejor_de_n(n_cands=n_cands, sampler_idx=strat_map[name], rules_kwargs=rules, pair_mat=pair_mat,
                              W=W, rng=rng, k=k, alpha_pairs=alpha_pairs, alpha_num=alpha_num, alpha_spread=alpha_spread)
            cand_arr = np.asarray(cand, dtype=np.int16)
            cand_arr.sort()
            if cumple_reglas_fast(cand_arr, **rules) and diversificar_sets(pred_sets, cand, overlap_now):
                preds.append(cand_arr.tolist())
                pred_sets.append(set(cand_arr.tolist()))
            tries += 1
        if len(preds) >= panels:
            break

    while len(preds) < panels:
        idx = samp_random_idx()
        nums = (idx + 1).astype(np.int16, copy=False)
        nums.sort()
        cand = nums.tolist()
        if set(cand) in pred_sets:
            continue
        preds.append(cand)
        pred_sets.append(set(cand))
    return preds


def main() -> None:
    ap = argparse.ArgumentParser(description="SuperKino predictor heurístico robusto.")
    ap.add_argument("--csv", default="superkino_historico_limpio.csv", help="Histórico CSV.")
    ap.add_argument("--panels", type=int, default=8, help="Cantidad de jugadas.")
    ap.add_argument("--pick-size", type=int, default=10, help="Tamaño de cada jugada.")
    ap.add_argument("--seed", type=int, default=None, help="Semilla.")
    ap.add_argument("--half-life", type=int, default=120, help="Half-life recencia.")
    ap.add_argument("--recent-window", type=int, default=300, help="Ventana reciente para pares.")
    ap.add_argument("--max-consec", type=int, default=2, help="Consecutivos máximos.")
    ap.add_argument("--max-overlap", type=int, default=7, help="Solapamiento máximo.")
    ap.add_argument("--n-cands", type=int, default=5000, help="Candidatos por panel.")
    ap.add_argument("--export", type=str, default=None, help="Exportar CSV.")
    args = ap.parse_args()

    historico = cargar_historico(args.csv)
    print(f"Histórico válido: {len(historico)} sorteos")
    preds = generar_panels(
        historico=historico,
        panels=max(1, int(args.panels)),
        k=max(1, min(20, int(args.pick_size))),
        seed=args.seed,
        half_life=int(args.half_life),
        recent_window=int(args.recent_window),
        max_consec=int(args.max_consec),
        max_overlap=int(args.max_overlap),
        n_cands=max(200, int(args.n_cands)),
    )

    for i, c in enumerate(preds, 1):
        arr = np.asarray(c, dtype=np.int16)
        pares = int((arr % 2 == 0).sum())
        mc = consecutivos_max_sorted(np.sort(arr))
        sp = int(arr.max() - arr.min()) if arr.size else 0
        print(f"{i:02d}. {sorted(c)} | pares={pares} impares={len(c)-pares} | maxConsec={mc} | spread={sp}")

    if args.export:
        out = pd.DataFrame([{"panel": i, **{f"n{j+1}": c[j] for j in range(len(c))}} for i, c in enumerate(preds, 1)])
        out.to_csv(args.export, index=False, encoding="utf-8")
        print(f"Exportado a: {args.export}")


if __name__ == "__main__":
    main()
