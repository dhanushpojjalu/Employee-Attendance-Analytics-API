from fastapi import APIRouter, Query
from app.schemas import CorrectionIn, PunchInIn, PunchOutIn
from app.services import attendance_service

router = APIRouter()


@router.post("/attendance/punch-in", status_code=201)
def punch_in(body: PunchInIn):
    return attendance_service.punch_in(body)


@router.post("/attendance/punch-out")
def punch_out(body: PunchOutIn):
    return attendance_service.punch_out(body)


@router.get("/attendance")
def list_attendance(
    emp_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return attendance_service.list_attendance(
        emp_code, date_from, date_to, status, page, page_size
    )


@router.patch("/attendance/{emp_code}/{date}")
def regularize(emp_code: str, date: str, body: CorrectionIn):
    return attendance_service.regularize(emp_code, date, body)
