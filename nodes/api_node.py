import base64
import configparser
import io
import os

import numpy as np
import requests
import torch
import torchvision.transforms as transforms
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential

API_ENDPOINTS = {
    "list_models": "/models",  # response type is list of strings
    "image_generate": "/image/generate",  # response type is dict with images key, each item is image in base64
    "upscale_image": "/image/upscale",  # NOTE: not supported yet in code, response type is image/png file
}


class ConfigLoader:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        config_path = os.path.join(parent_dir, "config.ini")
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.set_api_key()
        self.set_base_url()

    def get_config_key(self, section, key):
        try:
            return self.config[section][key]
        except KeyError:
            raise KeyError(f"{key} not found in section {section} of config file.")

    def set_api_key(self):
        try:
            api_key = self.get_config_key("API", "API_KEY")
            os.environ["VENICE_API_KEY"] = api_key
        except KeyError as e:
            print(f"Error: {str(e)}")

    # load base url from config
    def set_base_url(self):
        try:
            base_url = self.get_config_key("API", "BASE_URL")
            os.environ["VENICE_BASE_URL"] = base_url
        except KeyError as e:
            print(f"Error: {str(e)}")


config_loader = ConfigLoader()


# region image gen
class GenerateImageBase:
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate_image"
    CATEGORY = "venice.ai"

    def get_models(self, model_type: str) -> list:  # model_type = image or text model
        try:
            headers = {"Authorization": f"Bearer {os.getenv('VENICE_API_KEY')}"}
            url = os.getenv("VENICE_BASE_URL") + API_ENDPOINTS["list_models"]
            response = requests.get(url, headers=headers).json()

            print(f"Debug - Response: {response}")
            #print(f"Debug - Response type: {type(response)}")

            if not isinstance(response, dict) or "data" not in response or not isinstance(response["data"], list):
                raise ValueError("Unexpected API response format")

            return [model["id"] for model in response["data"] if model.get("type") == model_type]

        except Exception as e:
            print(f"Could not fetch models: {str(e)}\nAttempting to switch to default selection...")
            if model_type == "image":
                return ["flux-dev", "flux-dev-uncensored", "fluently-xl", "pony-realism"]
            elif model_type == "text":
                return ["dolphin-2.9.2-qwen2-72b"]
            else:
                return ["check console"]  # dont know which models supported or if any

    def process_result(self, result):
        try:
            if isinstance(result, dict) and "images" in result:
                img_data = result["images"][0]  # Only first image is returned because only 1 is possible rn
            else:
                raise ValueError("Unexpected response format")

            img_bytes = base64.b64decode(img_data)
            img = Image.open(io.BytesIO(img_bytes))
            img_array = np.array(img).astype(np.float32) / 255.0
            img_tensor = torch.from_numpy(img_array).unsqueeze(0)
            print(f"Debug - Image tensor shape: {img_tensor.shape}")
            return img_tensor

        except Exception as e:
            print(f"Error processing image result: {str(e)}")
            return self.create_blank_image()

    def create_blank_image(self):
        blank_img = Image.new("RGB", (512, 512), color="black")
        img_array = np.array(blank_img).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_array)[None,]
        return (img_tensor,)

    def check_multiple_of_32(self, width, height):
        if width % 32 != 0 or height % 32 != 0:
            raise ValueError(f"Width {width} and height {height} must be multiples of 32.")

    # NOTE: unused,
    def generate_image(self, arguments):
        self.check_multiple_of_32(arguments["width"], arguments["height"])

        # try:
        #     response = self.client.images.generate(
        #         model=model_path,
        #         prompt=arguments["prompt"],
        #         width=arguments["width"],
        #         height=arguments["height"],
        #         steps=arguments["steps"],
        #         n=1,
        #         response_format="b64_json",
        #         **{k: v for k, v in arguments.items() if k not in ["prompt", "width", "height", "steps"]}
        #     )
        #     return self.process_result(response)
        # except Exception as e:
        #     print(f"Error generating image: {str(e)}")
        #     return self.create_blank_image()
        # todo: is unsued rn
        try:
            payload = {
                "model": arguments["model"],
                "prompt": arguments["prompt"],
                "negative_prompt": arguments["neg_prompt"],
                "width": arguments["width"],
                "height": arguments["height"],
                "steps": arguments["steps"],
                "hide_watermark": arguments["hide_watermark"],
                "return_binary": False,
                "seed": arguments["steps"],
                "cfg_scale": arguments["cfg_scale"],
                "style_preset": arguments["style_preset"],
            }
            headers = {"Authorization": f"Bearer {os.getenv('VENICE_API_KEY')}", "Content-Type": "application/json"}

            url = os.getenv("VENICE_BASE_URL") + API_ENDPOINTS["image_generate"]
            response = requests.request("POST", url, json=payload, headers=headers)
            return self.process_result(response.json())

        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return self.create_blank_image()


class GenerateImage(GenerateImageBase):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (
                    ["flux-dev", "flux-dev-uncensored", "fluently-xl", "pony-realism", "stable-diffusion-3.5"],
                    {"default": "flux-dev"},
                ),
                "prompt": ("STRING", {"default": "A flying cat made of lettuce", "multiline": True}),
                "neg_prompt": (
                    "STRING",
                    {
                        "placeholder": "bad quality, worst quality,",
                        "multiline": True,
                        "tooltip": "Negative prompt. This is ignored when using flux-dev or flux-dev-uncensored",
                    },
                ),
                "width": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 256,
                        "max": 2048,
                        "step": 8,
                    },
                ),
                "height": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 256,
                        "max": 2048,
                        "step": 8,
                    },
                ),
                "batch_size": ("INT", {"default": 1, "min:": 1, "max": 4}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 30}),
                "guidance": ("FLOAT", {"default": 3.0, "min": 0.1, "max": 15.0}),
                "style_preset": (
                    [
                        "none",
                        "3D Model",
                        "Analog Film",
                        "Anime",
                        "Cinematic",
                        "Comic Book",
                        "Craft Clay",
                        "Digital Art",
                        "Enhance",
                        "Fantasy Art",
                        "Isometric Style",
                        "Line Art",
                        "Lowpoly",
                        "Neon Punk",
                        "Origami",
                        "Photographic",
                        "Pixel Art",
                        "Texture",
                        "Advertising",
                        "Food Photography",
                        "Real Estate",
                        "Abstract",
                        "Cubist",
                        "Graffiti",
                        "Hyperrealism",
                        "Impressionist",
                        "Pointillism",
                        "Pop Art",
                        "Psychedelic",
                        "Renaissance",
                        "Steampunk",
                        "Surrealist",
                        "Typography",
                        "Watercolor",
                        "Fighting Game",
                        "GTA",
                        "Super Mario",
                        "Minecraft",
                        "Pokemon",
                        "Retro Arcade",
                        "Retro Game",
                        "RPG Fantasy Game",
                        "Strategy Game",
                        "Street Fighter",
                        "Legend of Zelda",
                        "Architectural",
                        "Disco",
                        "Dreamscape",
                        "Dystopian",
                        "Fairy Tale",
                        "Gothic",
                        "Grunge",
                        "Horror",
                        "Minimalist",
                        "Monochrome",
                        "Nautical",
                        "Space",
                        "Stained Glass",
                        "Techwear Fashion",
                        "Tribal",
                        "Zentangle",
                        "Collage",
                        "Flat Papercut",
                        "Kirigami",
                        "Paper Mache",
                        "Paper Quilling",
                        "Papercut Collage",
                        "Papercut Shadow Box",
                        "Stacked Papercut",
                        "Thick Layered Papercut",
                        "Alien",
                        "Film Noir",
                        "HDR",
                        "Long Exposure",
                        "Neon Noir",
                        "Silhouette",
                        "Tilt-Shift",
                    ],
                    {"default": "none"},
                ),
                "hide_watermark": ("BOOLEAN", {"default": True}),
                "api_key": ("STRING", {"default": "your_key_here"}),
            },
            "optional": {"seed": ("INT", {"default": -1})},
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_image(
        self,
        model,
        prompt,
        neg_prompt,
        width,
        height,
        batch_size,
        steps,
        guidance,
        style_preset,
        hide_watermark,
        api_key,
        seed=-1,
    ):
        os.environ["VENICE_API_KEY"] = api_key  # todo: updating nodes replaces config ini

        if model in ["flux-dev", "flux-dev-uncensored"]:
            print("Ignoring negative prompt for flux-dev and flux-dev-uncensored models")
            neg_prompt = ""

        images_tensor = []  # empty list

        arguments = {  # ignore for now
            "model": model,
            "prompt": prompt,
            "neg_prompt": neg_prompt,
            "width": width,
            "height": height,
            "batch_size": batch_size,
            "steps": steps,
            "cfg_scale": guidance,
            "style_preset": style_preset,
            "hide_watermark": hide_watermark,
            "seed": seed,
        }

        try:
            # Override the base class method to handle the response directly
            self.check_multiple_of_32(width, height)

            payload = {
                "model": model,
                "prompt": prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "hide_watermark": hide_watermark,
                "return_binary": False,
                "seed": seed,
                "cfg_scale": guidance,
                "style_preset": style_preset,
                "negative_prompt": neg_prompt,
            }
            if style_preset == "none":
                del payload["style_preset"]

            headers = {"Authorization": f"Bearer {os.getenv('VENICE_API_KEY')}", "Content-Type": "application/json"}

            url = os.getenv("VENICE_BASE_URL") + API_ENDPOINTS["image_generate"]

            for i in range(batch_size):
                payload["seed"] = seed + i
                response = requests.request("POST", url, json=payload, headers=headers)
                if response.status_code != 200:
                    raise ValueError(f"Error in response: {response}") #{response.content}
                images_tensor.append(self.process_result(response.json()))
            return torch.cat(images_tensor, dim=0)
            # return super().generate_image(arguments)

        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return self.create_blank_image()


# endregion


# region text gen
# class GenerateText:
#     @classmethod
#     def INPUT_TYPES(cls):
#         return {
#             "required": {
#                 "model": (
#                     ["llama-3.3-70b", "llama-3.2-3b", "dolphin-2.9.2-qwen2-72b", "llama-3.1-405b", "qwen32b"],
#                     {"default": "llama-3.3-70b"},
#                 ),
#                 "prompt": ("STRING", {"default": "A flying cat made of lettuce", "multiline": True}),
#                 "neg_prompt": (
#                     "STRING",
#                     {
#                         "placeholder": "bad quality, worst quality,",
#                         "multiline": True,
#                         "tooltip": "Negative prompt. This is ignored when using flux-dev or flux-dev-uncensored",
#                     },
#                 ),
#                 "width": (
#                     "INT",
#                     {
#                         "default": 1024,
#                         "min": 256,
#                         "max": 2048,
#                         "step": 8,
#                     },
#                 ),
#                 "height": (
#                     "INT",
#                     {
#                         "default": 1024,
#                         "min": 256,
#                         "max": 2048,
#                         "step": 8,
#                     },
#                 ),
#                 "steps": ("INT", {"default": 20, "min": 1, "max": 30}),
#                 "guidance": ("FLOAT", {"default": 3.0, "min": 0.1, "max": 15.0}),
#                 "style_preset": (
#                     [
#                         "none",
#                         "3D Model",
#                         "Analog Film",
#                         "Anime",
#                     ],
#                     {"default": "none"},
#                 ),
#                 "hide_watermark": ("BOOLEAN", {"default": True}),
#                 "api_key": ("STRING", {"default": "your_key_here"}),
#             },
#             "optional": {"seed": ("INT", {"default": -1})},
#         }


# endregion

# region FluxPro


# class FluxPro(BaseFlux):
#     @classmethod
#     def INPUT_TYPES(cls):
#         return {
#             "required": {
#                 "prompt": ("STRING", {"default": "", "multiline": True}),
#                 "width": ("INT", {"default": 1024, "min": 256, "max": 1440}),
#                 "height": ("INT", {"default": 1024, "min": 256, "max": 1440}),
#                 "steps": ("INT", {"default": 4, "min": 1, "max": 40}),
#                 "prompt_upsampling": ("BOOLEAN", {"default": True}),
#                 "safety_tolerance": (["1", "2", "3", "4", "5", "6"], {"default": "2"}),
#                 "guidance": ("FLOAT", {"default": 2.5, "min": 0.1, "max": 10.0}),
#                 "interval": ("INT", {"default": 2, "min": 1, "max": 10}),
#             },
#             "optional": {"seed": ("INT", {"default": -1})},
#         }

#     def generate_image(
#         self, prompt, width, height, steps, prompt_upsampling, safety_tolerance, guidance, interval, seed=-1
#     ):
#         arguments = {
#             "prompt": prompt,
#             "width": width,
#             "height": height,
#             "steps": steps,
#             "prompt_upsampling": prompt_upsampling,
#             "safety_tolerance": safety_tolerance,
#             "guidance": guidance,
#             "interval": interval,
#         }
#         if seed != -1:
#             arguments["seed"] = seed
#         return super().generate_image("black-forest-labs/FLUX.1-pro", arguments)


# class FluxPro11(BaseFlux):
#     @classmethod
#     def INPUT_TYPES(cls):
#         return {
#             "required": {
#                 "prompt": ("STRING", {"default": "", "multiline": True}),
#                 "width": ("INT", {"default": 1024, "min": 256, "max": 1440}),
#                 "height": ("INT", {"default": 1024, "min": 256, "max": 1440}),
#                 "prompt_upsampling": ("BOOLEAN", {"default": True}),
#                 "steps": ("INT", {"default": 1, "min": 1, "max": 1}),
#                 "safety_tolerance": (["1", "2", "3", "4", "5", "6"], {"default": "2"}),
#             },
#             "optional": {"seed": ("INT", {"default": -1})},
#         }

#     def generate_image(self, prompt, width, height, prompt_upsampling, steps, safety_tolerance, seed=-1):
#         arguments = {
#             "prompt": prompt,
#             "width": width,
#             "height": height,
#             "prompt_upsampling": prompt_upsampling,
#             "steps": steps,
#             "safety_tolerance": safety_tolerance,
#         }
#         if seed != -1:
#             arguments["seed"] = seed
#         return super().generate_image("black-forest-labs/FLUX.1.1-pro", arguments)


# endregion


class TestNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images_A": ("IMAGE",),
                "images_B": ("IMAGE",),
            }
        }

    CATEGORY = "testaaaaa"

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "merge"

    def merge(self, images_A, images_B):
        images = []
        print(f"images_A: {images_A.shape}")
        print(f"images_B: {images_B.shape}")
        images.append(images_A)
        # images.append(images_B)
        all_images = torch.cat(images, dim=0)
        print(f"all_images: {all_images.shape}")
        return (all_images,)


class TestNode2:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images_A": ("IMAGE",),
                "images_B": ("IMAGE",),
            }
        }

    CATEGORY = "testaaaaa"

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "merge"

    def merge(self, images_A, images_B):
        images = []
        print(f"images_A: {images_A.shape}")
        print(f"images_B: {images_B.shape}")

        transform = transforms.ToPILImage()
        images_A = images_A.permute(0, 3, 1, 2)
        images_B = images_B.permute(0, 3, 1, 2)
        imgA = transform(images_A[0])
        imgB = transform(images_B[0])
        imgA.show()
        imgB.show()

        img_array = np.array(imgA).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_array).unsqueeze(0)
        print(f"Debug - Image tensor shape: {img_tensor.shape}")
        images.append(img_tensor)

        img_array = np.array(imgB).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_array).unsqueeze(0)
        print(f"Debug - Image tensor shape: {img_tensor.shape}")
        images.append(img_tensor)
        all_images = torch.cat(images, dim=0)
        print(f"all_images: {all_images.shape}")
        return (all_images,)


NODE_CLASS_MAPPINGS = {
    "testaaaaa": TestNode,
    "testaaaaa2": TestNode2,
    "GenerateImage_VENICE": GenerateImage,
    # "FluxPro_TOGETHER": FluxPro, # venice doesnt have flux pro/1.1/ultra
    # "FluxPro11_TOGETHER": FluxPro11,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "testaaaaa": "TestAAAAA",
    "testaaaaa2": "TestAAAAA2",
    "GenerateImage_VENICE": "Generate Image (Venice)",
    # "FluxPro_TOGETHER": "Flux Pro (TOGETHER)",https://music.youtube.com/watch?v=mH_Zl2Rgl5M
    # "FluxPro11_TOGETHER": "Flux Pro 1.1 (TOGETHER)",
}
