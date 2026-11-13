"""Actualización automática: copias vivas, ciclo y endpoints."""

from __future__ import annotations

import subprocess
from datetime import date

from app import actualizador
from app.config import get_settings


def _csv(path, texto):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")
    return path


def test_combinar_une_base_y_viva_sin_duplicar(tmp_path):
    base = _csv(
        tmp_path / "base.csv", "id,fecha,loteria,primer,segundo,tercero\n1,2025-01-01,A,1,2,3\n2,2025-01-02,A,4,5,6\n"
    )
    viva = _csv(tmp_path / "vivo.csv", "fecha,loteria,primer,segundo,tercero\n2025-01-02,A,4,5,6\n2025-01-03,A,7,8,9\n")
    assert actualizador.combinar(base, viva, 2) == 1  # aporta solo 2025-01-01
    lineas = viva.read_text(encoding="utf-8").splitlines()
    assert lineas[0] == "fecha,loteria,primer,segundo,tercero"
    assert lineas[1:] == ["2025-01-01,A,1,2,3", "2025-01-02,A,4,5,6", "2025-01-03,A,7,8,9"]
    assert actualizador.combinar(base, viva, 2) == 0  # idempotente


def test_combinar_crea_la_copia_viva(tmp_path):
    base = _csv(tmp_path / "base.csv", "fecha,n1,n2\n2025-01-01,1,2\n")
    viva = tmp_path / "vivo" / "x.csv"
    actualizador.combinar(base, viva, 1)
    assert viva.read_text(encoding="utf-8").splitlines() == ["fecha,n1,n2", "2025-01-01,1,2"]


def test_rutas_vivas_solo_con_auto_actualizar(env):
    from app.config import VIVO_DIR

    env(AUTO_ACTUALIZAR="true", RESULTADOS_CSV="", LOTO_CSV="", SUPERKINO_CSV="", LOTOPOOL_CSV="")
    s = get_settings()
    assert s.loto_csv == VIVO_DIR / "loto" / "loto_historico.csv"
    assert s.csv_base["loto"].name == "loto_historico.csv" and s.csv_base["loto"] != s.loto_csv
    env(AUTO_ACTUALIZAR="false")
    s = get_settings()
    assert s.loto_csv == s.csv_base["loto"]


def test_comandos_cubren_todos_los_juegos(env, tmp_path):
    reciente = _csv(tmp_path / "r.csv", "fecha,loteria,primer,segundo,tercero\n2026-11-12,A,1,2,3\n")
    env(RESULTADOS_CSV=str(reciente))
    cmds = actualizador.comandos(get_settings(), hoy=date(2026, 11, 13))
    assert set(cmds) == {"tradicionales", "loto", "superkino", "lotopool"}
    t = cmds["tradicionales"]
    assert (
        "--completar" in t and t[t.index("--desde") + 1] == "2026-11-10" and t[t.index("--hasta") + 1] == "2026-11-13"
    )
    assert "--append-latest" in cmds["loto"] and "--append-latest" in cmds["superkino"]


def test_ciclo_sigue_aunque_un_juego_falle(monkeypatch):
    llamadas = []
    refrescos = []
    monkeypatch.setattr(actualizador, "_refrescar_caches", lambda: refrescos.append(1))

    def runner(cmd, **kw):
        llamadas.append(cmd[1])
        if "superkino" in cmd[1]:
            raise subprocess.TimeoutExpired(cmd, 900)
        code = 1 if "loto/sync" in cmd[1] else 0
        return subprocess.CompletedProcess(cmd, code, stdout="hecho: 3 nuevos\n", stderr="error de red\n")

    r = actualizador.ejecutar_ciclo(get_settings(), runner=runner)
    assert len(llamadas) == 4 and refrescos == [1]
    assert r["tradicionales"] == {"ok": True, "detalle": "hecho: 3 nuevos"}
    assert r["loto"] == {"ok": False, "detalle": "error de red"}
    assert r["superkino"]["ok"] is False and "TimeoutExpired" in r["superkino"]["detalle"]
    assert actualizador.estado["ultima"] and actualizador.estado["en_curso"] is False


def test_ciclo_no_se_solapa(monkeypatch):
    assert actualizador._lock.acquire(blocking=False)
    try:
        assert "omitido" in actualizador.ejecutar_ciclo(get_settings(), runner=lambda *a, **k: None)
    finally:
        actualizador._lock.release()


def test_health_y_admin_actualizar(env, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    env(ADMIN_TOKEN="secreto")
    monkeypatch.setattr(actualizador, "ejecutar_ciclo", lambda s: {"loto": {"ok": True, "detalle": "x"}})
    with TestClient(create_app()) as c:
        assert c.get("/api/health").json()["actualizacion"] == {"activa": False}
        assert c.post("/api/admin/actualizar").status_code == 401
        r = c.post("/api/admin/actualizar", headers={"X-Admin-Token": "secreto"})
        assert r.status_code == 200 and r.json()["loto"]["ok"] is True


def test_desde_recupera_dias_si_la_api_estuvo_apagada(tmp_path):
    reciente = _csv(tmp_path / "a.csv", "fecha,loteria,primer,segundo,tercero\n2026-11-12,A,1,2,3\n")
    antiguo = _csv(tmp_path / "b.csv", "id,fecha,loteria,primer,segundo,tercero\n9,2026-11-07,A,1,2,3\n")
    hoy = date(2026, 11, 13)
    assert actualizador._desde(reciente, hoy) == "2026-11-10"  # margen normal de 3 días
    assert actualizador._desde(antiguo, hoy) == "2026-11-08"  # retoma tras el último dato
    assert actualizador._desde(tmp_path / "no-existe.csv", hoy) == "2026-11-10"
    assert actualizador.ultima_fecha(antiguo) == date(2026, 11, 7)
