from datetime import datetime

from fastapi import HTTPException
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from app.constants import UTC
from app.database import db
from app.schemas import EmployeeIn
from app.utils import epoch_ms


def create_employee(body: EmployeeIn) -> dict:
    document = body.model_dump()
    document["created_at"] = datetime.now(UTC)
    try:
        db.employees.insert_one(document)
    except DuplicateKeyError:
        raise HTTPException(409, "emp_code already exists") from None
    return {**body.model_dump(), "created_at": epoch_ms(document["created_at"])}


def list_employees(department: str | None, page: int, page_size: int) -> dict:
    query = {"department": department} if department is not None else {}
    offset = (page - 1) * page_size
    items = list(
        db.employees.find(query, {"_id": 0})
        .sort("emp_code", ASCENDING)
        .skip(offset)
        .limit(page_size)
    )
    for item in items:
        item["created_at"] = epoch_ms(item.get("created_at"))
    return {
        "items": items,
        "total": db.employees.count_documents(query),
        "page": page,
        "page_size": page_size,
    }
