"""
drama_downloader
~~~~~~~~~~~~~~~~
Multi-Platform Short Drama Extractor and Downloader Python Module.
"""

from .models import Series, Episode, Subtitle, CatalogItem, CatalogResult
from .downloader import DramaDownloader, DownloadProgress, vtt_to_srt
from .platforms import (
    load_series,
    detect_platform,
    get_platform,
    get_all_platforms,
    get_video_url,
)
from .client import http, HttpClient
from .crypto import sign_dramabox, derive_content_key, decrypt_spade_url

__version__ = "1.0.0"
__all__ = [
    "Series",
    "Episode",
    "Subtitle",
    "CatalogItem",
    "CatalogResult",
    "DramaDownloader",
    "DownloadProgress",
    "vtt_to_srt",
    "load_series",
    "detect_platform",
    "get_platform",
    "get_all_platforms",
    "get_video_url",
    "http",
    "HttpClient",
    "sign_dramabox",
    "derive_content_key",
    "decrypt_spade_url",
]
