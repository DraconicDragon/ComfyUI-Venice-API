import logging
import os
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple


from comfy.utils import ProgressBar  # type: ignore

from ..globals import API_ENDPOINTS
from ..venice_client import VeniceAPIError, client

LOG = logging.getLogger(__name__)

# Defaults
POLL_INTERVAL_SECONDS = 5
MAX_POLLS = 100  # MAX_POLLS * POLL_INTERVAL_SECONDS = x minutes total wait time
PROGRESS_BAR_TOTAL = 100
PROJECT_ROOT = Path(__file__).resolve().parents[1]
VIDEO_OUTPUT_DIR = PROJECT_ROOT / "testing_video"
VIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_SAVE_API_VIDEOS = os.environ.get("VENICE_CLIENT_DEBUG", "").lower() in {"1", "true"}


def queue_video_job(payload: dict) -> Tuple[str, str]:
    """
    Enqueue a Venice video generation job and return (model, queue_id).
    Raises VeniceAPIError on failure.
    """
    resp = client.post_json(API_ENDPOINTS["video_queue"], payload)
    model = resp.get("model") or payload.get("model") or ""
    queue_id = resp.get("queue_id")
    if not queue_id:
        raise VeniceAPIError(f"Video queue response missing queue_id: {resp}")
    LOG.info("Venice video queued: model=%s queue_id=%s", model, queue_id)
    return model, queue_id


def _guess_suffix(content_type: str) -> str:
    if "mp4" in content_type:
        return ".mp4"
    if "webm" in content_type:
        return ".webm"
    if "quicktime" in content_type or "mov" in content_type:
        return ".mov"
    return ".bin"


def _build_video_path(queue_id: str, suffix: str) -> Path:
    clean_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in queue_id)
    timestamp = int(time.time())
    filename = f"{clean_id or 'queue'}_{timestamp}{suffix}"
    return VIDEO_OUTPUT_DIR / filename


def poll_video_until_ready(
    *,
    model: str,
    queue_id: str,
    progress_bar: Optional[ProgressBar] = None,
    delete_on_completion: bool = True,
    max_polls: int = MAX_POLLS,
    poll_interval: float = POLL_INTERVAL_SECONDS,
) -> Tuple[str, str]:
    """
    Poll Venice /video/retrieve until the video is ready.
    Returns (video_filepath, queue_id). Raises VeniceAPIError on failure/timeout.
    """
    pbar = progress_bar or ProgressBar(PROGRESS_BAR_TOTAL)
    last_progress = 0

    for attempt in range(max_polls):
        time.sleep(poll_interval)

        retrieve_payload = {
            "model": model,
            "queue_id": queue_id,
            "delete_media_on_completion": delete_on_completion,
        }

        resp = client.request(
            "POST",
            API_ENDPOINTS["video_retrieve"],
            json=retrieve_payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "*/*",  # allow binary video or JSON status
            },
        )
        ctype = (resp.headers or {}).get("Content-Type", "").lower()

        is_status_json = ctype.startswith("application/json") or ctype.startswith("text/")
        if is_status_json:
            data = resp.json()
            status = (data.get("status") or "UNKNOWN").upper()
            exec_dur = float(data.get("execution_duration") or 0)
            avg_exec = float(data.get("average_execution_time") or 0)

            LOG.debug(
                "Venice video status: status=%s queue_id=%s exec_ms=%s avg_ms=%s attempt=%s/%s",
                status,
                queue_id,
                exec_dur,
                avg_exec,
                attempt + 1,
                max_polls,
            )

            if avg_exec and avg_exec > 0:
                progress_value = min(int(exec_dur / avg_exec * PROGRESS_BAR_TOTAL), PROGRESS_BAR_TOTAL)
            else:
                progress_value = min(last_progress + 1, PROGRESS_BAR_TOTAL)

            delta = progress_value - last_progress
            if delta > 0:
                pbar.update(delta)
                last_progress = progress_value

            if status not in {"PROCESSING", "QUEUED"}:
                raise VeniceAPIError(f"Video job reported unexpected status '{status}' for queue_id {queue_id}")
            continue

        # Got binary content (video)
        suffix = _guess_suffix(ctype)
        if DEBUG_SAVE_API_VIDEOS:
            video_path = _build_video_path(queue_id, suffix)
            with open(video_path, "wb") as fp:
                fp.write(resp.content)
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(resp.content)
                video_path = Path(tmp_file.name)

        LOG.debug(
            "Venice video ready: queue_id=%s saved_to=%s content_type=%s",
            queue_id,
            video_path,
            ctype,
        )

        if last_progress < PROGRESS_BAR_TOTAL:
            pbar.update(PROGRESS_BAR_TOTAL - last_progress)

        return str(video_path), queue_id

    raise VeniceAPIError(
        f"Timed out waiting for Venice video. queue_id={queue_id} after {max_polls * poll_interval:.0f}s"
    )


def list_testing_videos() -> List[str]:
    """Return cached video filenames that can be selected inside a node."""
    if not VIDEO_OUTPUT_DIR.exists():
        return []
    return sorted(entry.name for entry in VIDEO_OUTPUT_DIR.iterdir() if entry.is_file())


def get_testing_video_path(filename: str) -> Path:
    """Resolve the video file inside testing_video and ensure it exists."""
    video_path = VIDEO_OUTPUT_DIR / filename
    if not video_path.exists() or not video_path.is_file():
        raise FileNotFoundError(f"Test video not found: {filename}")
    return video_path
