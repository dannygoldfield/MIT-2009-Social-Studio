from fastapi.testclient import TestClient

from mit2009_studio.server import create_app

HEADERS = {"X-Studio-Request": "1"}


def test_api_guards_and_validation(tmp_path):
    app = create_app(tmp_path / "data", start_worker=False)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/api/status").json()["duration"] == 15
        assert client.get("/api/status", headers={"Host": "evil.example"}).status_code == 403
        body = {"name": "Test", "author": "Talla"}
        assert client.post("/api/projects", json=body).status_code == 403
        assert (
            client.post(
                "/api/projects", json=body, headers={**HEADERS, "Origin": "https://elsewhere.example"}
            ).status_code
            == 403
        )
        assert client.post("/api/projects", json={**body, "duration": 20}, headers=HEADERS).status_code == 422
        response = client.post("/api/projects", json=body, headers=HEADERS)
        assert response.status_code == 201
        pid = response.json()["id"]
        assert client.get("/api/projects/" + pid).json()["project"]["author"] == "Talla"
        response = client.post(
            "/api/projects/" + pid + "/assets",
            headers=HEADERS,
            data={"role": "photo"},
            files={"file": ("../../bad.jpg", b"not an image", "image/jpeg")},
        )
        assert response.status_code == 400
        assert client.get("/api/projects/" + pid).json()["assets"] == []
        assert client.get("/api/candidates/missing/file/output").status_code == 400
