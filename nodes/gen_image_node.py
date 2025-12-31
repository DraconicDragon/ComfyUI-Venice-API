import logging
import re

import torch

from comfy_api.latest import io

from ..globals import API_ENDPOINTS
from ..nodes.catalog_utils import image_model_choices, style_choices
from ..nodes.gen_image_base import GenerateImageBase
from ..nodes.utils import ensure_multiple_of, ensure_prompt_length
from ..venice_client import client

LOG = logging.getLogger(__name__)


class GenerateImage(io.ComfyNode):
    _processor = GenerateImageBase()

    @classmethod
    def define_schema(cls) -> io.Schema:
        model_choices = list(image_model_choices())
        if not model_choices:
            model_choices = ["none_available"]
        style_options = list(style_choices())
        if not style_options:
            style_options = ["none_available"]

        return io.Schema(
            node_id="GenerateImage_VENICE",
            display_name="Generate Image (Venice)",
            category="venice.ai",
            inputs=[
                io.Combo.Input(
                    "model",
                    options=model_choices,
                    default=model_choices[0],
                    tooltip="Model to use for image generation",
                ),
                io.String.Input(
                    "prompt",
                    default="A flying cat made of lettuce",
                    multiline=True,
                    placeholder="Positive Prompt. Example: A flying cat made of lettuce",
                    tooltip="The text prompt to guide the image generation",
                ),
                io.String.Input(
                    "neg_prompt",
                    default="",
                    multiline=True,
                    placeholder="Negative Prompt. Example: bad composition, low quality",
                    tooltip="Negative prompt (ignored for models that do not support CFG)",
                ),
                io.Int.Input(
                    "width",
                    default=1024,
                    min=0,
                    max=2048,
                    step=16,
                    tooltip="Must be a multiple of 32. Maximum allowed by venice.ai at time of writing is 1280",
                ),
                io.Int.Input(
                    "height",
                    default=1024,
                    min=0,
                    max=2048,
                    step=16,
                    tooltip="Must be a multiple of 32. Maximum allowed by venice.ai at time of writing is 1280",
                ),
                io.Int.Input(
                    "batch_size",
                    default=1,
                    min=1,
                    max=4,
                    tooltip="Number of images to generate in a single batch (sends that many sequential requests)",
                ),
                io.Int.Input(
                    "steps",
                    default=20,
                    min=1,
                    max=50,
                    tooltip=(
                        "Number of inference steps. Some models have lower per-model max steps, e.g. venice-sd35 (30), "
                        "fluently-xl (50), flux-dev (30), lustify-sdxl (50), pony-realism (50), stable-diffusion-3.5 (30), juggernaut-xi (50)."
                    ),
                ),
                io.Float.Input(
                    "guidance",
                    default=3.0,
                    min=0.0,
                    max=20.0,
                    step=0.05,
                    tooltip="CFG scale parameter (or Guidance for Flux models)",
                ),
                io.Combo.Input(
                    "style_preset",
                    options=style_options,
                    default=style_options[0],
                    tooltip="Style preset to apply to the generated images",
                ),
                io.Boolean.Input(
                    "hide_watermark",
                    default=True,
                    tooltip="Hide the Venice watermark when possible",
                ),
                io.Boolean.Input(
                    "safe_mode",
                    default=False,
                    tooltip="Enable safe mode (blurs NSFW content)",
                ),
                io.Int.Input(
                    "seed",
                    optional=True,
                    default=-1,
                    min=-0x3B9AC9FF,
                    max=0x3B9AC9FF,
                    tooltip="Seed for the generation; use -1 for random values",
                ),
            ],
            outputs=[io.Image.Output(id="image", display_name="Image")],
        )

    @classmethod
    def execute(
        cls,
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
        safe_mode,
        seed=-1,
    ) -> io.NodeOutput:
        ensure_multiple_of(width, height)
        ensure_prompt_length(prompt, 1500, "Prompt")
        ensure_prompt_length(neg_prompt, 1500, "Negative Prompt", allow_empty=True)

        if re.match(r"^flux.*", model):
            LOG.info("VeniceAPI INFO: Ignoring negative prompt for %s.", model)
            neg_prompt = ""

        seed_value = -1 if seed is None else seed
        images_tensor = ()

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "negative_prompt": neg_prompt,
                "style_preset": style_preset,
                "height": height,
                "width": width,
                "steps": steps,
                "cfg_scale": guidance,
                "seed": seed_value,
                "return_binary": False,
                "hide_watermark": hide_watermark,
                "safe_mode": safe_mode,
                "format": "png",
                "embed_exif_metadata": True,
            }
            if style_preset == "none":
                del payload["style_preset"]

            for i in range(batch_size):
                payload["seed"] = seed_value + i
                response_json = client.post_json(API_ENDPOINTS["image_generate"], payload)
                images_tensor += cls._processor.process_result(response_json)

            merged = torch.cat(images_tensor, dim=0)
            return io.NodeOutput(merged)

        except Exception as exc:
            raise Exception(f"Error processing image result: {str(exc)}") from exc
