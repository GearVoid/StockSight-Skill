import unittest

from core import detect_anomalies, normalize_quote_data

from tests.fixtures import sample_stock


class QualityAndDetectorTests(unittest.TestCase):
    def test_normalize_quote_data_clears_suspicious_optional_fields(self):
        stock = sample_stock(
            volume_ratio=-1.0,
            turnover_rate=678.8,
            volume=-100,
            amount=-1.0,
        )

        normalized, notes = normalize_quote_data([stock])

        self.assertEqual(normalized[0].volume_ratio, 0.0)
        self.assertEqual(normalized[0].turnover_rate, 0.0)
        self.assertEqual(normalized[0].volume, 0)
        self.assertEqual(normalized[0].amount, 0.0)
        self.assertTrue(notes)

    def test_detector_ignores_unavailable_turnover_rate(self):
        stock = sample_stock(volume_ratio=1.0, turnover_rate=0.0, change_percent=1.0)

        signals = detect_anomalies([stock])

        self.assertFalse(
            [signal for signal in signals if "turnover" in signal.risk_type.lower()]
        )


if __name__ == "__main__":
    unittest.main()

