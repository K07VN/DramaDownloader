"""
drama_downloader.platforms.dramabox
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Extractor for DramaBox (dramaboxdb.com, webfic, goodbos aggregator).
"""

import json
import re
from typing import Optional, List, Dict, Any
from .base import BasePlatform, GOODBOS_TOKEN
from ..models import Series, Episode, Subtitle, CatalogResult, CatalogItem
from ..crypto.dramabox_rsa import sign_dramabox


class DramaBoxPlatform(BasePlatform):
    platform_id = "dramabox"
    display_name = "DramaBox"

    GOODBOS_BASE = "https://dramabox.goodbos.online"

    def can_handle(self, url: str) -> bool:
        u = url.lower().strip()
        return "dramabox" in u or u.startswith("dramabox:")

    def _extract_id(self, url: str) -> str:
        m = re.search(r"/(?:movie|ep|detail)[/-](\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"(\d{5,})", url)
        if m:
            return m.group(1)
        return ""

    def load_series(self, url: str) -> Series:
        book_id = self._extract_id(url)
        if not book_id:
            raise ValueError(f"Could not extract DramaBox book ID from: {url}")

        series_name = "DramaBox Series"
        cover = ""
        description = ""
        episodes: List[Episode] = []

        db_url = f"https://www.dramaboxdb.com/movie/{book_id}/drama"
        resp = self.http.get(db_url)
        if resp.status_code == 200:
            m = re.search(r'<script id="__NEXT_DATA__" type="application/json">([\s\S]*?)</script>', resp.text)
            if m:
                try:
                    data = json.loads(m.group(1))
                    page_props = data.get("props", {}).get("pageProps", {})
                    book_info = page_props.get("bookInfo", {})
                    series_name = book_info.get("bookName") or book_info.get("name") or series_name
                    cover = book_info.get("cover") or book_info.get("coverWap") or ""
                    description = book_info.get("introduction") or book_info.get("desc") or ""

                    chapter_list = page_props.get("chapterList", [])
                    for idx, ch in enumerate(chapter_list):
                        ep_num = (ch.get("index") + 1 if ch.get("index") is not None else ch.get("chapterIndex")) or (idx + 1)
                        is_locked = (ch.get("unlock") is False and not ch.get("mp4") and not ch.get("m3u8Url"))
                        direct_url = ch.get("mp4") or ch.get("m3u8Url") or ch.get("videoPath") or None

                        episodes.append(
                            Episode(
                                num=ep_num,
                                title=ch.get("name") or ch.get("chapterName") or f"Episode {ep_num}",
                                url=url,
                                direct_url=direct_url,
                                thumb=ch.get("cover") or cover,
                                locked=is_locked,
                                extra={"chapter_id": str(ch.get("id") or ch.get("chapterId") or "")},
                            )
                        )
                except Exception:
                    pass

        locked_count = sum(1 for ep in episodes if ep.locked)
        if locked_count > 0 or not episodes:
            try:
                gb_resp = self.http.get(
                    f"{self.GOODBOS_BASE}/api/dramabox/allepisode",
                    params={"bookId": book_id},
                    headers={"User-Agent": "okhttp/4.10.0", "x-token": GOODBOS_TOKEN},
                )
                if gb_resp.status_code == 200:
                    gb_episodes = gb_resp.json()
                    if isinstance(gb_episodes, list):
                        gb_map = {item.get("chapterIndex"): item for item in gb_episodes if isinstance(item, dict)}

                        if not episodes:
                            for item in gb_episodes:
                                ep_idx = item.get("chapterIndex", 0)
                                ep_num = ep_idx + 1
                                v_url = (
                                    item.get("videoUrl720")
                                    or item.get("videoUrl")
                                    or item.get("videoUrl1080")
                                    or item.get("videoUrl540")
                                )
                                episodes.append(
                                    Episode(
                                        num=ep_num,
                                        title=item.get("chapterName") or f"Episode {ep_num}",
                                        url=url,
                                        direct_url=v_url,
                                        thumb=cover,
                                        locked=not bool(v_url),
                                    )
                                )
                        else:
                            for ep in episodes:
                                if ep.locked:
                                    gb_item = gb_map.get(ep.num - 1)
                                    if gb_item:
                                        v_url = (
                                            gb_item.get("videoUrl720")
                                            or gb_item.get("videoUrl")
                                            or gb_item.get("videoUrl1080")
                                            or gb_item.get("videoUrl540")
                                        )
                                        if v_url:
                                            ep.direct_url = v_url
                                            ep.locked = False
            except Exception:
                pass

        accessible = sum(1 for ep in episodes if not ep.locked)
        return Series(
            name=series_name,
            platform=self.platform_id,
            series_id=f"dramabox:{book_id}",
            cover=cover,
            description=description,
            episode_count=len(episodes),
            accessible_count=accessible,
            episodes=episodes,
            url=url,
        )

    def get_catalog(
        self,
        page: int = 1,
        query: Optional[str] = None,
        category: Optional[str] = None,
    ) -> CatalogResult:
        try:
            payload = {
                "typeTwoId": int(category) if category and category.isdigit() else 0,
                "pageNo": page,
                "pageSize": 30,
            }
            resp = self.http.post(
                "https://www.webfic.com/webfic/home/browse",
                json=payload,
                headers={"Content-Type": "application/json", "pline": "DRAMABOX", "language": "en"},
            )
            data = resp.json()
            book_list = data.get("data", {}).get("bookList", [])
            items = []
            for b in book_list:
                bid = str(b.get("bookId") or "")
                title = b.get("bookName") or b.get("name") or ""
                if query and query.lower() not in title.lower():
                    continue
                items.append(
                    CatalogItem(
                        id=bid,
                        name=title,
                        cover=b.get("cover") or b.get("coverWap") or "",
                        episodes=b.get("chapterCount", 0),
                        score=str(b.get("score") or ""),
                        tags=[t.get("tagName", "") for t in b.get("tagV3s", []) if isinstance(t, dict)],
                        desc=b.get("introduction") or "",
                        link=f"https://www.dramaboxdb.com/movie/{bid}/drama",
                        platform=self.platform_id,
                    )
                )
            total = data.get("data", {}).get("total") or len(items)
            return CatalogResult(items=items, total=total, platform=self.platform_id)
        except Exception:
            return CatalogResult(items=[], total=0, platform=self.platform_id)
