import os

import requests
import torch

from ..globals import API_ENDPOINTS, VENICEAI_BASE_URL
from ..nodes.gen_image_base import GenerateImageBase


class GenerateImage(GenerateImageBase):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (
                    "COMBO",
                    {"default": "flux-dev"},
                ),
                "prompt": ("STRING", {"default": "A flying cat made of lettuce", "multiline": True}),
                "neg_prompt": (
                    "STRING",
                    {
                        "placeholder": "Bad composition, rating_explicit, Text, signature, lowres, lowres, low details, faded image, out of focus, cropped, clipped, cut-off, out of frame, deserted scene, empty scene, vacant scene, desolate scene, sparse décor, bad quality, worst quality,",
                        "multiline": True,
                        "tooltip": "Negative prompt. This is ignored when using flux-dev or flux-dev-uncensored",
                    },
                ),
                "width": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 256,
                        "max": 2048,  # limit is 1280 but i dont want to restrict this in case of future updates, https://docs.venice.ai/api-reference/endpoint/image/generate#body-height
                        "step": 8,
                        "tooltip": "Must be a multiple of 32. Maximum allowed by venice.ai is 1280",
                    },
                ),
                "height": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 256,
                        "max": 2048,
                        "step": 8,
                        "tooltip": "Must be a multiple of 32. Maximum allowed by venice.ai is 1280",
                    },
                ),
                "batch_size": ("INT", {"default": 1, "min:": 1, "max": 4}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 30}),
                "guidance": ("FLOAT", {"default": 3.0, "min": 0.1, "max": 15.0}),
                "style_preset": ("COMBO", {"default": "none"}),
                "hide_watermark": ("BOOLEAN", {"default": True}),
            },
            "optional": {"seed": ("INT", {"default": -1})},
        }

    def generate(
        self,
        model,
        prompt,
        neg_prompt,
        width,
        height,
        batch_size,
        steps,
        guidance,
        style_preset,
        hide_watermark,
        seed=-1,
    ):
        images_tensor = ()  # empty tuple for tensors

        if model in ["flux-dev", "flux-dev-uncensored"]:
            print(f"VeniceAPI INFO: Ignoring negative prompt for {model}.")
            neg_prompt = ""

        try:
            self.check_multiple_of_32(width, height)  # todo: make this be validate node instead

            headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}", "Content-Type": "application/json"}
            url = VENICEAI_BASE_URL + API_ENDPOINTS["image_generate"]

            payload = {
                "model": model,
                "prompt": prompt,
                "negative_prompt": neg_prompt,
                "style_preset": style_preset,
                "height": height,
                "width": width,
                "steps": steps,
                "cfg_scale": guidance,
                "seed": seed,
                "return_binary": False,
                "hide_watermark": hide_watermark,
                "format": "png",
            }
            if style_preset == "none":
                del payload["style_preset"]

            for i in range(batch_size):
                payload["seed"] = seed + i
                response = requests.request("POST", url, json=payload, headers=headers)

                if response.status_code != 200:
                    raise requests.exceptions.HTTPError(
                        f"HTTP error: {response.status_code}, Response: {response.text}"
                    )

                images_tensor += self.process_result(response.json())

            merged = torch.cat(images_tensor, dim=0)
            return (merged,)

        except Exception as e:
            raise Exception(f"Error processing image result: {str(e)}") from e


NODE_CLASS_MAPPINGS = {
    "GenerateImage_VENICE": GenerateImage,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "GenerateImage_VENICE": "Generate Image (Venice)",
}
