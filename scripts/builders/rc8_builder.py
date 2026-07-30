from .base import BaseBuilder
class RC8Builder(BaseBuilder):
    name="rc8"
    def build_env(self):
        e=super().build_env(); e["INSIGHTEC_RUNTIME"]=self.ctx.runtime; return e
