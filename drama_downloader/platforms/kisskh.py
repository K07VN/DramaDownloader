"""
drama_downloader.platforms.kisskh
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Extractor for KissKH and its mirrors (kisskh.co, kisskh.do, kisskh.id, kisskh.is).
"""

import re
from typing import Optional, List, Dict, Any
from .base import BasePlatform
from ..models import Series, Episode, Subtitle, CatalogResult, CatalogItem


class KisskhPlatform(BasePlatform):
    platform_id = "kisskh"
    display_name = "KissKH"

    MIRRORS = ["kisskh.co", "kisskh.do", "kisskh.id", "kisskh.is"]

    def can_handle(self, url: str) -> bool:
        u = url.lower().strip()
        return "kisskh" in u or u.startswith("kisskh:")

    def _extract_id(self, url: str) -> str:
        u = url.strip()
        m = re.search(r"kisskh:(\d+)", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"[?&]id=(\d+)", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"/DramaList/Drama/(\d+)", u, re.I)
        return m.group(1) if m else ""

    def _request_mirror(self, endpoint: str) -> Any:
        last_err = None
        for domain in self.MIRRORS:
            try:
                url = f"https://{domain}/api/{endpoint}"
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                    "Referer": f"https://{domain}/",
                }
                resp = self.http.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                last_err = e
        raise ValueError(f"KissKH all mirrors failed: {last_err}")

    def load_series(self, url: str) -> Series:
        kk_id = self._extract_id(url)
        if not kk_id:
            raise ValueError(f"Could not extract KissKH drama ID from: {url}")

        data = self._request_mirror(f"DramaList/Drama/{kk_id}?isq=false")
        if not data or not isinstance(data.get("episodes"), list):
            raise ValueError(f"KissKH: drama not found for ID: {kk_id}")

        raw_episodes = data["episodes"]
        raw_episodes = sorted(raw_episodes, key=lambda x: float(x.get("number") or 0))

        title = str(data.get("title") or f"KissKH {kk_id}").strip()
        cover = data.get("thumbnail") or ""
        desc = data.get("description") or ""

        episodes: List[Episode] = []
        for idx, ep_data in enumerate(raw_episodes):
            ep_num = idx + 1
            ep_no = str(ep_data.get("number", ep_num))
            ep_id = ep_data.get("id")

            episodes.append(
                Episode(
                    num=ep_num,
                    title=f"Episode {ep_no}" if len(raw_episodes) > 1 else "Movie",
                    url=f"https://kisskh.co/Drama/{title}/Episode-{ep_no}?id={kk_id}&ep={ep_id}",
                    direct_url=None,
                    thumb=cover,
                    locked=False,
                    extra={"kk_id": kk_id, "kk_ep": ep_id, "kk_num": ep_no},
                )
            )

        return Series(
            name=title,
            platform=self.platform_id,
            series_id=f"kisskh:{kk_id}",
            cover=cover,
            description=desc,
            episode_count=len(episodes),
            accessible_count=len(episodes),
            episodes=episodes,
            url=f"https://kisskh.co/Drama/?id={kk_id}",
        )

    def get_video_url(self, episode: Episode) -> Optional[str]:
        if episode.direct_url:
            return episode.direct_url

        kk_ep = episode.extra.get("kk_ep")
        if not kk_ep:
            return None

        try:
            res = self._request_mirror(f"DramaList/Episode/{kk_ep}.png?err=false&ts=null&time=null")
            if res and isinstance(res, dict):
                v_url = res.get("Video") or res.get("Video_tmp")
                if v_url:
                    if v_url.startswith("//"):
                        v_url = "https:" + v_url
                    episode.direct_url = v_url
                    return v_url
        except Exception:
            pass

        return None
