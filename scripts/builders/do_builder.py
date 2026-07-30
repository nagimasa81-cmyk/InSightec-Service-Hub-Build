from .base import BaseBuilder
class DOBuilder(BaseBuilder):
    name="do"
    def build_env(self):
        e=super().build_env(); e["INSIGHTEC_RUNTIME"]="R5"; e["INSIGHTEC_NATIVE_HANDOFF"]="1"; return e
