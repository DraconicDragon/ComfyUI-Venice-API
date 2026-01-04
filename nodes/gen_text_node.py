from comfy_api.latest import io

from ..globals import API_ENDPOINTS
from ..nodes.catalog_utils import text_model_choices
from ..nodes.utils import encode_tensor_for_vision, ensure_prompt_length
from ..venice_client import client


class GenerateTextAdvanced(io.ComfyNode):
    @classmethod
    def _model_options(cls) -> list[str]:
        options = list(text_model_choices())
        return options or ["none_available"]

    @classmethod
    def define_schema(cls) -> io.Schema:
        model_options = cls._model_options()

        return io.Schema(
            node_id="GenerateTextAdvanced_VENICE",
            display_name="Generate Text Advanced (Venice)",
            category="venice.ai",
            inputs=[
                io.Combo.Input(
                    "model",
                    options=model_options,
                    default=model_options[0],
                    tooltip="The model to use for text generation.",
                ),
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
                io.Boolean.Input(
                    "enable_system_prompt",
                    default=True,
                    tooltip="Enable or disable system prompt being passed on.",
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
                io.Float.Input(
                    "temperature",
                    default=0.5,
                    min=0.0,
                    max=2.0,
                    step=0.05,
                    tooltip=(
                        "Higher values like 0.8 will make the output more random, "
                        "while lower values like 0.2 will make it more focused and deterministic. "
                        "We generally recommend altering this or top_p but not both."
                    ),
                ),
                io.Int.Input(
                    "top_k",
                    default=40,
                    min=0,
                    tooltip="The number of highest probability vocabulary tokens to keep for top-k-filtering.",
                ),
                io.Float.Input(
                    "top_p",
                    default=0.8,
                    min=0.0,
                    max=2.0,
                    step=0.01,
                    tooltip=(
                        "An alternative to sampling with temperature, called nucleus sampling, "
                        "where the model considers the results of the tokens with top_p probability mass. "
                        "So 0.1 means only the tokens comprising the top 10% probability mass are considered."
                    ),
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
                io.Boolean.Input(
                    "enable_vision",
                    default=False,
                    tooltip=(
                        "Enable or disable vision tasks. Requires image_for_vision input to be populated and "
                        "for the LLM to actually support vision tasks to process."
                    ),
                ),
                io.String.Input(
                    "venice_parameters",
                    default="",
                    optional=True,
                    tooltip=(
                        "Optional input. Use the Textgen Parameters (Venice) node to pass extra Venice-specific parameters."
                    ),
                ),
                io.Image.Input(
                    "image_for_vision",
                    optional=True,
                    tooltip=(
                        "Optional input. Add an image for vision-supported LLMs to process when vision mode is enabled."
                    ),
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
        venice_parameters=None,
        image_for_vision=None,
    ) -> io.NodeOutput:
        ensure_prompt_length(prompt, 1500, label="Prompt")

        user_content = []
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
        if venice_parameters:
            payload["venice_parameters"] = venice_parameters

        json_response = client.post_json(API_ENDPOINTS["text_generate"], payload)
        try:
            content = json_response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Unexpected API response format: {json_response}") from exc

        return io.NodeOutput(content)
