from fastapi import APIRouter, Query

from app.services import analytics_service

router = APIRouter()


@router.get("/analytics/employees/{emp_code}/monthly")
def employee_monthly(emp_code: str, month: str):
    return analytics_service.employee_monthly(emp_code, month)


@router.get("/analytics/departments/summary")
def department_summary(month: str, department: str | None = None):
    return analytics_service.department_summary(month, department)


@router.get("/analytics/leaderboard/late")
def late_leaderboard(
    month: str,
    limit: int = Query(10, ge=1, le=50),
    department: str | None = None,
):
    return analytics_service.late_leaderboard(month, limit, department)


@router.get("/analytics/departments/{department}/trend")
def department_trend(
    department: str,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
):
    return analytics_service.department_trend(department, from_date, to_date)
