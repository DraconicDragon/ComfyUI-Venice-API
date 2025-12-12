import logging
import tempfile
import time
from typing import Optional, Tuple

from comfy.utils import ProgressBar  # type: ignore

from ..globals import API_ENDPOINTS
from ..venice_client import VeniceAPIError, client

LOG = logging.getLogger(__name__)

# Defaults
POLL_INTERVAL_SECONDS = 3
MAX_POLLS = 600  # MAX_POLLS * POLL_INTERVAL_SECONDS = x minutes total wait time


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
    pbar = progress_bar or ProgressBar(max_polls)
    polls_done = 0

    for attempt in range(max_polls):
        polls_done += 1
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
            exec_dur = data.get("execution_duration")
            avg_exec = data.get("average_execution_time")

            LOG.info(
                "Venice video status: status=%s queue_id=%s exec_ms=%s avg_ms=%s attempt=%s/%s",
                status,
                queue_id,
                exec_dur,
                avg_exec,
                attempt + 1,
                max_polls,
            )

            pbar.update(1)

            if status not in {"PROCESSING", "QUEUED"}:
                raise VeniceAPIError(f"Video job reported unexpected status '{status}' for queue_id {queue_id}")
            continue

        # Got binary content (video)
        suffix = _guess_suffix(ctype)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
            fp.write(resp.content)
            video_path = fp.name

        LOG.info("Venice video ready: queue_id=%s saved_to=%s content_type=%s", queue_id, video_path, ctype)

        remaining = max_polls - polls_done
        if remaining > 0:
            pbar.update(remaining)

        return video_path, queue_id

    raise VeniceAPIError(
        f"Timed out waiting for Venice video. queue_id={queue_id} after {max_polls * poll_interval:.0f}s"
    )
