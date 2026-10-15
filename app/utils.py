import re
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException

from app.constants import IST, UTC


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def epoch_ms(value: datetime | None) -> int | None:
    return int(as_utc(value).timestamp() * 1000) if isinstance(value, datetime) else None


def instant(milliseconds: int | None) -> datetime:
    if milliseconds is None:
        return datetime.now(UTC).replace(microsecond=0)
    if (
        isinstance(milliseconds, bool)
        or not isinstance(milliseconds, int)
        or milliseconds < 100_000_000_000
        or milliseconds > 4_102_444_800_000
    ):
        raise HTTPException(422, "timestamps must be epoch milliseconds")
    return datetime.fromtimestamp(milliseconds / 1000, UTC).replace(microsecond=0)


def local(value: datetime) -> datetime:
    return as_utc(value).astimezone(IST)


def day_for_punch(punched: datetime, employee: dict) -> date:
    local_dt = local(punched)
    attendance_date = local_dt.date()
    shift_start = time.fromisoformat(employee["shift_start"])
    shift_end = time.fromisoformat(employee["shift_end"])
    if (
        shift_end <= shift_start
        and local_dt.time().replace(tzinfo=None) < shift_end
    ):
        attendance_date -= timedelta(days=1)
    return attendance_date


def shift_boundary(
    day: str | date, clock: str, overnight_next: bool = False
) -> datetime:
    shift_date = date.fromisoformat(day) if isinstance(day, str) else day
    shift_time = time.fromisoformat(clock)
    if overnight_next:
        shift_date += timedelta(days=1)
    return datetime.combine(shift_date, shift_time, IST).astimezone(UTC)


def late_minutes(punch: datetime | None, employee: dict) -> int:
    if punch is None:
        return 0
    local_punch = local(punch).replace(microsecond=0)
    shift_start = datetime.combine(
        local_punch.date(), time.fromisoformat(employee["shift_start"]), IST
    )
    if day_for_punch(punch, employee) < local_punch.date():
        shift_start -= timedelta(days=1)
    minutes_late = int((local_punch - shift_start).total_seconds() // 60)
    return minutes_late if (local_punch - shift_start).total_seconds() > 600 else 0


def work_hours(punch_in: datetime, punch_out: datetime) -> float:
    elapsed_seconds = (as_utc(punch_out) - as_utc(punch_in)).total_seconds()
    hours = Decimal(str(elapsed_seconds)) / Decimal(3600)
    rounded_hours = hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(rounded_hours)


def overtime_minutes(
    punch_out: datetime, record_day: str | date, employee: dict
) -> int:
    shift_end = time.fromisoformat(employee["shift_end"])
    shift_start = time.fromisoformat(employee["shift_start"])
    overnight = shift_end <= shift_start
    shift_end_at = shift_boundary(record_day, employee["shift_end"], overnight)
    minutes_after_shift = int((as_utc(punch_out) - shift_end_at).total_seconds() // 60)
    return minutes_after_shift if minutes_after_shift >= 30 else 0


def derived(punch_in, punch_out, record_day, employee):
    hours = work_hours(punch_in, punch_out) if punch_in and punch_out else None
    return {
        "late_minutes": late_minutes(punch_in, employee),
        "work_hours": hours,
        "overtime_minutes": (
            overtime_minutes(punch_out, record_day, employee) if punch_out else 0
        ),
        "half_day": hours is not None and hours < 4.50,
    }


def output_doc(document: dict) -> dict:
    result = {key: value for key, value in document.items() if key != "_id"}
    for field in ("punch_in", "punch_out"):
        result[field] = epoch_ms(result.get(field))
    result.setdefault("work_hours", None)
    result.setdefault("late_minutes", 0)
    result.setdefault("overtime_minutes", 0)
    result.setdefault("half_day", False)
    result.setdefault("history", [])
    for entry in result["history"]:
        entry["at"] = epoch_ms(entry.get("at"))
        for field in ("punch_in", "punch_out"):
            if field in entry.get("changes", {}):
                change = entry["changes"][field]
                change["from"] = epoch_ms(change.get("from"))
                change["to"] = epoch_ms(change.get("to"))
    return result


def parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise HTTPException(422, "date must be YYYY-MM-DD")


def month_bounds(month: str) -> tuple[date, date]:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month or ""):
        raise HTTPException(422, "month must be YYYY-MM")
    year, month_number = map(int, month.split("-"))
    return (
        date(year, month_number, 1),
        date(year, month_number, monthrange(year, month_number)[1]),
    )


def round_half(value, places: int = 2):
    if value is None:
        return None
    return float(
        Decimal(str(value)).quantize(
            Decimal("1").scaleb(-places), rounding=ROUND_HALF_UP
        )
    )


def working_days(start: date, end: date) -> int:
    count = 0
    while start <= end:
        count += start.weekday() < 5
        start += timedelta(days=1)
    return count
