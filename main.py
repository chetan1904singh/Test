from pathlib import Path
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .certificate import CERTIFICATE_DIR, generate_certificate
from .database import Base, SessionLocal, engine, get_db
from .models import GenerationJob, JobStatus, Recipient, RecipientStatus, utcnow
from .schemas import GenerationRequest, JobResponse, RecipientResponse

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Bulk Certificate Generator", version="1.0.0")


def build_job_response(db: Session, job: GenerationJob) -> JobResponse:
    recipients = list(job.recipients)
    pending = sum(r.status == RecipientStatus.PENDING.value for r in recipients)
    processing = sum(r.status == RecipientStatus.PROCESSING.value for r in recipients)
    successful = sum(r.status == RecipientStatus.SUCCESS.value for r in recipients)
    failed = sum(r.status in (RecipientStatus.FAILED.value, RecipientStatus.INVALID.value) for r in recipients)
    finished = successful + failed
    progress = round((finished / job.total) * 100, 2) if job.total else 100.0

    if finished == job.total:
        status = JobStatus.COMPLETED.value if failed == 0 else JobStatus.COMPLETED_WITH_ERRORS.value
    elif processing or finished:
        status = JobStatus.PROCESSING.value
    else:
        status = JobStatus.PENDING.value

    job.status = status
    job.successful = successful
    job.failed = failed
    db.commit()

    return JobResponse(
        id=job.id,
        event_name=job.event_name,
        issued_date=job.issued_date,
        status=status,
        total=job.total,
        successful=successful,
        failed=failed,
        pending=pending,
        processing=processing,
        progress_percent=progress,
        recipients=[RecipientResponse(
            id=r.id,
            name=r.name,
            email=r.email,
            status=r.status,
            error_message=r.error_message,
            certificate_url=f"/certificates/{r.id}" if r.status == RecipientStatus.SUCCESS.value else None,
        ) for r in recipients],
    )


def process_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if not job:
            return
        job.status = JobStatus.PROCESSING.value
        db.commit()

        recipients = db.query(Recipient).filter(Recipient.job_id == job_id).all()
        for recipient in recipients:
            if recipient.status == RecipientStatus.INVALID.value:
                continue
            recipient.status = RecipientStatus.PROCESSING.value
            db.commit()
            try:
                output_path = CERTIFICATE_DIR / f"certificate_{recipient.id}.pdf"
                generate_certificate(
                    recipient_name=recipient.name,
                    event_name=job.event_name,
                    issued_date=job.issued_date,
                    output_path=output_path,
                )
                recipient.certificate_path = str(output_path)
                recipient.status = RecipientStatus.SUCCESS.value
                recipient.error_message = None
            except Exception as exc:
                recipient.status = RecipientStatus.FAILED.value
                recipient.error_message = str(exc)[:1000]
            finally:
                recipient.updated_at = utcnow()
                db.commit()

        # Final state is calculated by the same rules used by GET /jobs/{id}.
        build_job_response(db, job)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/jobs", response_model=JobResponse, status_code=202)
def create_job(payload: GenerationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = GenerationJob(
        event_name=payload.event_name.strip(),
        issued_date=payload.issued_date.isoformat(),
        total=len(payload.recipients),
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.flush()

    for item in payload.recipients:
        recipient = Recipient(job_id=job.id, name=item.name, email=item.email)
        db.add(recipient)

    db.commit()
    db.refresh(job)
    background_tasks.add_task(process_job, job.id)
    return build_job_response(db, job)


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return build_job_response(db, job)


@app.get("/certificates/{recipient_id}")
def get_certificate(recipient_id: int, db: Session = Depends(get_db)):
    recipient = db.get(Recipient, recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Certificate recipient not found")
    if recipient.status != RecipientStatus.SUCCESS.value or not recipient.certificate_path:
        raise HTTPException(status_code=409, detail="Certificate is not available yet")

    path = Path(recipient.certificate_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Generated certificate file is missing")
    return FileResponse(path, media_type="application/pdf", filename=f"certificate_{recipient.id}.pdf")
