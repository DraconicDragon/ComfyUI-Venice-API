import base64
import io
import logging

import torchvision.transforms as transforms
from PIL import Image


class GenerateImageBase:
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate"
    CATEGORY = "venice.ai"

    def process_result(self, result):
        try:
            if isinstance(result, dict) and "images" in result:
                img_data = result["images"][0]  # Only first image is returned because only 1 is possible rn
            else:
                raise Exception("Error, unexpected response: result does not contain 'images'")

            img_bytes = base64.b64decode(img_data)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            transform = transforms.ToTensor()
            img_tensor = transform(img)  # Shape: [C, H, W]
            img_tensor = img_tensor.unsqueeze(0)  # add batch dimension as dimension 0
            img_tensor = img_tensor.permute(0, 2, 3, 1)  # Shape: [B, H, W, C]

            logging.debug(f"Debug - Image tensor shape: {img_tensor.shape}")
            return (img_tensor,)

        except Exception as e:
            raise Exception(f"Error processing image result: {str(e)}") from e
