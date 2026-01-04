from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Sequence, Tuple

from ..venice_catalog import get_characters, get_models, get_styles

log = logging.getLogger(__name__)


def _safe_values(
    loader,
    key: str,
    fallback: Sequence[str] = ("This list is unavailable; check logs for details?",),
) -> Tuple[str, ...]:
    """
    Safely retrieves a sequence of string values from a loader payload keyed by `key`.

    Attempts to call the provided `loader` callable to obtain a payload, logging failures
    and falling back to the provided default values. Extracts and normalizes the value
    associated with `key`, ensuring it is returned as a tuple of strings. If the extracted
    value is missing, empty, or otherwise falsy, the fallback values are returned instead.
    """
    try:
        payload = loader()
    except Exception as exc:
        log.debug("Failed to load %s catalog: %s", key, exc)
        return tuple(fallback)

    raw = payload.get(key)
    if raw is None:
        return tuple(fallback)

    if isinstance(raw, Iterable) and not isinstance(raw, (str, bytes)):
        values = tuple(str(item) for item in raw if item)
    else:
        values = tuple(str(raw)) if raw else ()

    return values or tuple(fallback)


def image_model_choices() -> Tuple[str, ...]:
    return _safe_values(lambda: get_models(), "image_models")


def text2video_model_choices() -> Tuple[str, ...]:
    return _safe_values(lambda: get_models(), "text2video_models")


def image2video_model_choices() -> Tuple[str, ...]:
    return _safe_values(lambda: get_models(), "image2video_models")


def video_model_specs() -> Dict[str, Dict[str, Any]]:
    """Return a by-id mapping of video model specs with constraints for DynamicCombo use."""
    models = get_models()
    return models.get("video_models_by_id", {})


def image_model_specs() -> Dict[str, Dict[str, Any]]:
    """Return a by-id mapping of image model specs and constraints for UI validation."""
    models = get_models()
    return models.get("image_models_by_id", {})


def text_model_specs() -> Dict[str, Dict[str, Any]]:
    """Return a by-id mapping of text model specs and constraints for UI validation."""
    models = get_models()
    return models.get("text_models_by_id", {})


def text_model_choices() -> Tuple[str, ...]:
    return _safe_values(lambda: get_models(), "text_models")


def tts_model_choices() -> Tuple[str, ...]:
    return _safe_values(lambda: get_models(), "tts_models")


def tts_voice_choices() -> Tuple[str, ...]:
    return _safe_values(lambda: get_models(), "tts_voices")


def style_choices() -> Tuple[str, ...]:
    return _safe_values(lambda: get_styles(), "data")


def character_choices() -> Tuple[str, ...]:
    return _safe_values(lambda: get_characters(), "characters")
