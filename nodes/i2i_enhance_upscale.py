import base64
import io as python_io
import logging

import requests
from PIL import Image
from torchvision.transforms import ToPILImage, ToTensor  # type: ignore

from comfy_api.latest import io

from ..globals import API_ENDPOINTS
from ..nodes.utils import ensure_prompt_length
from ..venice_client import client

LOG = logging.getLogger(__name__)


class I2IEnhanceUpscale(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="I2IEnhanceUpscale_VENICE",
            display_name="Img2Img Enhance + Upscale (Venice)",
            category="venice.ai",
            inputs=[
                io.Image.Input(
                    "image",
                    tooltip="Image tensor to enhance or upscale",
                ),
                io.Float.Input(
                    "scale",
                    default=2.0,
                    min=1.0,
                    max=4.0,
                    step=0.01,
                    tooltip=(
                        "Scale factor for upscaling the image. Valid values are 1, 2, 3, or 4.\n"
                        "If set to 1, the image will not be upscaled but enhanced, 'enhance' must be set to 'True'."
                    ),
                ),
                io.Boolean.Input(
                    "enhance",
                    default=False,
                    tooltip=(
                        "Whether to enhance the image using Venice's image engine during upscaling.\n"
                        "Must be set to 'True' if scale is set to 1."
                    ),
                ),
                io.Float.Input(
                    "enhance_creativity",
                    default=0.5,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip=(
                        "Higher values let the enhancement AI change the image more. "
                        "Setting this to 1 effectively creates an entirely new image."
                    ),
                ),
                io.String.Input(
                    "enhance_prompt",
                    default="",
                    multiline=True,
                    placeholder="gold, graffiti, minimalistic",
                    tooltip=(
                        "The text to image style to apply during prompt enhancement. "
                        "Does best with short descriptive prompts, like gold, marble or angry, menacing."
                    ),
                ),
                io.Float.Input(
                    "replication",
                    default=0.1,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip=(
                        "How strongly lines and noise in the base image are preserved. "
                        "Higher values are noisier but less plastic/AI 'generated'/hallucinated"
                    ),
                ),
            ],
            outputs=[io.Image.Output(id="image", display_name="Image")],
        )

    @classmethod
    def execute(
        cls,
        image,
        scale,
        enhance,
        enhance_creativity,
        enhance_prompt,
        replication,
    ) -> io.NodeOutput:
        ensure_prompt_length(enhance_prompt, 1500, "Enhance prompt", allow_empty=True)
        if scale == 1 and not enhance:
            raise ValueError("Upscale Image (Venice) 'enhance' must be set to 'True' if scale is 1.")
        if scale == 4:
            LOG.info(
                (
                    "Upscale Image (Venice) A scale of 4 with large images will result "
                    "in the scale being dynamically set (by venice) to ensure the "
                    "final image stays within the maximum size limits."
                )
            )

        # Convert tensor to PIL Image
        try:
            # Get first image from batch
            img_tensor = image[0].detach().cpu()  # Shape: (H, W, C)

            # Ensure RGB format by taking first 3 channels
            if img_tensor.shape[-1] > 3:
                img_tensor = img_tensor[:, :, :3]

            # Convert to CHW format and create PIL Image
            pil_image = ToPILImage()(img_tensor.permute(2, 0, 1))
        except Exception as exc:
            raise ValueError(f"Upscale Image (Venice) Failed to convert tensor to PIL image: {str(exc)}")

        # Convert image to base64
        byte_io = python_io.BytesIO()
        pil_image.save(byte_io, format="PNG")
        byte_io.seek(0)
        image_base64 = base64.b64encode(byte_io.read()).decode("utf-8")

        payload = {
            "image": image_base64,
            "scale": scale,
            "enhance": enhance,
            "enhanceCreativity": enhance_creativity,
            "enhancePrompt": enhance_prompt,
            "replication": replication,
        }

        response = None
        try:
            response = client.request(
                "POST",
                API_ENDPOINTS["upscale_image"],
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Upscale Image (Venice) API request failed: {str(exc)}")

        try:
            upscaled_image = Image.open(python_io.BytesIO(response.content))
            tensor = ToTensor()(upscaled_image)  # Converts to (C, H, W)
            tensor = tensor.permute(1, 2, 0)  # Convert to (H, W, C)
            tensor = tensor.unsqueeze(0)  # Add batch dimension (1, H, W, C)
        except Exception as exc:
            raise ValueError(f"Upscale Image (Venice) Failed to process response image: {str(exc)}")

        return io.NodeOutput(tensor)
