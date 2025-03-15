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
    "CharCountTextBox": CharCountTextBox,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CharCountTextBox": "Textbox w/ char count",
}
