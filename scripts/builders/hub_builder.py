from __future__ import annotations
import json
from pathlib import Path
from .base import BaseBuilder


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _write(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class HubBuilder(BaseBuilder):
    name = "hub"

    def build_env(self):
        env = super().build_env()
        env["INSIGHTEC_RUNTIME"] = "RC9"
        env["INSIGHTEC_HUB_VARIANT"] = self.ctx.hub_variant
        return env

    def prepare_source(self):
        root = self.ctx.source_root
        variant = self.ctx.hub_variant
        if variant not in {"zip_drop", "card_launcher"}:
            raise ValueError(f"Unsupported Hub variant: {variant}")

        config_path = root / "config.json"
        if not config_path.is_file():
            raise FileNotFoundError("Hub config.json was not found")
        config = _read(config_path)
        config["hub_variant"] = variant
        config["startup_page"] = "auto_analyzer" if variant == "zip_drop" else "tools"
        config["guide_tour_enabled"] = bool(self.ctx.guide)
        config["build_selection"] = {
            "hub_variant": variant,
            "guide_enabled": bool(self.ctx.guide),
            "service_hub_modules": self.ctx.registry["workflow_selection"]["service_hub_modules"],
        }
        _write(config_path, config)

        version_path = root / "version.json"
        version = _read(version_path)
        version["hub_variant"] = variant
        version["guide_tour"] = "included" if self.ctx.guide else "removed"
        version["build_selection"] = f"{variant}-{'guide' if self.ctx.guide else 'no-guide'}"
        _write(version_path, version)

        release_path = root / "release_mode.json"
        if release_path.is_file():
            release = _read(release_path)
            release["guide_tour_enabled_in_release"] = bool(self.ctx.guide)
            release["hub_variant"] = variant
            _write(release_path, release)

        contract_path = root / "insightec_build_contract.json"
        if contract_path.is_file():
            contract = _read(contract_path)
            contract["guide_runtime"] = bool(self.ctx.guide)
            contract.setdefault("release_mode", {})["guide_tour_enabled"] = bool(self.ctx.guide)
            contract["selected_hub_variant"] = variant
            _write(contract_path, contract)

        marker = root / "BUILD_SELECTION.json"
        _write(marker, {
            "hub_variant": variant,
            "startup_page": config["startup_page"],
            "guide_enabled": bool(self.ctx.guide),
            "modules": self.ctx.registry["workflow_selection"]["service_hub_modules"],
        })

    def build(self):
        self.prepare_source()
        return super().build()
