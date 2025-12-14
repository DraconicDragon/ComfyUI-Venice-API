from comfy_api.latest import InputImpl, io

from ..nodes.catalog_utils import image2video_model_choices, text2video_model_choices
from ..nodes.utils import ensure_prompt_length
from ..nodes.video_utils import (
    get_testing_video_path,
    list_testing_videos,
    poll_video_until_ready,
    queue_video_job,
)


class GenerateVideoFromText(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        i2v_models = image2video_model_choices()
        t2v_models = text2video_model_choices()
        model_choices = i2v_models + t2v_models

        video_choices = list_testing_videos()
        existing_default = video_choices[0] if video_choices else "none_available"
        choices_for_combo = video_choices or ["none_available"]

        return io.Schema(
            node_id="TextToVideo_VENICE",
            display_name="Generate Video from Text (Venice)",
            category="venice.ai",
            inputs=[
                io.Combo.Input(
                    "model",
                    options=model_choices,
                    default="longcat-distilled-text-to-video",
                    tooltip="Model to use for text-to-video generation",
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
                io.Combo.Input(
                    "duration",
                    options=["4s", "5s", "6s", "8s", "10s", "12s", "14s", "15s", "16s", "18s", "20s"],
                    default="5s",
                    tooltip="Duration of the generated video",
                ),
                io.Combo.Input(
                    "aspect_ratio",
                    options=["16:9", "9:16", "1:1"],
                    default="16:9",
                    tooltip="Aspect ratio for the video",
                ),
                io.Combo.Input(
                    "resolution",
                    options=["1080p", "720p", "480p"],
                    default="720p",
                    tooltip="Resolution of the generated video",
                ),
                io.Boolean.Input(
                    "audio",
                    default=True,
                    tooltip="Generate audio if the model supports it",
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
        duration,
        aspect_ratio,
        resolution,
        audio,
        use_existing_video,
        existing_video,
    ) -> io.NodeOutput:
        ensure_prompt_length(prompt, 2500, label="Prompt")
        ensure_prompt_length(negative_prompt, 2500, label="Negative Prompt", allow_empty=True)

        payload = {
            "model": model,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            # "audio": audio, # todo: this will error if the model lacks audio support, fix with a future schema update
        }

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

        model_id, queue_id = queue_video_job(payload)
        video_path, _ = poll_video_until_ready(model=model_id, queue_id=queue_id)

        return io.NodeOutput(InputImpl.VideoFromFile(video_path))
