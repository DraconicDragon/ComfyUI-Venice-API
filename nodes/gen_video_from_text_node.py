import logging
from typing import Any, Dict, Iterable

from comfy_api.latest import InputImpl, io

from ..nodes.catalog_utils import video_model_specs
from ..nodes.utils import encode_tensor_for_vision, ensure_prompt_length
from ..nodes.video_utils import poll_video_until_ready, queue_video_job

LOG = logging.getLogger(__name__)


class GenerateVideoFromText(io.ComfyNode):

    @staticmethod
    def _option_input_id(model_id: str, field: str) -> str:
        sanitized = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in model_id)
        return f"{sanitized}__{field}"

    @staticmethod
    def _constraint_values(value: Iterable | None) -> list[str]:
        if not value:
            return []
        if isinstance(value, (str, bytes)):
            normalized = str(value).strip()
            return [normalized] if normalized else []
        return [str(item) for item in value if item]

    @classmethod
    def _video_specs(cls) -> Dict[str, Dict[str, Any]]:
        specs = video_model_specs() or {}
        if not specs:
            raise ValueError(
                "No Venice video model specs available; refresh the catalog in VeniceAI settings and retry."
            )
        return specs

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
    def _build_model_options(cls) -> list[io.DynamicCombo.Option]:
        specs = cls._video_specs()
        options: list[io.DynamicCombo.Option] = []

        def _sorted_models_by_group(group: str) -> list[tuple[str, Dict[str, Any]]]:
            return sorted(
                (
                    (model_id, spec)
                    for model_id, spec in specs.items()
                    if spec.get("constraints", {}).get("model_type") == group
                ),
                key=lambda item: item[0],
            )

        ordered_specs = [
            # didnt know about this, is same as [] + []
            *_sorted_models_by_group("text-to-video"),
            *_sorted_models_by_group("image-to-video"),
        ]

        for model_id, spec in ordered_specs:
            constraints = spec.get("constraints") or {}
            aspect_ratios = cls._constraint_values(constraints.get("aspect_ratios"))
            resolutions = cls._constraint_values(constraints.get("resolutions"))
            durations = cls._constraint_values(constraints.get("durations"))
            audio_default = bool(constraints.get("audio")) if constraints.get("audio") is not None else False

            option_inputs: list[io.Input] = []
            if constraints.get("model_type") == "image-to-video":
                option_inputs.append(
                    io.Image.Input(
                        cls._option_input_id(model_id, "image"),
                        display_name="image",
                        tooltip="Source image for image-to-video models",
                    )
                )

            if durations:
                option_inputs.append(
                    io.Combo.Input(
                        id=cls._option_input_id(model_id, "duration"),
                        display_name="duration",
                        options=durations,
                        default=durations[0],
                        tooltip="Duration allowed by the selected model",
                    )
                )
            if aspect_ratios:
                option_inputs.append(
                    io.Combo.Input(
                        cls._option_input_id(model_id, "aspect_ratio"),
                        display_name="aspect_ratio",
                        options=aspect_ratios,
                        default=aspect_ratios[0],
                        tooltip="Aspect ratios allowed by the selected model",
                    )
                )
            if resolutions:
                option_inputs.append(
                    io.Combo.Input(
                        cls._option_input_id(model_id, "resolution"),
                        display_name="resolution",
                        options=resolutions,
                        default=resolutions[0],
                        tooltip="Resolutions allowed by the selected model",
                    )
                )

            if constraints.get("audio_configurable"):
                option_inputs.append(
                    io.Boolean.Input(
                        cls._option_input_id(model_id, "audio"),
                        display_name="audio",
                        default=audio_default,
                        tooltip="Generate audio (only when the model allows toggling)",
                    )
                )

            options.append(io.DynamicCombo.Option(model_id, option_inputs))

        return options

    @classmethod
    def define_schema(cls) -> io.Schema:
        model_options = cls._build_model_options()

        return io.Schema(
            node_id="TextToVideo_VENICE",
            display_name="Generate Video from Text (Venice)",
            category="venice.ai",
            inputs=[
                io.DynamicCombo.Input(
                    "model",
                    options=model_options,
                    tooltip="Select a Venice video model to auto-populate valid parameters",
                ),
                io.String.Input(
                    "prompt",
                    default="A cat made of lettuce flying through space",
                    placeholder="Positive Prompt. Example: A cat made of lettuce flying through space",
                    tooltip="Text prompt to generate the video from",
                    multiline=True,
                ),
                io.String.Input(
                    "negative_prompt",
                    default="low resolution, error, worst quality, low quality, defects",
                    placeholder="Negative Prompt",
                    tooltip="Negative prompt to avoid elements in the video",
                    multiline=True,
                ),
            ],
            outputs=[
                io.Video.Output(id="video", display_name="Video"),
            ],
        )

    @classmethod
    def execute(
        cls,
        model,
        prompt,
        negative_prompt,
    ) -> io.NodeOutput:
        ensure_prompt_length(prompt, 2500, label="Prompt")
        ensure_prompt_length(negative_prompt, 2500, label="Negative Prompt", allow_empty=True)

        if not isinstance(model, dict) or "model" not in model:
            raise ValueError("Model selection is required")

        model_id = model.get("model")
        specs = cls._video_specs()
        spec = specs.get(model_id)
        if not spec:
            raise ValueError("Selected model is missing from the Venice catalog; refresh the catalog and try again.")
        constraints = spec.get("constraints") or {}

        durations = cls._constraint_values(constraints.get("durations"))
        aspect_ratios = cls._constraint_values(constraints.get("aspect_ratios"))
        resolutions = cls._constraint_values(constraints.get("resolutions"))

        duration = cls._get_option_value(model, model_id, "duration")
        if durations:
            if duration is None:
                raise ValueError(f"Model {model_id} requires a duration selection")
            if duration not in durations:
                raise ValueError(f"Duration '{duration}' is not supported by model {model_id}")

        aspect_ratio = cls._get_option_value(model, model_id, "aspect_ratio")
        if aspect_ratios:
            if aspect_ratio is None:
                raise ValueError(f"Model {model_id} requires an aspect ratio selection")
            if aspect_ratio not in aspect_ratios:
                raise ValueError(f"Aspect ratio '{aspect_ratio}' is not supported by model {model_id}")

        resolution = cls._get_option_value(model, model_id, "resolution")
        if resolutions:
            if resolution is None:
                raise ValueError(f"Model {model_id} requires a resolution selection")
            if resolution not in resolutions:
                raise ValueError(f"Resolution '{resolution}' is not supported by model {model_id}")

        audio_configurable = bool(constraints.get("audio_configurable"))
        audio_default = bool(constraints.get("audio")) if constraints.get("audio") is not None else False
        audio_value = cls._get_option_value(model, model_id, "audio") if audio_configurable else None
        audio = audio_value if audio_value is not None else audio_default

        payload = {
            "model": model_id,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
        }
        if durations:
            payload["duration"] = duration
        if aspect_ratios:
            payload["aspect_ratio"] = aspect_ratio
        if resolutions:
            payload["resolution"] = resolution
        if audio is not None:
            payload["audio"] = audio

        if constraints.get("model_type") == "image-to-video":
            image = cls._get_option_value(model, model_id, "image")
            if image is None:
                raise ValueError(f"Model {model_id} requires an input image")
            payload["image_url"] = encode_tensor_for_vision(image)

        model_id_resp, queue_id = queue_video_job(payload)
        video_path, _ = poll_video_until_ready(model=model_id_resp, queue_id=queue_id)

        return io.NodeOutput(InputImpl.VideoFromFile(video_path))
