from pathlib import Path

import pytest

from app.services.files import UnsafePathError, WorkspaceService


def create_project(client):
    response = client.post("/projects", data={"name": "Demo", "description": "ทดสอบ"}, follow_redirects=False)
    assert response.status_code == 303
    return int(response.headers["location"].split("/")[-1])


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_project_creation(client):
    project_id = create_project(client)
    page = client.get(f"/projects/{project_id}")
    assert "Demo" in page.text and "ทดสอบ" in page.text


def test_approval_flow_requires_decision(client):
    project_id = create_project(client)
    response = client.post(f"/projects/{project_id}/commands", data={"instruction": "สร้าง readme"}, follow_redirects=False)
    command_url = response.headers["location"]
    target = Path("test-workspaces") / str(project_id) / "AI_PLAN.md"
    assert not target.exists()
    page = client.get(command_url)
    assert "pending approval" in page.text
    approved = client.post(f"{command_url}/decision", data={"decision": "approve"}, follow_redirects=False)
    assert approved.status_code == 303
    assert target.exists() and "สร้าง readme" in target.read_text(encoding="utf-8")
    target.unlink(); target.parent.rmdir()


def test_rejection_does_not_write(client):
    project_id = create_project(client)
    response = client.post(f"/projects/{project_id}/commands", data={"instruction": "Do work"}, follow_redirects=False)
    client.post(f"{response.headers['location']}/decision", data={"decision": "reject"})
    assert not (Path("test-workspaces") / str(project_id) / "AI_PLAN.md").exists()


def test_file_safety(tmp_path):
    service = WorkspaceService(tmp_path)
    for unsafe in ("../secret", "/etc/passwd", "folder/../../secret", "..\\secret"):
        with pytest.raises(UnsafePathError):
            service.safe_path(1, unsafe)
    service.write(1, "nested/file.txt", "safe")
    assert (tmp_path / "1/nested/file.txt").read_text() == "safe"
