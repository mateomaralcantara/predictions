# sacar_8_predicciones_hoy.py
# Genera 8 predicciones usando el predictor real del sistema.
# Por defecto excluye la fecha de hoy del historial para evitar "trampa estadística".

import argparse
import csv
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

CSV_HISTORIAL = BASE_DIR / "lotto_pool_historial.csv"
CSV_TEMP_SIN_HOY = BASE_DIR / "_tmp_lotto_pool_historial_sin_hoy.csv"

PREDICTOR_8 = BASE_DIR / "lottopool_predictor_8_patched.py"
PREDICTOR_10 = BASE_DIR / "lottopool_predictor_10.py"
PREDICTOR_10_ALT = BASE_DIR / "lottopool_predictor_10(1).py"

SALIDA_FINAL = BASE_DIR / "predicciones_8_hoy.csv"


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
            pass

    return texto


def crear_csv_sin_hoy(csv_entrada, csv_salida):
    if not csv_entrada.exists():
        raise FileNotFoundError(f"No existe el historial: {csv_entrada}")

    hoy = datetime.now().date().isoformat()

    df = pd.read_csv(csv_entrada)

    if "fecha" not in df.columns:
        raise ValueError("El CSV histórico debe tener una columna llamada 'fecha'.")

    df["fecha_normalizada"] = df["fecha"].apply(normalizar_fecha)

    filas_antes = len(df)
    df = df[df["fecha_normalizada"] != hoy].copy()
    filas_despues = len(df)

    df = df.drop(columns=["fecha_normalizada"])

    df.to_csv(csv_salida, index=False, encoding="utf-8")

    print(f"CSV temporal creado sin hoy: {csv_salida}")
    print(f"Filas antes: {filas_antes}")
    print(f"Filas después: {filas_despues}")
    print(f"Filas excluidas de hoy: {filas_antes - filas_despues}")


def buscar_predictor():
    if PREDICTOR_8.exists():
        return PREDICTOR_8, "predictor_8"

    if PREDICTOR_10.exists():
        return PREDICTOR_10, "predictor_10"

    if PREDICTOR_10_ALT.exists():
        return PREDICTOR_10_ALT, "predictor_10"

    raise FileNotFoundError(
        "No encontré ningún predictor válido. Debe existir uno de estos archivos:\n"
        "- lottopool_predictor_8_patched.py\n"
        "- lottopool_predictor_10.py\n"
        "- lottopool_predictor_10(1).py"
    )


def ejecutar_predictor_8(predictor, csv_usado, salida, seed=None):
    comando = [
        sys.executable,
        str(predictor),
        "--csv",
        str(csv_usado),
        "--panels",
        "8",
        "--export",
        str(salida),
    ]

    if seed is not None:
        comando.extend(["--seed", str(seed)])

    print("\nEjecutando predictor de 8 jugadas:")
    print(" ".join(comando))

    subprocess.run(comando, cwd=BASE_DIR, check=True)


def ejecutar_predictor_10_y_cortar_8(predictor, csv_usado, salida, seed=None):
    salida_20 = BASE_DIR / "_tmp_lottopool_predicciones_20.csv"

    comando = [
        sys.executable,
        str(predictor),
        "--csv",
        str(csv_usado),
        "--export",
        str(salida_20),
    ]

    if seed is not None:
        comando.extend(["--seed", str(seed)])

    print("\nEjecutando predictor del sistema y cortando las primeras 8:")
    print(" ".join(comando))

    subprocess.run(comando, cwd=BASE_DIR, check=True)

    df = pd.read_csv(salida_20)

    if df.empty:
        raise ValueError("El predictor no generó predicciones.")

    df_8 = df.head(8).copy()
    df_8.to_csv(salida, index=False, encoding="utf-8")

    print(f"\nArchivo completo temporal: {salida_20}")
    print(f"Archivo final con 8 predicciones: {salida}")


def mostrar_predicciones(salida):
    if not salida.exists():
        raise FileNotFoundError(f"No se generó el archivo de salida: {salida}")

    df = pd.read_csv(salida)

    print("\n========================================")
    print("8 PREDICCIONES PARA HOY")
    print("========================================")

    for _, row in df.iterrows():
        panel = int(row.get("panel", len(df)))

        nums = []
        for i in range(1, 6):
            col = f"n{i}"
            if col in row:
                nums.append(int(row[col]))

        if nums:
            suma = sum(nums)
            pares = sum(1 for n in nums if n % 2 == 0)
            impares = 5 - pares
            jugada = " - ".join(str(n) for n in nums)

            extra = ""
            if "perfil" in row:
                extra += f" | perfil={row['perfil']}"
            if "score" in row:
                extra += f" | score={row['score']}"

            print(f"{panel:02d}. {jugada} | suma={suma} | pares={pares} | impares={impares}{extra}")

    print("========================================")
    print(f"CSV generado: {salida}")


def main():
    parser = argparse.ArgumentParser(
        description="Saca 8 predicciones desde el predictor real del sistema Loto Pool."
    )

    parser.add_argument(
        "--usar-hoy",
        action="store_true",
        help="Incluye la fila de hoy si ya existe en el historial. No recomendado para predecir antes del sorteo.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semilla opcional para repetir exactamente las mismas jugadas.",
    )

    parser.add_argument(
        "--salida",
        default=str(SALIDA_FINAL),
        help="Ruta del CSV final de salida.",
    )

    args = parser.parse_args()

    salida = Path(args.salida).resolve()

    if args.usar_hoy:
        csv_usado = CSV_HISTORIAL
        print("Modo: usando historial completo, incluyendo hoy si existe.")
    else:
        csv_usado = CSV_TEMP_SIN_HOY
        print("Modo: excluyendo la fecha de hoy del historial.")
        crear_csv_sin_hoy(CSV_HISTORIAL, CSV_TEMP_SIN_HOY)

    predictor, tipo = buscar_predictor()

    print(f"\nPredictor detectado: {predictor.name}")

    if tipo == "predictor_8":
        ejecutar_predictor_8(predictor, csv_usado, salida, seed=args.seed)
    else:
        ejecutar_predictor_10_y_cortar_8(predictor, csv_usado, salida, seed=args.seed)

    mostrar_predicciones(salida)


if __name__ == "__main__":
    main()