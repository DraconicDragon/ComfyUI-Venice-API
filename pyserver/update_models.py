import json
import os
import re
from pathlib import Path

import requests
from aiohttp import web

from server import PromptServer  # type: ignore

from ..globals import API_ENDPOINTS, VENICEAI_BASE_URL

routes = PromptServer.instance.routes

script_dir = Path(__file__).resolve().parent
data_dir = script_dir.parent / "data"
data_dir.mkdir(exist_ok=True)
all_model_list_path = data_dir / "all_model_list.json"


async def fetch_models_list():
    try:
        headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}"}
        url = f"{VENICEAI_BASE_URL}{API_ENDPOINTS['list_models']}"
        params = {"type": "all"}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raises HTTPError for bad responses

        response_data = response.json()

        # params = {"type": "embedding"}

        # r2 = requests.get(url, headers=headers, params=params)
        # r2.raise_for_status()  # Raises HTTPError for bad responses

        # r2_data = r2.json()

        # # concatenate response_data and r2_data
        # if isinstance(response_data, list) and isinstance(r2_data, list):
        #     response_data = response_data + r2_data

    # except requests.exceptions.HTTPError as http_err:
    #     print(f"HTTP error occurred: {http_err}")
    # except requests.exceptions.RequestException as req_err:
    #     print(f"Request error occurred: {req_err}")
    # except (ValueError, KeyError) as data_err:
    #     print(f"Data parsing error: {data_err}")
    except Exception as e:
        return (f"Unexpected error: {e}", True)

    return (response_data, False)


async def humanize_name(model_id: str) -> str:

    # Handle number-letter combinations without space
    model_id = re.sub(r"(\d+)([a-zA-Z]+)", lambda m: f"{m.group(1)}{m.group(2).upper()}", model_id)

    # Replace remaining separators with spaces and title case
    model_id = re.sub(r"[-_]", " ", model_id).title()

    humanized = model_id.replace("xl", "XL").replace("vl", "VL").replace("sd", "SD").replace("llama", "LLaMA")

    return humanized


@routes.get("/veniceai/update_models_list")
async def update_models_list_server(request):
    # img_model_json = await fetch_model_list("image")
    # txt_model_json = await fetch_model_list("text")
    # merged_json = {"object": "list", "data": img_model_json.get("data", []) + txt_model_json.get("data", [])}

    response = await fetch_models_list()

    if response[1]:  # true = error happened
        return response

    merged_json = response[0]

    # Validating response structure
    if not isinstance(merged_json, dict) or "data" not in merged_json:
        raise ValueError("Unexpected API response format")

    # Create lookup dictionary and enhanced JSON
    enhanced_data = []
    model_dict = {}

    # Process all models for enhanced JSON
    for model in merged_json["data"]:
        model_id = model["id"]
        model_spec = model.get("model_spec", {})

        # Format traits excluding function_calling_default
        traits = [
            trait.replace("_", " ").title()
            for trait in model_spec.get("traits", [])
            if trait != "function_calling_default"
        ]

        # Create humanized description
        parts = [await humanize_name(model_id)]
        if "availableContextTokens" in model_spec:
            parts.append(f"ctx: {model_spec['availableContextTokens']}")
        if traits:
            parts.append(" | ".join(traits))

        # Add to enhanced data
        enhanced_model = model.copy()
        enhanced_model["humanized"] = " | ".join(parts)
        enhanced_data.append(enhanced_model)
        model_dict[model_id] = enhanced_model

    # Save enhanced JSON
    enhanced_json = {"object": "list", "data": enhanced_data}
    with open(all_model_list_path, "w") as f:
        json.dump(enhanced_json, f, indent=2)

    response = ("Model list update success", False)
    return web.json_response({"message": response[0], "error": response[1]})


# NOTE: routes are frozen and don't update with ComfyUI-HotReloadHack
@routes.get("/veniceai/get_models_list")
async def get_local_models_list_server(request):
    with open(all_model_list_path, "r") as f:
        model_list_json = json.load(f)

    data = model_list_json["data"]

    # Create final sorted lists of names/ids
    img_models = [m["id"] for m in data if m.get("type") == "image"]
    txt_models = [m["id"] for m in data if m.get("type") == "text"]
    tts_models = [m["id"] for m in data if m.get("type") == "tts"]

    # Collect voices with humanized model name
    tts_voices = []
    for m in data:
        if m.get("type") == "tts":
            voices = m.get("model_spec", {}).get("voices", [])
            # humanized = m.get("humanized", m.get("id", ""))
            humanized = m.get("id", "")
            tts_voices.extend([f"{humanized} - {voice}" for voice in voices])

    # if tts_voices:
    #     print(f"TTS Voices: {', '.join(tts_voices[:100])}")

    data = {
        "image_models": sorted(img_models),
        "text_models": sorted(txt_models),
        "tts_models": sorted(tts_models),
        "tts_voices": sorted(tts_voices),
        "model_list_json": model_list_json,
    }
    return web.json_response(data)
