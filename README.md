last guaranteed working commit: 4d66f0e2da35bb211b3243a6bd4324dd20422d39

# ComfyUI venice.ai Flux/SDXL API Node

A custom node implementation for ComfyUI that integrates with venice.ai's Flux and SDXL image generation models. This project is adapted from [ComfyUI-FLUX-TOGETHER-API](https://github.com/BZcreativ/ComfyUI-FLUX-TOGETHER-API) to work with the venice.ai API.

### Disclaimer: I just made this on a whim because someone wanted something similar to Together.AI custom nodes but have them use venice instead and I don't have access to any API keys for any of the mentioned services.

Currently only supports generating an image, no list models/chat completions or upscale is implemented yet

## Features

- Direct integration with venice.ai's Flux and SDXL models
- Support for flux-dev, flux-dev-uncensored, fluently-xl and pony-realism 
- Configurable parameters including steps, guidance scale, and dimensions
- Negative prompt support (ignored when Flux is selected)
- Error handling and retry mechanisms


## Installation

1. Clone this repository into your ComfyUI custom_nodes directory:
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/DraconicDragon/ComfyUI-Venice-API.git
```

2. Install the required dependencies: (this might be done by comfyui automatically on restart?)
```bash
pip install -r requirements.txt
```

OR From the Comfyui Folder (this one is usually preferred if you have portable edition)
```bash
 ./python_embeded\python.exe -m pip install -r ComfyUI\custom_nodes\ComfyUI-Venice-API\requirements.txt
```

3. Edit the `config.ini` file in the root directory and add venice.ai API key:
```ini
[API]
API_KEY = your_api_key_here
BASE_URL = https://api.venice.ai/api/v1
```

## Configuration

1. Get your API key from [venice.ai](https://venice.ai)
2. Add your API key to the configuration file

## Usage

1. Start ComfyUI
2. Find the "Generate Image (Venice)" in the node browser
3. Configure the parameters:
   - Prompt: Your image generation prompt
   - Negative Prompt: Elements to avoid in the generation
   - Steps: Generation steps (1-30)
   - Width: Image width (512-2048)
   - Height: Image height (512-2048)
   - Seed: Generation seed
   - CFG: Guidance scale (0.1-15.0)

For detailed usage instructions, see [USAGE.md](USAGE.md)

## Parameters

| Parameter       | Type    | Range     | Default | Description                |
|-----------------|---------|-----------|---------|----------------------------|
| prompt          | string  | -         | ""      | Main generation prompt     |
| negative_prompt | string  | -         | ""      | Elements to avoid          |
| steps           | integer | 1-30      | 20      | Number of generation steps |
| width           | integer | 512-2048  | 1024    | Image width                |
| height          | integer | 512-2048  | 1024    | Image height               |
| seed            | integer | 0-MAX_INT | 0       | Generation seed            |
| cfg             | float   | 0.1-15.0  | 3.5     | Guidance scale             |

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Credits

- This project is adapted from [ComfyUI-FLUX-TOGETHER-API](https://github.com/BZcreativ/ComfyUI-FLUX-TOGETHER-API)
- venice.ai for providing the Flux/SDXL API
- [ComfyUI-FLUX-TOGETHER-API](https://github.com/BZcreativ/ComfyUI-FLUX-TOGETHER-API) for their work
- ComfyUI team for the amazing framework

## Author

Created by [BZcreativ](https://github.com/BZcreativ)

venice.ai rewrite by [DraconicDragon](https://github.com/DraconicDragon)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Example

todo

i never installed these nodes lol