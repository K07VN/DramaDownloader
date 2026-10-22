"""
drama_downloader.platforms.netshort
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Extractor for NetShort and FlickReels platforms.
"""

import re
import time
from typing import Optional, List, Dict, Any
from .base import BasePlatform, GOODBOS_TOKEN
from ..models import Series, Episode, Subtitle, CatalogResult, CatalogItem


class NetShortPlatform(BasePlatform):
    platform_id = "netshort"
    display_name = "NetShort"

    BASE_URL = "https://netshort.goodbos.online/api"

    def can_handle(self, url: str) -> bool:
        u = url.lower().strip()
        return "netshort" in u or "flickreels" in u or u.startswith("netshort:")

    def _extract_id(self, url: str) -> str:
        u = url.strip()
        m = re.search(r"netshort:([A-Za-z0-9_-]+)", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"/(?:drama|series|detail|play)/([A-Za-z0-9_-]+)", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"[?&](?:id|dramaId|bookId)=([A-Za-z0-9_-]+)", u, re.I)
        if m:
            return m.group(1)
        m = re.search(r"([A-Za-z0-9_-]{8,})", u)
        return m.group(1) if m else ""

    def _parse_subs(self, sub_list: Any) -> List[Subtitle]:
        if not isinstance(sub_list, list):
            return []
        subs = []
        for s in sub_list:
            if isinstance(s, dict) and s.get("url"):
                lang = str(s.get("lang") or s.get("subtitleLanguage") or "en").replace("_", "-")
                subs.append(Subtitle(lang=lang, name=lang, url=s["url"]))
        return subs

    def load_series(self, url: str) -> Series:
        ns_key = self._extract_id(url)
        if not ns_key:
            raise ValueError(f"Could not read NetShort drama ID from: {url}")

        params = {"lang": "en"}
        resp = self.http.get(f"{self.BASE_URL}/drama/{ns_key}", params=params)
        if resp.status_code == 429:
            raise ValueError("NetShort API rate limited - please wait a few minutes")
        if resp.status_code != 200:
            raise ValueError(f"NetShort API error: HTTP {resp.status_code}")

        res_json = resp.json()
        data = res_json.get("data") or {}
        raw_episodes = data.get("shortPlayEpisodeList") or []
        if not raw_episodes:
            raise ValueError("NetShort: drama has no episodes or ID is incorrect")

        raw_episodes = sorted(raw_episodes, key=lambda x: x.get("episodeNo", 0))

        series_name = data.get("shortPlayName") or "NetShort Drama"
        cover = data.get("shortPlayCover") or ""

        episodes: List[Episode] = []
        for idx, ep in enumerate(raw_episodes):
            ep_num = idx + 1
            ep_no = ep.get("episodeNo") or ep_num
            direct_url = ep.get("playVoucher") or None
            subs = self._parse_subs(ep.get("subtitleList"))

            episodes.append(
                Episode(
                    num=ep_num,
                    title=f"Episode {ep_num}",
                    url=f"https://netshort.com/drama/{ns_key}/{ep_num}",
                    direct_url=direct_url,
                    thumb=ep.get("episodeCover") or cover,
                    locked=False,
                    subs=subs,
                    extra={"ns_key": ns_key, "ns_ep": ep_no, "ts": time.time() if direct_url else 0},
                )
            )

        return Series(
            name=series_name,
            platform=self.platform_id,
            series_id=f"netshort:{ns_key}",
            cover=cover,
            episode_count=len(episodes),
            accessible_count=len(episodes),
            episodes=episodes,
            url=f"https://netshort.com/drama/{ns_key}",
        )

    def get_video_url(self, episode: Episode) -> Optional[str]:
        ns_key = episode.extra.get("ns_key")
        ns_ep = episode.extra.get("ns_ep", episode.num)

        ts = episode.extra.get("ts", 0)
        if episode.direct_url and ts and (time.time() - ts < 6 * 3600):
            return episode.direct_url

        if not ns_key:
            return episode.direct_url

        try:
            resp = self.http.get(
                f"{self.BASE_URL}/watch/{ns_key}/{ns_ep}",
                params={"code": GOODBOS_TOKEN, "lang": "en"},
            )
            if resp.status_code == 200:
                data = resp.json().get("data") or {}
                v_url = data.get("videoUrl")
                if v_url:
                    episode.direct_url = v_url
                    episode.extra["ts"] = time.time()
                subs = self._parse_subs(data.get("subtitles"))
                if subs:
                    episode.subs = subs
                return episode.direct_url
        except Exception:
            pass

        return episode.direct_url
