from fastapi import APIRouter, Query

from app.schemas import EmployeeIn
from app.services import employee_service

router = APIRouter()


@router.post("/employees", status_code=201)
def create_employee(body: EmployeeIn):
    return employee_service.create_employee(body)


@router.get("/employees")
def list_employees(
    department: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return employee_service.list_employees(department, page, page_size)
