from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {"apikey": ""}


class VeniceConfig:
    _instance: "VeniceConfig" | None = None

    def __new__(cls) -> "VeniceConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.path = Path(__file__).with_name("veniceai_config.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._read()
        self._sync_env()

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            self._write(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
        try:
            with self.path.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        except (ValueError, json.JSONDecodeError):
            self._write(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

    def _write(self, data: Dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2)

    def _sync_env(self) -> None:
        os.environ.setdefault("VENICEAI_API_KEY", self._data.get("apikey", ""))

    @property
    def apikey(self) -> str:
        return self._data.get("apikey", "") or ""

    def save_apikey(self, key: str) -> None:
        self._data["apikey"] = key
        self._write(self._data)
        os.environ["VENICEAI_API_KEY"] = key


config = VeniceConfig()
