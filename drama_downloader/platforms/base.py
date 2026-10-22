"""
drama_downloader.platforms.base
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Abstract base class for all platform extractors.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from ..models import Series, Episode, CatalogResult, CatalogItem
from ..client import http, HttpClient

GOODBOS_TOKEN = "6EB57533425BC1D78ADA1F80354161D4"


class BasePlatform(ABC):
    """Abstract Base Class for drama platform extractors."""

    platform_id: str = "base"
    display_name: str = "Base Platform"

    def __init__(self, client: Optional[HttpClient] = None):
        self.http = client or http

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Determines if this platform can handle the given URL or identifier."""
        pass

    @abstractmethod
    def load_series(self, url: str) -> Series:
        """Parses series metadata and list of episodes from a URL or series ID."""
        pass

    def get_video_url(self, episode: Episode) -> Optional[str]:
        """Resolves direct stream/video URL for an episode if not already populated."""
        return episode.direct_url

    def get_catalog(
        self,
        page: int = 1,
        query: Optional[str] = None,
        category: Optional[str] = None,
    ) -> CatalogResult:
        """Retrieves catalog/browse listings if supported by platform."""
        return CatalogResult(items=[], total=0, platform=self.platform_id)
