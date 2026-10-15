from fastapi import APIRouter, Query

from app.services import admin_service

router = APIRouter()


@router.get("/admin/explain/{endpoint}")
def explain_endpoint(
    endpoint: str,
    emp_code: str | None = None,
    month: str | None = None,
    department: str | None = None,
    limit: int = Query(10, ge=1, le=50),
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
):
    return admin_service.explain_endpoint(
        endpoint,
        emp_code,
        month,
        department,
        limit,
        date_from,
        date_to,
        status,
        page,
        page_size,
        from_date,
        to_date,
    )
