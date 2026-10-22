"""
drama_downloader.platforms
~~~~~~~~~~~~~~~~~~~~~~~~~~
Platform registry, automatic detection router, and unified extraction API.
"""

from typing import Optional, List, Type
from .base import BasePlatform
from .dramabox import DramaBoxPlatform
from .goodshort import GoodShortPlatform
from .shortmax import ShortMaxPlatform
from .netshort import NetShortPlatform
from .freereels import FreeReelsPlatform
from .kisskh import KisskhPlatform
from .hongguo import HongguoPlatform
from .goodbos_aggregators import (
    DramaWavePlatform,
    RaptDramaPlatform,
    FlexTVPlatform,
    StardustTVPlatform,
)

PLATFORM_CLASSES: List[Type[BasePlatform]] = [
    DramaBoxPlatform,
    GoodShortPlatform,
    ShortMaxPlatform,
    NetShortPlatform,
    FreeReelsPlatform,
    KisskhPlatform,
    HongguoPlatform,
    DramaWavePlatform,
    RaptDramaPlatform,
    FlexTVPlatform,
    StardustTVPlatform,
]

_INSTANCES: List[BasePlatform] = [cls() for cls in PLATFORM_CLASSES]


def get_all_platforms() -> List[BasePlatform]:
    """Returns a list of all instantiated platforms."""
    return _INSTANCES


def get_platform(name_or_id: str) -> Optional[BasePlatform]:
    """Finds a platform by platform_id or display_name."""
    target = name_or_id.lower().strip()
    for p in _INSTANCES:
        if p.platform_id.lower() == target or p.display_name.lower() == target:
            return p
    return None


def detect_platform(url_or_id: str) -> Optional[BasePlatform]:
    """Detects which platform handles the given URL or identifier."""
    if not url_or_id:
        return None
    for p in _INSTANCES:
        if p.can_handle(url_or_id):
            return p
    return None


def load_series(url_or_id: str, platform_hint: Optional[str] = None) -> "Series":
    """Unified entrypoint: auto-detects platform and loads Series metadata."""
    platform = None
    if platform_hint:
        platform = get_platform(platform_hint)
    if not platform:
        platform = detect_platform(url_or_id)
    if not platform:
        raise ValueError(f"No platform extractor found to handle: {url_or_id}")

    return platform.load_series(url_or_id)


def get_video_url(episode: "Episode", platform_hint: Optional[str] = None) -> Optional[str]:
    """Resolves direct stream URL for an episode."""
    if episode.direct_url:
        return episode.direct_url

    platform = None
    if platform_hint:
        platform = get_platform(platform_hint)
    if not platform:
        platform = detect_platform(episode.url)

    if platform:
        return platform.get_video_url(episode)
    return None
