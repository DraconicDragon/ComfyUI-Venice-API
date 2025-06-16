import base64
import io
import os

import numpy as np
import requests
from PIL import Image

from ..globals import API_ENDPOINTS, VENICEAI_BASE_URL


class GenerateTextAdvanced:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "llama-3.3-70b"}),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "system_prompt": ("STRING", {"default": "", "multiline": True}),
                "enable_system_prompt": ("BOOLEAN", {"default": True}),
                "frequency_penalty": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": -2.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "Positive values penalize new tokens based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim.",
                    },
                ),
                "presence_penalty": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": -2.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics.",
                    },
                ),
                "repetition_penalty": (
                    "FLOAT",
                    {
                        "default": 1.2,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "1.0 means no penalty. Values > 1.0 discourage repetition.",
                    },
                ),
                "max_temp": (
                    "FLOAT",
                    {
                        "default": 1.5,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "Maximum temperature value for dynamic temperature scaling.",
                    },
                ),
                "min_temp": (
                    "FLOAT",
                    {
                        "default": 0.1,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "Minimum temperature value for dynamic temperature scaling.",
                    },
                ),
                "max_completion_tokens": (
                    "INT",
                    {
                        "default": 123,
                        "min": 1,
                        "max": 131072,
                        "step": 1,
                        "tooltip": "An upper bound for the number of tokens that can be generated for a completion, including visible output tokens and reasoning tokens.",
                    },
                ),
                "temperature": (
                    "FLOAT",
                    {
                        "default": 0.5,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. We generally recommend altering this or top_p but not both.",
                    },
                ),
                "top_k": (
                    "INT",
                    {
                        "default": 40,
                        "min": 0,
                        "tooltip": "The number of highest probability vocabulary tokens to keep for top-k-filtering.",
                    },
                ),
                "top_p": (
                    "FLOAT",
                    {
                        "default": 0.8,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.01,
                        "tooltip": "An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered.",
                    },
                ),
                "min_p": (
                    "FLOAT",
                    {
                        "default": 0.05,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.01,
                        "tooltip": "Sets a minimum probability threshold for token selection. Tokens with probabilities below this value are filtered out.",
                    },
                ),
                # "stop": ("STRING", {"default": "", "tooltip": "Up to 4 sequences where the API will stop generating further tokens. Defaults to null.", "placeholder": "stop: [\"\\n\"]"}),
                # "stop_token_ids": ("STRING", {"default": "", "tooltip": "Array of token IDs where the API will stop generating further tokens. Example: [151643, 151645]", "placeholder": "151643, 151645, ..."}),
                "enable_vision": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "venice_parameters": ("STRING", {"forceInput": True}),
                "image_for_vision": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("response",)
    FUNCTION = "generate_text"
    CATEGORY = "venice.ai"

    def generate_text(
        # region params
        self,
        model,
        prompt,
        system_prompt,
        enable_system_prompt,
        frequency_penalty,
        presence_penalty,
        repetition_penalty,
        max_temp,
        min_temp,
        max_completion_tokens,
        temperature,
        top_k,
        top_p,
        min_p,
        enable_vision,
        **kwargs,
        # endregion
    ):

        url = VENICEAI_BASE_URL + API_ENDPOINTS["text_generate"]

        user_content = []
        venice_parameters = kwargs.get("venice_parameters", None)
        image_for_vision = kwargs.get("image_for_vision", None)

        if image_for_vision is not None and enable_vision:
            # Convert tensor to PIL Image
            image_tensor = image_for_vision[0]  # shape: (H, W, 3)
            image_np = image_tensor.cpu().numpy()  # Still in (H, W, 3)
            image_np = (image_np * 255).astype(np.uint8)  # Scale from [0, 1] to [0, 255] if needed
            pil_image = Image.fromarray(image_np)

            # Resize image to meet constraints
            original_width, original_height = pil_image.size
            aspect_ratio = original_width / original_height

            # Determine target dimensions
            if original_width > original_height:
                target_width = 1024
                target_height = int(target_width / aspect_ratio)
                if target_height < 256:
                    target_height = 256
                    target_width = int(target_height * aspect_ratio)
            else:
                target_height = 1024
                target_width = int(target_height * aspect_ratio)
                if target_width < 256:
                    target_width = 256
                    target_height = int(target_width / aspect_ratio)

            # Round dimensions to multiples of 14
            def round_down_to_multiple(value, multiple):
                return (value // multiple) * multiple

            target_width = round_down_to_multiple(target_width, 14)
            target_height = round_down_to_multiple(target_height, 14)

            # Ensure minimum dimension is 256 after rounding
            if min(target_width, target_height) < 256:
                if target_width < target_height:
                    target_width = ((256 + 13) // 14) * 14
                    target_height = round_down_to_multiple(int(target_width / aspect_ratio), 14)
                else:
                    target_height = ((256 + 13) // 14) * 14
                    target_width = round_down_to_multiple(int(target_height * aspect_ratio), 14)

            pil_image = pil_image.resize((target_width, target_height), Image.LANCZOS)  # type: ignore

            # Convert to base64 and check size
            buffered = io.BytesIO()
            pil_image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            # Resize further if base64 exceeds 4.5MB
            while len(img_base64) > 4500000:
                scaling_factor = (4500000 / len(img_base64)) ** 0.5
                new_width = int(target_width * scaling_factor)
                new_height = int(target_height * scaling_factor)

                new_width = max(round_down_to_multiple(new_width, 14), 256)
                new_height = max(round_down_to_multiple(new_height, 14), 256)

                pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)  # type: ignore
                target_width, target_height = new_width, new_height

                buffered = io.BytesIO()
                pil_image.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            user_content.extend(
                [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}},
                ]
            )
        else:
            user_content.append({"type": "text", "text": prompt})

        if not enable_system_prompt:
            system_prompt = ""

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": model,
            "messages": messages,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "repetition_penalty": repetition_penalty,
            "max_temp": max_temp,
            "min_temp": min_temp,
            "max_completion_tokens": max_completion_tokens,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "min_p": min_p,
        }
        if venice_parameters is not None:
            payload["venice_parameters"] = venice_parameters

        headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}", "Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            raise requests.exceptions.HTTPError(f"HTTP error: {response.status_code}, Response: {response.text}")

        json_response = response.json()
        content = json_response["choices"][0]["message"]["content"]
        # print(content)
        return (content,)


NODE_CLASS_MAPPINGS = {
    "GenerateTextAdvanced_VENICE": GenerateTextAdvanced,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GenerateTextAdvanced_VENICE": "Generate Text Advanced BETA (Venice)",
}
