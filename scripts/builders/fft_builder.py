from .base import BaseBuilder
class FFTBuilder(BaseBuilder):
    name="fft"
    def build_env(self):
        e=super().build_env(); e["INSIGHTEC_RUNTIME"]="FFT"; e["INSIGHTEC_INCLUDE_PYDICOM_DATA"]="1"; return e
