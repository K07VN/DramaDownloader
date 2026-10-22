"""
drama_downloader.platforms.freereels
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Extractor for FreeReels platform.
"""

import re
from typing import Optional, List, Dict, Any
from .base import BasePlatform, GOODBOS_TOKEN
from ..models import Series, Episode, Subtitle, CatalogResult, CatalogItem


class FreeReelsPlatform(BasePlatform):
    platform_id = "freereels"
    display_name = "FreeReels"

    BASE_URL = "https://drakula.goodbos.online/api/freereels"

    def can_handle(self, url: str) -> bool:
        u = url.lower().strip()
        return "freereels" in u or u.startswith("freereels:")

    def _extract_id(self, url: str) -> str:
        u = url.strip()
        m = re.search(r"freereels:[/\\]*([A-Za-z0-9_-]+)", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"/(?:drama|series|detail|video)/([A-Za-z0-9_-]{6,})", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"[?&](?:id|key|series_id)=([A-Za-z0-9_-]{6,})", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"/([A-Za-z0-9_-]{8,14})/?(?:[?#].*)?$", u)
        return m.group(1) if m else ""

    def _pick_mp4(self, item: Dict[str, Any]) -> Optional[str]:
        vlist = item.get("video_list") or item.get("play_list") or []
        if isinstance(vlist, list) and vlist:
            for item_v in vlist:
                if isinstance(item_v, dict) and item_v.get("video_path"):
                    return item_v["video_path"]
        return item.get("video_path") or item.get("play_url") or item.get("m3u8_url") or None

    def load_series(self, url: str) -> Series:
        fr_key = self._extract_id(url)
        if not fr_key:
            raise ValueError(f"Could not read FreeReels drama ID from: {url}")

        params = {"key": fr_key, "lang": "en", "code": GOODBOS_TOKEN}
        resp = self.http.get(f"{self.BASE_URL}/episodes", params=params)
        if resp.status_code != 200:
            raise ValueError(f"FreeReels API error: HTTP {resp.status_code}")

        res_json = resp.json()
        data = res_json.get("data") or res_json
        items = data.get("items") or data.get("episodes") or []

        valid_items = [it for it in items if not it.get("is_blooper")]
        if not valid_items:
            valid_items = items

        valid_items = sorted(valid_items, key=lambda x: x.get("serial_number", 0))

        series_name = data.get("name") or data.get("title") or "FreeReels Drama"
        cover = data.get("cover") or ""
        desc = data.get("desc") or ""

        episodes: List[Episode] = []
        for idx, it in enumerate(valid_items):
            ep_num = idx + 1
            direct_url = self._pick_mp4(it)

            subs = []
            sub_list = it.get("subtitle_list") or []
            if isinstance(sub_list, list):
                for s in sub_list:
                    if isinstance(s, dict) and s.get("subtitle_url"):
                        lang = str(s.get("language_name") or s.get("lang") or "en")
                        subs.append(Subtitle(lang=lang, name=lang, url=s["subtitle_url"]))

            episodes.append(
                Episode(
                    num=ep_num,
                    title=it.get("name") or f"Episode {ep_num}",
                    url=f"https://freereels.app/drama/{fr_key}/{ep_num}",
                    direct_url=direct_url,
                    thumb=it.get("cover") or cover,
                    locked=not bool(direct_url),
                    subs=subs,
                    extra={"fr_key": fr_key},
                )
            )

        accessible = sum(1 for ep in episodes if not ep.locked)
        return Series(
            name=series_name,
            platform=self.platform_id,
            series_id=f"freereels:{fr_key}",
            cover=cover,
            description=desc,
            episode_count=len(episodes),
            accessible_count=accessible,
            episodes=episodes,
            url=f"https://freereels.app/drama/{fr_key}",
        )
