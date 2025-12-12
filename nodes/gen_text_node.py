from ..globals import API_ENDPOINTS
from ..nodes.catalog_utils import text_model_choices
from ..nodes.utils import encode_tensor_for_vision, ensure_prompt_length
from ..venice_client import client


class GenerateText:
    @classmethod
    def INPUT_TYPES(cls):
        model_choices = text_model_choices()

        return {
            "required": {
                "model": (
                    model_choices,
                    {
                        "default": model_choices[0],
                    },
                ),
                "system_prompt": ("STRING", {"default": "", "multiline": True}),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "frequency_penalty": ("FLOAT", {"default": 1.5, "min": 0.0, "max": 2.0, "step": 0.1}),
                "presence_penalty": ("FLOAT", {"default": 1.5, "min": 0.0, "max": 2.0, "step": 0.1}),
                "temperature": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 2.0, "step": 0.1}),
                "top_p": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.1}),
                "enable_vision": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "image_for_vision": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("response",)
    FUNCTION = "generate_text"
    CATEGORY = "venice.ai"

    def generate_text(
        self,
        model,
        system_prompt,
        prompt,
        frequency_penalty,
        presence_penalty,
        temperature,
        top_p,
        enable_vision,
        **kwargs,
    ):
        ensure_prompt_length(prompt, 1500, label="Prompt")
        user_content = []
        image_for_vision = kwargs.get("image_for_vision")

        if image_for_vision is not None and enable_vision:
            encoded_image = encode_tensor_for_vision(image_for_vision[0])
            user_content.extend(
                [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": encoded_image}},
                ]
            )
        else:
            user_content.append({"type": "text", "text": prompt})

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": model,
            "messages": messages,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "temperature": temperature,
            "top_p": top_p,
        }

        json_response = client.post_json(API_ENDPOINTS["text_generate"], payload)
        content = json_response["choices"][0]["message"]["content"]
        # print(content)
        return (content,)


NODE_CLASS_MAPPINGS = {
    "GenerateText_VENICE": GenerateText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GenerateText_VENICE": "Generate Text (Venice)",
}
