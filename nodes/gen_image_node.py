import logging
from typing import Any, Dict

import torch

from comfy_api.latest import io

from ..globals import API_ENDPOINTS
from ..nodes.catalog_utils import image_model_specs, style_choices
from ..nodes.gen_image_base import GenerateImageBase
from ..nodes.utils import ensure_multiple_of, ensure_prompt_length
from ..venice_client import client

LOG = logging.getLogger(__name__)


class GenerateImage(io.ComfyNode):
    _processor = GenerateImageBase()

    @classmethod
    def _image_specs(cls, require: bool = False) -> Dict[str, Dict[str, Any]]:
        specs = image_model_specs() or {}
        if require and not specs:
            raise ValueError(
                "No Venice image model specs available; refresh the catalog in VeniceAI settings and retry."
            )
        return specs

    @staticmethod
    def _style_options() -> tuple[str, ...]:
        options = list(style_choices())
        if not options:
            return ("none_available",)
        return tuple(options)

    @staticmethod
    def _option_input_id(model_id: str, field: str) -> str:
        sanitized = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in model_id)
        return f"{sanitized}__{field}"

    @classmethod
    def _get_option_value(cls, model_payload: Dict[str, Any], model_id: str, field: str) -> Any:
        candidates = (
            cls._option_input_id(model_id, field),
            field,
            f"{field}__{model_id}",
            f"{model_id}__{field}",
        )
        for key in candidates:
            if key in model_payload:
                return model_payload.get(key)
        return None

    @classmethod
    def _resolve_option_value(cls, model_payload: Dict[str, Any], model_id: str, field: str, default: Any) -> Any:
        value = cls._get_option_value(model_payload, model_id, field)
        return default if value is None else value

    @staticmethod
    def _coerce_positive_int(value: Any) -> int | None:
        try:
            candidate = int(value)
        except (TypeError, ValueError):
            return None
        return candidate if candidate > 0 else None

    @staticmethod
    def _width_height_divisor(constraints: Dict[str, Any]) -> int:
        divisor = constraints.get("widthHeightDivisor")
        if isinstance(divisor, int) and divisor > 0:
            return divisor
        return 16

    @classmethod
    def _steps_limits(cls, constraints: Dict[str, Any]) -> tuple[int, int]:
        steps = constraints.get("steps") or {}
        default = cls._coerce_positive_int(steps.get("default"))
        max_value = cls._coerce_positive_int(steps.get("max"))
        default = default if default is not None else 20
        max_steps = max_value if max_value is not None else 50
        if default > max_steps:
            max_steps = default
        return default, max_steps

    @classmethod
    def _model_option_inputs(
        cls,
        model_id: str,
        width_divisor: int,
        steps_default: int,
        steps_max: int,
    ) -> list[io.Input]:
        return [
            io.Int.Input(
                cls._option_input_id(model_id, "width"),
                display_name="width",
                default=1024,
                min=0,
                max=2048,
                step=width_divisor,
                tooltip="Target width for the generated image; stepping is tied to the model's `widthHeightDivisor`. Defaults to 16",
            ),
            io.Int.Input(
                cls._option_input_id(model_id, "height"),
                display_name="height",
                default=1024,
                min=0,
                max=2048,
                step=width_divisor,
                tooltip="Target height for the generated image; stepping is tied to the model's `widthHeightDivisor`. Defaults to 16",
            ),
            io.Int.Input(
                cls._option_input_id(model_id, "steps"),
                display_name="steps",
                default=steps_default,
                min=1,
                max=steps_max,
                tooltip="Number of inference steps. Model constraints can reduce the range and have different defaults.",
            ),
        ]

    @classmethod
    def _build_model_options(cls) -> list[io.DynamicCombo.Option]:
        specs = cls._image_specs(require=False)
        options: list[io.DynamicCombo.Option] = []

        def _sorted_model_items() -> list[tuple[str, Dict[str, Any]]]:
            return sorted(specs.items())

        for model_id, spec in _sorted_model_items():
            if (
                model_id == "nano-banana"
            ):  # todo: implement ui for nano-banana, might be able to use code from video node
                continue
            constraints = spec.get("constraints") or {}
            width_divisor = cls._width_height_divisor(constraints)
            steps_default, steps_max = cls._steps_limits(constraints)
            option_inputs = cls._model_option_inputs(
                model_id,
                width_divisor,
                steps_default,
                steps_max,
            )
            options.append(io.DynamicCombo.Option(model_id, option_inputs))

        if not options:
            option_inputs = cls._model_option_inputs(
                "none_available",
                16,
                20,
                50,
            )
            options.append(io.DynamicCombo.Option("none_available", option_inputs))

        return options

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
        model_options = cls._build_model_options()
        style_options = cls._style_options()

        return io.Schema(
            node_id="GenerateImage_VENICE",
            display_name="Generate Image (Venice)",
            category="venice.ai",
            inputs=[
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
                    tooltip=(
                        "Negative prompt (ignored for models that do not support CFG - z-image-turbo, flux-dev, etc.). "
                        "Character limit depends on model (usually around 1500-7500 characters)."
                    ),
                ),
                io.DynamicCombo.Input(
                    "model",
                    options=model_options,
                    tooltip="Select a Venice image model to auto-populate valid parameters",
                ),
                io.Int.Input(
                    "batch_size",
                    default=1,
                    min=1,
                    max=4,
                    tooltip="Number of images to generate in a single batch (sequential requests, does not use variants api (yet?)).",
                ),
                io.Float.Input(
                    "guidance",
                    default=6.0,
                    min=0.0,
                    max=20.0,
                    step=0.05,
                    tooltip=(
                        "CFG scale (SDXL based models work well with 6.0, most newer ones work with 3-4. "
                        "Closed Source models may ignore this setting and distilled models too, such as z-image-turbo or flux-dev and similar)."
                    ),
                ),
                io.Combo.Input(
                    "style_preset",
                    options=list(style_options),
                    default=style_options[0],
                    tooltip="Venice.ai style preset to apply to the generated image.",
                ),
                io.Boolean.Input(
                    "hide_watermark",
                    default=True,
                    tooltip="Hide the Venice watermark when possible.",
                ),
                io.Boolean.Input(
                    "safe_mode",
                    default=False,
                    tooltip="Enable safe mode (blurs NSFW content).",
                ),
                io.Int.Input(
                    "seed",
                    optional=True,
                    default=42,
                    min=-0x3B9AC9FF,
                    max=0x3B9AC9FF,
                    tooltip="Seed for reproducibility.",
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
        guidance,
        batch_size,
        style_preset,
        hide_watermark,
        safe_mode,
        seed=-1,
    ) -> io.NodeOutput:
        if not isinstance(model, dict) or "model" not in model:
            raise ValueError("Model selection is required")

        model_id = model.get("model")
        specs = cls._image_specs(require=True)
        spec = specs.get(model_id)
        if not spec:
            raise ValueError("Selected model is missing from the Venice catalog; refresh the catalog and try again.")

        constraints = spec.get("constraints") or {}
        prompt_limit = cls._prompt_limit_from_spec(spec)
        width_height_divisor = cls._width_height_divisor(constraints)
        steps_default, _steps_max = cls._steps_limits(constraints)

        width = int(cls._resolve_option_value(model, model_id, "width", 1024))
        height = int(cls._resolve_option_value(model, model_id, "height", 1024))
        steps = int(cls._resolve_option_value(model, model_id, "steps", steps_default))
        guidance = float(guidance)
        batch_size = int(batch_size)
        style_options = cls._style_options()
        if style_preset not in style_options:
            style_preset = style_options[0]
        hide_watermark = bool(hide_watermark)
        safe_mode = bool(safe_mode)
        seed = seed

        ensure_multiple_of(width, height, multiple=width_height_divisor)
        ensure_prompt_length(prompt, prompt_limit, "Prompt")
        ensure_prompt_length(neg_prompt, prompt_limit, "Negative Prompt", allow_empty=True)

        seed_value = -1 if seed is None else int(seed)
        images_tensor = ()

        try:
            payload = {
                "model": model_id,
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
