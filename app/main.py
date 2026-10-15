"""FastAPI application setup and top-level routes."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, Response
from pymongo.errors import PyMongoError

from app.database import db, ensure_indexes
from app.routers import admin, analytics, attendance, employees

app = FastAPI(title="Employee Attendance & Analytics API", version="2.0.0")

app.include_router(employees.router)
app.include_router(attendance.router)
app.include_router(analytics.router)
app.include_router(admin.router)


@app.on_event("startup")
def startup() -> None:
    ensure_indexes()


@app.get("/")
def root():
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/health")
def health():
    try:
        db.command("ping")
    except PyMongoError as exc:
        raise HTTPException(503, "database unavailable") from exc
    return {"status": "ok"}
