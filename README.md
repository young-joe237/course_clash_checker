# Course Clash Checker

A student course registration conflict detection system that uses graph theory. It finds courses that share students, detects timetable clashes by date and time, and suggests time slots.

**CSC213 Discrete Structures | Group 1 | Lecturer: Dr. Gabriel Ayem**

**Live demo:** https://YOUR-USERNAME.github.io/course-clash-checker/

## How it works

Each course is a **vertex**. Two courses are joined by an **edge** when at least one student is registered for both, because those courses must not be scheduled at the same time.

From this graph the program:

- lists every pair of conflicting courses and the students who cause each conflict
- builds the **adjacency list** and **adjacency matrix**
- calculates the **degree** of each course and finds the course(s) with the most conflicts
- checks the **handshake lemma** (sum of degrees = 2 × number of edges)
- detects **timetable clashes**: a student registered for two courses whose times overlap
- suggests **time slots** using greedy graph colouring
- draws the conflict graph

## Two ways to use it

### 1. Web version (no install)

Open the live demo link above, or download `index.html` and double-click it. Add each course with its date and times, type each student's courses (one line per student, for example `S001: MAT101, PHY101`), and press **Check clashes**. Everything runs in your browser and no data is sent anywhere.

### 2. Python version

```bash
pip install networkx matplotlib

python conflict_detector.py                    # built-in sample data
python conflict_detector.py --interactive      # type courses, dates and times in
python conflict_detector.py sample_registrations.csv --schedule sample_schedule.csv
python conflict_detector.py data.csv --no-plot # skip the graph window
python -m unittest -v                          # run the 16 tests
```

On a Mac or Linux, use `python3` and `pip3`.

## Input formats

**Registrations** (`sample_registrations.csv`): one row per student.

```
student_id,course1,course2,course3
S001,MAT101,PHY101,CSC101
```

**Schedule** (`sample_schedule.csv`): one row per course. Dates are `YYYY-MM-DD` and times are 24-hour `HH:MM`.

```
course,date,start,end
MAT101,2026-12-07,09:00,11:00
```

## Files

| File | Purpose |
|---|---|
| `index.html` | Web version |
| `conflict_detector.py` | Python program |
| `test_conflict_detector.py` | Unit tests |
| `sample_registrations.csv` | Sample student registrations |
| `sample_schedule.csv` | Sample course dates and times |
| `conflict_graph.png` | Example output graph |

## Discrete structures used

Sets, graphs (vertices and edges), adjacency list, adjacency matrix, vertex degree, handshake lemma and graph colouring.

## Limitations

- It detects conflicts and suggests slot groups. It does not generate a full timetable.
- Room capacity and lecturer availability are not considered.
- Each course has one session.
- Results depend on the accuracy of the data entered.

## Group members

| Name | Matric number |
|---|---|
| Oluwafolayinka Oladipo | A00025456 |
| Muhammad Umar | A00026016 |
| Francisca Okorie-Enyinnaya | A00025252 |
| Secondee Samuel Alfa | A00025801 |
| Mohammed Alameen | A00024595 |
| Joseph Yonga | A00026543 |

## References

- Diestel, R. (2017). *Graph theory* (5th ed.). Springer.
- Python Software Foundation. Python 3 documentation. https://docs.python.org/3/
- NetworkX Developers. NetworkX documentation. https://networkx.org/documentation/stable/
