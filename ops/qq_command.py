"""Strict QQ command parser; dispatch only fixed arguments, never shell text."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path

PROJECTS = {"自动驾驶": "ad", "情感计算": "ac", "全部": "all", "ad": "ad", "ac": "ac"}
ACTIONS = {
    "更新论文": "update",
    "更新": "update",
    "补跑": "retry",
    "预览论文": "preview",
    "预览": "preview",
    "状态": "status",
    "帮助": "help",
}
COMMAND = re.compile(
    r"(?:(自动驾驶|情感计算|全部|ad|ac)\s+)?"
    r"(更新论文|更新|补跑|预览论文|预览|状态|帮助)"
    r"(?:\s+(today|\d{4}-\d{2}-\d{2}))?"
)


def parse_command(message: str, default_project: str = "ad") -> dict[str, str]:
    match = COMMAND.fullmatch(message.strip())
    if not match:
        raise ValueError("命令格式错误，例如：情感计算 补跑 2026-09-16")
    project, action, day = match.groups()
    action = ACTIONS[action]
    if default_project not in {"ad", "ac"}:
        raise ValueError("Invalid default project")
    if action in {"help", "status"} and day:
        raise ValueError("状态/帮助不能附带日期")
    if action in {"retry", "preview"} and not day:
        raise ValueError("补跑/预览必须指定日期或 today")
    if day and day != "today":
        try:
            date.fromisoformat(day)
        except ValueError as exc:
            raise ValueError(f"无效日期：{day}") from exc
    return {
        "project": PROJECTS.get(project, default_project),
        "command": action,
        "date": day or ("today" if action == "update" else ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True)
    parser.add_argument("--plan", action="store_true", help="Validate only; do not dispatch")
    args = parser.parse_args()
    settings = json.loads(Path(__file__).with_name("projects.json").read_text(encoding="utf-8"))
    try:
        command = parse_command(args.message, settings["default_project"])
    except ValueError as exc:
        parser.error(str(exc))
    if args.plan:
        print(json.dumps(command, ensure_ascii=False))
        return 0
    invocation = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(Path(__file__).with_name("autoclaw.ps1")), "-Command", command["command"],
        "-Project", command["project"],
    ]
    if command["date"]:
        invocation.extend(["-Date", command["date"]])
    return subprocess.run(invocation, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
