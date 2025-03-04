# dont follow stuff thats in here i dont think its correct 


# ComfyUI venice.ai API Node Usage Guide

### Disclaimer: I just made this on a whim because someone wanted something similar to Together.AI custom nodes but use venice instead and I don't have access to any API keys for any of the mentioned services.

## Setup

1. Ensure you have a venice.ai account and API key
2. Configure your API key in `config.ini`
3. Install all required dependencies (should be done automatically by comfy?)

## Node Configuration

### Input Parameters

#### Required Parameters:
- **Prompt** (String)
  - Your main generation prompt
  - Be specific and detailed for best results if using Flux

- **Negative Prompt** (String)
  - Elements you want to avoid in the generation
  - Leave empty if not needed | Will be ignored if flux-dev or flux-dev-uncensored is selected as model

- **Steps** (Integer)
  - Range: 1-30
  - Default: 20

- **Width** (Integer)
  - Range: 512-2048
  - Default: 1024
  - Must be a multiple of 32
  - Common values: 512, 768, 1024 (1MP), 1440 (Flux | 2MP)

- **Height** (Integer)
  - Range: 512-2048
  - Default: 1024
  - Must be a multiple of 32
  - Common values: 512, 768, 1024 (1MP), 1440 (Flux | 2MP)

- **Seed** (Integer)
  - Range: 0 to max 64-bit integer
  - Default: -1 | Random
  - Reuse a seed with same prompt to reproduce an image 

- **CFG (Guidance Scale)** (Float)
  - Range: 0.1-15.0
  - Default: 3.5
  - Recommended range: 5.0-10.0 (SDXL) | ~3.5 (Flux)

### Output

The node outputs a single image tensor compatible with other ComfyUI nodes.

## Best Practices

1. **Prompt Engineering**
   - Be specific and detailed in your prompts
   - Use descriptive adjectives
   - Include style references when needed

2. **Performance**
   - Start with lower step counts (20-30) for testing
   - Increase steps for final generations
   - Use reasonable image dimensions (1024x1024 is standard)

3. **Error Handling/Troubleshooting**
   - Check console for error messages
   - Verify API key is correctly configured
   - Ensure parameters are within valid ranges

## Common Workflows

### Basic Image Generation
1. Add Together API Node to workspace
2. Connect to a Load Image node
3. Configure prompt and basic parameters
4. Execute workflow

### Advanced Usage
1. Combine with other ComfyUI nodes
2. Use seed control for consistent results
3. Experiment with guidance scale for style control

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify key in config.ini
   - Check API key validity
   - Ensure proper formatting

2. **Generation Errors**
   - Verify parameter ranges
   - Check prompt length
   - Monitor API rate limits

3. **Image Quality Issues**
   - Adjust step count
   - Modify guidance scale
   - Refine prompt

## Examples

### Basic Prompt Example
```
A beautiful landscape with mountains and lakes, cinematic lighting, high detail
```

### Advanced Prompt Example
```
A stunning mountain landscape at sunset, volumetric lighting, 
golden hour, ultra detailed, professional photography, 
8k resolution, artistic composition
```

### Negative Prompt Example
```
blur, haze, low quality, distortion, bad composition, 
oversaturated, unrealistic lighting
```

## Support

For issues and feature requests, please use the GitHub issue tracker.
