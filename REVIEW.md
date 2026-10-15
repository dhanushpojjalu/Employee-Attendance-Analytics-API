# Employee Attendance & Analytics API

## Project Overview

This project is a Python API built with FastAPI and MongoDB. It manages employee records and daily attendance, including punch-in and punch-out, manual corrections with an audit history, and analytics for employees and departments.

The code is organized by responsibility:

- `app/main.py` creates the FastAPI application, registers routes, and creates MongoDB indexes at startup.
- `app/routers/` defines the HTTP endpoints and request parameters.
- `app/services/` contains the business rules and database operations used by the endpoints.
- `app/schemas.py` validates request bodies.
- `app/database.py` configures the MongoDB client and indexes.
- `app/constants.py` and `app/utils.py` provide shared values and date/time helpers.

## Requirements

- Python 3.11 or newer
- MongoDB 6.0 or newer, running locally or available through MongoDB Atlas

## Setup and Run on Windows

Open PowerShell in the `candidate_kit` project folder and create a virtual environment:

```powershell
py -3.11 -m venv .venv
```

Install the dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set the MongoDB connection for the current PowerShell session. For a local MongoDB server, use:

```powershell
$env:MONGO_URI = "mongodb://localhost:27017"
$env:MONGO_DB = "attendance_db"
```

For MongoDB Atlas, set `MONGO_URI` to your Atlas connection string instead. Keep credentials out of source control.

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` to view and try the API endpoints.

## Sample Data

To load the sample employees and attendance records, open a second PowerShell window in the project folder, set the same `MONGO_URI` and `MONGO_DB`, then run:

```powershell
.\.venv\Scripts\python.exe sample_seed.py
```

The seed script replaces the `employees` and `attendance_logs` collections in the configured database. Skip this step if those collections contain data you need to keep.
