from fastapi import HTTPException

from app.database import db
from app.services.analytics_service import (
    department_pipeline,
    employee_month_pipeline,
    trend_pipeline,
)
from app.utils import month_bounds, parse_day


def explain_endpoint(
    endpoint: str,
    emp_code: str | None,
    month: str | None,
    department: str | None,
    limit: int,
    date_from: str | None,
    date_to: str | None,
    status: str | None,
    page: int,
    page_size: int,
    from_date: str | None,
    to_date: str | None,
) -> dict:
    if endpoint == "attendance_list":
        query = {}
        if emp_code:
            query["emp_code"] = emp_code
        if status:
            query["status"] = status
        if date_from or date_to:
            query["date"] = {}
            if date_from:
                query["date"]["$gte"] = parse_day(date_from).isoformat()
            if date_to:
                query["date"]["$lte"] = parse_day(date_to).isoformat()
        offset = (page - 1) * page_size
        command = {
            "find": "attendance_logs",
            "filter": query,
            "sort": {"date": -1},
            "skip": offset,
            "limit": page_size,
        }
        collection_name = "attendance_logs"
    elif endpoint in {
        "employee_monthly",
        "department_summary",
        "late_leaderboard",
        "department_trend",
    }:
        if not month and endpoint != "department_trend":
            raise HTTPException(422, "month is required")
        if endpoint == "employee_monthly":
            if not emp_code:
                raise HTTPException(422, "emp_code is required")
            start, end = month_bounds(month)
            command = {
                "aggregate": "attendance_logs",
                "pipeline": employee_month_pipeline(emp_code, start, end),
                "cursor": {},
            }
            collection_name = "attendance_logs"
        elif endpoint == "department_summary":
            start, end = month_bounds(month)
            command = {
                "aggregate": "employees",
                "pipeline": department_pipeline(start, end, department),
                "cursor": {},
            }
            collection_name = "employees"
        elif endpoint == "late_leaderboard":
            start, end = month_bounds(month)
            pipeline = [
                {
                    "$match": {
                        "date": {
                            "$gte": start.isoformat(),
                            "$lte": end.isoformat(),
                        },
                        "late_minutes": {"$gt": 0},
                    }
                },
                {
                    "$group": {
                        "_id": "$emp_code",
                        "total_late_minutes": {"$sum": "$late_minutes"},
                    }
                },
            ]
            command = {
                "aggregate": "attendance_logs",
                "pipeline": pipeline,
                "cursor": {},
            }
            collection_name = "attendance_logs"
        else:
            if not department or not from_date or not to_date:
                raise HTTPException(422, "department, from and to are required")
            start, end = parse_day(from_date), parse_day(to_date)
            command = {
                "aggregate": 1,
                "pipeline": trend_pipeline(department, start, end),
                "cursor": {},
            }
            collection_name = "$cmd"
    else:
        raise HTTPException(422, "unknown endpoint")

    explain = db.command("explain", command, verbosity="executionStats")
    return {
        "endpoint": endpoint,
        "collection": collection_name,
        "explain": explain,
    }
