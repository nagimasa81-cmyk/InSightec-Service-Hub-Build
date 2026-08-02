import unittest
from pathlib import Path
import numpy as np

from core.hybrid_compensation import detect_artifacts as hybrid_detect_artifacts


class Commit0099Tests(unittest.TestCase):
    def test_explicit_auto_controls_exist(self):
        text = Path('app.py').read_text(encoding='utf-8')
        for name in (
            'comp_mask_expansion_auto', 'comp_donor_halo_auto',
            'comp_pass_count_auto', 'comp_strength_override_auto',
        ):
            self.assertIn(name, text)
        self.assertNotIn('setSpecialValueText("Auto")', text)
        self.assertIn('if self.comp_mask_expansion_auto.isChecked()', text)
        self.assertIn('if self.comp_strength_override_auto.isChecked()', text)

    def test_smooth_normal_signal_not_overmasked(self):
        n = 128
        y, x = np.mgrid[:n, :n]
        cy = cx = (n - 1) / 2
        r = np.hypot(y-cy, x-cx)
        mag = np.exp(-(r/18.0)**2) + 0.12*np.exp(-(r/44.0)**2)
        phase = 0.01 * (x-cx)
        k = mag * np.exp(1j*phase)
        result = hybrid_detect_artifacts(k, 'Auto', 3.0, 'Conservative')
        self.assertLess(np.count_nonzero(result.mask) / result.mask.size, 0.04)
        self.assertEqual(result.stats.get('detector_revision'), 'mri_auto_detection_v8_stage2_artifact_validation')

    def test_compact_block_survives_guard(self):
        n = 128
        rng = np.random.default_rng(9)
        k = (rng.normal(0, 0.01, (n,n)) + 1j*rng.normal(0, 0.01, (n,n)))
        k[30:36, 18:30] += 8.0
        k[-36:-30, -30:-18] += 8.0
        result = hybrid_detect_artifacts(k, 'Auto', 2.5, 'Balanced')
        self.assertGreater(np.count_nonzero(result.mask), 0)
        self.assertLess(np.count_nonzero(result.mask) / result.mask.size, 0.06 + 1e-3)


if __name__ == '__main__':
    unittest.main()
