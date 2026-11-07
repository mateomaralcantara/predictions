from __future__ import annotations

import argparse
import csv
import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Draw:
    fecha: str
    nums: tuple[int,...]
    mas: int
    super_mas: int


def load_csv(path: str) -> list[Draw]:
    p=Path(path); out=[]
    if not p.exists(): return out
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        for i,row in enumerate(csv.reader(f)):
            if not row or (i==0 and row[0].lower() in {"fecha","date"}): continue
            try:
                d=datetime.strptime(row[0],"%Y-%m-%d").date().isoformat(); vals=[int(x) for x in row[1:9]]
            except Exception: continue
            nums=vals[:6]; mas,sup=vals[6],vals[7]
            if len(set(nums))==6 and all(1<=n<=40 for n in nums) and 1<=mas<=12 and 1<=sup<=15:
                out.append(Draw(d,tuple(sorted(nums)),mas,sup))
    dedup={d.fecha:d for d in out}; return [dedup[k] for k in sorted(dedup)]


def recency(n:int,half:int)->np.ndarray:
    if n<=0:return np.array([],dtype=float)
    a=np.arange(n,dtype=float); w=.5**((n-1-a)/max(1,half)); return w/w.sum()


def stats(draws:Sequence[Draw],half:int):
    W=np.zeros(41,float); P=np.zeros((41,41),float)
    if not draws: W[1:]=1/40; return W,P
    for wi,d in zip(recency(len(draws),half),draws):
        for n in d.nums: W[n]+=wi
        for a,b in itertools.combinations(d.nums,2): P[min(a,b),max(a,b)]+=wi
    W[1:]/=W[1:].sum(); return W,P


def extra_weights(draws:Sequence[Draw],attr:str,upper:int,half:int)->np.ndarray:
    W=np.zeros(upper+1,float)
    if not draws: W[1:]=1/upper; return W
    for wi,d in zip(recency(len(draws),half),draws): W[getattr(d,attr)]+=wi
    W[1:]/=W[1:].sum(); return W


def shape(nums:Sequence[int])->bool:
    s=sorted(nums); ev=sum(n%2==0 for n in s); low=sum(n<=20 for n in s)
    consec=max((sum(1 for _ in g) for k,g in itertools.groupby(enumerate(s),lambda x:x[1]-x[0])),default=1)
    buckets=[sum(1 for n in s if lo<=n<=lo+9) for lo in (1,11,21,31)]
    return len(s)==6 and len(set(s))==6 and 2<=ev<=4 and 2<=low<=4 and consec<=2 and s[-1]-s[0]>=20 and max(buckets)<=3


def score(nums:Sequence[int],W:np.ndarray,P:np.ndarray)->float:
    s=sorted(nums); return sum(W[n] for n in s)+.75*sum(P[a,b] for a,b in itertools.combinations(s,2))+.08*((s[-1]-s[0])/39)


def pick(weights:np.ndarray,k:int,rng:np.random.Generator)->list[int]:
    p=np.clip(weights[1:],1e-12,None); p=p/p.sum(); return sorted(int(x) for x in rng.choice(np.arange(1,len(weights)),k,replace=False,p=p))


def panels(draws:Sequence[Draw],count:int,seed:int | None,half:int,candidates:int,max_overlap:int)->list[list[int]]:
    rng=np.random.default_rng(seed); recent=list(draws[-220:]); W,P=stats(recent,half)
    cold=np.zeros_like(W); cold[1:]=1/np.clip(W[1:],1e-9,None); cold[1:]/=cold[1:].sum()
    pool={}
    for mode in (W,cold):
        for _ in range(max(700,candidates//2)):
            c=pick(mode,6,rng)
            if shape(c): pool[tuple(c)]=max(pool.get(tuple(c),-1e9),score(c,W,P))
    ranked=sorted(pool.items(),key=lambda x:x[1],reverse=True); out=[]
    for c,_ in ranked:
        if all(len(set(c)&set(p))<=max_overlap for p in out): out.append(list(c))
        if len(out)>=count: break
    while len(out)<count:
        c=sorted(int(x) for x in rng.choice(np.arange(1,41),6,replace=False))
        if shape(c) and all(len(set(c)&set(p))<=min(5,max_overlap+1) for p in out): out.append(c)
    return out


def extras(draws:Sequence[Draw],count:int):
    mw=extra_weights(draws[-160:],"mas",12,40); sw=extra_weights(draws[-160:],"super_mas",15,40)
    mr=[int(x) for x in np.argsort(mw[1:])[::-1]+1]; sr=[int(x) for x in np.argsort(sw[1:])[::-1]+1]
    return [(mr[i%len(mr)],sr[(i*2)%len(sr)]) for i in range(count)]


def main():
    ap=argparse.ArgumentParser(description="Predictor heurístico Loto LEIDSA 6/40")
    ap.add_argument("--csv",default="loto_historico.csv"); ap.add_argument("--panels",type=int,default=8)
    ap.add_argument("--seed",type=int,default=None); ap.add_argument("--half-life",type=int,default=60)
    ap.add_argument("--candidates",type=int,default=4000); ap.add_argument("--max-overlap",type=int,default=4)
    args=ap.parse_args(); draws=load_csv(args.csv)
    print(f"Histórico válido Loto: {len(draws)} sorteos")
    if draws:
        d=draws[-1]; print(f"Último: {d.fecha} -> {list(d.nums)} | Más={d.mas} | Súper Más={d.super_mas}")
    ps=panels(draws,max(1,args.panels),args.seed,max(1,args.half_life),max(1500,args.candidates),max(2,min(5,args.max_overlap)))
    ex=extras(draws,len(ps)); print("\nJugadas sugeridas (heurísticas; no cambian las probabilidades reales):")
    for i,(nums,(mas,sup)) in enumerate(zip(ps,ex),1):
        ev=sum(n%2==0 for n in nums); print(f"{i:02d}. {nums} | Más={mas:02d} | Súper Más={sup:02d} | pares={ev} impares={6-ev}")

if __name__=="__main__": main()
