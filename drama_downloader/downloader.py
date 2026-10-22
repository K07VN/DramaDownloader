"""
drama_downloader.downloader
~~~~~~~~~~~~~~~~~~~~~~~~~~~
High-performance video and subtitle download engine with chunking and progress reporting.
"""

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional, List, Dict, Any
from .models import Series, Episode, Subtitle
from .client import http, HttpClient
from .platforms import get_video_url


class DownloadProgress:
    def __init__(self, total_bytes: int = 0):
        self.total_bytes = total_bytes
        self.downloaded_bytes = 0
        self.start_time = time.time()
        self.speed = 0.0

    def update(self, chunk_size: int):
        self.downloaded_bytes += chunk_size
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            self.speed = self.downloaded_bytes / elapsed

    @property
    def percent(self) -> float:
        if self.total_bytes > 0:
            return min(100.0, (self.downloaded_bytes / self.total_bytes) * 100.0)
        return 0.0


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:100] if cleaned else "video"


def vtt_to_srt(vtt_text: str) -> str:
    """Converts WebVTT subtitle text to standard SubRip (.srt) format."""
    lines = vtt_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output = []
    idx = 1
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("STYLE"):
            if line.startswith("STYLE") or line.startswith("NOTE"):
                while i < len(lines) and lines[i].strip():
                    i += 1
            i += 1
            continue

        m = re.search(
            r"(?:(\d{2}):)?(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(?:(\d{2}):)?(\d{2}):(\d{2})\.(\d{3})",
            line,
        )
        if m:
            h1 = m.group(1) or "00"
            m1, s1, ms1 = m.group(2), m.group(3), m.group(4)
            h2 = m.group(5) or "00"
            m2, s2, ms2 = m.group(6), m.group(7), m.group(8)
            srt_timestamp = f"{h1}:{m1}:{s1},{ms1} --> {h2}:{m2}:{s2},{ms2}"

            output.append(str(idx))
            output.append(srt_timestamp)
            idx += 1
            i += 1
            while i < len(lines) and lines[i].strip():
                cleaned_text = re.sub(r"<[^>]+>", "", lines[i].strip())
                if cleaned_text:
                    output.append(cleaned_text)
                i += 1
            output.append("")
        else:
            i += 1
    return "\n".join(output)


class DramaDownloader:
    """Download orchestrator for drama episodes and subtitles."""

    def __init__(
        self,
        output_dir: str = "./downloads",
        concurrency: int = 2,
        client: Optional[HttpClient] = None,
        save_vtt: bool = False,
    ):
        self.output_dir = output_dir
        self.concurrency = concurrency
        self.http = client or http
        self.save_vtt = save_vtt
        os.makedirs(self.output_dir, exist_ok=True)

    def download_episode(
        self,
        episode: Episode,
        series_name: Optional[str] = None,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> str:
        """Downloads a single episode to the output directory and returns the file path."""
        stream_url = episode.direct_url or get_video_url(episode)
        if not stream_url:
            raise ValueError(f"Could not resolve stream URL for Episode {episode.num}")

        folder = self.output_dir
        if series_name:
            folder = os.path.join(self.output_dir, sanitize_filename(series_name))
            os.makedirs(folder, exist_ok=True)

        ep_prefix = f"EP{episode.num:02d}"
        clean_title = sanitize_filename(episode.title)
        filename = f"{ep_prefix} - {clean_title}.mp4"
        out_path = os.path.join(folder, filename)

        part_path = out_path + ".part"

        resp = self.http.get(stream_url, stream=True)
        resp.raise_for_status()

        total_size = int(resp.headers.get("content-length", 0))
        progress = DownloadProgress(total_size)

        chunk_size = 1024 * 64
        with open(part_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    progress.update(len(chunk))
                    if progress_callback:
                        progress_callback(progress)

        if os.path.exists(out_path):
            os.remove(out_path)
        os.rename(part_path, out_path)

        for sub in episode.subs:
            self._download_subtitle(sub, folder, ep_prefix)

        return out_path

    def _download_subtitle(self, sub: Subtitle, folder: str, ep_prefix: str):
        try:
            raw_content = b""
            if sub.url.startswith("data:"):
                import base64
                data_part = sub.url.split(",", 1)[1]
                raw_content = base64.b64decode(data_part)
            else:
                s_resp = self.http.get(sub.url)
                if s_resp.status_code == 200:
                    raw_content = s_resp.content

            if not raw_content:
                return

            text_content = raw_content.decode("utf-8", errors="ignore")

            is_vtt = "WEBVTT" in text_content[:50] or sub.url.endswith(".vtt")

            if is_vtt:
                if self.save_vtt:
                    vtt_path = os.path.join(folder, f"{ep_prefix}_{sub.lang}.vtt")
                    with open(vtt_path, "w", encoding="utf-8") as f:
                        f.write(text_content)

                srt_content = vtt_to_srt(text_content)
                srt_path = os.path.join(folder, f"{ep_prefix}_{sub.lang}.srt")
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(srt_content)
            else:
                srt_path = os.path.join(folder, f"{ep_prefix}_{sub.lang}.srt")
                with open(srt_path, "wb") as f:
                    f.write(raw_content)
        except Exception:
            pass

    def download_series(
        self,
        series: Series,
        episodes_range: Optional[List[int]] = None,
        on_episode_start: Optional[Callable[[Episode], None]] = None,
        on_episode_done: Optional[Callable[[Episode, str], None]] = None,
        on_episode_error: Optional[Callable[[Episode, Exception], None]] = None,
    ) -> List[str]:
        """Batch downloads multiple episodes in a series using thread pool."""
        target_episodes = series.episodes
        if episodes_range:
            target_episodes = [ep for ep in target_episodes if ep.num in episodes_range]

        completed_paths = []

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = {}
            for ep in target_episodes:
                if on_episode_start:
                    on_episode_start(ep)
                fut = executor.submit(self.download_episode, ep, series.name)
                futures[fut] = ep

            for fut in as_completed(futures):
                ep = futures[fut]
                try:
                    path = fut.result()
                    completed_paths.append(path)
                    if on_episode_done:
                        on_episode_done(ep, path)
                except Exception as e:
                    if on_episode_error:
                        on_episode_error(ep, e)

        return completed_paths
