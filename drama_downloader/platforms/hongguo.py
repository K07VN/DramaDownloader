"""
drama_downloader.platforms.hongguo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Extractor for Hongguo / Fanqie platform (hongguoduanju.com).
"""

import json
import re
from typing import Optional, List, Dict, Any
from .base import BasePlatform
from ..models import Series, Episode, Subtitle, CatalogResult, CatalogItem
from ..crypto.spade import derive_content_key, decrypt_spade_url


class HongguoPlatform(BasePlatform):
    platform_id = "hongguo"
    display_name = "Hongguo / Fanqie"

    BASE_URL = "https://hongguoduanju.com"

    def can_handle(self, url: str) -> bool:
        u = url.lower().strip()
        return "hongguo" in u or "fqnovel" in u or u.startswith("hongguo:")

    def _extract_id(self, url: str) -> str:
        u = url.strip()
        m = re.search(r"series_id=(\d+)", u)
        if m:
            return m.group(1)
        m = re.search(r"/(?:detail|player)/(\d+)", u)
        if m:
            return m.group(1)
        m = re.search(r"^(\d{6,})$", u)
        return m.group(1) if m else ""

    def load_series(self, url: str) -> Series:
        series_id = self._extract_id(url)
        if not series_id:
            raise ValueError(f"Could not extract series ID from: {url}")

        detail_url = f"{self.BASE_URL}/detail?series_id={series_id}"
        loader_url = f"{detail_url}&__loader=detail_page"

        series_detail = None

        try:
            resp = self.http.get(
                loader_url,
                headers={"Accept": "application/json, text/plain, */*", "X-Modernjs-Response": "yes"},
            )
            if resp.status_code == 200:
                data = resp.json()
                series_detail = data.get("seriesDetail")
        except Exception:
            pass

        if not series_detail:
            resp = self.http.get(detail_url)
            if resp.status_code == 200:
                m = re.search(r"_ROUTER_DATA\s*=\s*(\{[\s\S]*?\});", resp.text)
                if m:
                    try:
                        router_data = json.loads(m.group(1))
                        series_detail = (
                            router_data.get("loaderData", {})
                            .get("detail_page", {})
                            .get("seriesDetail")
                        )
                    except Exception:
                        pass

        if not series_detail:
            raise ValueError(f"Could not parse series detail for Hongguo ID: {series_id}")

        vid_list = series_detail.get("vid_list") or []
        series_name = series_detail.get("series_name") or f"Series {series_id}"
        cover = series_detail.get("series_cover") or ""
        intro = series_detail.get("series_intro") or ""

        episodes: List[Episode] = []
        for idx, vid in enumerate(vid_list):
            ep_num = idx + 1
            episodes.append(
                Episode(
                    num=ep_num,
                    title=f"Episode {ep_num}",
                    url=f"{self.BASE_URL}/player/{series_id}?vid={vid}",
                    direct_url=None,
                    thumb=cover,
                    locked=False,
                    extra={"vid": str(vid), "series_id": series_id},
                )
            )

        accessible = series_detail.get("accessible_episode_cnt", len(episodes))
        return Series(
            name=series_name,
            platform=self.platform_id,
            series_id=f"hongguo:{series_id}",
            cover=cover,
            description=intro,
            episode_count=len(episodes),
            accessible_count=min(accessible, len(episodes)),
            episodes=episodes,
            url=detail_url,
        )

    def get_video_url(self, episode: Episode) -> Optional[str]:
        if episode.direct_url:
            return episode.direct_url

        vid = episode.extra.get("vid")
        series_id = episode.extra.get("series_id")
        if not vid or not series_id:
            return None

        player_url = f"{self.BASE_URL}/player/{series_id}?vid={vid}&__loader=player_page"
        try:
            resp = self.http.get(
                player_url,
                headers={"Accept": "application/json, text/plain, */*", "X-Modernjs-Response": "yes"},
            )
            if resp.status_code == 200:
                data = resp.json()
                play_info = data.get("videoPlayInfo") or {}
                v_url = play_info.get("video_url") or play_info.get("play_url")
                if v_url:
                    episode.direct_url = v_url
                    return v_url

                spade_a = play_info.get("spade_a")
                enc_url = play_info.get("encrypted_url") or play_info.get("main_url")
                if spade_a and enc_url:
                    key = derive_content_key(spade_a)
                    dec_url = decrypt_spade_url(enc_url, key)
                    if dec_url:
                        episode.direct_url = dec_url
                        return dec_url
        except Exception:
            pass

        return None
