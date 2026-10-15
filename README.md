# Employee Attendance & Analytics API

A REST API built with FastAPI and MongoDB for managing employee records, daily attendance, manual attendance corrections, and attendance analytics.

## Features

- Create and list employees, with unique employee codes.
- Record punch-ins and punch-outs using epoch-millisecond timestamps.
- Assign punches to IST attendance dates, including overnight shifts.
- Correct attendance records with a reason, regularizer, and append-only change history.
- Generate employee monthly summaries, department summaries, late leaderboards, and department attendance trends using MongoDB aggregation pipelines.
- Inspect query execution plans through the admin explain endpoint.
- Check API and MongoDB availability through `/health`.

## API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/employees` | Create an employee |
| `GET` | `/employees` | List employees with optional department filtering and pagination |
| `POST` | `/attendance/punch-in` | Record an employee punch-in |
| `POST` | `/attendance/punch-out` | Record the punch-out and calculate attendance metrics |
| `GET` | `/attendance` | Filter and paginate attendance records |
| `PATCH` | `/attendance/{emp_code}/{date}` | Correct a record and append an audit entry |
| `GET` | `/analytics/employees/{emp_code}/monthly` | Get an employee’s monthly attendance summary |
| `GET` | `/analytics/departments/summary` | Summarize attendance by department and month |
| `GET` | `/analytics/leaderboard/late` | Rank employees by late minutes for a month |
| `GET` | `/analytics/departments/{department}/trend` | Return daily attendance trend data for a department |
| `GET` | `/admin/explain/{endpoint}` | Return MongoDB execution statistics for a supported query |

The root URL redirects to the interactive API docs at `/docs`. Request and response timestamps use epoch milliseconds. Shift times and attendance dates use IST. Attendance metrics are calculated from punch times and employee shifts; corrections retain a history of changed fields.

## Project Structure

- `app/main.py` creates the FastAPI app, registers routers, and defines system endpoints.
- `app/routers/` maps HTTP requests to service functions.
- `app/services/` implements employee, attendance, analytics, and explain operations.
- `app/schemas.py` defines request validation models.
- `app/database.py` configures MongoDB and creates indexes at startup.
- `app/constants.py` and `app/utils.py` hold shared statuses, time handling, and formatting helpers.

## Run Locally

Use Python 3.11 or newer and MongoDB 6.0 or newer. From the project directory, install the dependencies and configure the MongoDB connection in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:MONGO_URI = "mongodb://localhost:27017"
$env:MONGO_DB = "attendance_db"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Set `MONGO_URI` to your MongoDB Atlas connection string when using Atlas. Keep credentials and local `.env` files out of version control. Open `http://127.0.0.1:8000/docs` to explore the API.

The optional `python sample_seed.py` command loads sample documents into the configured database and replaces its `employees` and `attendance_logs` collections.
