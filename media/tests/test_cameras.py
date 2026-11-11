from app import db


def create_camera(client, path="lzzz001", name="前门", **overrides):
    data = {
        "path": path,
        "display_name": name,
        "location": "A 区",
        "description": "测试",
        "enabled": "on",
        "push_username": "zeaho",
        "push_password": "secret-pass",
    }
    data.update(overrides)
    return client.post("/cameras", data=data, follow_redirects=True)


def test_create_and_list_camera(client):
    response = create_camera(client)
    assert response.status_code == 200
    assert "lzzz001" in response.text
    assert "前门" in response.text
    assert "zeaho:***@" in response.text
    assert 'data-hls-url="http://129.211.239.229:8888/lzzz001/"' in response.text
    assert 'data-webrtc-url="http://129.211.239.229:8889/lzzz001/"' in response.text
    assert 'data-copy="rtsp://zeaho:secret-pass@' in response.text


def test_invalid_path_rejected(client):
    response = client.post(
        "/cameras",
        data={"path": "bad path!", "display_name": "", "location": "", "description": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "路径只能包含" in response.text
    assert 'window.__tbOpenDialog = "add-dialog"' in response.text
    assert db.get_camera_by_path("bad path!") is None


def test_duplicate_path_rejected(client):
    create_camera(client)
    response = create_camera(client, name="重复")
    assert "该路径已存在" in response.text
    assert len(db.list_cameras()) == 1


def test_path_is_locked_and_push_merged(client):
    create_camera(client)
    camera = db.get_camera_by_path("lzzz001")
    assert camera is not None

    response = client.post(
        f"/cameras/{camera['id']}",
        data={
            "path": "changed",
            "display_name": "新名称",
            "location": "B 区",
            "description": "备注",
            "enabled": "on",
            "push_username": "user2",
            "push_password": "pass2",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    updated = db.get_camera(camera["id"])
    assert updated["path"] == "lzzz001"
    assert updated["display_name"] == "新名称"
    assert updated["push_username"] == "user2"
    assert updated["push_password"] == "pass2"
    assert "user2:***@" in response.text


def test_delete_camera(client):
    create_camera(client)
    camera = db.get_camera_by_path("lzzz001")
    response = client.post(f"/cameras/{camera['id']}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert db.get_camera(camera["id"]) is None


def test_camera_detail_api_returns_push_credentials(client):
    create_camera(client)
    camera = db.get_camera_by_path("lzzz001")
    response = client.get(f"/api/cameras/{camera['id']}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["path"] == "lzzz001"
    assert payload["push_username"] == "zeaho"
    assert payload["push_password"] == "secret-pass"
    assert client.get("/api/cameras/999999").status_code == 404


def test_old_routes_removed(client):
    for path in ("/streams", "/preview"):
        assert client.get(path).status_code == 404
    assert client.get("/cameras/new").status_code in (404, 405)
