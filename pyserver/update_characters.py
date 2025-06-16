import json
import os
from pathlib import Path

import requests
from aiohttp import web

from server import PromptServer  # type: ignore

from ..globals import API_ENDPOINTS, VENICEAI_BASE_URL

routes = PromptServer.instance.routes

script_dir = Path(__file__).resolve().parent
data_dir = script_dir.parent / "data"
data_dir.mkdir(exist_ok=True)
characters_list_path = data_dir / "characters_list.json"

# TODO: unfinished


@routes.get("/veniceai/update_characters_list")
async def update_characters_list_server(request):
    try:
        headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}"}
        url = f"{VENICEAI_BASE_URL}{API_ENDPOINTS['characters']}"

        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises HTTPError for bad responses

        response_data = response.json()

        # remove "object" key from response_data
        response_data.pop("object", None)

        response_data["data"] = sorted(response_data.get("data", []), key=lambda item: item.get("slug", ""))

        with open(characters_list_path, "w") as f:
            json.dump(response_data, f, indent=4)

    except Exception as e:
        return (f"Unexpected error: {e}", True)

    response = (response_data, False)
    return web.json_response({"message": response[0], "error": response[1]})


@routes.get("/veniceai/get_characters_list")
async def get_local_characters_list(request):
    with open(characters_list_path, "r") as f:
        characters_list_json = json.load(f)

    characters = []
    for item in characters_list_json.get("data", []):
        if isinstance(item, dict) and item.get("slug"):
            characters.append(item.get("slug"))

    return web.json_response({"characters": characters})
