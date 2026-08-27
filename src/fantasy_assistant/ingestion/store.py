"""Immutable local snapshot storage for raw and normalized source data."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class SnapshotPaths:
    raw: Path
    normalized: Path


class SnapshotStore:
    """Write timestamped snapshots without overwriting prior observations."""

    def __init__(self, root: Path = Path("data")) -> None:
        self.root = root

    @staticmethod
    def _validate_component(value: str) -> str:
        if not value or not _SAFE_COMPONENT.fullmatch(value):
            raise ValueError(f"Unsafe snapshot path component: {value!r}")
        return value

    @staticmethod
    def _write_json(path: Path, value: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            temporary_path = Path(handle.name)
        temporary_path.replace(path)

    def save(
        self,
        *,
        source: str,
        league_id: str,
        season: int,
        fetched_at: str,
        raw: Mapping[str, Any],
        normalized: Mapping[str, Any],
    ) -> SnapshotPaths:
        source = self._validate_component(source)
        league_id = self._validate_component(str(league_id))
        timestamp = self._validate_component(fetched_at.replace(":", "-").replace("+", "_"))
        relative = Path(source) / league_id / str(season) / f"{timestamp}.json"
        paths = SnapshotPaths(
            raw=self.root / "raw" / relative,
            normalized=self.root / "normalized" / relative,
        )
        self._write_json(paths.raw, raw)
        self._write_json(paths.normalized, normalized)
        return paths
