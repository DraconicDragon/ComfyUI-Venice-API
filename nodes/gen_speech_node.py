import os
import tempfile

import requests
import torch  # type: ignore
import torchaudio  # type: ignore

from ..globals import API_ENDPOINTS, VENICEAI_BASE_URL


class GenerateSpeech:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (
                    "COMBO",
                    {
                        "default": "tts-kokoro",
                    },
                ),
                "input": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": ("The text to generate audio for. The maximum length is 4096 characters."),
                    },
                ),
                "response_format": (
                    [
                        # todo: some dont work because idk implementing would be ass
                        "mp3",
                        # "opus",
                        # "aac",
                        # "flac",
                        "wav",
                        "pcm",
                    ],
                    {
                        "default": "mp3",
                        "tooltip": (
                            "mp3: widely supported, lossy; "
                            # "opus: very good quality at low bitrate; "
                            # "aac: lossy, good for streaming; "
                            # "flac: lossless compressed audio; "
                            "wav: lossless raw audio; "
                            "pcm: uncompressed raw audio."
                        ),
                    },
                ),
                "speed": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.25,
                        "max": 4,
                        "step": 0.01,
                        "tooltip": (
                            "The text to image style to apply during prompt enhancement. "
                            "Does best with short descriptive prompts, like gold, marble or angry, menacing."
                        ),
                    },
                ),
                # "streaming": (
                #     "BOOLEAN",
                #     {
                #         "default": False,
                #         "tooltip": (
                #             "Should the content stream back sentence by sentence or be processed and returned as a complete audio file."
                #
                # ),
                #     },
                # ),
                "voice": (
                    "COMBO",
                    {
                        "default": "af_sky - tts-kokoro",
                    },
                ),
            }
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "gen_speech"
    CATEGORY = "venice.ai"

    EXPERIMENTAL = True

    def gen_speech(self, model, input, response_format, speed, voice):
        if len(input) > 4096 or len(input) == 0:
            raise ValueError("Generate Speech (Venice) Input exceeds the max length of 4096 characters or is empty.")

        url = VENICEAI_BASE_URL + API_ENDPOINTS["speech_generate"]

        # remove everything from voice string after and including the hyphen " - blabla"
        voice = voice.split(" - ")[0] if " - " in voice else voice

        # Prepare JSON payload
        payload = {
            "model": model,
            "input": input,
            "speed": speed,
            "voice": voice,
            "response_format": response_format,
            "streaming": False,
        }

        headers = {"Authorization": f"Bearer {os.getenv('VENICEAI_API_KEY')}", "Content-Type": "application/json"}

        # Send request
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Generate Speech (Venice) API request failed: {str(e)}")

        # Convert the audio response to a ComfyUI-compatible tensor and return it
        if not response.content or len(response.content) == 0:
            raise RuntimeError("No audio data received from Venice API.")

        # Save to temporary file and load with torchaudio for better format support
        with tempfile.NamedTemporaryFile(suffix=f".{response_format}", delete=False) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        try:
            # Load audio using torchaudio from the temporary file
            waveform, sample_rate = torchaudio.load(temp_file_path)
        except Exception as e:
            # Fallback: try different approaches for problematic formats
            try:
                if response_format == "pcm":
                    # For PCM, we need to handle it as raw audio data
                    # Assume 16-bit PCM, mono, 16kHz (adjust as needed based on API response)
                    audio_data = torch.frombuffer(response.content, dtype=torch.int16).float() / 32768.0
                    waveform = audio_data.unsqueeze(0)  # Add channel dimension
                    sample_rate = 16000  # Default sample rate, adjust if needed
                else:
                    # For other formats, try loading without specifying format
                    waveform, sample_rate = torchaudio.load(temp_file_path, format=None)
            except Exception as e2:
                raise RuntimeError(
                    f"Failed to load audio format '{response_format}' with all methods. Errors: {str(e)}, {str(e2)}"
                )
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass

        # Ensure shape is [B, C, T] (batch size 1)
        if waveform.dim() == 2:
            waveform = waveform.unsqueeze(0)  # [1, C, T]
        elif waveform.dim() == 1:
            waveform = waveform.unsqueeze(0).unsqueeze(0)  # [1, 1, T]

        return ({"waveform": waveform, "sample_rate": sample_rate},)


NODE_CLASS_MAPPINGS = {
    "GenerateSpeech_VENICE": GenerateSpeech,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GenerateSpeech_VENICE": "Generate Speech [BETA] (Venice)",
}
