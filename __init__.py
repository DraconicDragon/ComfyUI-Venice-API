import os

from comfy_api.latest import ComfyExtension, io

from .nodes.gen_video_from_text_node import GenerateVideoFromText
from .nodes.test_node import DCTestNode


class VeniceExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [DCTestNode, GenerateVideoFromText]


async def comfy_entrypoint() -> VeniceExtension:
    return VeniceExtension()


WEB_DIRECTORY = os.path.join(os.path.dirname(__file__), "js")

__all__ = ["WEB_DIRECTORY"]
