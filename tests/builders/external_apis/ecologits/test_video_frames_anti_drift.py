"""
Anti-drift guard for the EcoLogits video frame-count formula.

This test is intentionally tight: it pins the exact upstream formula
``duration_to_frames(d) == int(d * 24 + 1)``. EcoLogits' compute-side regression
is calibrated against the 24 fps assumption baked into this formula, and our
``EcoLogitsVideoGenExternalAPIJob.update_data_transferred`` reuses ``fps = 24 / s``
as its local hypothesis. If upstream re-fits this formula (e.g. switches to
30 fps or adds an offset), our network-energy contribution drifts silently
from what the compute-side numbers assume.

This test is **meant to fail loudly** on upstream changes. Do not soften it
by loosening the equality — fix the integration's ``fps`` hypothesis (and
re-document the assumption) instead.
"""
import unittest

from ecologits.estimations.video import duration_to_frames


class TestVideoFramesAntiDrift(unittest.TestCase):
    def test_duration_to_frames_matches_pinned_formula(self):
        for duration in (0.0, 0.5, 1.0, 2.0, 8.0, 12.5, 60.0, 600.0):
            self.assertEqual(
                int(duration * 24 + 1),
                duration_to_frames(duration),
                msg=(
                    f"EcoLogits duration_to_frames({duration}) drifted from the pinned 24 fps formula. "
                    f"The integration's `fps = 24 / s` hypothesis in update_data_transferred must be revisited."
                ),
            )


if __name__ == "__main__":
    unittest.main()
