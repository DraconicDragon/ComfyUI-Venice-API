API_ENDPOINTS = {
    "list_models": "/models",  # response type is list of strings
    "image_generate": "/image/generate",  # response type is json with images key, each item is image in base64
    "upscale_image": "/image/upscale",  # NOTE: apparently doesnt even work yet? idk; response type is image/png file, content type is multipart/form-data
    "text_generate": "/chat/completions",  # has much info, text response is in choices: content, can have multiple choices apparently but dosnt seem to be utilized
}

VENICEAI_BASE_URL = "https://api.venice.ai/api/v1"

# unused right now
headers = {"User-Agent": "ComfyUI-Venice-API/1.0 (by draconicdragon on github)"}
