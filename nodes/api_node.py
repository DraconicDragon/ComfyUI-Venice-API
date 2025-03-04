
# Todo: chat history/memory/context for LLM

# todo: inpainting

# todo: LLM characters

# todo: use variants api (currently in beta)

# todo: fix upscale node (see updated api doc)





import base64
import configparser
import io
import os

import numpy as np
import requests
import torch
import torchvision.transforms as transforms
from PIL import Image
from torchvision.transforms import ToPILImage, ToTensor

from ..globals import API_ENDPOINTS, VENICEAI_BASE_URL


# region image gen
class GenerateImageBase:
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate_image"
    CATEGORY = "venice.ai"

    def process_result(self, result):
        try:
            if isinstance(result, dict) and "images" in result:
                img_data = result["images"][0]  # Only first image is returned because only 1 is possible rn
            else:
                raise Exception(f"Error, unexpected response: {str(e)}") from e

            img_bytes = base64.b64decode(img_data)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            # img = Image.open("./a.png").convert("RGB")

            transform = transforms.ToTensor()
            img_tensor = transform(img)  # Shape: [C, H, W]
            img_tensor = img_tensor.unsqueeze(0)  # add batch dimension as dimension 0
            img_tensor = img_tensor.permute(0, 2, 3, 1)  # Shape: [B, H, W, C]

            print(f"Debug - Image tensor shape: {img_tensor.shape}")
            return (img_tensor,)

        except Exception as e:
            raise Exception(f"Error processing image result: {str(e)}") from e

    def create_blank_image(self):
        blank_img = Image.new("RGB", (512, 512), color="black")
        img_array = np.array(blank_img).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_array)[None,]
        return (img_tensor,)

    def check_multiple_of_32(self, width, height):
        if width % 32 != 0 or height % 32 != 0:
            raise ValueError(f"Width {width} and height {height} must be multiples of 32.")


class GenerateImage(GenerateImageBase):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (
                    "COMBO",
                    {"default": "flux-dev"},
                ),
                "prompt": ("STRING", {"default": "A flying cat made of lettuce", "multiline": True}),
                "neg_prompt": (
                    "STRING",
                    {
                        "placeholder": "Bad composition, rating_explicit, Text, signature, lowres, lowres, low details, faded image, out of focus, cropped, clipped, cut-off, out of frame, deserted scene, empty scene, vacant scene, desolate scene, sparse décor, bad quality, worst quality,",
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
                "style_preset": ("COMBO", {"default": "none"}),
                "hide_watermark": ("BOOLEAN", {"default": True}),
            },
            "optional": {"seed": ("INT", {"default": -1})},
        }

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
        seed=-1,
    ):
        images_tensor = ()  # empty tuple for tensors

        if model in ["flux-dev", "flux-dev-uncensored"]:
            print(f"VeniceAPI INFO: Ignoring negative prompt for {model}.")
            neg_prompt = ""

        try:
            self.check_multiple_of_32(width, height)  # todo: make this be validate node instead

            headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}", "Content-Type": "application/json"}
            url = VENICEAI_BASE_URL + API_ENDPOINTS["image_generate"]

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

            for i in range(batch_size):
                payload["seed"] = seed + i
                response = requests.request("POST", url, json=payload, headers=headers)

                if response.status_code != 200:
                    raise requests.exceptions.HTTPError(
                        f"HTTP error: {response.status_code}, Response: {response.text}"
                    )

                images_tensor += self.process_result(response.json())

            merged = torch.cat(images_tensor, dim=0)
            return (merged,)

        except Exception as e:
            raise Exception(f"Error processing image result: {str(e)}") from e


# endregion

# todo: https://docs.comfy.org/custom-nodes/backend/more_on_inputs#dynamically-created-inputs
# for model list update?


# region text gen
class GenerateText:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (
                    "COMBO",
                    {
                        "default": "llama-3.3-70b",
                    },
                ),
                "system_prompt": ("STRING", {"default": "", "multiline": True}),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "frequency_penalty": ("FLOAT", {"default": 1.5, "min": 0.0, "max": 2.0, "step": 0.1}),
                "presence_penalty": ("FLOAT", {"default": 1.5, "min": 0.0, "max": 2.0, "step": 0.1}),
                "temperature": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 2.0, "step": 0.1}),
                "top_p": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.1}),
                "enable_qwen25_vision": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "image_for_vision": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("response",)
    FUNCTION = "generate_text"
    CATEGORY = "venice.ai"

    def generate_text(
        self,
        model,
        system_prompt,
        prompt,
        frequency_penalty,
        presence_penalty,
        temperature,
        top_p,
        enable_qwen25_vision,
        **kwargs,
    ):
        url = VENICEAI_BASE_URL + API_ENDPOINTS["text_generate"]

        user_content = []
        image_for_vision = kwargs.get("image_for_vision", None)

        if image_for_vision is not None and enable_qwen25_vision:
            # Convert tensor to PIL Image
            image_tensor = image_for_vision[0]  # shape: (H, W, 3)
            image_np = image_tensor.cpu().numpy()  # Still in (H, W, 3)
            image_np = (image_np * 255).astype(np.uint8)  # Scale from [0, 1] to [0, 255] if needed
            pil_image = Image.fromarray(image_np)

            # Resize image to meet constraints
            original_width, original_height = pil_image.size
            aspect_ratio = original_width / original_height

            # Determine target dimensions
            if original_width > original_height:
                target_width = 1024
                target_height = int(target_width / aspect_ratio)
                if target_height < 256:
                    target_height = 256
                    target_width = int(target_height * aspect_ratio)
            else:
                target_height = 1024
                target_width = int(target_height * aspect_ratio)
                if target_width < 256:
                    target_width = 256
                    target_height = int(target_width / aspect_ratio)

            # Round dimensions to multiples of 14
            def round_down_to_multiple(value, multiple):
                return (value // multiple) * multiple

            target_width = round_down_to_multiple(target_width, 14)
            target_height = round_down_to_multiple(target_height, 14)

            # Ensure minimum dimension is 256 after rounding
            if min(target_width, target_height) < 256:
                if target_width < target_height:
                    target_width = ((256 + 13) // 14) * 14
                    target_height = round_down_to_multiple(int(target_width / aspect_ratio), 14)
                else:
                    target_height = ((256 + 13) // 14) * 14
                    target_width = round_down_to_multiple(int(target_height * aspect_ratio), 14)

            pil_image = pil_image.resize((target_width, target_height), Image.LANCZOS)

            # Convert to base64 and check size
            buffered = io.BytesIO()
            pil_image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            # Resize further if base64 exceeds 4.5MB
            while len(img_base64) > 4500000:
                scaling_factor = (4500000 / len(img_base64)) ** 0.5
                new_width = int(target_width * scaling_factor)
                new_height = int(target_height * scaling_factor)

                new_width = max(round_down_to_multiple(new_width, 14), 256)
                new_height = max(round_down_to_multiple(new_height, 14), 256)

                pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                target_width, target_height = new_width, new_height

                buffered = io.BytesIO()
                pil_image.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            user_content.extend(
                [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}},
                ]
            )
        else:
            user_content.append({"type": "text", "text": prompt})

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": model,
            "messages": messages,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "temperature": temperature,
            "top_p": top_p,
        }

        headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}", "Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            raise requests.exceptions.HTTPError(f"HTTP error: {response.status_code}, Response: {response.text}")

        json_response = response.json()
        content = json_response["choices"][0]["message"]["content"]
        print(content)
        return (content,)


# endregion


# region upscale img


# todo: needs rework
class UpscaleImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "upscale"
    CATEGORY = "venice.ai"

    def upscale(self, image):

        url = VENICEAI_BASE_URL + API_ENDPOINTS["upscale_image"]

        # Ensure the tensor is in the correct format (C, H, W) and has 3 channels
        if image.dim() == 4 and image.shape[0] == 1:
            image = image.squeeze(0)

        if image.shape[0] > 3:
            image = image[:3, :, :]  # Keep only the first 3 channels (RGB)

        to_pil = ToPILImage()
        pil_image = to_pil(image)

        # Save the PIL image to a byte buffer in PNG format
        byte_io = io.BytesIO()
        pil_image.save(byte_io, format="PNG")
        byte_io.seek(0)  # Rewind the buffer to the beginning

        # Create the multipart payload
        files = {"file": ("image.png", byte_io, "image/png")}

        headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}", "Content-Type": "multipart/form-data"}
        response = requests.request("POST", url, files=files, headers=headers)

        if response.status_code != 200:
            raise requests.exceptions.HTTPError(f"HTTP error: {response.status_code}, Response: {response.text}")

        try:
            upscaled_image = Image.open(io.BytesIO(response.content))

            to_tensor = ToTensor()
            tensor = to_tensor(upscaled_image)  # CHW format?
            #print(f"Debug - Upscaled image tensor shape: {tensor.shape}")
            tensor_bhwc = tensor.permute(1, 2, 0)  # from (C, H, W) to (H, W, C)
            tensor_bhwc = tensor_bhwc.to(torch.float32)

            if tensor_bhwc.ndimension() == 3:  # HWC format
                tensor_bhwc = tensor_bhwc.unsqueeze(0)  # Add batch dimension (B, H, W, C)
                # i hate tensors

            return (tensor_bhwc,)

        except Exception as e:
            raise requests.exceptions.HTTPError(
                f"Failed to retrieve upscaled image. Status code: {response.status_code}, Response: {response.text}"
            )


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


class CharCountTextBox:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_text": ("STRING", {"default": "", "multiline": True}),
            }
        }

    CATEGORY = "venice.ai"

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "return_same_text"

    def return_same_text(self, input_text):

        return {"ui": {"text": input_text}, "result": (input_text,)}


NODE_CLASS_MAPPINGS = {
    # "testaaaaa": TestNode,
    "CharCountTextBox": CharCountTextBox,
    "GenerateImage_VENICE": GenerateImage,
    "UpscaleImage_VENICE": UpscaleImage,
    "GenerateText_VENICE": GenerateText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    # "testaaaaa": "TestAAAAA",
    "CharCountTextBox": "Textbox w/ char count",
    "GenerateImage_VENICE": "Generate Image (Venice)",
    "UpscaleImage_VENICE": "Upscale Image (Venice) Not working!",
    "GenerateText_VENICE": "Generate Text (Venice)",
}
