from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecipientInput(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: str | None = Field(default=None, max_length=254)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("name cannot be blank")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("invalid email address")
        return value


class GenerationRequest(BaseModel):
    event_name: str = Field(min_length=2, max_length=200)
    issued_date: date
    recipients: list[RecipientInput] = Field(min_length=1, max_length=10000)


class RecipientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None
    status: str
    error_message: str | None
    certificate_url: str | None


class JobResponse(BaseModel):
    id: int
    event_name: str
    issued_date: str
    status: str
    total: int
    successful: int
    failed: int
    pending: int
    processing: int
    progress_percent: float
    recipients: list[RecipientResponse]
