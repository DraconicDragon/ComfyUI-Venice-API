from __future__ import annotations

import base64
import io

import numpy as np
import torch
from PIL import Image
from requests import RequestException

from ..globals import API_ENDPOINTS
from ..venice_client import VeniceAPIError, client
from ..venice_config import config as venice_config


def _round_down(value: int, multiple: int) -> int:
    return (value // multiple) * multiple


def ensure_prompt_length(text: str, maximum: int, label: str, *, allow_empty: bool = False) -> None:
    if not text:
        if allow_empty:
            return
        raise ValueError(f"{label} is required and cannot be empty")
    if len(text) > maximum:
        raise ValueError(f"{label} exceeds the maximum length of {maximum} characters")


def encode_tensor_for_vision(image_tensor: torch.Tensor, *, max_encoded_bytes: int = 4_500_000) -> str:
    """
    Encode a vision tensor into a Base64-encoded PNG string suitable for transmission.

    Parameters
    ----------
    image_tensor : torch.Tensor
        A height×width×(3 or 4) tensor representing an image in the range [0, 1].
    max_encoded_bytes : int, optional
        Maximum allowed length of the Base64 payload. Defaults to 4,500,000 bytes.

    Returns
    -------
    str
        A data URI containing the PNG image encoded in Base64.

    Raises
    ------
    ValueError
        If the tensor does not have 3 dimensions or the last dimension is not 3 or 4.
    """
    tensor = image_tensor.detach().cpu()
    if tensor.ndim != 3 or tensor.shape[-1] not in {3, 4}:
        raise ValueError("Vision images must be height×width×(3 or 4 channels)")

    if tensor.shape[-1] > 3:
        tensor = tensor[:, :, :3]

    array = (tensor.numpy() * 255).clip(0, 255).astype(np.uint8)
    pil_image = Image.fromarray(array, "RGB")

    original_width, original_height = pil_image.size
    aspect_ratio = original_width / original_height

    if original_width > original_height:
        target_width = 1024
        target_height = int(target_width / aspect_ratio)
        if target_height < 256:
            target_height = 256
            target_width = int(target_height * aspect_ratio)
    else:
        target_height = 1024
        target_width = int(target_height * aspect_ratio)
        if target_width < 256:
            target_width = 256
            target_height = int(target_width / aspect_ratio)

    target_width = _round_down(target_width, 14)
    target_height = _round_down(target_height, 14)

    if min(target_width, target_height) < 256:
        if target_width < target_height:
            target_width = _round_down(256 + 13, 14)
            target_height = _round_down(int(target_width / aspect_ratio), 14)
        else:
            target_height = _round_down(256 + 13, 14)
            target_width = _round_down(int(target_height * aspect_ratio), 14)

    pil_image = pil_image.resize((target_width, target_height), Image.LANCZOS)

    buffered = io.BytesIO()
    pil_image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    while len(img_base64) > max_encoded_bytes:
        scaling_factor = (max_encoded_bytes / len(img_base64)) ** 0.5
        new_width = max(_round_down(int(target_width * scaling_factor), 14), 256)
        new_height = max(_round_down(int(target_height * scaling_factor), 14), 256)

        pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
        target_width, target_height = new_width, new_height

        buffered = io.BytesIO()
        pil_image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{img_base64}"


def ensure_multiple_of(width: int, height: int, *, multiple: int = 32) -> None:
    bad_dimensions = []
    if width % multiple != 0:
        bad_dimensions.append(f"width ({width})")
    if height % multiple != 0:
        bad_dimensions.append(f"height ({height})")
    if bad_dimensions:
        dimensions = " and ".join(bad_dimensions)
        raise ValueError(f"{dimensions} must be multiples of {multiple}")


# unused right now, might be useful, or not
def ensure_api_key_valid() -> None:
    key = venice_config.apikey.strip()
    if not key:
        raise ValueError("VeniceAI API key is missing; set it in the VeniceAI settings first.")

    try:
        client.get_json(API_ENDPOINTS["list_api_keys"])
    except VeniceAPIError as exc:
        raise ValueError("Unable to validate the VeniceAI API key.", exc) from exc
    except RequestException as exc:
        raise ValueError("Unable to reach VeniceAI while validating the API key.", exc) from exc

    return None
