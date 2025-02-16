import json
import os
from pathlib import Path

from aiohttp import web
from server import PromptServer

routes = PromptServer.instance.routes

CONFIG_FILE = Path(__file__).parent.parent / "veniceai_config.json"


def ensure_config_file_exists():
    # Create the config file with a default value if it doesn't exist
    if not CONFIG_FILE.exists():
        default_key = "your_venice_api_key_here"  # Set a default value (e.g., empty string)
        set_venice_key(default_key)


def set_venice_key(apikey):
    os.environ["VENICEAI_API_KEY"] = apikey

    with open(CONFIG_FILE, "w") as f:
        json.dump({"apikey": apikey}, f)


@routes.post("/veniceai/save_apikey")
async def post_key(request):
    data = await request.json()
    print(data)

    set_venice_key(data.get("apikey", ""))

    return web.json_response({})


@routes.get("/veniceai/get_apikey")
async def get_key(request):
    return web.json_response({"apikey": os.getenv("VENICEAI_API_KEY")})


ensure_config_file_exists()


if CONFIG_FILE.exists():
    with open(CONFIG_FILE) as f:
        saved_key = json.load(f).get("apikey", "")
        set_venice_key(saved_key)
