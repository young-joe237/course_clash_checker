import unittest
import networkx as nx
from conflict_detector import *


class TestConflicts(unittest.TestCase):
    def setUp(self):
        # Slide 7 example: MAT conflicts with PHY, CSC, STA (degree 3)
        self.reg = {"A": {"MAT", "PHY"}, "B": {"MAT", "CSC"}, "C": {"MAT", "STA"}}
        self.v, self.e, self.shared = build_conflict_graph(self.reg)
        self.adj = adjacency_list(self.v, self.e)
        self.deg = degrees(self.adj)

    def test_vertices(self):
        self.assertEqual(self.v, ["CSC", "MAT", "PHY", "STA"])

    def test_edges(self):
        self.assertEqual(len(self.e), 3)
        self.assertIn(frozenset(("MAT", "PHY")), self.e)
        self.assertNotIn(frozenset(("PHY", "CSC")), self.e)

    def test_degree_and_max(self):
        self.assertEqual(self.deg["MAT"], 3)
        self.assertEqual(max_degree_courses(self.deg), (3, ["MAT"]))

    def test_matrix_symmetric_zero_diagonal(self):
        m = adjacency_matrix(self.v, self.e)
        for i in range(len(m)):
            self.assertEqual(m[i][i], 0)
            for j in range(len(m)):
                self.assertEqual(m[i][j], m[j][i])

    def test_handshake_lemma(self):
        self.assertEqual(sum(self.deg.values()), 2 * len(self.e))

    def test_single_course_student_no_conflict(self):
        v, e, _ = build_conflict_graph({"X": {"ENG"}})
        self.assertEqual(len(e), 0)

    def test_tie_for_max_degree(self):
        reg = {"A": {"P", "Q"}}
        v, e, _ = build_conflict_graph(reg)
        top, who = max_degree_courses(degrees(adjacency_list(v, e)))
        self.assertEqual((top, who), (1, ["P", "Q"]))

    def test_shared_students_recorded(self):
        reg = {"A": {"X", "Y"}, "B": {"X", "Y"}}
        _, _, shared = build_conflict_graph(reg)
        self.assertEqual(shared[frozenset(("X", "Y"))], ["A", "B"])

    def test_colouring_is_proper(self):
        v, e, _ = build_conflict_graph(SAMPLE_DATA)
        adj = adjacency_list(v, e)
        col = greedy_colouring(adj, degrees(adj))
        for edge in e:
            a, b = tuple(edge)
            self.assertNotEqual(col[a], col[b])

    def test_matches_networkx(self):
        v, e, _ = build_conflict_graph(SAMPLE_DATA)
        G = nx.Graph()
        G.add_nodes_from(v)
        G.add_edges_from(tuple(x) for x in e)
        adj = adjacency_list(v, e)
        self.assertEqual(dict(G.degree()), degrees(adj))

    def test_normalise(self):
        self.assertEqual(normalise_code(" mat 101 "), "MAT101")


class TestTimeClashes(unittest.TestCase):
    def slot(self, d, a, b):
        return parse_slot(d, a, b)

    def test_overlap_detected(self):
        a = self.slot("2026-12-07", "09:00", "11:00")
        b = self.slot("2026-12-07", "10:00", "12:00")
        self.assertTrue(slots_overlap(a, b))

    def test_back_to_back_is_not_clash(self):
        a = self.slot("2026-12-07", "09:00", "11:00")
        b = self.slot("2026-12-07", "11:00", "13:00")
        self.assertFalse(slots_overlap(a, b))

    def test_different_dates_no_clash(self):
        a = self.slot("2026-12-07", "09:00", "11:00")
        b = self.slot("2026-12-08", "09:00", "11:00")
        self.assertFalse(slots_overlap(a, b))

    def test_clash_needs_shared_student(self):
        sched = {"X": self.slot("2026-12-07", "09:00", "11:00"),
                 "Y": self.slot("2026-12-07", "10:00", "12:00")}
        self.assertEqual(find_time_clashes({"A": {"X"}, "B": {"Y"}}, sched), [])
        self.assertEqual(find_time_clashes({"A": {"X", "Y"}}, sched), [("X", "Y", ["A"])])

    def test_bad_time_rejected(self):
        with self.assertRaises(ValueError):
            parse_slot("2026-12-07", "12:00", "10:00")


if __name__ == "__main__":
    unittest.main()
