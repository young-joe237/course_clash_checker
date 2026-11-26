"""
Student Course Registration Conflict Detection System (Using Graph Theory)
CSC213 - Discrete Structures | Group 1

Courses are vertices; two courses are joined by an edge when at least one
student is registered for both (so they must not share a time slot).

Usage:
    python conflict_detector.py                  # run built-in sample data
    python conflict_detector.py data.csv         # load registrations from CSV
    python conflict_detector.py --interactive    # type courses, dates and times in
    python conflict_detector.py data.csv --schedule times.csv
    python conflict_detector.py data.csv --no-plot --output conflict_graph.png

CSV format (one row per student; header optional):
    student_id,course1,course2,course3,...
"""

import argparse
import csv
import sys
from itertools import combinations

# ----------------------------------------------------------------------------
# 1. DATA INPUT
# ----------------------------------------------------------------------------

SAMPLE_DATA = {
    "A": {"MAT112", "PHY132"},
    "B": {"MAT112", "CSC213"},
    "C": {"MAT112", "STA101"},
    "D": {"PHY132", "CSC213"},
    "E": {"WRI101", "STA101"},
    "F": {"WRI101"},
}


def normalise_code(code):
    """Clean a course code: strip spaces, upper-case (so 'mat 112' == 'MAT112')."""
    return "".join(code.split()).upper()


def load_csv(path):
    """Read registrations from a CSV file into {student_id: set(course codes)}."""
    registrations = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.reader(fh):
            cells = [c.strip() for c in row if c.strip()]
            if len(cells) < 2:
                continue  # blank line or student with no courses
            student, courses = cells[0], cells[1:]
            if student.lower() in ("student_id", "student", "id"):
                continue  # header row
            registrations.setdefault(student, set()).update(
                normalise_code(c) for c in courses
            )
    if not registrations:
        raise ValueError("No valid registrations found in %s" % path)
    return registrations


def read_interactive():
    """Ask the user to type registrations at the keyboard."""
    print("Enter registrations. Type courses separated by commas or spaces.")
    print("Leave the student ID empty to finish.\n")
    registrations = {}
    while True:
        student = input("Student ID: ").strip()
        if not student:
            break
        raw = input("  Courses for %s: " % student).replace(",", " ").split()
        courses = {normalise_code(c) for c in raw}
        if not courses:
            print("  (no courses entered, skipped)")
            continue
        registrations.setdefault(student, set()).update(courses)
    if not registrations:
        raise ValueError("No registrations were entered.")
    return registrations



# ----------------------------------------------------------------------------
# 1b. SCHEDULE (DATE AND TIME) INPUT
# ----------------------------------------------------------------------------
from datetime import datetime


def parse_slot(date_text, start_text, end_text):
    """Turn 'YYYY-MM-DD', 'HH:MM', 'HH:MM' into (start, end) datetimes."""
    start = datetime.strptime(date_text.strip() + " " + start_text.strip(), "%Y-%m-%d %H:%M")
    end = datetime.strptime(date_text.strip() + " " + end_text.strip(), "%Y-%m-%d %H:%M")
    if end <= start:
        raise ValueError("end time must be after start time")
    return start, end


def load_schedule_csv(path):
    """CSV rows: course,date(YYYY-MM-DD),start(HH:MM),end(HH:MM) -> {course: (start, end)}"""
    schedule = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for n, row in enumerate(csv.reader(fh), 1):
            cells = [c.strip() for c in row]
            if len(cells) < 4 or not cells[0] or cells[0].lower() == "course":
                continue
            try:
                schedule[normalise_code(cells[0])] = parse_slot(*cells[1:4])
            except ValueError as err:
                raise ValueError("%s line %d: %s" % (path, n, err))
    return schedule


def ask_slot(course):
    """Keep asking until a valid date and time range is typed."""
    while True:
        try:
            d = input("  %s date (YYYY-MM-DD): " % course)
            s = input("  %s start time (HH:MM, 24-hour): " % course)
            e = input("  %s end time (HH:MM, 24-hour): " % course)
            return parse_slot(d, s, e)
        except ValueError as err:
            print("  Invalid entry (%s). Please try again." % err)


def read_schedule_interactive(courses):
    print("\nNow enter the date and time of each course.")
    return {c: ask_slot(c) for c in courses}


def slots_overlap(a, b):
    """Two (start, end) slots overlap when each starts before the other ends."""
    return a[0] < b[1] and b[0] < a[1]


def find_time_clashes(registrations, schedule):
    """
    A real clash = a student registered for two courses whose times overlap.
    Returns a list of (course_a, course_b, [students]).
    """
    found = {}
    for student, taken in registrations.items():
        timed = sorted(c for c in taken if c in schedule)
        for a, b in combinations(timed, 2):
            if slots_overlap(schedule[a], schedule[b]):
                found.setdefault((a, b), []).append(student)
    return [(a, b, sorted(s)) for (a, b), s in sorted(found.items())]


def print_clashes(registrations, schedule):
    fmt = "%a %d %b %Y %H:%M"
    print("\n--- 0. Timetable clashes (overlapping times) ---")
    missing = sorted(set(get_courses(registrations)) - set(schedule))
    if missing:
        print("  No time given for: %s (skipped)" % ", ".join(missing))
    clashes = find_time_clashes(registrations, schedule)
    if not clashes:
        print("  No clashes: no student has two overlapping courses.")
    for a, b, who in clashes:
        print("  CLASH: %s (%s-%s) overlaps %s (%s-%s)" % (
            a, schedule[a][0].strftime(fmt), schedule[a][1].strftime("%H:%M"),
            b, schedule[b][0].strftime(fmt), schedule[b][1].strftime("%H:%M")))
        print("         students affected: %s" % ", ".join(who))
    return clashes


# ----------------------------------------------------------------------------
# 1c. SUGGESTED FIXES (move a course to a free time)
# ----------------------------------------------------------------------------
from datetime import timedelta


def suggest_fixes(registrations, schedule, day_start="08:00", day_end="18:00",
                  weekends=False, extra_days=6):
    """
    For every clash, move one of the two courses to the nearest free slot that
    (a) lies inside the allowed hours and days and
    (b) does not overlap ANY course that shares a student with it.
    Because rule (b) uses the conflict graph, a move never creates a new clash.
    Returns (moves, new_schedule, unresolved).
    """
    vertices = get_courses(registrations)
    _, edges, _ = build_conflict_graph(registrations)
    adj = adjacency_list(vertices, edges)
    deg = degrees(adj)
    sched = dict(schedule)
    if not sched:
        return [], sched, []
    t0 = datetime.strptime(day_start, "%H:%M").time()
    t1 = datetime.strptime(day_end, "%H:%M").time()
    first = min(s.date() for s, _ in sched.values())
    last = max(max(s.date() for s, _ in sched.values()),
               first + timedelta(days=extra_days))
    days, d = [], first
    while d <= last:
        if weekends or d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)

    def best_slot(c):
        start0, end0 = sched[c]
        length = end0 - start0
        best = None
        for day in days:
            s = datetime.combine(day, t0)
            limit = datetime.combine(day, t1)
            while s + length <= limit:
                cand = (s, s + length)
                if all(not slots_overlap(cand, sched[n]) for n in adj[c] if n in sched):
                    score = abs((day - start0.date()).days) * 100000 + \
                        abs(int((s - start0).total_seconds() // 60))
                    if best is None or score < best[0]:
                        best = (score, cand)
                s += timedelta(minutes=30)
        return best[1] if best else None

    moves, unresolved, skip = [], [], set()
    for _ in range(100):
        todo = [c for c in find_time_clashes(registrations, sched) if c[:2] not in skip]
        if not todo:
            break
        a, b, who = todo[0]
        order = sorted((a, b), key=lambda x: (deg[x], -sched[x][0].timestamp()))
        for c in order:
            slot = best_slot(c)
            if slot:
                other = b if c == a else a
                moves.append({"course": c, "other": other, "students": who,
                              "old": sched[c], "new": slot})
                sched[c] = slot
                break
        else:
            skip.add((a, b))
            unresolved.append((a, b, who))
    return moves, sched, unresolved


def print_fixes(registrations, schedule, clashes, **window):
    if not clashes:
        return
    fmt = "%a %d %b %H:%M"
    moves, _, unresolved = suggest_fixes(registrations, schedule, **window)
    print("\n--- 0b. Suggested fixes ---")
    for m in moves:
        print("  Move %s from %s-%s to %s-%s" % (
            m["course"], m["old"][0].strftime(fmt), m["old"][1].strftime("%H:%M"),
            m["new"][0].strftime(fmt), m["new"][1].strftime("%H:%M")))
        print("    clears the clash with %s (students: %s); no new clash with any"
              % (m["other"], ", ".join(m["students"])))
        print("    course that shares its students.")
    for a, b, who in unresolved:
        print("  No free time found for %s or %s inside the allowed hours." % (a, b))
        print("    Widen the hours (--day-start / --day-end) or add --weekends.")

# ----------------------------------------------------------------------------
# 2. GRAPH CONSTRUCTION  (sets, vertices, edges)
# ----------------------------------------------------------------------------

def get_courses(registrations):
    """Set of all unique courses, returned as a sorted list (the vertex set V)."""
    courses = set()
    for taken in registrations.values():
        courses |= taken
    return sorted(courses)


def build_conflict_graph(registrations):
    """
    Build the conflict graph.
    Returns (vertices, edges, shared) where
        vertices : sorted list of course codes
        edges    : set of frozenset({a, b}) - one per conflicting pair
        shared   : {frozenset({a, b}): sorted list of students taking both}
    """
    vertices = get_courses(registrations)
    edges = set()
    shared = {}
    for student, taken in registrations.items():
        for a, b in combinations(sorted(taken), 2):   # every pair in the set
            edge = frozenset((a, b))
            edges.add(edge)
            shared.setdefault(edge, []).append(student)
    for students in shared.values():
        students.sort()
    return vertices, edges, shared


def adjacency_list(vertices, edges):
    """{course: sorted list of conflicting courses}"""
    adj = {v: set() for v in vertices}
    for edge in edges:
        a, b = tuple(edge)
        adj[a].add(b)
        adj[b].add(a)
    return {v: sorted(n) for v, n in adj.items()}


def adjacency_matrix(vertices, edges):
    """Square 0/1 matrix; entry [i][j] = 1 when courses i and j conflict."""
    index = {v: i for i, v in enumerate(vertices)}
    n = len(vertices)
    matrix = [[0] * n for _ in range(n)]
    for edge in edges:
        a, b = tuple(edge)
        matrix[index[a]][index[b]] = 1
        matrix[index[b]][index[a]] = 1
    return matrix


# ----------------------------------------------------------------------------
# 3. ANALYSIS  (degrees, max degree, timetable support)
# ----------------------------------------------------------------------------

def degrees(adj):
    """Degree of each vertex = number of neighbours."""
    return {v: len(n) for v, n in adj.items()}


def max_degree_courses(deg):
    """Return (max degree, list of courses that reach it)."""
    top = max(deg.values())
    return top, sorted(v for v, d in deg.items() if d == top)


def greedy_colouring(adj, deg):
    """
    Welsh-Powell greedy colouring: courses with the same colour share no
    student, so each colour class can safely be one time slot.
    Returns {course: slot number starting at 1}.
    """
    colour = {}
    for v in sorted(adj, key=lambda x: (-deg[x], x)):   # highest degree first
        used = {colour[n] for n in adj[v] if n in colour}
        c = 1
        while c in used:
            c += 1
        colour[v] = c
    return colour


def suggested_slots(colour):
    """{slot: [courses]} from a colouring."""
    slots = {}
    for course, c in colour.items():
        slots.setdefault(c, []).append(course)
    return {c: sorted(v) for c, v in sorted(slots.items())}


# ----------------------------------------------------------------------------
# 4. OUTPUT
# ----------------------------------------------------------------------------

def print_matrix(vertices, matrix):
    width = max(len(v) for v in vertices) + 2
    print(" " * width + "".join(v.rjust(width) for v in vertices))
    for v, row in zip(vertices, matrix):
        print(v.ljust(width) + "".join(str(x).rjust(width) for x in row))


def print_report(registrations, schedule=None, window=None):
    vertices, edges, shared = build_conflict_graph(registrations)
    adj = adjacency_list(vertices, edges)
    matrix = adjacency_matrix(vertices, edges)
    deg = degrees(adj)
    top, top_courses = max_degree_courses(deg)
    colour = greedy_colouring(adj, deg)
    slots = suggested_slots(colour)

    line = "=" * 64
    print(line)
    print(" COURSE CONFLICT DETECTION SYSTEM")
    print(line)
    print("Students: %d | Courses (vertices): %d | Conflicts (edges): %d"
          % (len(registrations), len(vertices), len(edges)))

    if schedule:
        clashes = print_clashes(registrations, schedule)
        print_fixes(registrations, schedule, clashes, **(window or {}))

    print("\n--- 1. Conflicting course pairs (share students) ---")
    if not edges:
        print("No conflicts found: no student shares two courses.")
    for edge in sorted(tuple(sorted(e)) for e in edges):
        who = ", ".join(shared[frozenset(edge)])
        print("  %s <-> %s   (shared by: %s)" % (edge[0], edge[1], who))

    print("\n--- 2. Adjacency list ---")
    for v in vertices:
        print("  %-8s -> %s" % (v, ", ".join(adj[v]) if adj[v] else "(none)"))

    print("\n--- 3. Adjacency matrix ---")
    print_matrix(vertices, matrix)

    print("\n--- 4. Degree of each course ---")
    for v in vertices:
        print("  deg(%s) = %d" % (v, deg[v]))
    print("  Sum of degrees = %d = 2 x %d edges (Handshake Lemma)"
          % (sum(deg.values()), len(edges)))

    print("\n--- 5. Course(s) with the most conflicts ---")
    print("  Highest degree = %d : %s" % (top, ", ".join(top_courses)))

    print("\n--- 6. Suggested time slots (graph colouring) ---")
    for c, courses in slots.items():
        print("  Slot %d: %s" % (c, ", ".join(courses)))
    print("  %d slot(s) needed; courses in the same slot share no students."
          % len(slots))
    print(line)
    return vertices, edges, colour


def draw_graph(vertices, edges, colour, output="conflict_graph.png", show=True):
    """Draw the conflict graph (nodes coloured by suggested time slot)."""
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx

    G = nx.Graph()
    G.add_nodes_from(vertices)
    G.add_edges_from(tuple(e) for e in edges)

    palette = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#B279A2",
               "#72B7B2", "#EECA3B", "#9D755D"]
    node_colours = [palette[(colour[v] - 1) % len(palette)] for v in G.nodes]
    pos = nx.circular_layout(G) if len(G) > 2 else nx.spring_layout(G, seed=1)

    fig, ax = plt.subplots(figsize=(8, 6))
    nx.draw_networkx_edges(G, pos, ax=ax, width=2, edge_color="#555555")
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colours,
                           node_size=2200, edgecolors="black")
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=9, font_weight="bold",
                            font_color="white")
    ax.set_title("Course Conflict Graph\n(same colour = can share a time slot)")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    print("Graph saved to %s" % output)
    if show:
        plt.show()
    plt.close(fig)


# ----------------------------------------------------------------------------
# 5. MAIN
# ----------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(description="Detect course conflicts using graph theory.")
    p.add_argument("csv", nargs="?", help="CSV file: student_id,course,course,...")
    p.add_argument("--day-start", default="08:00", help="earliest class start for fixes")
    p.add_argument("--day-end", default="18:00", help="latest class end for fixes")
    p.add_argument("--weekends", action="store_true", help="allow Saturday/Sunday in fixes")
    p.add_argument("-s", "--schedule", help="CSV: course,date,start,end")
    p.add_argument("-i", "--interactive", action="store_true", help="enter data by keyboard")
    p.add_argument("-o", "--output", default="conflict_graph.png", help="graph image file")
    p.add_argument("--no-plot", action="store_true", help="skip the graph window")
    args = p.parse_args(argv)

    schedule = None
    try:
        if args.interactive:
            registrations = read_interactive()
            schedule = read_schedule_interactive(get_courses(registrations))
        elif args.csv:
            registrations = load_csv(args.csv)
            if args.schedule:
                schedule = load_schedule_csv(args.schedule)
        else:
            print("(No input given - using built-in sample data.)\n")
            registrations = SAMPLE_DATA
    except (OSError, ValueError) as err:
        print("Error: %s" % err)
        return 1

    vertices, edges, colour = print_report(registrations, schedule, dict(day_start=args.day_start, day_end=args.day_end, weekends=args.weekends))
    try:
        draw_graph(vertices, edges, colour, args.output, show=not args.no_plot)
    except ImportError:
        print("NetworkX/Matplotlib not installed: pip install networkx matplotlib")
    return 0


if __name__ == "__main__":
    sys.exit(main())
