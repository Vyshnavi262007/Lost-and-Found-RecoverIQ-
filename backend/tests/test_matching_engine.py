"""Pure-Python tests of the matching engine (no database needed)."""
import datetime as dt
import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location(
    "matching", pathlib.Path(__file__).resolve().parent.parent / "apps" / "reports" / "matching.py")
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

D = dt.date(2026, 10, 10)


def item(id, type_, text, cat=1, group="documents", loc=1, x=0, y=0, days=0, block="A"):
    return {"id": id, "type": type_, "category_id": cat, "category_group": group, "text": text,
            "location": {"id": loc, "x": x, "y": y, "block": block}, "date": D + dt.timedelta(days=days)}


class EngineTests(unittest.TestCase):
    def score(self, a, b, **kw):
        sim = m.text_similarities(a["text"], [b["text"]])[0]
        return m.compare(a, b, sim, **kw)

    def test_good_match_scores_high_with_explanation(self):
        lost = item(1, "lost", "black leather wallet fossil")
        found = item(2, "found", "black leather wallet", loc=2, x=80, days=1)
        r = self.score(lost, found)
        self.assertGreater(r.score, 0.6)
        self.assertIn("leather", r.explanation)
        self.assertIsNone(r.components["visual"]["score"])

    def test_same_type_excluded(self):
        a, b = item(1, "lost", "wallet"), item(2, "lost", "wallet")
        self.assertIsNone(self.score(a, b))

    def test_self_excluded(self):
        a = item(1, "lost", "wallet")
        self.assertIsNone(m.compare(a, dict(a, type="found"), 1.0))

    def test_incompatible_category_excluded(self):
        a = item(1, "lost", "phone", cat=1, group="documents")
        b = item(2, "found", "phone", cat=2, group="electronics")
        self.assertIsNone(self.score(a, b))

    def test_related_category_partial_credit(self):
        a = item(1, "lost", "wallet", cat=1, group="documents")
        b = item(2, "found", "wallet", cat=3, group="documents")
        self.assertEqual(self.score(a, b).components["category"]["score"], 0.5)

    def test_date_decay_and_implausible_order(self):
        a = item(1, "lost", "wallet")
        near = self.score(a, item(2, "found", "wallet", days=1)).components["date"]["score"]
        far = self.score(a, item(3, "found", "wallet", days=30)).components["date"]["score"]
        before = self.score(a, item(4, "found", "wallet", days=-5)).components["date"]["score"]
        self.assertGreater(near, far)
        self.assertLess(before, 0.6)

    def test_distance_lowers_location_score(self):
        a = item(1, "lost", "wallet")
        close = self.score(a, item(2, "found", "wallet", loc=2, x=50)).components["location"]["score"]
        distant = self.score(a, item(3, "found", "wallet", loc=3, x=900)).components["location"]["score"]
        self.assertGreater(close, distant)

    def test_missing_visual_renormalises_weights(self):
        a, b = item(1, "lost", "black wallet"), item(2, "found", "black wallet")
        no_photo = self.score(a, b)
        self.assertAlmostEqual(sum(c["weight_used"] for c in no_photo.components.values()), 1.0, places=2)
        with_bad_photo = self.score(a, b, visual=0.0)
        self.assertLess(with_bad_photo.score, no_photo.score)

    def test_configurable_weights(self):
        a, b = item(1, "lost", "red umbrella"), item(2, "found", "blue phone case", days=1)
        sim = m.text_similarities(a["text"], [b["text"]])[0]
        text_heavy = m.compare(a, b, sim, {"category": 0, "text": 1, "location": 0, "date": 0, "visual": 0})
        self.assertEqual(text_heavy.score, 0.0)

    def test_tfidf_ranks_relevant_first(self):
        sims = m.text_similarities("black leather wallet", ["black leather wallet", "red umbrella", "wallet brown"])
        self.assertGreater(sims[0], sims[2])
        self.assertEqual(sims[1], 0.0)

    def test_empty_text_is_none(self):
        self.assertEqual(m.text_similarities("", ["wallet"]), [None])


if __name__ == "__main__":
    unittest.main()
