import io
import os

import requests
from PIL import Image
from torchvision.transforms import ToPILImage, ToTensor

from ..globals import API_ENDPOINTS, VENICEAI_BASE_URL


class UpscaleImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "scale": (["2", "4"], {"default": "2"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "upscale"
    CATEGORY = "venice.ai"

    def upscale(self, image, scale):
        url = VENICEAI_BASE_URL + API_ENDPOINTS["upscale_image"]

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
            raise ValueError(f"Failed to convert tensor to PIL image: {str(e)}")

        # Prepare image bytes
        byte_io = io.BytesIO()
        pil_image.save(byte_io, format="PNG")
        byte_io.seek(0)

        # Prepare request data
        files = {
            "image": ("image.png", byte_io, "image/png"),
            "scale": (None, scale),  # Send scale as a string directly
        }

        headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}"}

        # Send request
        try:
            response = requests.post(url, files=files, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API request failed: {str(e)}")

        # Convert response to tensor
        try:
            upscaled_image = Image.open(io.BytesIO(response.content))
            tensor = ToTensor()(upscaled_image)  # Converts to (C, H, W)
            tensor = tensor.permute(1, 2, 0)  # Convert to (H, W, C)
            tensor = tensor.unsqueeze(0)  # Add batch dimension (1, H, W, C)
        except Exception as e:
            raise ValueError(f"Failed to process response image: {str(e)}")

        return (tensor,)



NODE_CLASS_MAPPINGS = {
    "UpscaleImage_VENICE": UpscaleImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UpscaleImage_VENICE": "Upscale Image (Venice)",
}