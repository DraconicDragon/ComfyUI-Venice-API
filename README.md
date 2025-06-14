# ComfyUI venice.ai Flux/SDXL/LLM API Nodes

An unofficial custom node implementation for ComfyUI that integrates with venice.ai's Flux and SDXL image generation models (and upscale + text gen). This project is adapted from [ComfyUI-FLUX-TOGETHER-API](https://github.com/BZcreativ/ComfyUI-FLUX-TOGETHER-API) to work with the venice.ai API.

Disclaimer: I just made this on a whim because someone wanted something similar to Together.AI custom nodes but have them use venice instead and also, I don't have access to any API keys for any of the mentioned services. i guess it should work, sometimes?

Speech API/TTS - Done (its in beta, Comfyui Settings > search for experimental and turn on the setting for having it show experimental nodes in search)
New models may have different voices which are not handled right now so any new model might not be surported until code updated to dynamically update voices upon model change but this may pose an issue for workflow sharing so i probably have to just bunch all the voices together, unless theres a better option, maybe a string input

Generate Image node: now has safe mode toggle and some more tooltips, and revised seed limits

~~# todo: fix upscale node (see updated api doc)~~ DONE, its now called "I2I Enhance + Upscale (Venice), its a new node so the old one wont work anymore

~~# todo: inpainting~~  Deprecated by venice, new thing coming ig

# todo: LLM characters list

# todo: use variants api (currently in beta) | idk what happened to this

# Todo: chat history/memory/context for LLM

*Implemented stuff from venice api:*

- Image generation endpoint
- Chat completion/Text generation endpoint
- Upscale image endpoint (untested)

*Missing-ish Stuff from venice api:*

- A way to update hardcoded things like:
  - available models using list models enpoint
  - available style presets using styles endpoint

- Some Validation on queue for API limits like prompt max length or width/height
  - these are different for different models so this isnt planned to be implemented unless the api exposes those limits somehow

If there's no "untested" on any of the points it means it should work but there's not been extensive testing on it

## Below ReadMe text is slightly altered from original Flux Together API readme, it was not reworked or anything so it might not be correct or up to date

### Features

- Direct integration with venice.ai's Flux and SDXL models
- Support for flux-dev, flux-dev-uncensored, fluently-xl and pony-realism (status: 25th Jan 2025)
- Support for all LLMs venice.ai offers (status: 25th Jan 2025)
- Configurable parameters including steps, guidance scale, and dimensions
  - including fake-ish batch size (just 2 requests after one another returned as 1 output)
- Negative prompt support (ignored when Flux is selected)
- Error handling i guess

### Installation - these instructions are a mess

1. Clone this repository into your ComfyUI custom_nodes directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/DraconicDragon/ComfyUI-Venice-API.git
```

2. Install the required dependencies: (this might be done by comfyui automatically on restart already?)

```bash
pip install -r requirements.txt
```

OR From the Comfyui Folder (this one is usually preferred if you have portable edition)

```bash
 ./python_embeded\python.exe -m pip install -r ComfyUI\custom_nodes\ComfyUI-Venice-API\requirements.txt
```

outdated, configure in node, in future this will likely be in comfy settings
3. Edit the `config.ini` file in the root directory and add venice.ai API key:

```ini
[API]
API_KEY = your_api_key_here
BASE_URL = https://api.venice.ai/api/v1
```

### Configuration

1. Get your API key from [venice.ai](https://venice.ai)
2. ~~Add your API key to the configuration file~~ yeah no just add it in the nodes

### Usage

1. Start ComfyUI
2. Find the "Generate Image (Venice)" in the node browser (double-click empty space in ComfyUI)
2.1. or the Generate Text (Venice) node
3. Configure the parameters:
   - Prompt: Your image generation prompt
   - Negative Prompt: Elements to avoid in the generation
   - Steps: Generation steps (1-30)
   - Width: Image width (512-2048)
   - Height: Image height (512-2048)
   - Seed: Generation seed
   - CFG: Guidance scale (0.1-15.0)

For detailed usage instructions, see [USAGE.md](USAGE.md)

### Parameters

| Parameter       | Type    | Range     | Default | Description                |
|-----------------|---------|-----------|---------|----------------------------|
| prompt          | string  | -         | ""      | Main generation prompt     |
| negative_prompt | string  | -         | ""      | Elements to avoid          |
| steps           | integer | 1-30      | 20      | Number of generation steps |
| width           | integer | 512-1280?  | 1024    | Image width                |
| height          | integer | 512-1280?  | 1024    | Image height               |
| seed            | integer | 0-MAX_INT | 0       | Generation seed            |
| cfg             | float   | 0.1-15.0  | 3.5     | Guidance scale             |

### License

MIT License - see [LICENSE](LICENSE) file for details.

### Credits

- This project is adapted from [ComfyUI-FLUX-TOGETHER-API](https://github.com/BZcreativ/ComfyUI-FLUX-TOGETHER-API)
- venice.ai for providing the Flux/SDXL API
- [ComfyUI-FLUX-TOGETHER-API](https://github.com/BZcreativ/ComfyUI-FLUX-TOGETHER-API) for their work
- ComfyUI team for the amazing framework

### Author

Created by [BZcreativ](https://github.com/BZcreativ)

venice.ai rewrite by [DraconicDragon](https://github.com/DraconicDragon)

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Example

todo

i never installed these nodes lol (i did now)
