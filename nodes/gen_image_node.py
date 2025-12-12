import logging
import re

import torch

from ..globals import API_ENDPOINTS
from ..nodes.catalog_utils import image_model_choices, style_choices
from ..nodes.gen_image_base import GenerateImageBase
from ..nodes.utils import ensure_multiple_of, ensure_prompt_length
from ..venice_client import client


class GenerateImage(GenerateImageBase):
    @classmethod
    def INPUT_TYPES(cls):
        model_choices = image_model_choices()
        style_preset_options = style_choices()

        return {
            "required": {
                "model": (
                    model_choices,
                    {
                        "default": model_choices[0],
                        "tooltip": "Model to use for image generation",
                    },
                ),
                "prompt": (
                    "STRING",
                    {
                        "default": "A flying cat made of lettuce",
                        "multiline": True,
                        "tooltip": "The text prompt to guide the image generation",
                        "placeholder": "Positive Prompt. Example: A flying cat made of lettuce",
                    },
                ),
                "neg_prompt": (
                    "STRING",
                    {
                        "placeholder": "Negative Prompt. (Ignored for Flux based models.)\n Example: bad composition, rating_explicit, bad quality,",
                        "multiline": True,
                        "tooltip": "Negative prompt. This is ignored when using flux-dev or flux-dev-uncensored or similar models that do not support CFG (Classifier-Free-Guidance)",
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
                "batch_size": (
                    "INT",
                    {
                        "default": 1,
                        "min": 1,
                        "max": 4,
                        "tooltip": "Number of images to generate in a single batch. IMPORTANT: Doesn't do actual batches like ComfyUI would, just sends batches amount of different requests to Venice.",
                    },
                ),
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
                "guidance": (
                    "FLOAT",
                    {
                        "default": 3.0,
                        "min": 0.0,
                        "max": 20.0,
                        "step": 0.05,
                        "tooltip": "CFG scale parameter or 'Guidance' for Flux",
                    },
                ),
                # "lora_strength": ("INT", {"default": 50, "min": 0, "max": 100}), # check docs idk how to work this yet
                "style_preset": (
                    style_preset_options,
                    {
                        "default": style_preset_options[0],
                    },
                ),
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

    # todo: add variants for batch size
    # todo: implement lora and lora_strength
    # todo: see if aspect_ratio needs to be added (some models incl nano banana pro use this)
    # https://docs.venice.ai/api-reference/endpoint/image/generate
    # todo: see if resolution needs to be added (some models incl nano banana pro use this)
    # todo: add enable_web_search, mention it charges extra credits
    # todo: change up default limits, prompt length max is 7500 now
    @classmethod
    def VALIDATE_INPUTS(cls, input_types, **kwargs):
        width = input_types.get("width", kwargs.get("width"))
        height = input_types.get("height", kwargs.get("height"))
        prompt = input_types.get("prompt", kwargs.get("prompt"))
        neg_prompt = input_types.get("neg_prompt", kwargs.get("neg_prompt"))

        ensure_multiple_of(width, height)
        ensure_prompt_length(prompt, 1500, "Prompt")
        ensure_prompt_length(neg_prompt, 1500, "Negative Prompt", allow_empty=True)

        return True

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
        if re.match(r"^flux.*", model):
            logging.info(f"VeniceAPI INFO: Ignoring negative prompt for {model}.")
            neg_prompt = ""

        images_tensor = ()  # empty tuple for tensors

        try:
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
                "embed_exif_metadata": True,  # this might not work and be overriden by comfyui on image save
            }
            if style_preset == "none":
                del payload["style_preset"]

            for i in range(batch_size):
                payload["seed"] = seed + i
                response_json = client.post_json(API_ENDPOINTS["image_generate"], payload)
                images_tensor += self.process_result(response_json)

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
