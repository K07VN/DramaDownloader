"""
drama_downloader.models
~~~~~~~~~~~~~~~~~~~~~~~
Data models for drama series, episodes, subtitles, and catalog items.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Subtitle:
    lang: str
    name: str
    url: str

    def to_dict(self) -> Dict[str, Any]:
        return {"lang": self.lang, "name": self.name, "url": self.url}


@dataclass
class Episode:
    num: int
    title: str
    url: str
    direct_url: Optional[str] = None
    thumb: Optional[str] = None
    locked: bool = False
    subs: List[Subtitle] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num": self.num,
            "title": self.title,
            "url": self.url,
            "direct_url": self.direct_url,
            "thumb": self.thumb,
            "locked": self.locked,
            "subs": [s.to_dict() for s in self.subs],
            "extra": self.extra,
        }


@dataclass
class Series:
    name: str
    platform: str
    series_id: str
    cover: Optional[str] = None
    description: Optional[str] = None
    episode_count: int = 0
    accessible_count: int = 0
    episodes: List[Episode] = field(default_factory=list)
    url: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "platform": self.platform,
            "series_id": self.series_id,
            "cover": self.cover,
            "description": self.description,
            "episode_count": self.episode_count,
            "accessible_count": self.accessible_count,
            "episodes": [e.to_dict() for e in self.episodes],
            "url": self.url,
        }


@dataclass
class CatalogItem:
    id: str
    name: str
    cover: Optional[str] = None
    episodes: int = 0
    score: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    desc: Optional[str] = None
    link: Optional[str] = None
    platform: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "cover": self.cover,
            "episodes": self.episodes,
            "score": self.score,
            "tags": self.tags,
            "desc": self.desc,
            "link": self.link,
            "platform": self.platform,
        }


@dataclass
class CatalogResult:
    items: List[CatalogItem] = field(default_factory=list)
    total: int = 0
    platform: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "platform": self.platform,
            "items": [it.to_dict() for it in self.items],
        }
