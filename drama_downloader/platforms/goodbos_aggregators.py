"""
drama_downloader.platforms.goodbos_aggregators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Extractors for platforms hosted on goodbos / drakula aggregators:
- DramaWave
- RaptDrama
- FlexTV
- Melolo
- StardustTV
"""

import re
from typing import Optional, List, Dict, Any
from .base import BasePlatform, GOODBOS_TOKEN
from ..models import Series, Episode, Subtitle, CatalogResult, CatalogItem


class DramaWavePlatform(BasePlatform):
    platform_id = "dramawave"
    display_name = "DramaWave"
    BASE_URL = "https://dramawave.goodbos.online/api"

    def can_handle(self, url: str) -> bool:
        u = url.lower().strip()
        return "dramawave" in u or u.startswith("dramawave:")

    def _extract_id(self, url: str) -> str:
        u = url.strip()
        m = re.search(r"dramawave:([A-Za-z0-9_-]+)", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"/(?:drama|series|detail|play)/([A-Za-z0-9_-]+)", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"[?&](?:id|playlet_id|series_id)=([A-Za-z0-9_-]+)", u, re.I)
        return m.group(1) if m else ""

    def load_series(self, url: str) -> Series:
        dw_id = self._extract_id(url)
        if not dw_id:
            raise ValueError(f"Could not read DramaWave ID from: {url}")

        resp = self.http.get(f"{self.BASE_URL}/allepisodes", params={"id": dw_id, "lang": "en", "code": GOODBOS_TOKEN})
        data = resp.json().get("data") or {}
        items = data.get("episodes") or []

        name = data.get("name") or "DramaWave Drama"
        cover = data.get("cover") or ""
        episodes = []
        for idx, it in enumerate(items):
            ep_num = idx + 1
            v_url = it.get("video_url") or it.get("url") or it.get("m3u8_path")
            episodes.append(
                Episode(
                    num=ep_num,
                    title=f"Episode {ep_num}",
                    url=f"https://www.dramawave.com/drama/{dw_id}",
                    direct_url=v_url,
                    thumb=it.get("cover") or cover,
                    locked=not bool(v_url),
                )
            )

        accessible = sum(1 for ep in episodes if not ep.locked)
        return Series(
            name=name,
            platform=self.platform_id,
            series_id=f"dramawave:{dw_id}",
            cover=cover,
            episode_count=len(episodes),
            accessible_count=accessible,
            episodes=episodes,
            url=f"https://www.dramawave.com/drama/{dw_id}",
        )


class RaptDramaPlatform(BasePlatform):
    platform_id = "raptdrama"
    display_name = "RaptDrama"
    BASE_URL = "https://raptdrama.goodbos.online/api/raptdrama"

    def can_handle(self, url: str) -> bool:
        u = url.lower().strip()
        return "raptdrama" in u or u.startswith("raptdrama:")

    def _extract_id(self, url: str) -> str:
        u = url.strip()
        m = re.search(r"raptdrama:(\d+)", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"/(\d{2,})(?:[/?#]|$)", u)
        if m:
            return m.group(1)
        m = re.search(r"[?&](?:id|vid)=(\d+)", u, re.I)
        return m.group(1) if m else ""

    def load_series(self, url: str) -> Series:
        rd_id = self._extract_id(url)
        if not rd_id:
            raise ValueError(f"Could not read RaptDrama ID from: {url}")

        resp = self.http.get(
            f"{self.BASE_URL}/episodes",
            params={"id": rd_id, "lang": "en"},
            headers={"x-token": GOODBOS_TOKEN},
        )
        data = resp.json().get("data") or {}
        items = data.get("episodes") or []

        name = data.get("name") or data.get("title") or "RaptDrama"
        cover = data.get("cover") or ""
        episodes = []
        for idx, it in enumerate(items):
            ep_num = idx + 1
            v_url = it.get("src") or it.get("video_url") or it.get("url")
            episodes.append(
                Episode(
                    num=ep_num,
                    title=f"Episode {ep_num}",
                    url=f"https://raptdrama.com/drama/{rd_id}",
                    direct_url=v_url,
                    thumb=it.get("cover") or cover,
                    locked=not bool(v_url),
                )
            )

        accessible = sum(1 for ep in episodes if not ep.locked)
        return Series(
            name=name,
            platform=self.platform_id,
            series_id=f"raptdrama:{rd_id}",
            cover=cover,
            episode_count=len(episodes),
            accessible_count=accessible,
            episodes=episodes,
            url=f"https://raptdrama.com/drama/{rd_id}",
        )


class FlexTVPlatform(BasePlatform):
    platform_id = "flextv"
    display_name = "FlexTV"
    BASE_URL = "https://flextv.goodbos.online/api"

    def can_handle(self, url: str) -> bool:
        u = url.lower().strip()
        return "flextv" in u or u.startswith("flextv:")

    def _extract_id(self, url: str) -> str:
        u = url.strip()
        m = re.search(r"flextv:([A-Za-z0-9]{5,})", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"[?&](?:series_id|id)=([A-Za-z0-9]{5,})", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"/(?:drama|detail|series|play|watch)/([A-Za-z0-9]{5,})", u, re.I)
        return m.group(1) if m else ""

    def load_series(self, url: str) -> Series:
        fx_id = self._extract_id(url)
        if not fx_id:
            raise ValueError(f"Could not read FlexTV ID from: {url}")

        resp = self.http.get(f"{self.BASE_URL}/allepisodes", params={"id": fx_id, "lang": "en", "code": GOODBOS_TOKEN})
        data = resp.json().get("data") or {}
        items = data.get("episodes") or []

        name = data.get("name") or "FlexTV Drama"
        cover = data.get("cover") or ""
        episodes = []
        for idx, it in enumerate(items):
            ep_num = idx + 1
            v_url = it.get("video_url") or it.get("url")
            episodes.append(
                Episode(
                    num=ep_num,
                    title=f"Episode {ep_num}",
                    url=f"https://flextv.com/drama/{fx_id}",
                    direct_url=v_url,
                    thumb=it.get("cover") or cover,
                    locked=not bool(v_url),
                )
            )

        accessible = sum(1 for ep in episodes if not ep.locked)
        return Series(
            name=name,
            platform=self.platform_id,
            series_id=f"flextv:{fx_id}",
            cover=cover,
            episode_count=len(episodes),
            accessible_count=accessible,
            episodes=episodes,
            url=f"https://flextv.com/drama/{fx_id}",
        )


class StardustTVPlatform(BasePlatform):
    platform_id = "stardusttv"
    display_name = "StardustTV"
    BASE_URL = "https://stardusttv2.goodbos.online"

    def can_handle(self, url: str) -> bool:
        u = url.lower().strip()
        return "stardust" in u or u.startswith("stardust:")

    def _extract_id(self, url: str) -> str:
        u = url.strip()
        m = re.search(r"stardust(?:tv)?:(\d+)", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"[?&](?:vid|id)=(\d+)", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"/(?:video|drama|detail|episodes)/(\d+)", u, re.I)
        return m.group(1) if m else ""

    def load_series(self, url: str) -> Series:
        sd_id = self._extract_id(url)
        if not sd_id:
            raise ValueError(f"Could not read StardustTV ID from: {url}")

        resp = self.http.get(f"{self.BASE_URL}/video/episodes", params={"vid": sd_id, "lang": "en_US"})
        data = resp.json()
        items = data.get("episodes") or []

        name = data.get("name") or "StardustTV Drama"
        cover = data.get("cover") or ""
        episodes = []
        for idx, it in enumerate(items):
            ep_num = idx + 1
            v_url = it.get("m3u8") or it.get("video_url") or it.get("url")
            episodes.append(
                Episode(
                    num=ep_num,
                    title=f"Episode {ep_num}",
                    url=f"https://stardusttv.com/video/{sd_id}",
                    direct_url=v_url,
                    thumb=it.get("cover") or cover,
                    locked=not bool(v_url),
                )
            )

        accessible = sum(1 for ep in episodes if not ep.locked)
        return Series(
            name=name,
            platform=self.platform_id,
            series_id=f"stardusttv:{sd_id}",
            cover=cover,
            episode_count=len(episodes),
            accessible_count=accessible,
            episodes=episodes,
            url=f"https://stardusttv.com/video/{sd_id}",
        )
