class GenerateTextVeniceParameters:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "character_slug": (
                    "COMBO",
                    {
                        "default": "strawberry-the-cat",
                        "tooltip": ("The character slug of a public Venice character."),
                    },
                ),
                "enable_character": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": ("Enable or disable character parameter being passed on."),
                    },
                ),
                "strip_thinking_response": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "Strip <think></think> blocks from the response. "
                            "Applicable only to reasoning / thinking models. "
                            "Also available to use as a model feature suffix. "
                            "Defaults to false."
                        ),
                    },
                ),
                "disable_thinking": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "On supported reasoning models, will disable thinking and "
                            "strip the <think></think> blocks from the response. "
                            "Defaults to false."
                        ),
                    },
                ),
                "web_search": (
                    ["auto", "on", "off"],
                    {
                        "default": "auto",
                        "tooltip": (
                            "Auto will enable it based on the model's discretion. "
                            "On will force web search on the request. "
                            "Citations will be returned either in the first chunk of a "
                            "streaming result, or in the non streaming response."
                            "Defaults to off. "
                        ),
                    },
                ),
                "enable_web_citations": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "When web search is enabled, this will request that the LLM cite "
                            "its sources using a [REF]0[/REF] format. "
                            "Defaults to false."
                        ),
                    },
                ),  # NOTE: include_search_results_in_stream not implemented
                "use_venice_system_prompt": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "Whether to include the Venice supplied system prompts "
                            "alongside specified system prompts. "
                            "Defaults to true."
                        ),
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("venice_parameters",)
    FUNCTION = "pass_on_params"
    CATEGORY = "venice.ai"
    DESCRIPTION = (
        "Passes on parameters unique parameters to Venice's API implementation for Venice text generation nodes."
    )

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
