from typing import Any, Dict, Iterable

from comfy_api.latest import io

from ..globals import API_ENDPOINTS
from ..nodes.catalog_utils import character_choices, text_model_specs
from ..nodes.utils import encode_tensor_for_vision
from ..venice_client import client


class GenerateTextAdvanced(io.ComfyNode):
    @classmethod
    def _option_input_id(cls, model_id: str, field: str) -> str:
        return f"{model_id}__{field}"

    @staticmethod
    def _constraint_default(value: Any, fallback: float) -> float:
        if isinstance(value, dict):
            default = value.get("default")
        else:
            default = value
        if isinstance(default, (int, float)):
            return float(default)
        return fallback

    @classmethod
    def _get_option_value(cls, model_payload: Dict[str, Any], model_id: str, field: str) -> Any:
        candidates = (
            cls._option_input_id(model_id, field),
            field,
            f"{field}__{model_id}",
            f"{model_id}__{field}",
        )
        for key in candidates:
            if key in model_payload:
                return model_payload.get(key)
        return None

    @classmethod
    def _text_specs(cls) -> Dict[str, Dict[str, Any]]:
        specs = text_model_specs() or {}
        if not specs:
            raise ValueError("No Venice text model specs available")
        return specs

    @staticmethod
    def _normalize_stop_tokens(value: str | Iterable[str] | None) -> list[str]:
        tokens: list[str] = []
        if not value:
            return tokens
        segments: Iterable[str] = value.splitlines() if isinstance(value, str) else value
        for segment in segments:
            for raw_token in str(segment).split(","):
                trimmed = raw_token.strip()
                if trimmed:
                    tokens.append(trimmed)
        return tokens

    @classmethod
    def _build_model_options(cls) -> list[io.DynamicCombo.Option]:
        specs = cls._text_specs()
        options: list[io.DynamicCombo.Option] = []
        for model_id, spec in sorted(specs.items(), key=lambda item: item[0]):
            constraints = spec.get("constraints") or {}
            capabilities = spec.get("capabilities") or {}
            temperature_default = cls._constraint_default(constraints.get("temperature"), 0.5)
            top_p_default = cls._constraint_default(constraints.get("top_p"), 0.8)

            option_inputs: list[io.Input] = [
                io.Float.Input(
                    cls._option_input_id(model_id, "temperature"),
                    display_name="temperature",
                    default=temperature_default,
                    min=0.0,
                    max=2.0,
                    step=0.01,
                    tooltip="Sampling temperature (per-model default taken from the catalog).",
                ),
                io.Float.Input(
                    cls._option_input_id(model_id, "top_p"),
                    display_name="top_p",
                    default=top_p_default,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Nucleus sampling probability (per-model default taken from the catalog).",
                ),
            ]

            if capabilities.get("supportsReasoning"):
                option_inputs.append(
                    io.Boolean.Input(
                        cls._option_input_id(model_id, "reasoning"),
                        display_name="reasoning",
                        default=True,
                        tooltip="Toggle reasoning capabilities for this model.",
                    )
                )

            if capabilities.get("supportsVision"):
                option_inputs.append(
                    io.Boolean.Input(
                        cls._option_input_id(model_id, "enable_vision"),
                        display_name="enable_vision",
                        default=False,
                        tooltip="Enable vision inputs when the model supports vision.",
                    )
                )
                option_inputs.append(
                    io.Image.Input(
                        cls._option_input_id(model_id, "image_for_vision"),
                        display_name="vision_image",
                        optional=True,
                        tooltip="Optional image input for vision-capable models.",
                    )
                )

            option_inputs.extend(cls._venice_parameter_inputs(model_id, capabilities))

            options.append(io.DynamicCombo.Option(model_id, option_inputs))

        return options

    @classmethod
    def _venice_parameter_inputs(cls, model_id: str, capabilities: Dict[str, Any]) -> list[io.Input]:
        character_options = ["none", *character_choices()]
        inputs: list[io.Input] = [
            io.Combo.Input(
                cls._option_input_id(model_id, "vp_character_slug"),
                display_name="vp_character_slug",
                options=character_options,
                default=character_options[0],
                optional=True,
                tooltip="Select a Venice character slug (public ID) from the catalog.",
            ),
        ]

        if capabilities.get("supportsReasoning"):
            inputs.extend(
                [
                    io.Boolean.Input(
                        cls._option_input_id(model_id, "vp_strip_thinking_response"),
                        display_name="vp_strip_thinking_response",
                        default=False,
                        tooltip="Strip thinking blocks from the response on reasoning models.",
                    ),
                    io.Boolean.Input(
                        cls._option_input_id(model_id, "vp_disable_thinking"),
                        display_name="vp_disable_thinking",
                        default=False,
                        tooltip="Disable thinking blocks for supported reasoning models.",
                    ),
                ]
            )

        if capabilities.get("supportsWebSearch"):
            inputs.extend(
                [
                    io.Combo.Input(
                        cls._option_input_id(model_id, "vp_enable_web_search"),
                        display_name="vp_enable_web_search",
                        options=["auto", "off", "on"],
                        default="off",
                        optional=True,
                        tooltip="Set to auto/off/on to control Venice web search for this request.",
                    ),
                    io.Boolean.Input(
                        cls._option_input_id(model_id, "vp_enable_web_scraping"),
                        display_name="vp_enable_web_scraping",
                        default=False,
                        tooltip="Enable Venice web scraping for URLs found in the latest user message.",
                    ),
                    io.Boolean.Input(
                        cls._option_input_id(model_id, "vp_enable_web_citations"),
                        display_name="vp_enable_web_citations",
                        default=False,
                        tooltip="Request citations when web search returns sources.",
                    ),
                ]
            )

        inputs.append(
            io.Boolean.Input(
                cls._option_input_id(model_id, "vp_include_venice_system_prompt"),
                display_name="vp_include_venice_system_prompt",
                default=True,
                tooltip="Include Venice-supplied system prompts alongside your own.",
            )
        )

        return inputs

    @classmethod
    def define_schema(cls) -> io.Schema:
        model_options = cls._build_model_options()

        return io.Schema(
            node_id="GenerateTextAdvanced_VENICE",
            display_name="Generate Text Advanced (Venice)",
            category="venice.ai",
            inputs=[
                io.String.Input(
                    "prompt",
                    default="",
                    multiline=True,
                    tooltip="The prompt to generate text from. Ask, command or chat with the model.",
                ),
                io.String.Input(
                    "system_prompt",
                    default="",
                    multiline=True,
                    tooltip="Optional system prompt to guide the model's behavior.",
                ),
                io.DynamicCombo.Input(
                    "model",
                    options=model_options,
                    tooltip="The model to use for text generation.",
                ),
                io.Float.Input(
                    "frequency_penalty",
                    default=0.0,
                    min=-2.0,
                    max=2.0,
                    step=0.05,
                    tooltip=(
                        "Positive values penalize new tokens based on their existing frequency in the text so far, "
                        "decreasing the model's likelihood to repeat the same line verbatim."
                    ),
                ),
                io.Float.Input(
                    "presence_penalty",
                    default=0.0,
                    min=-2.0,
                    max=2.0,
                    step=0.05,
                    tooltip=(
                        "Positive values penalize new tokens based on whether they appear in the text so far, "
                        "increasing the model's likelihood to talk about new topics."
                    ),
                ),
                io.Float.Input(
                    "repetition_penalty",
                    default=1.2,
                    min=0.0,
                    max=2.0,
                    step=0.05,
                    tooltip="1.0 means no penalty. Values > 1.0 discourage repetition.",
                ),
                io.Float.Input(
                    "max_temp",
                    default=1.5,
                    min=0.0,
                    max=2.0,
                    step=0.05,
                    tooltip="Maximum temperature value for dynamic temperature scaling.",
                ),
                io.Float.Input(
                    "min_temp",
                    default=0.1,
                    min=0.0,
                    max=2.0,
                    step=0.05,
                    tooltip="Minimum temperature value for dynamic temperature scaling.",
                ),
                io.Int.Input(
                    "max_completion_tokens",
                    default=420,
                    min=1,
                    max=131072,
                    step=1,
                    tooltip=(
                        "An upper bound for the number of tokens that can be generated for "
                        "a completion, including visible output tokens and reasoning tokens."
                    ),
                ),
                io.Int.Input(
                    "top_k",
                    default=40,
                    min=0,
                    tooltip="The number of highest probability vocabulary tokens to keep for top-k-filtering.",
                ),
                io.Float.Input(
                    "min_p",
                    default=0.05,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip=(
                        "Sets a minimum probability threshold for token selection. "
                        "Tokens with probabilities below this value are filtered out."
                    ),
                ),
                io.String.Input(
                    "stop_tokens",
                    default="",
                    multiline=True,
                    optional=True,
                    tooltip="Optional comma- or newline-separated tokens to stop generation on (requires at least one).",
                ),
                io.Boolean.Input(
                    "enable_system_prompt",
                    default=True,
                    tooltip="Enable or disable system prompt being passed on.",
                ),
            ],
            outputs=[io.String.Output(id="response", display_name="response")],
        )

    @classmethod
    def execute(
        cls,
        model,
        prompt,
        system_prompt,
        frequency_penalty,
        presence_penalty,
        repetition_penalty,
        max_temp,
        min_temp,
        max_completion_tokens,
        top_k,
        min_p,
        stop_tokens,
        enable_system_prompt,
    ) -> io.NodeOutput:
        if isinstance(model, str):
            model = {"model": model}
        if not isinstance(model, dict) or "model" not in model:
            raise ValueError("Model selection is required")

        model_id = model.get("model")
        specs = cls._text_specs()
        spec = specs.get(model_id)
        if not spec:
            raise ValueError("Selected model is missing from the Venice catalog; refresh the catalog and try again.")

        constraints = spec.get("constraints") or {}
        capabilities = spec.get("capabilities") or {}

        temperature_value = cls._get_option_value(model, model_id, "temperature")
        if temperature_value is None:
            temperature_value = cls._constraint_default(constraints.get("temperature"), 0.5)
        try:
            temperature_value = float(temperature_value)
        except (TypeError, ValueError):
            temperature_value = 0.5

        top_p_value = cls._get_option_value(model, model_id, "top_p")
        if top_p_value is None:
            top_p_value = cls._constraint_default(constraints.get("top_p"), 0.8)
        try:
            top_p_value = float(top_p_value)
        except (TypeError, ValueError):
            top_p_value = 0.8

        reasoning_value = cls._get_option_value(model, model_id, "reasoning")
        reasoning_enabled = (
            bool(reasoning_value) if reasoning_value is not None else bool(capabilities.get("supportsReasoning"))
        )
        reasoning_effort_value = "medium"
        vision_enabled = (
            bool(cls._get_option_value(model, model_id, "enable_vision"))
            if capabilities.get("supportsVision")
            else False
        )
        vision_image = cls._get_option_value(model, model_id, "image_for_vision")
        vision_tensor = None
        if vision_image is not None:
            if isinstance(vision_image, (list, tuple)):
                if len(vision_image) > 0 and vision_image[0] is not None:
                    vision_tensor = vision_image[0]
            else:
                vision_tensor = vision_image
        normalized_stop_tokens = cls._normalize_stop_tokens(stop_tokens)

        venice_parameters: Dict[str, Any] = {}

        def _set_bool(field: str, key: str) -> None:
            value = cls._get_option_value(model, model_id, field)
            if value is not None:
                venice_parameters[key] = bool(value)

        slug_value = cls._get_option_value(model, model_id, "vp_character_slug")
        if isinstance(slug_value, str):
            trimmed = slug_value.strip()
            if trimmed and trimmed.lower() not in {"", "none"}:
                venice_parameters["character_slug"] = trimmed

        if capabilities.get("supportsReasoning"):
            _set_bool("vp_strip_thinking_response", "strip_thinking_response")
            _set_bool("vp_disable_thinking", "disable_thinking")

        if capabilities.get("supportsWebSearch"):
            web_search = cls._get_option_value(model, model_id, "vp_enable_web_search")
            if isinstance(web_search, str):
                trimmed = web_search.strip()
                if trimmed:
                    venice_parameters["enable_web_search"] = trimmed
            elif web_search is not None:
                venice_parameters["enable_web_search"] = str(web_search)
            _set_bool("vp_enable_web_scraping", "enable_web_scraping")
            _set_bool("vp_enable_web_citations", "enable_web_citations")

        _set_bool("vp_include_venice_system_prompt", "include_venice_system_prompt")

        if vision_enabled and vision_tensor is None:
            raise ValueError("Vision input is enabled but no image was provided")

        user_content = []
        if vision_enabled and vision_tensor is not None:
            encoded_image = encode_tensor_for_vision(vision_tensor)
            user_content.extend(
                [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": encoded_image}},
                ]
            )
        else:
            user_content.append({"type": "text", "text": prompt})

        if not enable_system_prompt:
            system_prompt = ""

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": model_id,
            "messages": messages,
            "frequency_penalty": frequency_penalty,
            "logprobs": False,  # unused, not supported by all models
            "top_logprobs": 0,  # x >= 0
            "max_completion_tokens": max_completion_tokens,
            "max_temp": max_temp,
            "min_p": min_p,
            "min_temp": min_temp,
            "n": 1,  # basically batch size
            "presence_penalty": presence_penalty,
            "repetition_penalty": repetition_penalty,
            "seed": 42,
            "stream": False,
            "temperature": temperature_value,
            "top_k": top_k,
            "top_p": top_p_value,
            "parallel_tool_calls": True,
        }
        if reasoning_enabled:
            payload["reasoning"] = {"mode": reasoning_effort_value}
            payload["reasoning_effort"] = reasoning_effort_value
        if normalized_stop_tokens:
            payload["stop"] = normalized_stop_tokens
        if venice_parameters:
            payload["venice_parameters"] = venice_parameters

        json_response = client.post_json(API_ENDPOINTS["text_generate"], payload)
        try:
            content = json_response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Unexpected API response format: {json_response}") from exc

        return io.NodeOutput(content)
