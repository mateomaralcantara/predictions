def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["estado"] == "ok"
    assert body["fuente_datos"] == "csv"
    assert body["sorteos"] == 8
    assert body["sorteos_descartados"] == 1
    assert body["openai"] is False and body["pagos"] is False


def test_loterias(client):
    nombres = [x["nombre"] for x in client.get("/api/loterias").json()]
    assert nombres[0] == "Lotería Nacional"


def test_estadisticas(client):
    assert client.get("/api/estadisticas/top", params={"limite": 1}).json() == [{"numero": 10, "apariciones": 6}]
    assert client.get("/api/estadisticas/top", params={"loteria": "leidsa"}).json()[0]["numero"] == 11
    assert len(client.get("/api/estadisticas/ultimos", params={"limite": 2}).json()) == 2
    assert client.get("/api/estadisticas/combinaciones").status_code == 200
    assert client.get("/api/estadisticas/atrasados", params={"limite": 5}).status_code == 200
    resumen = client.get("/api/estadisticas/resumen", params={"loteria": "nacional"}).json()
    assert resumen["total_sorteos"] == 3


def test_numero_valida_rango(client):
    assert client.get("/api/estadisticas/numero/10").json()["total"] == 6
    assert client.get("/api/estadisticas/numero/100").status_code == 422
    assert client.get("/api/estadisticas/top", params={"limite": 0}).status_code == 422


def test_endpoints_legacy(client):
    assert client.get("/api/numeros-mas-salidores").json()[0] == {"numero": 10, "apariciones": 3}
    fechas = client.get("/api/fechas-numero", params={"numero": 10}).json()["fechas"]
    assert [f["fecha"] for f in fechas] == sorted(f["fecha"] for f in fechas)


def test_chat_rest_y_websocket(client):
    r = client.post("/api/chat", json={"pregunta": "top 1 números de la nacional"})
    assert r.status_code == 200 and r.json()["intencion"] == "top"
    assert client.post("/api/chat", json={"pregunta": ""}).status_code == 422
    assert client.post("/api/chat", json={"pregunta": "x" * 501}).status_code == 422
    assert "respuesta" in client.get("/pregunta", params={"texto": "hola"}).json()
    with client.websocket_connect("/ws") as ws:
        ws.send_text("últimos 2 resultados")
        assert "Últimos resultados" in ws.receive_text()
        ws.send_text("x" * 600)
        assert "muy larga" in ws.receive_text()


def test_predicciones(client):
    juegos = {j["id"] for j in client.get("/api/predicciones").json()}
    assert juegos == {"loto", "superkino"}

    loto = client.get("/api/predicciones/loto", params={"jugadas": 2}).json()
    assert len(loto["jugadas"]) == 2 and loto["limitado"] is False
    for j in loto["jugadas"]:
        assert len(set(j["numeros"])) == 6 and all(1 <= n <= 40 for n in j["numeros"])
        assert 1 <= j["mas"] <= 12 and 1 <= j["super_mas"] <= 15
    # Determinista mientras no cambie el último sorteo.
    assert client.get("/api/predicciones/loto", params={"jugadas": 2}).json() == loto

    sk = client.get("/api/predicciones/superkino", params={"jugadas": 2}).json()
    assert len(sk["jugadas"]) == 2
    for j in sk["jugadas"]:
        assert len(set(j["numeros"])) == 10 and all(1 <= n <= 84 for n in j["numeros"])

    assert client.get("/api/predicciones/quiniela").status_code == 422
    assert client.get("/api/predicciones/loto", params={"jugadas": 11}).status_code == 422


def test_prediccion_sin_historico_responde_503(env, client, tmp_path):
    env(LOTO_CSV=str(tmp_path / "no-existe.csv"))
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as c:
        assert c.get("/api/predicciones/loto").status_code == 503


def test_admin_oculto_sin_token(client):
    assert client.post("/api/admin/scraping").status_code == 404
    assert client.post("/api/admin/recargar").status_code == 404


def test_admin_requiere_token(env):
    env(ADMIN_TOKEN="secreto")
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as c:
        assert c.post("/api/admin/recargar").status_code == 401
        assert c.post("/api/admin/recargar", headers={"X-Admin-Token": "otro"}).status_code == 401
        r = c.post("/api/admin/recargar", headers={"X-Admin-Token": "secreto"})
        assert r.status_code == 200 and r.json()["sorteos"] == 8


def test_cors(client):
    r = client.options(
        "/api/health",
        headers={"Origin": "http://localhost:5174", "Access-Control-Request-Method": "GET"},
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5174"
    r = client.options(
        "/api/health",
        headers={"Origin": "https://malicioso.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in r.headers


def test_cabeceras_de_seguridad(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert (
        client.post("/api/auth/login", json={"email": "a@b.co", "password": "x"}).headers["cache-control"] == "no-store"
    )


def test_produccion_exige_secret_key(monkeypatch):
    import pytest

    from app.config import get_settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "corta")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        get_settings()
    monkeypatch.setenv("SECRET_KEY", "")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        get_settings()
    get_settings.cache_clear()


def test_normalizar_url_postgres():
    from app.db import normalizar_url

    assert normalizar_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalizar_url("postgresql://u@h/db") == "postgresql+psycopg://u@h/db"
    assert normalizar_url("postgresql+psycopg2://u@h/db") == "postgresql+psycopg://u@h/db"
    assert normalizar_url("sqlite:///x.db") == "sqlite:///x.db"
