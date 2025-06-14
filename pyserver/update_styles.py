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
styles_list_path = data_dir / "styles_list.json"


@routes.get("/veniceai/update_styles_list")
async def update_styles_list_server(request):
    try:
        headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}"}
        url = f"{VENICEAI_BASE_URL}{API_ENDPOINTS['list_styles']}"

        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises HTTPError for bad responses

        response_data = response.json()

        # remove "object" key from response_data
        response_data.pop("object", None)

        response_data["data"] = sorted(response_data.get("data", []))
        response_data["data"].insert(0, "none")

        with open(styles_list_path, "w") as f:
            json.dump(response_data, f, indent=2)

    # except requests.exceptions.HTTPError as http_err:
    #     print(f"HTTP error occurred: {http_err}")
    # except requests.exceptions.RequestException as req_err:
    #     print(f"Request error occurred: {req_err}")
    # except (ValueError, KeyError) as data_err:
    #     print(f"Data parsing error: {data_err}")
    except Exception as e:
        return (f"Unexpected error: {e}", True)

    response = (response_data, False)
    return web.json_response({"message": response[0], "error": response[1]})


@routes.get("/veniceai/get_styles_list")
async def get_local_styles_list(requests):
    with open(styles_list_path, "r") as f:
        styles_list_json = json.load(f)

    return web.json_response(styles_list_json)
