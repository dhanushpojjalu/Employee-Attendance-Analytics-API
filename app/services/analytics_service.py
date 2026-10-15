from datetime import date, datetime, time

from fastapi import HTTPException

from app.constants import PRESENCE, UTC
from app.database import db
from app.utils import month_bounds, parse_day, round_half, working_days


def employee_month_pipeline(emp_code: str, start: date, end: date) -> list[dict]:
    date_filter = {"$gte": start.isoformat(), "$lte": end.isoformat()}
    weekday = {"$dayOfWeek": {"$dateFromString": {"dateString": "$date"}}}
    is_present_weekday = {
        "$and": [
            {"$in": ["$status", list(PRESENCE)]},
            {"$gte": ["$_weekday", 2]},
            {"$lte": ["$_weekday", 6]},
        ]
    }
    present_day_value = {
        "$cond": [{"$eq": [{"$ifNull": ["$half_day", False]}, True]}, 0.5, 1]
    }
    return [
        {"$match": {"emp_code": emp_code, "date": date_filter}},
        {"$set": {"_weekday": weekday}},
        {
            "$group": {
                "_id": None,
                "present_days": {
                    "$sum": {"$cond": [is_present_weekday, present_day_value, 0]}
                },
                "leave_days": {
                    "$sum": {"$cond": [{"$eq": ["$status", "LEAVE"]}, 1, 0]}
                },
                "late_count": {
                    "$sum": {
                        "$cond": [{"$gt": [{"$ifNull": ["$late_minutes", 0]}, 0]}, 1, 0]
                    }
                },
                "total_late_minutes": {
                    "$sum": {"$ifNull": ["$late_minutes", 0]}
                },
                "total_overtime_minutes": {
                    "$sum": {"$ifNull": ["$overtime_minutes", 0]}
                },
            }
        },
    ]


def employee_monthly(emp_code: str, month: str) -> dict:
    start, end = month_bounds(month)
    employee = db.employees.find_one({"emp_code": emp_code})
    if not employee:
        raise HTTPException(404, "employee not found")
    rows = list(db.attendance_logs.aggregate(employee_month_pipeline(emp_code, start, end)))
    row = rows[0] if rows else {}
    work_start = max(start, parse_day(employee["joined_on"]))
    working_day_count = working_days(work_start, end) if work_start <= end else 0
    present_days = row.get("present_days", 0)
    return {
        "emp_code": emp_code,
        "month": month,
        "working_days": working_day_count,
        "present_days": present_days,
        "leave_days": row.get("leave_days", 0),
        "late_count": row.get("late_count", 0),
        "total_late_minutes": row.get("total_late_minutes", 0),
        "total_overtime_minutes": row.get("total_overtime_minutes", 0),
        "attendance_pct": (
            round_half(present_days * 100 / working_day_count)
            if working_day_count
            else None
        ),
    }


def department_pipeline(start: date, end: date, department: str | None = None) -> list[dict]:
    employee_filter = {"joined_on": {"$lte": end.isoformat()}}
    if department is not None:
        employee_filter["department"] = department
    return [
        {"$match": employee_filter},
        {
            "$lookup": {
                "from": "attendance_logs",
                "let": {"code": "$emp_code"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$emp_code", "$$code"]},
                                    {"$gte": ["$date", start.isoformat()]},
                                    {"$lte": ["$date", end.isoformat()]},
                                ]
                            }
                        }
                    }
                ],
                "as": "logs",
            }
        },
        {"$unwind": {"path": "$logs", "preserveNullAndEmptyArrays": True}},
        {
            "$group": {
                "_id": "$department",
                "headcount_employees": {"$addToSet": "$_id"},
                "present_days": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$in": ["$logs.status", list(PRESENCE)]},
                                    {
                                        "$gte": [
                                            {
                                                "$dayOfWeek": {
                                                    "$dateFromString": {
                                                        "dateString": {
                                                            "$ifNull": [
                                                                "$logs.date",
                                                                start.isoformat(),
                                                            ]
                                                        }
                                                    }
                                                }
                                            },
                                            2,
                                        ]
                                    },
                                    {
                                        "$lte": [
                                            {
                                                "$dayOfWeek": {
                                                    "$dateFromString": {
                                                        "dateString": {
                                                            "$ifNull": [
                                                                "$logs.date",
                                                                start.isoformat(),
                                                            ]
                                                        }
                                                    }
                                                }
                                            },
                                            6,
                                        ]
                                    },
                                ]
                            },
                            {
                                "$cond": [
                                    {
                                        "$eq": [
                                            {"$ifNull": ["$logs.half_day", False]},
                                            True,
                                        ]
                                    },
                                    0.5,
                                    1,
                                ]
                            },
                            0,
                        ]
                    }
                },
                "hours": {
                    "$avg": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$in": ["$logs.status", list(PRESENCE)]},
                                    {
                                        "$ne": [
                                            {"$ifNull": ["$logs.work_hours", None]},
                                            None,
                                        ]
                                    },
                                ]
                            },
                            "$logs.work_hours",
                            None,
                        ]
                    }
                },
                "late_count": {
                    "$sum": {
                        "$cond": [
                            {"$gt": [{"$ifNull": ["$logs.late_minutes", 0]}, 0]},
                            1,
                            0,
                        ]
                    }
                },
                "total_late_minutes": {
                    "$sum": {"$ifNull": ["$logs.late_minutes", 0]}
                },
                "leave_count": {
                    "$sum": {"$cond": [{"$eq": ["$logs.status", "LEAVE"]}, 1, 0]}
                },
                "on_duty_count": {
                    "$sum": {
                        "$cond": [{"$eq": ["$logs.status", "ON_DUTY"]}, 1, 0]
                    }
                },
            }
        },
        {"$set": {"headcount": {"$size": "$headcount_employees"}}},
        {"$unset": "headcount_employees"},
        {"$sort": {"_id": 1}},
    ]


def department_summary(month: str, department: str | None = None) -> dict:
    start, end = month_bounds(month)
    rows = list(db.employees.aggregate(department_pipeline(start, end, department)))
    items = [
        {
            "department": row["_id"],
            "headcount": row["headcount"],
            "present_days": row["present_days"],
            "avg_work_hours": round_half(row.get("hours")),
            "late_count": row["late_count"],
            "total_late_minutes": row["total_late_minutes"],
            "leave_count": row["leave_count"],
            "on_duty_count": row["on_duty_count"],
        }
        for row in rows
        if row["headcount"] > 0
    ]
    return {"month": month, "items": items}


def late_leaderboard(
    month: str, limit: int = 10, department: str | None = None
) -> dict:
    start, end = month_bounds(month)
    pipeline = [
        {
            "$match": {
                "date": {"$gte": start.isoformat(), "$lte": end.isoformat()},
                "late_minutes": {"$gt": 0},
            }
        },
        {
            "$group": {
                "_id": "$emp_code",
                "total_late_minutes": {"$sum": "$late_minutes"},
                "late_count": {"$sum": 1},
            }
        },
        {
            "$lookup": {
                "from": "employees",
                "localField": "_id",
                "foreignField": "emp_code",
                "as": "employee",
            }
        },
        {"$unwind": "$employee"},
    ]
    if department is not None:
        pipeline.append({"$match": {"employee.department": department}})
    pipeline.extend(
        [
            {
                "$setWindowFields": {
                    "sortBy": {"total_late_minutes": -1},
                    "output": {"rank": {"$rank": {}}},
                }
            },
            {"$match": {"rank": {"$lte": limit}}},
            {"$sort": {"total_late_minutes": -1, "_id": 1}},
            {
                "$project": {
                    "_id": 0,
                    "rank": 1,
                    "emp_code": "$_id",
                    "name": "$employee.name",
                    "department": "$employee.department",
                    "total_late_minutes": 1,
                    "late_count": 1,
                }
            },
        ]
    )
    return {"month": month, "items": list(db.attendance_logs.aggregate(pipeline))}


def trend_pipeline(department: str, start: date, end: date) -> list[dict]:
    start_at = datetime.combine(start, time(), UTC)
    end_at = datetime.combine(end, time(), UTC)
    attendance_lookup = {
        "from": "attendance_logs",
        "let": {"day": "$day"},
        "pipeline": [
            {"$match": {"$expr": {"$eq": ["$date", "$$day"]}}},
            {
                "$lookup": {
                    "from": "employees",
                    "localField": "emp_code",
                    "foreignField": "emp_code",
                    "as": "employee",
                }
            },
            {"$unwind": "$employee"},
            {"$match": {"employee.department": department}},
        ],
        "as": "logs",
    }
    headcount_lookup = {
        "from": "employees",
        "let": {"day": "$day"},
        "pipeline": [
            {
                "$match": {
                    "department": department,
                    "$expr": {"$lte": ["$joined_on", "$$day"]},
                }
            },
            {"$count": "count"},
        ],
        "as": "headcount_result",
    }
    present_logs = {
        "$filter": {
            "input": "$logs",
            "as": "log",
            "cond": {"$in": ["$$log.status", list(PRESENCE)]},
        }
    }
    late_logs = {
        "$filter": {
            "input": "$logs",
            "as": "log",
            "cond": {"$gt": [{"$ifNull": ["$$log.late_minutes", 0]}, 0]},
        }
    }
    return [
        {"$documents": [{"date": start_at}]},
        {
            "$densify": {
                "field": "date",
                "range": {
                    "step": 1,
                    "unit": "day",
                    "bounds": [start_at, end_at],
                },
            }
        },
        {"$match": {"date": {"$lte": end_at}}},
        {"$set": {"day": {"$dateToString": {"date": "$date", "format": "%Y-%m-%d"}}}},
        {"$lookup": attendance_lookup},
        {"$lookup": headcount_lookup},
        {
            "$set": {
                "headcount": {
                    "$ifNull": [{"$arrayElemAt": ["$headcount_result.count", 0]}, 0]
                },
                "present_count": {
                    "$sum": {
                        "$map": {
                            "input": present_logs,
                            "as": "log",
                            "in": {
                                "$cond": [
                                    {"$eq": ["$$log.half_day", True]},
                                    0.5,
                                    1,
                                ]
                            },
                        }
                    }
                },
                "late_count": {"$size": late_logs},
                "is_working_day": {
                    "$and": [
                        {"$gte": [{"$dayOfWeek": "$date"}, 2]},
                        {"$lte": [{"$dayOfWeek": "$date"}, 6]},
                    ]
                },
            }
        },
        {
            "$set": {
                "attendance_rate": {
                    "$cond": [
                        {"$and": ["$is_working_day", {"$gt": ["$headcount", 0]}]},
                        {"$divide": ["$present_count", "$headcount"]},
                        None,
                    ]
                }
            }
        },
        {
            "$setWindowFields": {
                "sortBy": {"date": 1},
                "output": {
                    "moving_avg_7d": {
                        "$avg": "$attendance_rate",
                        "window": {"documents": [-6, 0]},
                    }
                },
            }
        },
        {"$sort": {"date": 1}},
        {
            "$project": {
                "_id": 0,
                "date": "$day",
                "is_working_day": 1,
                "headcount": 1,
                "present_count": 1,
                "late_count": 1,
                "attendance_rate": 1,
                "moving_avg_7d": 1,
            }
        },
    ]


def department_trend(department: str, from_date: str, to_date: str) -> dict:
    start, end = parse_day(from_date), parse_day(to_date)
    if end < start or (end - start).days + 1 > 92:
        raise HTTPException(422, "invalid trend date range")
    if not db.employees.find_one({"department": department}):
        raise HTTPException(404, "department not found")
    items = list(db.aggregate(trend_pipeline(department, start, end)))
    for item in items:
        item["attendance_rate"] = round_half(item["attendance_rate"], 4)
        item["moving_avg_7d"] = round_half(item["moving_avg_7d"], 4)
    return {"department": department, "items": items}
