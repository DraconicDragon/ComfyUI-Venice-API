import logging
from typing import Any, Dict

import torch

from comfy_api.latest import io

from ..globals import API_ENDPOINTS
from ..nodes.catalog_utils import image_model_choices, image_model_specs, style_choices
from ..nodes.gen_image_base import GenerateImageBase
from ..nodes.utils import ensure_multiple_of, ensure_prompt_length
from ..venice_client import client

LOG = logging.getLogger(__name__)


class GenerateImage(io.ComfyNode):
    _processor = GenerateImageBase()

    @classmethod
    def _image_specs(cls) -> Dict[str, Dict[str, Any]]:
        specs = image_model_specs() or {}
        if not specs:
            raise ValueError(
                "No Venice image model specs available; refresh the catalog in VeniceAI settings and retry."
            )
        return specs

    @staticmethod
    def _prompt_limit_from_spec(spec: Dict[str, Any] | None, default: int = 1500) -> int:
        if not spec:
            return default
        constraints = spec.get("constraints") or {}
        limit = constraints.get("promptCharacterLimit")
        if isinstance(limit, int) and limit > 0:
            return limit
        try:
            normalized = int(limit)
        except (TypeError, ValueError):
            return default
        return normalized if normalized > 0 else default

    @classmethod
    def define_schema(cls) -> io.Schema:
        model_choices = list(image_model_choices())
        if not model_choices:
            model_choices = ["none_available"]
        else: # nano banana has it's own node
            model_choices = [m for m in model_choices if m != "nano-banana"]
        style_options = list(style_choices())
        if not style_options:
            style_options = ["none_available"]

        return io.Schema(
            node_id="GenerateImage_VENICE",
            display_name="Generate Image (Venice)",
            category="venice.ai",
            inputs=[
                io.Combo.Input(
                    "model",
                    options=model_choices,
                    default=model_choices[0],
                    tooltip="Model to use for image generation",
                ),
                io.String.Input(
                    "prompt",
                    default="A flying cat made of lettuce",
                    multiline=True,
                    placeholder="Positive Prompt. Example: A flying cat made of lettuce",
                    tooltip="The text prompt to guide the image generation. Character limit depends on model (usually around 1500-7500 characters).",
                ),
                io.String.Input(
                    "neg_prompt",
                    default="",
                    multiline=True,
                    placeholder="Negative Prompt. Example: low quality, vacant scene",
                    tooltip="Negative prompt (ignored for models that do not support CFG - z-image-turbo, flux-dev, etc.)",
                ),
                io.Int.Input(
                    "width",
                    default=1024,
                    min=0,
                    max=2048,
                    step=16,
                    tooltip="Width of the image. Maximum allowed by venice.ai at time of writing is 1280. Some models allow smaller stepping, like 1 or 8, while some others require stepping of 16 and so. If no data for this exists for a model, the UI will default to 16 since that is a safe number usually.",
                ),
                io.Int.Input(
                    "height",
                    default=1024,
                    min=0,
                    max=2048,
                    step=16,
                    tooltip="Height of the image. Maximum allowed by venice.ai at time of writing is 1280. Some models allow smaller stepping, like 1 or 8, while some others require stepping of 16 and so. If no data for this exists for a model, the UI will default to 16 since that is a safe number usually.",
                ),
                io.Int.Input(
                    "batch_size",
                    default=1,
                    min=1,
                    max=4,
                    tooltip="Number of images to generate in a single batch (sends that many sequential requests)",
                ),
                io.Int.Input(
                    "steps",
                    default=20,
                    min=1,
                    max=50,
                    tooltip="Number of inference steps. Some models do not require high steps like z-image-turbo (8 steps)",
                ),
                io.Float.Input(
                    "guidance",
                    default=3.0,
                    min=0.0,
                    max=20.0,
                    step=0.05,
                    tooltip="CFG scale parameter (or Guidance for Flux-dev models and similar. Has no effect on models like z-image-turbo and similar).",
                ),
                io.Combo.Input(
                    "style_preset",
                    options=style_options,
                    default=style_options[0],
                    tooltip="Style preset to apply to the generated images",
                ),
                io.Boolean.Input(
                    "hide_watermark",
                    default=True,
                    tooltip="Hide the Venice watermark when possible",
                ),
                io.Boolean.Input(
                    "safe_mode",
                    default=False,
                    tooltip="Enable safe mode (blurs NSFW content)",
                ),
                io.Int.Input(
                    "seed",
                    optional=True,
                    default=-1,
                    min=-0x3B9AC9FF,
                    max=0x3B9AC9FF,
                    tooltip="Seed for the generation; use -1 for random values",
                ),
            ],
            outputs=[io.Image.Output(id="image", display_name="Image")],
        )

    @classmethod
    def execute(
        cls,
        model,
        prompt,
        neg_prompt,
        width,
        height,
        batch_size,
        steps,
        guidance,
        style_preset,
        hide_watermark,
        safe_mode,
        seed=-1,
    ) -> io.NodeOutput:
        specs = cls._image_specs()
        spec = specs.get(model)
        if spec is None:
            raise ValueError("Selected model is missing from the Venice catalog; refresh the catalog and try again.")
        prompt_limit = cls._prompt_limit_from_spec(spec)

        ensure_multiple_of(width, height, multiple=spec.get("constraints", {}).get("dimensionMultiple", 16))
        ensure_prompt_length(prompt, prompt_limit, "Prompt")
        ensure_prompt_length(neg_prompt, prompt_limit, "Negative Prompt", allow_empty=True)

        seed_value = -1 if seed is None else seed
        images_tensor = ()

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "negative_prompt": neg_prompt,
                "style_preset": style_preset,
                "height": height,
                "width": width,
                "steps": steps,
                "cfg_scale": guidance,
                "seed": seed_value,
                "return_binary": False,
                "hide_watermark": hide_watermark,
                "safe_mode": safe_mode,
                "format": "png",
                "embed_exif_metadata": True,
            }
            if style_preset in ("none", "none_available"):
                payload.pop("style_preset", None)

            for i in range(batch_size):
                payload["seed"] = seed_value + i
                response_json = client.post_json(API_ENDPOINTS["image_generate"], payload)
                images_tensor += cls._processor.process_result(response_json)

            merged = torch.cat(images_tensor, dim=0)
            return io.NodeOutput(merged)

        except Exception as exc:
            raise Exception(f"Error processing image result: {str(exc)}") from exc
