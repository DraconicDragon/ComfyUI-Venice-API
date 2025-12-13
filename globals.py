import os

API_ENDPOINTS = {
    "list_models": "/models",  # response type is list of strings
    "list_styles": "/image/styles",  #
    "characters": "/characters",  # response type is list of strings
    "image_generate": "/image/generate",  # response type is json with images key, each item is image in base64
    "upscale_image": "/image/upscale",  # NOTE: apparently doesnt even work yet? idk; response type is image/png file, content type is multipart/form-data
    "text_generate": "/chat/completions",  # has much info, text response is in choices: content, can have multiple choices apparently but dosnt seem to be utilized
    "speech_generate": "/audio/speech",  # type: file (audio/aac; audio/mpeg; audio/wav.. etc)
    "video_queue": "/video/queue",  #
    "video_quote": "/video/quote",  # price estimate, takes same payload as video_queue
    "video_retrieve": "/video/retrieve",  # get video file by job id
    "list_api_keys": "/api_keys",
}

VENICEAI_BASE_URL = "https://api.venice.ai/api/v1"

# request hygiene
USER_AGENT = "ComfyUI-Venice-API/1.0 (by draconicdragon on github)"


os.environ["VENICE_CLIENT_DRY_RUN"] = "0"
os.environ["VENICE_CLIENT_DEBUG"] = "1"
