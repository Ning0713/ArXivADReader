from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from adpaper.config import load_config
from adpaper.migration import migrate
from adpaper.pipeline import UpdatePipeline
from adpaper.site import SiteBuilder
from adpaper.storage import Repository, validate_date
from adpaper.validate import validate_repository


def current_date() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")


def _date_arg(value: str) -> str:
    if value == "today":
        return current_date()
    return validate_date(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and publish AutoDrive Papers")
    parser.add_argument("--config", default="config/config.yml", help="YAML configuration path")
    sub = parser.add_subparsers(dest="command", required=True)

    update = sub.add_parser("update", help="Fetch, filter, enrich, and store one date")
    update.add_argument("--date", default="today", type=_date_arg)
    update.add_argument("--force", action="store_true")
    update.add_argument("--allow-arxiv-discovery", action="store_true")
    update.add_argument("--dry-run", action="store_true")

    build = sub.add_parser("build", help="Render the static site")
    build.set_defaults(command="build")

    validate = sub.add_parser("validate", help="Validate stored data")
    validate.set_defaults(command="validate")

    migration = sub.add_parser("migrate", help="Import an existing AutoClaw workspace")
    migration.add_argument("--legacy-root", required=True, type=Path)
    migration.add_argument("--no-refetch", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config(args.config)
    pipeline = UpdatePipeline(config)

    if args.command == "update":
        report = pipeline.run(
            args.date,
            force=args.force,
            allow_arxiv_discovery=args.allow_arxiv_discovery,
            dry_run=args.dry_run,
        )
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        if report.status in {"updated", "unchanged"}:
            SiteBuilder(config).build()
        return 0 if report.status in {"updated", "unchanged", "preview"} else 1

    if args.command == "build":
        output = SiteBuilder(config).build()
        print(json.dumps({"status": "built", "output": str(output)}, ensure_ascii=False))
        return 0

    if args.command == "validate":
        errors = validate_repository(Repository(config))
        if errors:
            print(json.dumps({"status": "invalid", "errors": errors}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps({"status": "valid"}, ensure_ascii=False))
        return 0

    if args.command == "migrate":
        report = migrate(args.legacy_root, pipeline, refetch=not args.no_refetch)
        print(json.dumps({"status": "migrated", **asdict(report)}, ensure_ascii=False, indent=2))
        return 0 if not report.warnings else 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
