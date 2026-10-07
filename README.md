# Bulk Certificate Generator

A FastAPI backend that accepts a bulk certificate generation request, processes recipients independently in the background, stores job progress in a relational database, and exposes generated PDF certificates through an API.

## Tech stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite (relational database; easy local setup)
- ReportLab for PDF generation
- Pytest + FastAPI TestClient

## Project structure

```text
bulk_certificate_generator/
├── app/
│   ├── certificate.py       # predefined PDF certificate template
│   ├── database.py          # SQLAlchemy engine/session
│   ├── main.py              # API + background processing
│   ├── models.py            # job/recipient database models
│   └── schemas.py           # request/response validation
├── storage/certificates/    # generated PDFs
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── requirements.txt
├── README.md
└── DESIGN.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload
```

API documentation is available at:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Run tests

```bash
pytest -q
```

The test suite covers job creation, request validation, PDF generation, progress/status reporting, isolated certificate failures, and certificate retrieval.

## Submit a certificate generation request

`POST /jobs`

Example:

```json
{
  "event_name": "Python Bootcamp 2026",
  "issued_date": "2026-10-07",
  "recipients": [
    {"name": "Alice Sharma", "email": "alice@example.com"},
    {"name": "Bob Kumar", "email": "bob@example.com"}
  ]
}
```

The endpoint returns HTTP `202 Accepted` and a job representation. The actual certificate work is performed as background processing.

## Check job status

`GET /jobs/{job_id}`

The response includes:

- overall status: `pending`, `processing`, `completed`, or `completed_with_errors`
- total recipients
- successful count
- failed count
- pending/processing counts
- progress percentage
- per-recipient status and error message
- certificate URL for successful recipients

Example successful result:

```json
{
  "id": 1,
  "status": "completed",
  "total": 2,
  "successful": 2,
  "failed": 0,
  "progress_percent": 100.0
}
```

## Retrieve a generated certificate

`GET /certificates/{recipient_id}`

The endpoint returns the generated PDF when that recipient has successfully completed generation. Before completion it returns HTTP `409`.

## Validation and failure handling

Request-level validation is handled by Pydantic. Each recipient is stored separately, and certificate rendering happens independently. If one recipient fails during PDF generation, the error is recorded against that recipient and the processor continues with the remaining recipients.

This means a single bad/rendering-failure recipient does not discard the entire bulk job.

## Design decisions

See `DESIGN.md` for the reasoning behind the background-processing approach, database model, failure isolation, storage strategy, and production improvements.
