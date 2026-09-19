"""CLI noi bo de test search/download/list/get ma khong can qua Claude moi lan.
Goi thang cac ham tool trong cao_anh_ref.server - khong phai san pham cho end-user.

Usage:
    python scripts/dev_cli.py search "moody blue neon night city" --limit 10
    python scripts/dev_cli.py download --project test-project --result-ids <id1> <id2>
    python scripts/dev_cli.py list --project test-project
    python scripts/dev_cli.py get <image_id>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cao_anh_ref import server  # noqa: E402


def cmd_search(args: argparse.Namespace) -> None:
    results = server.search_images(args.query, source=args.source, limit=args.limit)
    print(json.dumps(results, indent=2, ensure_ascii=False))


def cmd_download(args: argparse.Namespace) -> None:
    result = server.download_images(
        project=args.project,
        result_ids=args.result_ids or [],
        urls=args.urls or [],
        tags=args.tags or [],
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_list(args: argparse.Namespace) -> None:
    result = server.list_moodboard(args.project)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_get(args: argparse.Namespace) -> None:
    metadata, image = server.get_image(args.image_id)
    print(metadata)
    content = image.to_image_content()
    print(f"[anh: path={image.path}, mimeType={content.mimeType}, base64_len={len(content.data)}]")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search")
    p_search.add_argument("query")
    p_search.add_argument("--source", default="pinterest")
    p_search.add_argument("--limit", type=int, default=20)
    p_search.set_defaults(func=cmd_search)

    p_download = sub.add_parser("download")
    p_download.add_argument("--project", required=True)
    p_download.add_argument("--result-ids", nargs="*", default=[])
    p_download.add_argument("--urls", nargs="*", default=[])
    p_download.add_argument("--tags", nargs="*", default=[])
    p_download.set_defaults(func=cmd_download)

    p_list = sub.add_parser("list")
    p_list.add_argument("project")
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get")
    p_get.add_argument("image_id")
    p_get.set_defaults(func=cmd_get)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
