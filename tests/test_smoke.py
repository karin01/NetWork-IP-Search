"""스모크 테스트: 헬스·설정 API·토큰 미설정 시 기존 동작."""

import os
import sys

import pytest

# WHY: 프로젝트 루트에서 app import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client(monkeypatch):
    """토큰 없이 깨끗한 환경."""
    monkeypatch.delenv("NETWORK_IP_SEARCH_TOKEN", raising=False)
    import importlib

    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("ok") is True
    assert j.get("service") == "network-ip-search"


def test_nwip_whoami_ok(client):
    r = client.get("/api/nwip-whoami")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("ok") is True
    assert j.get("service") == "network-ip-search"
    assert "build_tag" in j


def test_build_info_aliases_ok(client):
    for path in ("/api/build-info", "/build-info"):
        r = client.get(path)
        assert r.status_code == 200, path
        j = r.get_json()
        assert j.get("ok") is True
        assert "build_tag" in j


def test_settings_get_ok(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("ok") is True
    assert "inventory_path" in j.get("data", {})


def test_dashboard_summary_ok(client):
    r = client.get("/api/dashboard-summary")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("ok") is True
    assert "build_tag" in j


def test_token_required_when_set(monkeypatch):
    monkeypatch.setenv("NETWORK_IP_SEARCH_TOKEN", "secret-test-token")
    import importlib

    import app as app_module

    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        r = c.get("/api/scan")
        assert r.status_code == 401
        r2 = c.get("/api/scan", headers={"X-NetWork-IP-Token": "secret-test-token"})
        assert r2.status_code in (200, 403, 500)  # 스캔은 환경에 따라 403/500 가능


def test_history_snapshots_list_ok(client):
    r = client.get("/api/history/snapshots?limit=3")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("ok") is True
    assert isinstance(j.get("data"), list)


def test_history_diff_requires_from_id(client):
    r = client.get("/api/history/diff")
    assert r.status_code == 400
    j = r.get_json()
    assert j.get("ok") is False
