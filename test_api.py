from pathlib import Path


def payload():
    return {
        "event_name": "Python Bootcamp 2026",
        "issued_date": "2026-10-07",
        "recipients": [
            {"name": "Alice Sharma", "email": "alice@example.com"},
            {"name": "Bob Kumar", "email": "bob@example.com"},
        ],
    }


def test_create_generation_job(client):
    response = client.post("/jobs", json=payload())
    assert response.status_code == 202
    body = response.json()
    assert body["total"] == 2
    assert body["id"] > 0


def test_input_validation(client):
    bad = payload()
    bad["recipients"][0]["name"] = ""
    response = client.post("/jobs", json=bad)
    assert response.status_code == 422


def test_certificate_generation_and_retrieval(client):
    response = client.post("/jobs", json=payload())
    job = response.json()
    assert job["status"] in {"pending", "processing", "completed"}

    refreshed = client.get(f"/jobs/{job['id']}").json()
    assert refreshed["status"] == "completed"
    recipient_id = refreshed["recipients"][0]["id"]

    certificate = client.get(f"/certificates/{recipient_id}")
    assert certificate.status_code == 200
    assert certificate.headers["content-type"] == "application/pdf"
    assert certificate.content.startswith(b"%PDF")


def test_job_status_progress(client):
    response = client.post("/jobs", json=payload())
    job_id = response.json()["id"]
    status = client.get(f"/jobs/{job_id}").json()
    assert status["progress_percent"] == 100.0
    assert status["successful"] == 2
    assert status["failed"] == 0


def test_individual_certificate_failure_does_not_stop_other_certificates(client, monkeypatch):
    from app import main

    real_generator = main.generate_certificate

    def failing_generator(**kwargs):
        if kwargs["recipient_name"] == "Bob Kumar":
            raise RuntimeError("simulated rendering failure")
        return real_generator(**kwargs)

    monkeypatch.setattr(main, "generate_certificate", failing_generator)
    response = client.post("/jobs", json=payload())
    assert response.status_code == 202

    job = client.get(f"/jobs/{response.json()['id']}").json()
    assert job["status"] == "completed_with_errors"
    assert job["successful"] == 1
    assert job["failed"] == 1

    recipients = {r["name"]: r for r in job["recipients"]}
    assert recipients["Alice Sharma"]["status"] == "success"
    assert recipients["Bob Kumar"]["status"] == "failed"
    assert "simulated rendering failure" in recipients["Bob Kumar"]["error_message"]
