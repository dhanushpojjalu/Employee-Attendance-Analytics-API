from datetime import datetime, timedelta

from fastapi import HTTPException
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.constants import PRESENCE, STATUSES, UTC
from app.database import db
from app.schemas import CorrectionIn, PunchInIn, PunchOutIn
from app.utils import (
    as_utc,
    day_for_punch,
    derived,
    instant,
    late_minutes,
    output_doc,
    parse_day,
)


def punch_in(body: PunchInIn) -> dict:
    employee = db.employees.find_one({"emp_code": body.emp_code})
    if not employee:
        raise HTTPException(404, "employee not found")
    punched_at = instant(body.punched_at)
    attendance_date = day_for_punch(punched_at, employee).isoformat()
    document = {
        "emp_code": body.emp_code,
        "date": attendance_date,
        "status": body.status,
        "punch_in": punched_at,
        "punch_out": None,
        "work_hours": None,
        "late_minutes": late_minutes(punched_at, employee),
        "overtime_minutes": 0,
        "half_day": False,
        "history": [],
    }
    try:
        db.attendance_logs.insert_one(document)
    except DuplicateKeyError:
        raise HTTPException(
            409, "already punched in for this attendance date"
        ) from None
    return output_doc(document)


def punch_out(body: PunchOutIn) -> dict:
    employee = db.employees.find_one({"emp_code": body.emp_code})
    if not employee:
        raise HTTPException(404, "employee not found")
    punched_at = instant(body.punched_at)
    record = db.attendance_logs.find_one(
        {
            "emp_code": body.emp_code,
            "punch_in": {"$lte": punched_at},
            "status": {"$in": list(PRESENCE)},
        },
        sort=[("punch_in", DESCENDING)],
    )
    if not record:
        raise HTTPException(404, "no punch-in found")
    punch_in_at = as_utc(record["punch_in"])
    if punched_at <= punch_in_at or punched_at - punch_in_at > timedelta(hours=24):
        raise HTTPException(422, "punch-out must be after punch-in and within 24 hours")
    calculated = derived(punch_in_at, punched_at, record["date"], employee)
    updated_record = db.attendance_logs.find_one_and_update(
        {"_id": record["_id"], "punch_out": None},
        {"$set": {"punch_out": punched_at, **calculated}},
        return_document=ReturnDocument.AFTER,
    )
    if updated_record is None:
        raise HTTPException(409, "record already punched out")
    return output_doc(updated_record)


def list_attendance(
    emp_code: str | None,
    date_from: str | None,
    date_to: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> dict:
    query = {}
    if emp_code:
        query["emp_code"] = emp_code
    if status:
        if status not in STATUSES:
            raise HTTPException(422, "invalid status")
        query["status"] = status
    if date_from or date_to:
        query["date"] = {}
        if date_from:
            query["date"]["$gte"] = parse_day(date_from).isoformat()
        if date_to:
            query["date"]["$lte"] = parse_day(date_to).isoformat()
    offset = (page - 1) * page_size
    cursor = (
        db.attendance_logs.find(query, {"_id": 0})
        .sort([("date", DESCENDING), ("emp_code", 1)])
        .skip(offset)
        .limit(page_size)
    )
    return {
        "items": [output_doc(document) for document in cursor],
        "total": db.attendance_logs.count_documents(query),
        "page": page,
        "page_size": page_size,
    }


def regularize(emp_code: str, date_str: str, body: CorrectionIn) -> dict:
    parse_day(date_str)
    employee = db.employees.find_one({"emp_code": emp_code})
    if not employee:
        raise HTTPException(404, "employee not found")

    record_key = {"emp_code": emp_code, "date": date_str}
    existing_record = db.attendance_logs.find_one(record_key)
    if not existing_record:
        raise HTTPException(404, "attendance record not found")

    status = body.status if body.status is not None else existing_record["status"]
    if status in {"ABSENT", "LEAVE"}:
        if body.punch_in is not None or body.punch_out is not None:
            raise HTTPException(422, "absent/leave cannot include punch times")
        punch_in_at = punch_out_at = None
    else:
        punch_in_at = (
            instant(body.punch_in)
            if body.punch_in is not None
            else existing_record.get("punch_in")
        )
        punch_out_at = (
            instant(body.punch_out)
            if body.punch_out is not None
            else existing_record.get("punch_out")
        )
        if punch_in_at is None:
            raise HTTPException(422, "presence status requires punch_in")
        if day_for_punch(punch_in_at, employee).isoformat() != date_str:
            raise HTTPException(
                422, "punch_in must belong to the record attendance date"
            )
        if punch_out_at and (
            punch_out_at <= punch_in_at
            or punch_out_at - punch_in_at > timedelta(hours=24)
        ):
            raise HTTPException(
                422, "punch_out must be after punch_in and within 24 hours"
            )

    fields = {
        "status": status,
        "punch_in": punch_in_at,
        "punch_out": punch_out_at,
        **derived(punch_in_at, punch_out_at, date_str, employee),
    }
    changes = {}
    for field, new_value in fields.items():
        previous_value = existing_record.get(field)
        if isinstance(previous_value, datetime):
            previous_value = as_utc(previous_value)
        if isinstance(new_value, datetime):
            new_value = as_utc(new_value)
        if previous_value != new_value:
            changes[field] = {"from": existing_record.get(field), "to": new_value}
    if not changes:
        raise HTTPException(422, "request makes no changes")

    history_entry = {
        "at": datetime.now(UTC),
        "by": body.regularized_by,
        "reason": body.reason,
        "changes": changes,
    }
    history = existing_record.get("history", [])
    compare_and_swap = (
        {**record_key, "history": history}
        if "history" in existing_record
        else {**record_key, "history": {"$exists": False}}
    )
    updated_record = db.attendance_logs.find_one_and_update(
        compare_and_swap,
        {"$set": fields, "$push": {"history": history_entry}},
        return_document=ReturnDocument.AFTER,
    )
    if updated_record is None:
        raise HTTPException(409, "record changed concurrently; retry")
    return output_doc(updated_record)
