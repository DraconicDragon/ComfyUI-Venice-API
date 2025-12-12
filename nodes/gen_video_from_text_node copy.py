import base64
import io
import logging

from PIL import Image
from torchvision.transforms import ToPILImage, ToTensor

from ..globals import API_ENDPOINTS
from ..nodes.catalog_utils import text2video_model_choices
from ..nodes.utils import ensure_prompt_length
from ..venice_client import client


class GenerateVideoFromText:
    @classmethod
    def INPUT_TYPES(cls):
        model_choices = text2video_model_choices()

        return {
            "required": {
                "model": (
                    model_choices,
                    {
                        "default": model_choices[0],
                        "tooltip": "Model to use for text-to-video generation",
                    },
                ),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "execute"
    CATEGORY = "venice.ai"

    def execute(self, model):
        url = API_ENDPOINTS["video_queue"]

        # ensure_prompt_length(enhance_prompt, 1500, label="Enhance prompt", allow_empty=True)

        # return dummy bhwc tensor for now
        pil_image = Image.new("RGB", (256, 256), color=(73, 109, 137))
        tensor = ToTensor()(pil_image).permute(1, 2, 0).unsqueeze(0)  # Shape: (1, H, W, C)
        return (tensor,)


NODE_CLASS_MAPPINGS = {
    "TextToVideo_VENICE": GenerateVideoFromText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TextToVideo_VENICE": "Generate Video from Text (Venice)",
}
