import importlib
import logging
import os

from .pyserver import (
    get_key_from_jssetting,  # noqa: F401
    update_characters,  # noqa: F401
    update_models,  # noqa: F401
    update_styles,  # noqa: F401
)

node_list = [
    # "things_n_stuff_node",
    "gen_image_node",
    # "gen_image_inpaint_node",
    "gen_text_node",
    "gen_text_advanced_node",
    "gen_text_venice_params_node",
    "i2i_enhance_upscale_node",
    "gen_speech_node",
    "util_nodes",
]

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

for module_name in node_list:
    try:
        imported_module = importlib.import_module(f".nodes.{module_name}", __name__)
        NODE_CLASS_MAPPINGS.update(imported_module.NODE_CLASS_MAPPINGS)
        NODE_DISPLAY_NAME_MAPPINGS.update(imported_module.NODE_DISPLAY_NAME_MAPPINGS)
    except ImportError as e:
        logging.warning(f"Could not import module '{module_name}': {e}")


WEB_DIRECTORY = os.path.join(os.path.dirname(__file__), "js")


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
