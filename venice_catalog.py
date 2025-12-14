import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from .venice_client import VeniceAPIError, VeniceClient

DATA_DIR = Path(__file__).with_name("data")
DATA_DIR.mkdir(exist_ok=True)


class CatalogStore:
    def __init__(
        self,
        name: str,
        default_factory: Optional[Callable[[], Dict[str, Any]]] = None,
        legacy_name: Optional[str] = None,
    ) -> None:
        self.file = DATA_DIR / name
        self._default_factory = default_factory or (lambda: {"object": "list", "data": []})
        self._legacy_name = legacy_name

    def load(self) -> Dict[str, Any]:
        if not self.file.exists():
            return self._load_legacy() or self._default_factory()
        try:
            with self.file.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        except (ValueError, json.JSONDecodeError):
            return self._load_legacy() or self._default_factory()

    def save(self, payload: Dict[str, Any]) -> None:
        with self.file.open("w", encoding="utf-8") as fp:
            json.dump(payload, fp, indent=2)

    def _load_legacy(self) -> Dict[str, Any] | None:
        if not self._legacy_name:
            return None
        legacy_file = self.file.with_name(self._legacy_name)
        if not legacy_file.exists():
            return None
        try:
            with legacy_file.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        except (ValueError, json.JSONDecodeError):
            return None

    def filter_by_type(self, payload: Dict[str, Any], *types: str) -> List[Dict[str, Any]]:
        data = payload.get("data") or []
        return [entry for entry in data if entry.get("type") in types]


_model_store = CatalogStore("models_list.json", legacy_name="all_model_list.json")
_styles_store = CatalogStore(
    "styles_list.json",
    lambda: {"data": ["none"], "object": "list"},
    legacy_name="styles_list.json",
)
_characters_store = CatalogStore(
    "characters_list.json",
    lambda: {"data": [], "object": "list"},
    legacy_name="characters_list.json",
)
_client = VeniceClient()

# to prevent spamming api.
# can be bypassed by setting force_refresh=True in get_* calls
_CACHE_TTL = float(os.environ.get("VENICE_CATALOG_TTL", "900"))
_models_last_refresh = 0.0
_styles_last_refresh = 0.0
_characters_last_refresh = 0.0
LOG = logging.getLogger(__name__)


def _enrich_models(raw: Dict[str, Any]) -> Dict[str, Any]:
    return raw.copy()


def _extract_video_models(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract Venice video models and expose a by-id mapping of their constraints.

    The mapping is intentionally lightweight (id, name, model_type, constraints) so downstream
    callers (nodes) can build DynamicCombo inputs without re-parsing the raw payload.
    """
    data = payload.get("data", []) or []
    by_id: Dict[str, Any] = {}

    for model in data:
        if model.get("type") != "video":
            continue
        model_id = model.get("id")
        if not model_id:
            continue

        model_spec = model.get("model_spec") or {}
        constraints = model_spec.get("constraints") or {}
        model_type = constraints.get("model_type")
        if not isinstance(constraints, dict):
            constraints = {}

        entry = {
            "id": model_id,
            "name": model_spec.get("name"),
            "model_type": model_type,
            "constraints": {
                "aspect_ratios": constraints.get("aspect_ratios") or [],
                "resolutions": constraints.get("resolutions") or [],
                "durations": constraints.get("durations") or [],
                "audio": constraints.get("audio"),
                "audio_configurable": constraints.get("audio_configurable"),
                "model_type": model_type,
            },
            "raw": model,
        }
        by_id[model_id] = entry

    return by_id


def _should_refresh(last_refresh: float) -> bool:
    if _CACHE_TTL <= 0:
        return False
    return (time.monotonic() - last_refresh) > _CACHE_TTL


def _record_models_refresh() -> None:
    global _models_last_refresh
    _models_last_refresh = time.monotonic()


def _record_styles_refresh() -> None:
    global _styles_last_refresh
    _styles_last_refresh = time.monotonic()


def _record_characters_refresh() -> None:
    global _characters_last_refresh
    _characters_last_refresh = time.monotonic()


def _should_attempt_refresh(payload: Dict[str, Any], should_refresh: bool) -> bool:
    if not should_refresh:
        return False
    if _client.dry_run and payload.get("data"):
        LOG.debug("Dry-run mode skipping catalog refresh because cached data is available.")
        return False
    return True


def refresh_models(model_type: str = "all") -> Dict[str, Any]:
    try:
        raw = _client.list_models(model_type or "all")
    except VeniceAPIError as exc:
        LOG.error("Failed to refresh Venice model list: %s", exc)
        raise
    enriched = _enrich_models(raw)
    if not enriched.get("data"):
        raise VeniceAPIError("Venice returned an empty model catalog")
    _model_store.save(enriched)
    _record_models_refresh()
    return enriched


def refresh_styles() -> Dict[str, Any]:
    try:
        raw = _client.list_styles()
    except VeniceAPIError as exc:
        LOG.error("Failed to refresh Venice styles list: %s", exc)
        raise

    data = raw.get("data")
    if not data:
        raise VeniceAPIError("Venice returned an empty styles catalog")

    sorted_data = sorted(data)
    sorted_data.insert(0, "none")
    payload = {"object": raw.get("object", "list"), "data": sorted_data}
    _styles_store.save(payload)
    _record_styles_refresh()
    return payload


def refresh_characters() -> Dict[str, Any]:
    try:
        raw = _client.list_characters()
    except VeniceAPIError as exc:
        LOG.error("Failed to refresh Venice characters list: %s", exc)
        raise

    items = raw.get("data")
    if not items:
        raise VeniceAPIError("Venice returned an empty characters catalog")

    sorted_items = sorted(items, key=lambda item: item.get("slug", "")) if isinstance(items, Iterable) else []
    payload = {"object": raw.get("object", "list"), "data": sorted_items}
    _characters_store.save(payload)
    _record_characters_refresh()
    return payload


def get_models(model_type: Optional[str] = None, *, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Return model metadata from the Venice catalog, optionally filtered by type.

    Parameters
    ----------
    model_type : Optional[str]
        If provided, filters models by the requested type (e.g., "image", "text", "tts") and
        returns only that subset; when omitted, the response contains categorized lists
        of model IDs, available TTS voices, and the raw payload.

    Returns
    -------
    Dict[str, Any]
        The filtered or fully categorized model information, keyed by categories such as
        "image_models", "text_models", "tts_models", "tts_voices", and "model_list_json".
        When a model_type filter is applied, returns a single "models" key with matching entries.
    """
    payload = _model_store.load()
    should_refresh = force_refresh or not payload.get("data") or _should_refresh(_models_last_refresh)
    if _should_attempt_refresh(payload, should_refresh):
        payload = refresh_models()
    if model_type:
        return {"models": _model_store.filter_by_type(payload, model_type)}

    video_models_by_id = _extract_video_models(payload)

    filtered = {
        "image_models": sorted([m.get("id") for m in payload.get("data", []) if m.get("type") == "image"]),
        "text_models": sorted([m.get("id") for m in payload.get("data", []) if m.get("type") == "text"]),
        "tts_models": sorted([m.get("id") for m in payload.get("data", []) if m.get("type") == "tts"]),
        "tts_voices": sorted(
            [
                f"{m.get('id', '')} - {voice}"
                for m in payload.get("data", [])
                if m.get("type") == "tts"
                for voice in (m.get("model_spec", {}).get("voices") or [])
            ]
        ),
        "text2video_models": sorted(
            [
                model_id
                for model_id, spec in video_models_by_id.items()
                if spec.get("constraints", {}).get("model_type") == "text-to-video"
            ]
        ),
        "image2video_models": sorted(
            [
                model_id
                for model_id, spec in video_models_by_id.items()
                if spec.get("constraints", {}).get("model_type") == "image-to-video"
            ]
        ),
        "video_models_by_id": video_models_by_id,
        "model_list_json": payload,
    }
    return filtered


def get_styles(*, force_refresh: bool = False) -> Dict[str, Any]:
    payload = _styles_store.load()
    should_refresh = force_refresh or not payload.get("data") or _should_refresh(_styles_last_refresh)
    if _should_attempt_refresh(payload, should_refresh):
        payload = refresh_styles()
    return payload


def get_characters(*, force_refresh: bool = False) -> Dict[str, Any]:
    payload = _characters_store.load()
    should_refresh = force_refresh or not payload.get("data") or _should_refresh(_characters_last_refresh)
    if _should_attempt_refresh(payload, should_refresh):
        payload = refresh_characters()
    data = payload.get("data", [])
    characters = [item.get("slug") for item in data if isinstance(item, dict) and item.get("slug")]
    return {"characters": characters}
