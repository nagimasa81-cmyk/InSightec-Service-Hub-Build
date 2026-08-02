import logging
from pathlib import Path

def configure_logging() -> Path:
    folder=Path.home()/"SonicationReplayEngine"/"logs"; folder.mkdir(parents=True,exist_ok=True)
    path=folder/"Sonication_Replay_Engine.log"
    logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",handlers=[logging.FileHandler(path,encoding="utf-8"),logging.StreamHandler()],force=True)
    return path
