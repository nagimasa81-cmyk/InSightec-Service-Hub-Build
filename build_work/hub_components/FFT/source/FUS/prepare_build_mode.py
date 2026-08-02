from __future__ import annotations

import json
import os
from pathlib import Path


def parse_bool(value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Standard/local and Hub assembly builds are release builds by default.
# build_selected_with_guide.yml explicitly supplies 0 to create a guide build.
release_mode = parse_bool(os.environ.get("INSIGHTEC_RELEASE_MODE"), True)
payload = {
    "release_mode_supported": True,
    "environment_variable": "INSIGHTEC_RELEASE_MODE",
    "release_value": "1",
    "release_mode": release_mode,
    "guide_tour_enabled_in_release": not release_mode,
    "profile": "hub-release-no-guide" if release_mode else "individual-guide-enabled",
}
Path("release_mode.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(f"FUS Image Explore build profile: {payload['profile']}")
