import asyncio

from aiohttp import web

from server import PromptServer  # type: ignore

from ..venice_catalog import (
    get_characters,
    get_models,
    get_styles,
    refresh_characters,
    refresh_models,
    refresh_styles,
)
from ..venice_config import config as venice_config

routes = PromptServer.instance.routes


def _error_response(message: str) -> web.Response:
    return web.json_response({"message": message, "error": True})


@routes.post("/veniceai/save_apikey")
async def save_key_server(request: web.Request) -> web.Response:
    payload = await request.json()
    venice_config.save_apikey(payload.get("apikey", ""))
    return web.json_response({"message": "API key saved", "error": False})


@routes.get("/veniceai/get_apikey")
async def get_key_server(_: web.Request) -> web.Response:
    return web.json_response({"apikey": venice_config.apikey})


# @routes.get("/veniceai/update_models_list")
# async def update_models_list_server(request: web.Request) -> web.Response:
#     model_type = request.rel_url.query.get("type")
#     try:
#         payload = await asyncio.to_thread(refresh_models, model_type)
#     except Exception as exc:
#         return _error_response(str(exc))
#     return web.json_response({"message": "Model list updated", "error": False, "data": payload})


# @routes.get("/veniceai/get_models_list")
# async def get_models_list_server(request: web.Request) -> web.Response:
#     model_type = request.rel_url.query.get("type")
#     try:
#         payload = await asyncio.to_thread(get_models, model_type)
#     except Exception as exc:
#         return _error_response(str(exc))
#     return web.json_response(payload)


# @routes.get("/veniceai/update_styles_list")
# async def update_styles_list_server(_: web.Request) -> web.Response:
#     try:
#         payload = await asyncio.to_thread(refresh_styles)
#     except Exception as exc:
#         return _error_response(str(exc))
#     return web.json_response({"message": "Styles updated", "error": False, "data": payload})


# @routes.get("/veniceai/get_styles_list")
# async def get_styles_list_server(_: web.Request) -> web.Response:
#     try:
#         payload = await asyncio.to_thread(get_styles)
#     except Exception as exc:
#         return _error_response(str(exc))
#     return web.json_response(payload)


# @routes.get("/veniceai/update_characters_list")
# async def update_characters_list_server(_: web.Request) -> web.Response:
#     try:
#         payload = await asyncio.to_thread(refresh_characters)
#     except Exception as exc:
#         return _error_response(str(exc))
#     return web.json_response({"message": "Characters updated", "error": False, "data": payload})


# @routes.get("/veniceai/get_characters_list")
# async def get_characters_list_server(_: web.Request) -> web.Response:
#     try:
#         payload = await asyncio.to_thread(get_characters)
#     except Exception as exc:
#         return _error_response(str(exc))
#     return web.json_response(payload)
