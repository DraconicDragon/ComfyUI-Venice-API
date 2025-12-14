import logging
from typing import Any, Dict, Iterable

from comfy_api.latest import InputImpl, _io, io

from ..nodes.catalog_utils import video_model_specs
from ..nodes.utils import encode_tensor_for_vision, ensure_prompt_length
from ..nodes.video_utils import (
    get_testing_video_path,
    list_testing_videos,
    poll_video_until_ready,
    queue_video_job,
)

LOG = logging.getLogger(__name__)


class GenerateVideoFromText(io.ComfyNode):
    _DEFAULT_DURATIONS = ["4s", "5s", "6s", "8s", "10s", "12s", "14s", "15s", "16s", "18s", "20s"]
    _DEFAULT_ASPECT_RATIOS = ["16:9", "9:16", "1:1"]
    _DEFAULT_RESOLUTIONS = ["1080p", "720p", "480p"]

    @classmethod
    def _video_specs(cls) -> Dict[str, Dict[str, Any]]:
        specs = video_model_specs() or {}
        if not specs:
            raise ValueError(
                "No Venice video model specs available; refresh the catalog in VeniceAI settings and retry."
            )
        return specs

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
    def _first_or_default(cls, values: Iterable[str] | None, fallback: list[str]) -> list[str]:
        items = list(values) if values else []
        return items or list(fallback)

    @classmethod
    def _build_model_options(cls) -> list[_io.DynamicCombo.Option]:
        specs = cls._video_specs()
        options: list[_io.DynamicCombo.Option] = []

        for model_id, spec in sorted(specs.items()):
            constraints = spec.get("constraints") or {}
            aspect_ratios = cls._first_or_default(constraints.get("aspect_ratios"), cls._DEFAULT_ASPECT_RATIOS)
            resolutions = cls._first_or_default(constraints.get("resolutions"), cls._DEFAULT_RESOLUTIONS)
            durations = cls._first_or_default(constraints.get("durations"), cls._DEFAULT_DURATIONS)
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

            option_inputs.extend(
                [
                    io.Combo.Input(
                        id=cls._option_input_id(model_id, "duration"),
                        display_name="durationaa",
                        options=durations,
                        default=durations[0],
                        tooltip="Duration allowed by the selected model",
                    ),
                    io.Combo.Input(
                        cls._option_input_id(model_id, "aspect_ratio"),
                        display_name="aspect_ratio",
                        options=aspect_ratios,
                        default=aspect_ratios[0],
                        tooltip="Aspect ratios allowed by the selected model",
                    ),
                    io.Combo.Input(
                        cls._option_input_id(model_id, "resolution"),
                        display_name="resolution",
                        options=resolutions,
                        default=resolutions[0],
                        tooltip="Resolutions allowed by the selected model",
                    ),
                ]
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

            options.append(_io.DynamicCombo.Option(model_id, option_inputs))

        return options

    @classmethod
    def define_schema(cls) -> io.Schema:
        video_choices = list_testing_videos()
        existing_default = video_choices[0] if video_choices else "none_available"
        choices_for_combo = video_choices or ["none_available"]

        model_options = cls._build_model_options()

        return io.Schema(
            node_id="TextToVideo_VENICE",
            display_name="Generate Video from Text (Venice)",
            category="venice.ai",
            inputs=[
                _io.DynamicCombo.Input(
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
                io.Boolean.Input(
                    "use_existing_video",
                    default=True,
                    tooltip="Use a cached video from testing_video instead of calling the Venice API",
                ),
                io.Combo.Input(
                    "existing_video",
                    options=choices_for_combo,
                    default=existing_default,
                    tooltip="Select the cached video file that should be emitted when bypassing the API",
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
        use_existing_video,
        existing_video,
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

        durations = cls._first_or_default(constraints.get("durations"), cls._DEFAULT_DURATIONS)
        aspect_ratios = cls._first_or_default(constraints.get("aspect_ratios"), cls._DEFAULT_ASPECT_RATIOS)
        resolutions = cls._first_or_default(constraints.get("resolutions"), cls._DEFAULT_RESOLUTIONS)

        duration = cls._get_option_value(model, model_id, "duration") or durations[0]
        aspect_ratio = cls._get_option_value(model, model_id, "aspect_ratio") or aspect_ratios[0]
        resolution = cls._get_option_value(model, model_id, "resolution") or resolutions[0]

        if duration not in durations:
            raise ValueError(f"Duration '{duration}' is not supported by model {model_id}")
        if aspect_ratio not in aspect_ratios:
            raise ValueError(f"Aspect ratio '{aspect_ratio}' is not supported by model {model_id}")
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
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "audio": audio,
        }

        if constraints.get("model_type") == "image-to-video":
            image = cls._get_option_value(model, model_id, "image")
            if image is None:
                raise ValueError(f"Model {model_id} requires an input image")
            payload["image_url"] = encode_tensor_for_vision(image)

        if use_existing_video:
            if not existing_video:
                raise ValueError("No cached video selected")
            cached_files = list_testing_videos()
            if existing_video not in cached_files:
                raise ValueError("Selected cached video does not exist anymore")
            video_path = get_testing_video_path(existing_video)
            if not video_path.exists():
                raise ValueError("Cached video file disappeared")
            return io.NodeOutput(InputImpl.VideoFromFile(video_path))

        model_id_resp, queue_id = queue_video_job(payload)
        video_path, _ = poll_video_until_ready(model=model_id_resp, queue_id=queue_id)

        return io.NodeOutput(InputImpl.VideoFromFile(video_path))
