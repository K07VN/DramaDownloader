"""
drama_downloader.cli
~~~~~~~~~~~~~~~~~~~~
Command-line interface for Drama Downloader.
"""

import argparse
import sys
from typing import List
from .models import Series, Episode
from .platforms import (
    load_series,
    detect_platform,
    get_all_platforms,
    get_platform,
)
from .downloader import DramaDownloader, DownloadProgress


def parse_range(range_str: str, max_ep: int) -> List[int]:
    """Parses episode range expressions like '1-10,12,15-20'."""
    res = set()
    parts = range_str.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            sub = part.split("-", 1)
            start = int(sub[0])
            end = int(sub[1]) if sub[1] else max_ep
            for i in range(start, end + 1):
                res.add(i)
        elif part.isdigit():
            res.add(int(part))
    return sorted(list(res))


def cmd_info(args):
    print(f"\n[*] Inspecting drama: {args.target}")
    try:
        series = load_series(args.target, platform_hint=args.platform)
        print("=" * 60)
        print(f"Title:       {series.name}")
        print(f"Platform:    {series.platform.upper()}")
        print(f"Series ID:   {series.series_id}")
        print(f"Episodes:    {series.episode_count} (Accessible: {series.accessible_count})")
        if series.cover:
            print(f"Cover:       {series.cover}")
        if series.description:
            desc = series.description.strip().replace("\n", " ")
            print(f"Description: {desc[:120]}..." if len(desc) > 120 else f"Description: {desc}")
        print("=" * 60)

        print("\nEpisode List:")
        for ep in series.episodes:
            status = "[FREE]" if not ep.locked else "[LOCKED]"
            direct = " [HAS STREAM]" if ep.direct_url else ""
            subs = f" ({len(ep.subs)} subs)" if ep.subs else ""
            print(f"  EP{ep.num:03d}: {ep.title} {status}{direct}{subs}")
        print(f"\nTotal: {len(series.episodes)} episodes found.\n")
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


def cmd_download(args):
    print(f"\n[*] Loading drama: {args.target}")
    try:
        series = load_series(args.target, platform_hint=args.platform)
        print(f"[*] Found series: '{series.name}' ({len(series.episodes)} episodes)")

        selected_nums = None
        if args.episodes:
            selected_nums = parse_range(args.episodes, len(series.episodes))
            print(f"[*] Downloading selected episodes: {selected_nums}")
        else:
            print(f"[*] Downloading all available episodes (1 to {len(series.episodes)})")

        dl = DramaDownloader(
            output_dir=args.output,
            concurrency=args.concurrency,
        )

        def on_done(ep: Episode, path: str):
            print(f"[+] Downloaded: EP{ep.num:02d} -> {path}")

        def on_error(ep: Episode, err: Exception):
            print(f"[x] Failed EP{ep.num:02d}: {err}")

        print(f"[*] Output directory: {dl.output_dir}")
        print("[*] Starting download...")
        dl.download_series(
            series,
            episodes_range=selected_nums,
            on_episode_done=on_done,
            on_episode_error=on_error,
        )
        print("\n[✔] Download batch finished!")
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


def cmd_catalog(args):
    platform = get_platform(args.platform)
    if not platform:
        print(f"[!] Unknown platform: {args.platform}")
        sys.exit(1)

    print(f"\n[*] Fetching catalog from {platform.display_name} (Page {args.page})...")
    res = platform.get_catalog(page=args.page, query=args.query, category=args.category)
    print("=" * 60)
    print(f"Catalog: {platform.display_name} | Total: {res.total}")
    print("=" * 60)
    for idx, it in enumerate(res.items):
        print(f"[{idx + 1:02d}] {it.name} ({it.episodes} eps) - ID: {it.id}")
        if it.link:
            print(f"     URL: {it.link}")
    print()


def cmd_platforms(args):
    print("\nSupported OTT & Short Drama Platforms:")
    print("=" * 50)
    for p in get_all_platforms():
        print(f" - {p.platform_id:<14} : {p.display_name}")
    print("=" * 50 + "\n")


def main():
    parser = argparse.ArgumentParser(
        prog="drama_downloader",
        description="Multi-Platform Short Drama Extractor and Downloader Module",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Info command
    p_info = subparsers.add_parser("info", help="Inspect series metadata and episode list")
    p_info.add_argument("target", help="URL or Series ID")
    p_info.add_argument("-p", "--platform", help="Explicit platform name/ID")
    p_info.set_defaults(func=cmd_info)

    # Download command
    p_dl = subparsers.add_parser("download", help="Download series or episodes")
    p_dl.add_argument("target", help="URL or Series ID")
    p_dl.add_argument("-p", "--platform", help="Explicit platform name/ID")
    p_dl.add_argument("-e", "--episodes", help="Episode range (e.g. 1-10,12,15)")
    p_dl.add_argument("-o", "--output", default="./downloads", help="Output directory (default: ./downloads)")
    p_dl.add_argument("-c", "--concurrency", type=int, default=2, help="Concurrency workers (default: 2)")
    p_dl.set_defaults(func=cmd_download)

    # Catalog command
    p_cat = subparsers.add_parser("catalog", help="Browse catalog of short dramas")
    p_cat.add_argument("platform", help="Platform ID (e.g. dramabox, shortmax, kisskh)")
    p_cat.add_argument("--page", type=int, default=1, help="Page number")
    p_cat.add_argument("-q", "--query", help="Search keyword")
    p_cat.add_argument("--category", help="Category filter")
    p_cat.set_defaults(func=cmd_catalog)

    # Platforms command
    p_plat = subparsers.add_parser("platforms", help="List all supported platforms")
    p_plat.set_defaults(func=cmd_platforms)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
