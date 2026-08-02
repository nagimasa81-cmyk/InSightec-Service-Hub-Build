import unittest
import numpy as np
from core.hybrid_compensation import detect_artifacts

class Commit0100Tests(unittest.TestCase):
    def test_validation_metadata_exists(self):
        n=128; y,x=np.mgrid[:n,:n]; c=(n-1)/2; r=np.hypot(y-c,x-c)
        k=np.exp(-(r/18)**2).astype(complex)
        out=detect_artifacts(k,'Auto',3.0,'Conservative')
        self.assertEqual(out.stats.get('detector_revision'),'mri_auto_detection_v8_stage2_artifact_validation')
        self.assertIn('artifact_validation',out.stats)
        self.assertLess(np.count_nonzero(out.mask)/out.mask.size,0.04)

    def test_true_block_survives_validation(self):
        n=128; rng=np.random.default_rng(10)
        k=rng.normal(0,.01,(n,n))+1j*rng.normal(0,.01,(n,n))
        k[24:31,18:34]+=9; k[-31:-24,-34:-18]+=9
        out=detect_artifacts(k,'Auto',2.5,'Balanced')
        self.assertGreater(np.count_nonzero(out.mask),0)
        self.assertTrue(any(v.get('accepted') for v in out.stats['artifact_validation'].values()))

if __name__=='__main__': unittest.main()
