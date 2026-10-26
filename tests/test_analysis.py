import unittest
from datetime import date, datetime, timezone

from backend import analysis

U = timezone.utc


class AnalysisTests(unittest.TestCase):
    def test_decision_forecast_uses_latest_before_cutoff(self):
        t = datetime(2026, 1, 3, 12, tzinfo=U)
        fc = {t: [(datetime(2026, 1, 2, 6, tzinfo=U), 100.0),
                  (datetime(2026, 1, 2, 8, tzinfo=U), 200.0),
                  (datetime(2026, 1, 2, 10, tzinfo=U), 300.0)]}  # after 09:00 cutoff: must be ignored
        cutoff = datetime(2026, 1, 2, 9, tzinfo=U)
        self.assertEqual(analysis.decision_forecast(fc, t, cutoff)[1], 200.0)
        self.assertIsNone(analysis.decision_forecast(fc, t, datetime(2026, 1, 2, 5, tzinfo=U)))

    def test_metrics(self):
        m = analysis.metrics([(100, 120), (100, 80)])  # errors -20, +20
        self.assertEqual(m["mae"], 20)
        self.assertEqual(m["bias"], 0)
        self.assertAlmostEqual(m["rmse"], 20)
        self.assertEqual(m["rel_mae_pct"], 20)

    def test_day_series_has_48_points_and_handles_missing(self):
        pts = analysis.day_series({}, {}, date(2026, 1, 2), 9)
        self.assertEqual(len(pts), 48)
        self.assertIsNone(pts[0]["forecast"])


if __name__ == "__main__":
    unittest.main()
