"""
drama_downloader.platforms.goodshort
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Extractor for GoodShort and GoodReels platforms.
"""

import re
from typing import Optional, List, Dict, Any
from .base import BasePlatform, GOODBOS_TOKEN
from ..models import Series, Episode, Subtitle, CatalogResult, CatalogItem


class GoodShortPlatform(BasePlatform):
    platform_id = "goodshort"
    display_name = "GoodShort"

    BASE_URL = "https://goodshort.goodbos.online"

    def can_handle(self, url: str) -> bool:
        u = url.lower().strip()
        return "goodshort" in u or "goodreels" in u or u.startswith("goodshort:")

    def _extract_id(self, url: str) -> str:
        m = re.search(r"/(\d{8,})", url)
        if m:
            return m.group(1)
        m = re.search(r"[?&]id=(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"(\d{6,})", url)
        return m.group(1) if m else ""

    def load_series(self, url: str) -> Series:
        book_id = self._extract_id(url)
        if not book_id:
            raise ValueError(f"Could not extract GoodShort book ID from URL: {url}")

        headers = {"User-Agent": "okhttp/4.10.0", "x-token": GOODBOS_TOKEN}

        name = "GoodShort Drama"
        cover = ""
        desc = ""
        total_episodes = 0

        try:
            resp = self.http.get(f"{self.BASE_URL}/book/{book_id}?lang=en", headers=headers)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                book_data = data.get("book") or data
                name = book_data.get("bookName") or book_data.get("title") or name
                cover = book_data.get("cover") or book_data.get("bookDetailCover") or ""
                desc = book_data.get("introduction") or book_data.get("desc") or ""
                total_episodes = book_data.get("chapterCount") or 0
        except Exception:
            pass

        episodes: List[Episode] = []
        try:
            resp = self.http.get(
                f"{self.BASE_URL}/chapters/{book_id}?lang=en&code={GOODBOS_TOKEN}",
                headers=headers,
            )
            if resp.status_code == 200:
                ch_list = resp.json().get("data", {}).get("list", [])
                for idx, item in enumerate(ch_list):
                    ep_num = (item.get("index") + 1 if item.get("index") is not None else None) or (idx + 1)
                    cdn_list = item.get("cdnList") or []
                    first_cdn = cdn_list[0].get("videoPath") if cdn_list and isinstance(cdn_list[0], dict) else ""
                    direct_url = item.get("cdn") or first_cdn or ""

                    episodes.append(
                        Episode(
                            num=ep_num,
                            title=item.get("chapterName") or f"Episode {ep_num}",
                            url=f"https://www.goodshort.com/video/{book_id}/{ep_num}",
                            direct_url=direct_url or None,
                            thumb=cover,
                            locked=not bool(direct_url),
                            extra={"book_id": book_id},
                        )
                    )
        except Exception:
            pass

        if not episodes and total_episodes > 0:
            for i in range(1, total_episodes + 1):
                episodes.append(
                    Episode(
                        num=i,
                        title=f"Episode {i}",
                        url=f"https://www.goodshort.com/video/{book_id}/{i}",
                        direct_url=None,
                        thumb=cover,
                        locked=True,
                        extra={"book_id": book_id},
                    )
                )

        accessible = sum(1 for ep in episodes if not ep.locked)
        return Series(
            name=name,
            platform=self.platform_id,
            series_id=f"goodshort:{book_id}",
            cover=cover,
            description=desc,
            episode_count=len(episodes),
            accessible_count=accessible,
            episodes=episodes,
            url=url,
        )

    def get_video_url(self, episode: Episode) -> Optional[str]:
        if episode.direct_url:
            return episode.direct_url

        book_id = episode.extra.get("book_id")
        if not book_id:
            return None

        try:
            resp = self.http.get(
                f"{self.BASE_URL}/video/{book_id}/{episode.num}?lang=en&code={GOODBOS_TOKEN}",
                headers={"User-Agent": "okhttp/4.10.0", "x-token": GOODBOS_TOKEN},
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                v_url = data.get("videoUrl") or data.get("url") or data.get("cdn")
                if v_url:
                    episode.direct_url = v_url
                    episode.locked = False
                    return v_url
        except Exception:
            pass

        return None
