import base64
import io
import logging
import os

import requests
from PIL import Image
from torchvision.transforms import ToPILImage, ToTensor

from ..globals import API_ENDPOINTS, VENICEAI_BASE_URL


class I2IEnhanceUpscale:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "scale": (
                    "FLOAT",
                    {
                        "default": 2,
                        "min": 1,
                        "max": 4,
                        "step": 0.01,
                        "tooltip": (
                            "Scale factor for upscaling the image. Valid values are 1, 2, 3, or 4.\n"
                            "If set to 1, the image will not be upscaled but enhanced, 'enhanced setting must be set to 'True'."
                        ),
                    },
                ),
                "enhance": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "Whether to enhance the image using Venice's image engine during upscaling.\n"
                            "Must be set to 'True' if scale is set to 1."
                        ),
                    },
                ),
                "enhance_creativity": (
                    "FLOAT",
                    {
                        "default": 0.5,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.01,
                        "tooltip": (
                            "Higher values let the enhancement AI change the image more. "
                            "Setting this to 1 effectively creates an entirely new image."
                        ),
                    },
                ),
                "enhance_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "placeholder": "gold, graffiti, minimalistic",
                        "multiline": True,
                        "tooltip": (
                            "The text to image style to apply during prompt enhancement. "
                            "Does best with short descriptive prompts, like gold, marble or angry, menacing."
                        ),
                    },
                ),
                "replication": (
                    "FLOAT",
                    {
                        "default": 0.1,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.01,
                        "tooltip": (
                            "How strongly lines and noise in the base image are preserved. "
                            "Higher values are noisier but less plastic/AI 'generated'/hallucinated"
                        ),
                    },
                ),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "i2i_enhance_upscale"
    CATEGORY = "venice.ai"

    def i2i_enhance_upscale(self, image, scale, enhance, enhance_creativity, enhance_prompt, replication):
        url = VENICEAI_BASE_URL + API_ENDPOINTS["upscale_image"]

        if len(enhance_prompt) > 1500:
            raise ValueError()
        if scale == 1:
            raise ValueError("Upscale Image (Venice) 'enhance' must be set to 'True' if scale is 1.")
        if scale == 4:
            logging.info(
                (
                    "Upscale Image (Venice) A scale of 4 with large images will result "
                    "in the scale being dynamically set (by venice) to ensure the "
                    "final image stays within the maximum size limits."
                )
            )

        # if not api_key:
        #     raise ValueError("VENICEAI_API_KEY environment variable not set")

        # Convert tensor to PIL Image
        try:
            # Get first image from batch
            img_tensor = image[0].detach().cpu()  # Shape: (H, W, C)

            # Ensure RGB format by taking first 3 channels
            if img_tensor.shape[-1] > 3:
                img_tensor = img_tensor[:, :, :3]

            # Convert to CHW format and create PIL Image
            pil_image = ToPILImage()(img_tensor.permute(2, 0, 1))
        except Exception as e:
            raise ValueError(f"Upscale Image (Venice) Failed to convert tensor to PIL image: {str(e)}")

        # Convert image to base64
        byte_io = io.BytesIO()
        pil_image.save(byte_io, format="PNG")
        byte_io.seek(0)
        image_base64 = base64.b64encode(byte_io.read()).decode("utf-8")

        # Prepare JSON payload
        payload = {
            "image": image_base64,
            "scale": scale,
            "enhance": enhance,
            "enhanceCreativity": enhance_creativity,
            "enhancePrompt": enhance_prompt,
            "replication": replication,
        }

        headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}", "Content-Type": "application/json"}

        # Send request
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Upscale Image (Venice) API request failed: {str(e)}")

        # Convert response to tensor
        try:
            upscaled_image = Image.open(io.BytesIO(response.content))
            tensor = ToTensor()(upscaled_image)  # Converts to (C, H, W)
            tensor = tensor.permute(1, 2, 0)  # Convert to (H, W, C)
            tensor = tensor.unsqueeze(0)  # Add batch dimension (1, H, W, C)
        except Exception as e:
            raise ValueError(f"Upscale Image (Venice) Failed to process response image: {str(e)}")

        return (tensor,)


NODE_CLASS_MAPPINGS = {
    "I2IEnhanceUpscale_VENICE": I2IEnhanceUpscale,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "I2IEnhanceUpscale_VENICE": "Img2Img Enhance + Upscale (Venice)",
}
