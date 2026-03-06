from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml
from rich import print as rprint


@dataclass
class Config:
    raw: Dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        path = Path(path)
        if not path.exists():
            rprint(f"[red]Config file not found:[/red] {path}")
            rprint("Create one by copying configs/config.yaml and setting your values.")
            sys.exit(1)

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        cfg = cls(raw=data)
        cfg.validate()
        return cfg

    def get(self, *keys: str, default=None):
        cur: Any = self.raw
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def validate(self) -> None:
        """Check that required config keys are present and valid."""
        errors = []

        # Required sections
        for section in ("boundaries", "nightlights", "outputs", "processing"):
            if not isinstance(self.raw.get(section), dict):
                errors.append(f"Missing required section: '{section}'")

        if errors:
            self._fail(errors)

        # Earth Engine project ID
        ee_project = self.get("nightlights", "viirs", "ee_project")
        use_ee = self.get("nightlights", "viirs", "use_earth_engine", default=True)

        if use_ee:
            if ee_project is None or ee_project == "YOUR_GCP_PROJECT_ID":
                errors.append(
                    "nightlights.viirs.ee_project is not set.
"
                    "  Open configs/config.yaml and set it to your Google Cloud project ID.
"
                    "  See HOW-TO-USE.md for step-by-step setup instructions."
                )

        # Service account key: warn if path is set but file doesn't exist
        sa_key = self.get("nightlights", "viirs", "ee_service_account_key")
        if sa_key and isinstance(sa_key, str):
            if not Path(sa_key).exists():
                rprint(
                    f"[yellow]Warning:[/yellow] ee_service_account_key is set to '{sa_key}' "
                    f"but the file does not exist.
"
                    f"  The pipeline will fall back to OAuth credentials (earthengine authenticate)."
                )

        # Year range
        start = self.get("nightlights", "years", "start")
        end = self.get("nightlights", "years", "end")
        if start is not None and end is not None:
            if int(start) > int(end):
                errors.append(
                    f"nightlights.years.start ({start}) is after years.end ({end})"
                )

        # Output paths
        if not self.get("outputs", "csv_path"):
            errors.append("outputs.csv_path is not set")
        if not self.get("outputs", "geojson_dir"):
            errors.append("outputs.geojson_dir is not set")

        if errors:
            self._fail(errors)

    @staticmethod
    def _fail(errors: list[str]) -> None:
        rprint("[bold red]Configuration errors:[/bold red]")
        for e in errors:
            rprint(f"  [red]x[/red] {e}")
        sys.exit(1)
