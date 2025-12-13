from comfy_api.latest import InputImpl, io

from ..nodes.catalog_utils import image2video_model_choices, text2video_model_choices
from ..nodes.utils import ensure_prompt_length
from ..nodes.video_utils import (
    get_testing_video_path,
    list_testing_videos,
    poll_video_until_ready,
    queue_video_job,
)


class GenerateVideoFromText:
    @classmethod
    def INPUT_TYPES(cls):
        i2v_models = image2video_model_choices()
        t2v_models = text2video_model_choices()
        model_choices = i2v_models + t2v_models
        # todo: make model choices show model name instead of id for readability and prepend i2v/t2v

        video_choices = list_testing_videos()
        existing_default = video_choices[0] if video_choices else "none_available"
        choices_for_combo = video_choices or ["none_available"]

        return {
            "required": {
                "model": (
                    model_choices,
                    {
                        # "default": model_choices[0],
                        "default": "longcat-distilled-text-to-video",
                        "tooltip": "Model to use for text-to-video generation",
                    },
                ),
                "prompt": (
                    "STRING",
                    {
                        "default": "A cat made of lettuce flying through space",
                        "placeholder": "Positive Prompt. Example: A cat made of lettuce flying through space",
                        "tooltip": "Text prompt to generate the video from",
                        "multiline": True,
                    },
                ),
                "negative_prompt": (
                    "STRING",
                    {
                        "default": "low resolution, error, worst quality, low quality, defects",
                        "placeholder": "Negative Prompt",
                        "multiline": True,
                        "tooltip": "Negative prompt to avoid elements in the video",
                    },
                ),
                "duration": (
                    ["4s", "5s", "6s", "8s", "10s", "12s", "14s", "15s", "16s", "18s", "20s"],
                    {
                        "default": "5s",
                        "tooltip": "Duration of the generated video",
                    },
                ),
                "aspect_ratio": (
                    ["16:9", "9:16", "1:1"],
                    {
                        "default": "16:9",
                        "tooltip": "Aspect ratio for the video",
                    },
                ),
                "resolution": (
                    ["1080p", "720p", "480p"],
                    {
                        "default": "720p",
                        "tooltip": "Resolution of the generated video",
                    },
                ),
                "audio": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Generate audio if the model supports it",
                    },
                ),
                "use_existing_video": (
                    "BOOLEAN",
                    {
                        "default": True,  # NOTE: IMPORTANT DEFAULT TO TRUE FOR TESTING PURPOSES THE WHOLE TIME DO NOT REMOVE UNTIL DEPLOYMENT
                        "tooltip": "Use a cached video from testing_video instead of calling the Venice API",
                    },
                ),
                "existing_video": (
                    choices_for_combo,
                    {
                        "default": existing_default,
                        "tooltip": "Select the cached video file that should be emitted when bypassing the API",
                    },
                ),
            }
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "execute"
    CATEGORY = "venice.ai"

    def execute(
        self,
        model,
        prompt,
        negative_prompt,
        duration,
        aspect_ratio,
        resolution,
        audio,
        use_existing_video,
        existing_video,
    ):
        ensure_prompt_length(prompt, 2500, label="Prompt")
        ensure_prompt_length(negative_prompt, 2500, label="Negative Prompt", allow_empty=True)

        payload = {
            "model": model,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            # "audio": audio, # todo: this will error with bad request if model without audio support is used, fix with node schema v3 rewrite
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


NODE_CLASS_MAPPINGS = {
    "TextToVideo_VENICE": GenerateVideoFromText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TextToVideo_VENICE": "Generate Video from Text (Venice)",
}
