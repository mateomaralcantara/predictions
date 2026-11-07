from __future__ import annotations

import argparse
import csv
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DEFAULT_CSV = "loto_historico.csv"
MIN_NUMBER, MAX_NUMBER, DRAW_SIZE = 1, 40, 6
MAS_MIN, MAS_MAX = 1, 12
SUPER_MIN, SUPER_MAX = 1, 15
DOW = ["L", "M", "X", "J", "V", "S", "D"]
MONTHS = {1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"}
URL = "https://labanca.do/loterias/leidsa/loto/{:%Y-%m-%d}/"
LATEST_URL = "https://labanca.do/loterias/leidsa/loto/"
HEADERS = {"User-Agent":"Mozilla/5.0 Chrome/124.0","Accept-Language":"es-ES,es;q=0.9"}

try:
    from zoneinfo import ZoneInfo
    RD_TZ = ZoneInfo("America/Santo_Domingo")
except Exception:
    RD_TZ = None


def now_rd() -> datetime:
    return datetime.now(RD_TZ) if RD_TZ else datetime.now()


def parse_date(raw: str) -> date:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except Exception:
            pass
    raise ValueError(f"Fecha inválida: {raw}")


def valid(nums: list[int], mas: int, super_mas: int) -> bool:
    return len(nums)==6 and len(set(nums))==6 and all(1<=n<=40 for n in nums) and 1<=mas<=12 and 1<=super_mas<=15


def ensure_csv(path: Path) -> None:
    if path.exists() and path.stat().st_size:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["fecha","num_1","num_2","num_3","num_4","num_5","num_6","mas","super_mas"])


def read_map(path: Path) -> dict[date, tuple[list[int], int, int]]:
    out: dict[date, tuple[list[int], int, int]] = {}
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for i,row in enumerate(csv.reader(f)):
            if not row or (i==0 and row[0].lower() in {"fecha","date"}):
                continue
            try:
                d=parse_date(row[0]); vals=[int(x.strip()) for x in row[1:9]]
            except Exception:
                continue
            nums,mas,super_mas=vals[:6],vals[6],vals[7]
            if valid(nums,mas,super_mas): out[d]=(nums,mas,super_mas)
    return dict(sorted(out.items()))


def write_map(path: Path, rows: dict[date, tuple[list[int], int, int]], backup: bool=False) -> None:
    if backup and path.exists():
        stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        path.with_suffix(path.suffix+f".bak_{stamp}").write_bytes(path.read_bytes())
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w=csv.writer(f); w.writerow(["fecha","num_1","num_2","num_3","num_4","num_5","num_6","mas","super_mas"])
        for d,(nums,mas,sup) in sorted(rows.items()): w.writerow([d.isoformat(),*nums,mas,sup])
    tmp.replace(path)


def extract_date(soup: BeautifulSoup) -> date | None:
    text=" ".join(soup.get_text(" ",strip=True).split()).lower()
    names={v:k for k,v in MONTHS.items()}
    m=re.search(r"\b(\d{1,2}) de (enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre) de (20\d{2})\b",text)
    if not m: return None
    try: return date(int(m.group(3)),names[m.group(2)],int(m.group(1)))
    except Exception: return None


def extract_result(soup: BeautifulSoup, d: date) -> tuple[list[int], int, int] | None:
    text=" ".join(soup.get_text(" ",strip=True).split())
    phrase=re.escape(f"{d.day} de {MONTHS[d.month]} de {d.year}")
    patterns=[
        rf"Loto\s+Leidsa.{{0,180}}?{phrase}.{{0,160}}?fue\s+((?:\d{{1,2}}[-\s]+){{7}}\d{{1,2}})",
        rf"{phrase}.{{0,220}}?((?:\b\d{{1,2}}\b\s+){{7}}\b\d{{1,2}}\b)",
    ]
    for pat in patterns:
        m=re.search(pat,text,re.I|re.S)
        if not m: continue
        vals=[int(x) for x in re.findall(r"\b\d{1,2}\b",m.group(1))]
        if len(vals)==8 and valid(vals[:6],vals[6],vals[7]): return vals[:6],vals[6],vals[7]
    return None


def fetch(session: requests.Session, d: date, timeout: float, attempts: int) -> tuple[list[int], int, int] | None:
    url=URL.format(datetime.combine(d,datetime.min.time()))
    for i in range(attempts):
        try:
            r=session.get(url,timeout=timeout)
            if r.status_code==404: return None
            r.raise_for_status(); soup=BeautifulSoup(r.text,"html.parser")
            page_d=extract_date(soup)
            if page_d and page_d!=d: return None
            return extract_result(soup,d)
        except requests.RequestException:
            if i+1<attempts: time.sleep(0.6*(i+1))
    return None


def fetch_latest(session: requests.Session, timeout: float, attempts: int):
    for i in range(attempts):
        try:
            r=session.get(LATEST_URL,timeout=timeout); r.raise_for_status(); soup=BeautifulSoup(r.text,"html.parser")
            d=extract_date(soup)
            if d:
                result=extract_result(soup,d)
                if result: return d,result
        except requests.RequestException:
            if i+1<attempts: time.sleep(0.6*(i+1))
    return None


def target_dates(start: date, end: date, existing: set[date], include_today_early: bool=False) -> list[date]:
    out=[]; d=start; now=now_rd()
    while d<=end:
        if DOW[d.weekday()] in {"X","S"} and d not in existing:
            if d==now.date() and not include_today_early and (now.hour,now.minute)<(20,55): pass
            else: out.append(d)
        d+=timedelta(days=1)
    return out


def main() -> None:
    ap=argparse.ArgumentParser(description="Loto LEIDSA: 6/40 + Más 1/12 + Súper Más 1/15")
    ap.add_argument("--csv",default=DEFAULT_CSV); ap.add_argument("--probe",nargs="*")
    ap.add_argument("--sync-missing",action="store_true"); ap.add_argument("--append-latest",action="store_true")
    ap.add_argument("--start",default=None); ap.add_argument("--backup-csv",action="store_true")
    ap.add_argument("--repair-csv",action="store_true"); ap.add_argument("--watch-latest",action="store_true")
    ap.add_argument("--poll-seconds",type=float,default=90); ap.add_argument("--max-cycles",type=int,default=0)
    ap.add_argument("--timeout-s",type=float,default=12); ap.add_argument("--attempts",type=int,default=2)
    ap.add_argument("--delay",type=float,default=.3); ap.add_argument("--include-early-today",action="store_true")
    args=ap.parse_args(); path=Path(args.csv); ensure_csv(path); rows=read_map(path)

    if args.repair_csv:
        write_map(path,rows,args.backup_csv); print(f"🧹 Loto CSV reparado: {len(rows)} sorteos válidos")

    session=requests.Session(); session.headers.update(HEADERS)
    if args.probe:
        for raw in args.probe:
            d=parse_date(raw); res=fetch(session,d,args.timeout_s,max(1,args.attempts))
            print(f"Probe {d} ({DOW[d.weekday()]}): "+(f"OK LB -> {res[0]} | Más={res[1]} | Súper Más={res[2]}" if res else "—"))

    if args.watch_latest:
        cycles=0
        print(f"👀 Vigilando Loto cada {max(15,args.poll_seconds):.0f}s. Ctrl+C para salir.")
        while True:
            cycles+=1; latest=fetch_latest(session,args.timeout_s,max(1,args.attempts))
            if latest:
                d,(nums,mas,sup)=latest; old=rows.get(d); rows[d]=(nums,mas,sup)
                if old!=(nums,mas,sup): write_map(path,rows,args.backup_csv); print(f"✅ {d}: {nums} | Más={mas} | Súper Más={sup}")
                else: print(f"… sin novedad ({d})")
            else: print("… resultado reciente no disponible")
            if args.max_cycles>0 and cycles>=args.max_cycles: break
            time.sleep(max(15,args.poll_seconds))

    if not any((args.sync_missing,args.append_latest,args.probe,args.watch_latest,args.repair_csv)):
        args.append_latest=True

    if args.sync_missing or args.append_latest:
        dates=sorted(rows); today=now_rd().date()
        if args.sync_missing: start=parse_date(args.start) if args.start else (dates[0] if dates else date(2026,1,1))
        else: start=(dates[-1]+timedelta(days=1)) if dates else (parse_date(args.start) if args.start else date(2026,1,1))
        targets=target_dates(start,today,set(rows),args.include_early_today)
        print(f"🧩 Faltantes Loto: {len(targets)} (de {start} a {today})")
        ins=upd=miss=0
        for d in targets:
            print(f"🔍 {d} ({DOW[d.weekday()]}) ... ",end="",flush=True); res=fetch(session,d,args.timeout_s,max(1,args.attempts))
            if res:
                old=rows.get(d); rows[d]=res; ins+=old is None; upd+=old is not None and old!=res
                print(f"✅ (LB) {res[0]} + {res[1]}/{res[2]}")
            else: miss+=1; print("—")
            time.sleep(args.delay)
        if ins or upd: write_map(path,rows,args.backup_csv)
        print(f"🎉 Loto listo. CSV: {path} | Insertados: {ins} | Actualizados: {upd} | Sin resultado: {miss}")


if __name__=="__main__": main()
