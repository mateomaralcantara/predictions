# actualizar_y_predecir_hoy.py
# Orquestador Loto Pool:
# 1) Actualiza lotto_pool_historial.csv usando lottopool_change_watcher.py
# 2) Genera 8 predicciones para hoy usando el predictor del sistema
# 3) Por defecto excluye la fila de hoy del predictor para evitar "trampa estadística"

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


BASE_DIR = Path(__file__).resolve().parent

DEFAULT_CSV = BASE_DIR / "lotto_pool_historial.csv"
DEFAULT_WATCHER = BASE_DIR / "lottopool_change_watcher.py"

PREDICTOR_8 = BASE_DIR / "lottopool_predictor_8_patched.py"
PREDICTOR_10 = BASE_DIR / "lottopool_predictor_10.py"
PREDICTOR_10_ALT = BASE_DIR / "lottopool_predictor_10(1).py"

DEFAULT_OUTPUT = BASE_DIR / "predicciones_8_hoy.csv"
TMP_CSV_SIN_HOY = BASE_DIR / "_tmp_lotto_pool_historial_sin_hoy.csv"
TMP_PREDICCIONES_20 = BASE_DIR / "_tmp_lottopool_predicciones_20.csv"

DEFAULT_LOG = BASE_DIR / "lottopool_watcher.log"
DEFAULT_STATE = BASE_DIR / "lottopool_watcher_state.json"
DEFAULT_LOCK = BASE_DIR / "lottopool_watcher.lock"

RD_TZ_NAME = "America/Santo_Domingo"


def ahora_rd():
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(RD_TZ_NAME))
        except Exception:
            pass

    return datetime.now()


def normalizar_fecha(valor):
    texto = str(valor).strip()

    formatos = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]

    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt).date().isoformat()
        except ValueError:
            continue

    return texto


def ejecutar(comando, cwd):
    print("")
    print("Ejecutando:")
    print(" ".join(str(x) for x in comando))
    print("")

    resultado = subprocess.run(
        comando,
        cwd=str(cwd),
        text=True,
        capture_output=False,
    )

    if resultado.returncode != 0:
        raise RuntimeError(f"El comando falló con código {resultado.returncode}.")


def verificar_archivo(path, nombre):
    if not Path(path).exists():
        raise FileNotFoundError(f"No encontré {nombre}: {path}")


def actualizar_csv(args):
    verificar_archivo(args.watcher, "el watcher")
    verificar_archivo(args.csv, "el CSV histórico")

    comando = [
        sys.executable,
        str(args.watcher),
        "--csv",
        str(args.csv),
        "--log",
        str(args.log),
        "--state",
        str(args.state),
        "--lock",
        str(args.lock),
        "--watch-days",
        str(args.watch_days),
        "--delay",
        str(args.delay),
        "--once",
    ]

    if args.verbose:
        comando.append("--verbose")

    if args.allow_global_fallback:
        comando.append("--allow-global-fallback")

    print("========================================")
    print("PASO 1: ACTUALIZANDO CSV")
    print("========================================")

    ejecutar(comando, BASE_DIR)

    if Path(args.state).exists():
        try:
            data = json.loads(Path(args.state).read_text(encoding="utf-8"))
            print("")
            print("Estado del watcher:")
            print(f"- Última ejecución: {data.get('last_run_at')}")
            print(f"- Fechas vigiladas: {data.get('watched_dates')}")
            print(f"- Cambió CSV: {data.get('changed')}")
            print(f"- Agregados: {data.get('added')}")
            print(f"- Actualizados: {data.get('updated')}")
            print(f"- Sin cambio: {data.get('unchanged')}")
            print(f"- Errores: {data.get('errors')}")
        except Exception:
            print("No pude leer el state JSON, pero el watcher terminó.")


def crear_csv_sin_hoy(csv_entrada, csv_salida):
    hoy = ahora_rd().date().isoformat()

    with open(csv_entrada, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        if not fieldnames:
            raise ValueError("El CSV histórico no tiene encabezados.")

        if "fecha" not in fieldnames:
            raise ValueError("El CSV histórico debe tener una columna llamada 'fecha'.")

        rows = list(reader)

    total_antes = len(rows)

    rows_filtradas = [
        row for row in rows
        if normalizar_fecha(row.get("fecha", "")) != hoy
    ]

    total_despues = len(rows_filtradas)
    excluidas = total_antes - total_despues

    with open(csv_salida, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_filtradas)

    print("")
    print("CSV temporal para predicción:")
    print(f"- Archivo: {csv_salida}")
    print(f"- Filas antes: {total_antes}")
    print(f"- Filas después: {total_despues}")
    print(f"- Filas de hoy excluidas: {excluidas}")

    return csv_salida


def buscar_predictor(predictor_manual=None):
    if predictor_manual:
        predictor_manual = Path(predictor_manual).resolve()
        verificar_archivo(predictor_manual, "el predictor indicado manualmente")

        if "8" in predictor_manual.name:
            return predictor_manual, "predictor_8"

        return predictor_manual, "predictor_10"

    if PREDICTOR_8.exists():
        return PREDICTOR_8, "predictor_8"

    if PREDICTOR_10.exists():
        return PREDICTOR_10, "predictor_10"

    if PREDICTOR_10_ALT.exists():
        return PREDICTOR_10_ALT, "predictor_10"

    raise FileNotFoundError(
        "No encontré ningún predictor válido. Debe existir uno de estos:\n"
        "- lottopool_predictor_8_patched.py\n"
        "- lottopool_predictor_10.py\n"
        "- lottopool_predictor_10(1).py"
    )


def generar_con_predictor_8(predictor, csv_usado, salida, args):
    comando = [
        sys.executable,
        str(predictor),
        "--csv",
        str(csv_usado),
        "--panels",
        "8",
        "--half-life",
        str(args.half_life),
        "--recent-window",
        str(args.recent_window),
        "--candidate-pool",
        str(args.candidate_pool),
        "--max-consec",
        str(args.max_consec),
        "--max-overlap",
        str(args.max_overlap_8),
        "--export",
        str(salida),
    ]

    if args.seed is not None:
        comando.extend(["--seed", str(args.seed)])

    ejecutar(comando, BASE_DIR)


def generar_con_predictor_10(predictor, csv_usado, salida, args):
    comando = [
        sys.executable,
        str(predictor),
        "--csv",
        str(csv_usado),
        "--half-life",
        str(args.half_life),
        "--recent-window",
        str(args.recent_window_10),
        "--max-consec",
        str(args.max_consec),
        "--max-overlap",
        str(args.max_overlap_10),
        "--export",
        str(TMP_PREDICCIONES_20),
    ]

    if args.seed is not None:
        comando.extend(["--seed", str(args.seed)])

    ejecutar(comando, BASE_DIR)

    with open(TMP_PREDICCIONES_20, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        if not fieldnames:
            raise ValueError("El predictor 10/20 no generó encabezados válidos.")

        rows = list(reader)

    rows_8 = rows[:8]

    with open(salida, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_8)

    print("")
    print(f"Se tomaron las primeras 8 jugadas desde: {TMP_PREDICCIONES_20}")


def generar_predicciones(args):
    print("")
    print("========================================")
    print("PASO 2: GENERANDO 8 PREDICCIONES")
    print("========================================")

    predictor, tipo = buscar_predictor(args.predictor)

    print(f"Predictor detectado: {predictor.name}")

    if args.usar_hoy:
        csv_usado = Path(args.csv)
        print("Modo predictor: usando historial completo, incluyendo hoy si existe.")
    else:
        csv_usado = crear_csv_sin_hoy(Path(args.csv), TMP_CSV_SIN_HOY)
        print("Modo predictor: excluyendo hoy del historial.")

    salida = Path(args.output).resolve()

    if tipo == "predictor_8":
        generar_con_predictor_8(predictor, csv_usado, salida, args)
    else:
        generar_con_predictor_10(predictor, csv_usado, salida, args)

    imprimir_predicciones(salida)

    return salida


def imprimir_predicciones(path):
    verificar_archivo(path, "el archivo de predicciones")

    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print("")
    print("========================================")
    print("8 PREDICCIONES DE HOY")
    print("========================================")

    for idx, row in enumerate(rows[:8], start=1):
        nums = []

        for col in ["n1", "n2", "n3", "n4", "n5"]:
            valor = row.get(col)
            if valor is not None and str(valor).strip() != "":
                try:
                    nums.append(int(float(valor)))
                except ValueError:
                    pass

        if not nums:
            continue

        pares = sum(1 for n in nums if n % 2 == 0)
        impares = len(nums) - pares
        suma = sum(nums)
        jugada = " - ".join(str(n) for n in nums)

        extra = []

        if row.get("perfil"):
            extra.append(f"perfil={row.get('perfil')}")

        if row.get("score"):
            extra.append(f"score={row.get('score')}")

        extra_txt = ""
        if extra:
            extra_txt = " | " + " | ".join(extra)

        print(f"{idx:02d}. {jugada} | suma={suma} | pares={pares} | impares={impares}{extra_txt}")

    print("========================================")
    print(f"Archivo generado: {path}")


def ciclo(args):
    actualizar_csv(args)
    salida = generar_predicciones(args)
    print("")
    print("Proceso terminado correctamente.")
    print(f"Predicciones listas en: {salida}")


def main():
    parser = argparse.ArgumentParser(
        description="Actualiza el CSV de Loto Pool y luego genera 8 predicciones de hoy."
    )

    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV),
        help="Ruta del CSV histórico principal.",
    )

    parser.add_argument(
        "--watcher",
        default=str(DEFAULT_WATCHER),
        help="Ruta del script lottopool_change_watcher.py.",
    )

    parser.add_argument(
        "--predictor",
        default=None,
        help="Ruta manual del predictor. Si no se indica, detecta automáticamente.",
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Archivo CSV final con las 8 predicciones.",
    )

    parser.add_argument(
        "--log",
        default=str(DEFAULT_LOG),
        help="Archivo log del watcher.",
    )

    parser.add_argument(
        "--state",
        default=str(DEFAULT_STATE),
        help="Archivo JSON de estado del watcher.",
    )

    parser.add_argument(
        "--lock",
        default=str(DEFAULT_LOCK),
        help="Archivo lock del watcher.",
    )

    parser.add_argument(
        "--watch-days",
        type=int,
        default=3,
        help="Cantidad de días recientes a revisar. Recomendado: 2 o 3.",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Pausa entre fechas consultadas por el watcher.",
    )

    parser.add_argument(
        "--allow-global-fallback",
        action="store_true",
        help="Permite fallback global del watcher. Úsalo solo si sabes lo que haces.",
    )

    parser.add_argument(
        "--usar-hoy",
        action="store_true",
        help="Incluye la fila de hoy en el predictor si ya existe. No recomendado antes de predecir.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semilla para repetir las mismas jugadas.",
    )

    parser.add_argument(
        "--half-life",
        type=int,
        default=180,
        help="Peso de recencia.",
    )

    parser.add_argument(
        "--recent-window",
        type=int,
        default=180,
        help="Ventana reciente para predictor de 8.",
    )

    parser.add_argument(
        "--recent-window-10",
        type=int,
        default=400,
        help="Ventana reciente para predictor de 10/20.",
    )

    parser.add_argument(
        "--candidate-pool",
        type=int,
        default=12000,
        help="Cantidad de candidatos para predictor de 8.",
    )

    parser.add_argument(
        "--max-consec",
        type=int,
        default=2,
        help="Máximo de números consecutivos permitidos.",
    )

    parser.add_argument(
        "--max-overlap-8",
        type=int,
        default=3,
        help="Solapamiento máximo entre jugadas para predictor de 8.",
    )

    parser.add_argument(
        "--max-overlap-10",
        type=int,
        default=2,
        help="Solapamiento máximo entre jugadas para predictor de 10/20.",
    )

    parser.add_argument(
        "--loop",
        action="store_true",
        help="Corre en ciclo: actualiza CSV y genera predicciones cada intervalo.",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Segundos entre ciclos cuando usas --loop.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Muestra más detalles del watcher.",
    )

    args = parser.parse_args()

    args.csv = Path(args.csv).resolve()
    args.watcher = Path(args.watcher).resolve()
    args.log = Path(args.log).resolve()
    args.state = Path(args.state).resolve()
    args.lock = Path(args.lock).resolve()
    args.output = Path(args.output).resolve()

    if args.loop:
        print("Modo continuo activado. Ctrl+C para detener.")
        while True:
            try:
                ciclo(args)
            except KeyboardInterrupt:
                print("")
                print("Proceso detenido por el usuario.")
                break
            except Exception as e:
                print("")
                print(f"ERROR: {e}")

            print("")
            print(f"Próximo ciclo en {args.interval} segundos...")
            time.sleep(args.interval)
    else:
        ciclo(args)


if __name__ == "__main__":
    main()