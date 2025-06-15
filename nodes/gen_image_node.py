import logging
import os
import re

import requests
import torch  # type: ignore

from ..globals import API_ENDPOINTS, VENICEAI_BASE_URL
from ..nodes.gen_image_base import GenerateImageBase


class GenerateImage(GenerateImageBase):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (
                    "COMBO",
                    {
                        "default": "flux-dev",
                        "tooltip": "Model to use for image generation, if this just says flux-dev or C O M B O then something failed oopsie.",
                    },
                ),
                "prompt": ("STRING", {"default": "A flying cat made of lettuce", "multiline": True}),
                "neg_prompt": (
                    "STRING",
                    {
                        "placeholder": "Negative Prompt. (Ignored for Flux based models.)\nBad composition, rating_explicit, Text, signature, lowres, faded image, out of focus, cropped, out of frame, vacant scene, bad quality, worst quality,",
                        "multiline": True,
                        "tooltip": "Negative prompt. This is ignored when using flux-dev or flux-dev-uncensored",
                    },
                ),
                "width": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 0,
                        "max": 2048,  # limit is 1280 but i dont want to restrict this in case of future updates, https://docs.venice.ai/api-reference/endpoint/image/generate#body-height
                        "step": 16,
                        "tooltip": "Must be a multiple of 32. Maximum allowed by venice.ai at time of writing is 1280",
                    },
                ),
                "height": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 0,
                        "max": 2048,
                        "step": 16,
                        "tooltip": "Must be a multiple of 32. Maximum allowed by venice.ai at time of writing is 1280",
                    },
                ),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 4}),
                "steps": (
                    "INT",
                    {
                        "default": 20,
                        "min": 1,
                        "max": 50,
                        "tooltip": (
                            "Number of inference steps. The following models have reduced max steps from "
                            "the global max: venice-sd35: 30 max steps, hidream: 50 max steps, fluently-xl: 50 max steps, "
                            "flux-dev: 30 max steps, flux-dev-uncensored: 30 max steps, getphat-flux: 50 max steps, "
                            "lustify-sdxl: 50 max steps, pony-realism: 50 max steps, stable-diffusion-3.5: 30 max steps, "
                            "juggernaut-xi: 50 max steps."
                        ),
                    },
                ),
                "guidance": ("FLOAT", {"default": 3.0, "min": 0.0, "max": 20.0, "step": 0.05}),
                # "lora_strength": ("INT", {"default": 50, "min": 0, "max": 100}), # check docs idk how to work this yet
                "style_preset": ("COMBO", {"default": "none"}),
                "hide_watermark": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Whether to hide the Venice watermark. Venice may ignore this parameter for certain generated content (mainl NSFW seems like).",
                    },
                ),
                "safe_mode": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Whether to use safe mode. If enabled, this will blur images that are classified as having adult content.",
                    },
                ),
                # "format": (["png", "jpeg", "webp"], {"default": "png",}),
            },
            "optional": {
                "seed": ("INT", {"default": -1, "min": -0x3B9AC9FF, "max": 0x3B9AC9FF})
            },  # 0xffffffffffffffff is 64 bit integer limit, current hex is 999999999, venice max
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
        # lora_strength,
        style_preset,
        hide_watermark,
        safe_mode,
        # format,
        seed=-1,
    ):
        if prompt == "" or len(prompt) > 1500:
            raise ValueError("VeniceAI Generate Image Node: Prompt cannot be empty or above 1500 characters")
        if len(neg_prompt) > 1500:
            raise ValueError("VeniceAI Generate Image Node: Negative prompt cannot be above 1500 characters")
        if re.match(r"^flux.*", model):
            logging.info(f"VeniceAPI INFO: Ignoring negative prompt for {model}.")
            neg_prompt = ""

        images_tensor = ()  # empty tuple for tensors

        try:
            self.check_multiple_of_32(width, height)  # todo: make this be validate node instead

            headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}", "Content-Type": "application/json"}
            url = VENICEAI_BASE_URL + API_ENDPOINTS["image_generate"]

            payload = {
                "model": model,
                "prompt": prompt,
                "negative_prompt": neg_prompt,
                # "lora_strength": lora_strength,
                "style_preset": style_preset,
                "height": height,
                "width": width,
                "steps": steps,
                "cfg_scale": guidance,
                "seed": seed,
                "return_binary": False,
                "hide_watermark": hide_watermark,
                "safe_mode": safe_mode,
                "format": "png",  # hardcoded because, change to format var and uncomment related stuff above if want dynamic
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
