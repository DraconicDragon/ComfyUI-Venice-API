import json
import os
from pathlib import Path

from aiohttp import web
from server import PromptServer

routes = PromptServer.instance.routes

CONFIG_FILE = Path(__file__).parent.parent / "veniceai_config.json"


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


if CONFIG_FILE.exists():
    with open(CONFIG_FILE) as f:
        saved_key = json.load(f).get("apikey", "")
        set_venice_key(saved_key)
