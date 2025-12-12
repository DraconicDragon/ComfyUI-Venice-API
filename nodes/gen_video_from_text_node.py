import logging

from ..nodes.catalog_utils import text2video_model_choices
from ..nodes.utils import ensure_prompt_length
from ..nodes.video_utils import poll_video_until_ready, queue_video_job

LOG = logging.getLogger(__name__)


class GenerateVideoFromText:
    @classmethod
    def INPUT_TYPES(cls):
        model_choices = text2video_model_choices()

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
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("video_path", "queue_id")
    FUNCTION = "execute"
    CATEGORY = "venice.ai"

    def execute(self, model, prompt, negative_prompt, duration, aspect_ratio, resolution, audio):
        ensure_prompt_length(prompt, 2500, label="Prompt")
        ensure_prompt_length(negative_prompt, 2500, label="Negative Prompt", allow_empty=True)

        payload = {
            "model": model,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "audio": audio,
        }

        model_id, queue_id = queue_video_job(payload)
        video_path, _ = poll_video_until_ready(model=model_id, queue_id=queue_id)

        return (video_path, queue_id)


NODE_CLASS_MAPPINGS = {
    "TextToVideo_VENICE": GenerateVideoFromText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TextToVideo_VENICE": "Generate Video from Text (Venice)",
}
