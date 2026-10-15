# Design Decisions

## Keeping attendance records consistent

I used `emp_code` as the employee identifier because it is the code HR staff already recognize. MongoDB’s `_id` stays internal and never becomes part of the API. I also added unique indexes for employee codes and for each employee’s attendance date. That way, if two punch-in requests arrive at the same time, the database accepts only one instead of relying on a check that could race.

## Handling dates and shifts

I store real timestamps in UTC and convert them to IST when deciding which attendance date a punch belongs to. Shift times and calendar dates stay as strings because they describe local business hours and dates, not globally unique instants. This distinction also lets overnight shifts assign early-morning punches to the shift that started the previous day.

## Keeping corrections auditable

I treat a manual correction as an append-only audit event: the record keeps the original values in its history and adds one entry describing who changed what and why. The update compares the history observed before the edit, so concurrent corrections do not silently overwrite each other’s audit entries.

## Building analytics

I use MongoDB aggregation pipelines for monthly and department summaries so filtering and grouping happen in the database. Analytics use the stored derived fields, as required by the API contract. For department headcount, the query starts from employees and then looks up attendance, which includes people who have no attendance rows in the selected period.

The late leaderboard uses MongoDB’s competition ranking. If several employees tie at the limit, they all appear; employee code provides a stable order within the tie.

## Planning for growth

The current indexes support employee lookup, date filtering, department headcount, and punch-out selection. If the dataset grows substantially, I would consider pre-aggregated daily analytics. I would make that change only after checking real query plans and how fresh the reports need to be.
