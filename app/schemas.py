import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class EmployeeIn(StrictModel):
    emp_code: str = Field(pattern=r"^EMP\d{4,6}$")
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    department: str = Field(min_length=1, max_length=50)
    shift_start: str = "09:30"
    shift_end: str = "18:30"
    joined_on: str

    @field_validator("shift_start", "shift_end")
    @classmethod
    def valid_clock(cls, value):
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("time must be HH:MM")
        return value

    @field_validator("joined_on")
    @classmethod
    def valid_joined(cls, value):
        date.fromisoformat(value)
        return value


class PunchInIn(StrictModel):
    emp_code: str
    punched_at: int | None = Field(
        default=None,
        ge=100_000_000_000,
        le=4_102_444_800_000,
        strict=True,
    )
    status: Literal["PRESENT", "WFH", "ON_DUTY"] = "PRESENT"


class PunchOutIn(StrictModel):
    emp_code: str
    punched_at: int | None = Field(
        default=None,
        ge=100_000_000_000,
        le=4_102_444_800_000,
        strict=True,
    )


class CorrectionIn(StrictModel):
    status: Literal["PRESENT", "WFH", "ON_DUTY", "ABSENT", "LEAVE"] | None = None
    punch_in: int | None = Field(
        default=None,
        ge=100_000_000_000,
        le=4_102_444_800_000,
        strict=True,
    )
    punch_out: int | None = Field(
        default=None,
        ge=100_000_000_000,
        le=4_102_444_800_000,
        strict=True,
    )
    reason: str = Field(min_length=5, max_length=200)
    regularized_by: str = Field(min_length=1, max_length=50)
