import base64
import io
import os

import numpy as np
import requests
from PIL import Image

from ..globals import API_ENDPOINTS, VENICEAI_BASE_URL


class GenerateTextVeniceParameters:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "character_slug": (
                    "STRING",
                    {
                        "default": "cslug",
                        "tooltip": "",
                    },
                ),
                "enable_character": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "",
                    },
                ),
                "strip_thinking_response": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "",
                    },
                ),
                "disable_thinking": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "",
                    },
                ),
                "web_search": (
                    ["auto", "on", "off"],
                    {
                        "default": "auto",
                        "tooltip": "",
                    },
                ),
                "enable_web_citations": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "",
                    },
                ),
                "use_venice_system_prompt": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "",
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("response",)
    FUNCTION = "pass_on_params"
    CATEGORY = "venice.ai"

    def pass_on_params(
        self,
        character_slug,
        enable_character,
        strip_thinking_response,
        disable_thinking,
        web_search,
        enable_web_citations,
        use_venice_system_prompt,
    ):
        venice_params = {
            "strip_thinking_response": strip_thinking_response,
            "disable_thinking": disable_thinking,
            "enable_web_search": web_search,
            "enable_web_citations": enable_web_citations,
            "include_venice_system_prompt": use_venice_system_prompt,
        }
        if enable_character:
            venice_params["character_slug"] = character_slug

        return (venice_params,)


NODE_CLASS_MAPPINGS = {
    "GenerateTextVeniceParameters_VENICE": GenerateTextVeniceParameters,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GenerateTextVeniceParameters_VENICE": "Textgen Parameters (Venice)",
}
