import logging
import os
import shutil
import subprocess
import tempfile

import requests
import torch
import torchaudio

from comfy_api.latest import io

try:
    import imageio_ffmpeg
except ImportError:  # pragma: no cover
    imageio_ffmpeg = None

from ..globals import API_ENDPOINTS
from ..nodes.catalog_utils import tts_model_choices, tts_voice_choices
from ..nodes.utils import ensure_prompt_length
from ..venice_client import client

try:
    from torchaudio import sox_io_backend
except ImportError:  # pragma: no cover - default backend may not be available everywhere
    sox_io_backend = None

try:
    from torchaudio import soundfile_backend
except ImportError:  # pragma: no cover
    soundfile_backend = None


LOG = logging.getLogger(__name__)


class GenerateSpeech(io.ComfyNode):
    @classmethod
    def _model_options(cls) -> list[str]:
        options = list(tts_model_choices())
        return options or ["none_available"]

    @classmethod
    def _voice_options(cls) -> list[str]:
        options = list(tts_voice_choices())
        return options or ["none_available"]

    @staticmethod
    def _ffmpeg_decode(temp_path: str) -> tuple[torch.Tensor, int]:
        if imageio_ffmpeg is None:
            LOG.error("imageio-ffmpeg is not installed; ffmpeg fallback unavailable")
            raise RuntimeError("imageio-ffmpeg is not installed; install it to enable ffmpeg fallback.")

        try:
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as exc:
            LOG.error("Unable to download ffmpeg via imageio-ffmpeg: %s", exc)
            raise RuntimeError("Failed to download ffmpeg via imageio-ffmpeg") from exc

        LOG.info("Decoding Venice audio via ffmpeg executable %s", ffmpeg)
        try:
            process = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    temp_path,
                    "-acodec",
                    "pcm_f32le",
                    "-f",
                    "f32le",
                    "-ac",
                    "1",
                    "-ar",
                    "44100",
                    "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            LOG.error("ffmpeg failed to decode %s: %s", temp_path, exc.stderr.decode(errors="ignore"))
            raise RuntimeError(f"ffmpeg failed to decode {temp_path}: {exc.stderr.decode(errors='ignore')}") from exc

        audio_data = torch.frombuffer(process.stdout, dtype=torch.float32).clone()
        audio_data = audio_data.reshape(-1, 1).transpose(0, 1)
        return audio_data, 44100

    @staticmethod
    def _load_with_torchaudio_backends(temp_path: str, response_format: str) -> tuple[torch.Tensor, int]:
        backends = [sox_io_backend, soundfile_backend]
        errors: list[str] = []
        for backend in backends:
            if backend is None:
                continue
            backend_name = getattr(backend, "__name__", "torchaudio_backend")
            try:
                return backend.load(temp_path)
            except Exception as exc:
                error = str(exc)
                errors.append(error)
                LOG.warning("torchaudio backend %s failed to load %s: %s", backend_name, response_format, error)
        if errors:
            raise RuntimeError(f"Failed to load audio format '{response_format}' with all methods: {', '.join(errors)}")
        raise RuntimeError(
            f"Failed to load audio format '{response_format}' because no torchaudio backend is available."
        )

    @classmethod
    def define_schema(cls) -> io.Schema:
        response_formats = ["mp3", "opus", "aac", "flac", "wav", "pcm"]
        model_options = cls._model_options()
        voice_options = cls._voice_options()

        return io.Schema(
            node_id="GenerateSpeech_VENICE",
            display_name="Generate Speech (Venice)",
            category="venice.ai",
            inputs=[
                io.Combo.Input(
                    "model",
                    options=model_options,
                    default=model_options[0],
                    tooltip="Model to use for text-to-speech",
                ),
                io.String.Input(
                    "input",
                    default="",
                    multiline=True,
                    placeholder="Text to speak",
                    tooltip="The text prompt used for speech generation (max 4096 chars)",
                ),
                io.Combo.Input(
                    "response_format",
                    options=response_formats,
                    default=response_formats[0],
                    tooltip="Audio format to request from the Venice TTS API",
                ),
                io.Float.Input(
                    "speed",
                    default=1.0,
                    min=0.25,
                    max=4.0,
                    step=0.01,
                    tooltip="Playback speed multiplier (1.0 = normal speed)",
                ),
                io.Combo.Input(
                    "voice",
                    options=voice_options,
                    default=voice_options[0],
                    tooltip="Voice preset to use for the TTS model",
                ),
            ],
            outputs=[io.Audio.Output(id="audio", display_name="audio")],
        )

    @classmethod
    def execute(cls, model, input, response_format, speed, voice) -> io.NodeOutput:
        ensure_prompt_length(input, 4096, label="TTS input")

        # todo: currently models' voices show up as "model-name - voice_name"
        # todo: this can be in dynamiccombo so the single combo dropdown is not cluttered with all the voices of all selectable models
        normalized_voice = voice.split(" - ")[-1].strip() if " - " in voice else voice
        payload = {
            "model": model,
            "input": input,
            "speed": speed,
            "voice": normalized_voice,
            "response_format": response_format,
            "streaming": False,
        }

        try:
            response = client.request(
                "POST",
                API_ENDPOINTS["speech_generate"],
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Generate Speech (Venice) API request failed: {str(exc)}")

        if not response.content:
            raise RuntimeError("No audio data received from Venice API.")

        temp_path = None
        waveform = None
        sample_rate = None
        try:
            # Save to temp file and load with torchaudio for better format support
            with tempfile.NamedTemporaryFile(suffix=f".{response_format}", delete=False) as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name

            try:
                waveform, sample_rate = cls._load_with_torchaudio_backends(temp_path, response_format)
            except RuntimeError as audio_exc:
                LOG.warning("torchaudio decoding failed for %s: %s", response_format, audio_exc)
                if response_format == "pcm" and response.content:
                    LOG.info("Falling back to raw PCM interpretation for %s", response_format)
                    audio_data = torch.frombuffer(response.content, dtype=torch.int16).float() / 32768.0
                    waveform = audio_data.unsqueeze(0)
                    sample_rate = 16000  # Default sample rate, might need change?
                else:
                    LOG.info("Attempting ffmpeg fallback for %s audio", response_format)
                    waveform, sample_rate = cls._ffmpeg_decode(temp_path)
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

        if waveform is None or sample_rate is None:
            raise RuntimeError("Unable to decode Venice speech response.")

        if waveform.dim() == 2:
            waveform = waveform.unsqueeze(0)  # [1, C, T]
        elif waveform.dim() == 1:
            waveform = waveform.unsqueeze(0).unsqueeze(0)  # [1, 1, T]

        audio_value: io.Audio.Type = {"waveform": waveform, "sample_rate": sample_rate}
        return io.NodeOutput(audio_value)
