# Design Note

## 1. Processing model

The API returns `202 Accepted` and schedules generation using FastAPI `BackgroundTasks`. This keeps the HTTP request short and makes the API suitable for a bulk payload instead of forcing the client to wait for every PDF.

For this assignment, this is intentionally simple and has no external queue dependency.

For production-scale workloads, the background task should be replaced with a durable queue such as Celery/RQ + Redis or a managed task queue. That would allow multiple workers, retries, horizontal scaling, and recovery after process restarts.

## 2. Relational data model

There are two main tables:

- `generation_jobs`: one row per bulk request, containing aggregate counters and job status.
- `recipients`: one row per recipient, linked to a job by foreign key. It stores the individual status, failure reason, and certificate path.

Keeping recipient state separately makes progress tracking and failure isolation straightforward.

## 3. Failure isolation

Each recipient is processed inside its own `try/except`. A rendering exception changes only that recipient to `failed` and stores an error message. The loop continues, so other certificates can succeed.

A final job state is calculated from recipient outcomes:

- all successful -> `completed`
- at least one failure after processing -> `completed_with_errors`

## 4. Certificate template

`app/certificate.py` contains one predefined ReportLab template. The recipient name, event name, and issue date are inserted dynamically. No template editor or multiple designs are required by the assignment.

## 5. Storage

Generated PDFs are stored locally under `storage/certificates/` and referenced from the database.

For production, object storage such as S3/GCS/Azure Blob would be preferable. The database would store an object key rather than a local filesystem path.

## 6. Validation

Pydantic validates the request schema before a job is created. Names have length limits and whitespace normalization; email values receive basic format validation. The payload also has a maximum of 10,000 recipients to prevent an accidentally enormous request.

A production API could add stronger email validation, authentication/authorization, rate limits, request-size limits, and idempotency keys.

## 7. Scaling considerations

The implementation processes recipients sequentially inside a background worker. This is intentionally predictable and avoids creating an unbounded number of threads/processes.

For large workloads, workers could process recipients in bounded batches, use a queue, and update counters transactionally. Database indexes on `job_id` support efficient status queries.

## 8. Long-term improvements

1. Replace FastAPI `BackgroundTasks` with a durable job queue.
2. Store PDFs in object storage and return signed download URLs.
3. Add authentication and authorization.
4. Add idempotency keys so retried POST requests do not duplicate jobs.
5. Add automatic retry policy for transient generation/storage failures.
6. Add structured logging and metrics.
7. Add pagination for very large recipient lists in job-status responses.
8. Use PostgreSQL in production instead of SQLite.
