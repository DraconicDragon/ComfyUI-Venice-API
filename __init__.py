import importlib
import logging
import os
from pathlib import Path

from .pyserver import routes  # noqa: F401

NODE_PACKAGE = Path(__file__).with_name("nodes")
node_list = sorted(
    module.stem for module in NODE_PACKAGE.glob("*.py") if module.is_file() and not module.name.startswith("_")
)

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
NODE_MODULE_PREFIX = f"{__name__}.nodes"

for module_name in node_list:
    try:
        imported_module = importlib.import_module(f"{NODE_MODULE_PREFIX}.{module_name}")
    except ImportError as e:
        logging.warning(f"Could not import module '{module_name}': {e}")
        continue

    has_classes = hasattr(imported_module, "NODE_CLASS_MAPPINGS")
    has_display = hasattr(imported_module, "NODE_DISPLAY_NAME_MAPPINGS")

    if has_classes and has_display:
        NODE_CLASS_MAPPINGS.update(imported_module.NODE_CLASS_MAPPINGS)
        NODE_DISPLAY_NAME_MAPPINGS.update(imported_module.NODE_DISPLAY_NAME_MAPPINGS)
    elif has_classes or has_display:
        logging.warning(
            "Module '%s' defines '%s' but is missing '%s'; module skipped",
            module_name,
            "NODE_CLASS_MAPPINGS" if has_classes else "NODE_DISPLAY_NAME_MAPPINGS",
            "NODE_DISPLAY_NAME_MAPPINGS" if has_classes else "NODE_CLASS_MAPPINGS",
        )
    # modules without either mapping are ignored silently

WEB_DIRECTORY = os.path.join(os.path.dirname(__file__), "js")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
