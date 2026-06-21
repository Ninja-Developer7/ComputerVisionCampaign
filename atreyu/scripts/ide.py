#!/usr/bin/env python3
"""
atreyu IDE assistant
====================

Subcommands:
  complete   -- basic code completion hints for Python files
  refactor   -- simple automated renames / structure suggestions
  docs       -- generate Markdown docs from Python modules
  prompt     -- generate an AI coding prompt from a source file
  agent      -- scaffold a new atreyu agent / worker script
  docker     -- generate Dockerfile / docker-compose boilerplate
  bugs       -- static checks: unused imports, bare excepts, long lines

Usage
-----
  python ide.py complete  backend/app.py
  python ide.py refactor  --rename old_name new_name backend/app.py
  python ide.py docs      backend/ > docs.md
  python ide.py prompt    backend/app.py --style implementation
  python ide.py agent     --name worker --type cron
  python ide.py docker    --service backend --port 8000
  python ide.py bugs      backend/ frontend/
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]


# ============================================================================
# helpers
# ============================================================================
def _python_files(paths: Sequence[str]) -> List[Path]:
    out: List[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            out.extend(sorted(p for p in path.rglob("*.py")))
        elif path.suffix == ".py":
            out.append(path)
    return out


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


# ============================================================================
# complete
# ============================================================================
def _complete(path: Path) -> List[str]:
    text = path.read_text(errors="ignore")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ["// syntax error; cannot analyze"]

    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            names.append(f"def {node.name}(")
        elif isinstance(node, ast.AsyncFunctionDef):
            names.append(f"async def {node.name}(")
        elif isinstance(node, ast.ClassDef):
            names.append(f"class {node.name}:")
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.append(t.id)
    # suggest common calls too
    names += [
        "import os",
        "from pathlib import Path",
        "import json",
        "def main():",
        "if __name__ == '__main__':",
        "print(",
        "return",
        "yield",
        "raise ",
        "try:",
        "except ",
        "finally:",
        "with ",
    ]
    # dedupe preserving order
    seen = set()
    out = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out[:120]


def cmd_complete(args: argparse.Namespace):
    for path in _python_files([args.path]):
        print(f"## {_rel(path)}")
        for item in _complete(path):
            print(item)
        print()


# ============================================================================
# refactor
# ============================================================================
def cmd_refactor(args: argparse.Namespace):
    path = Path(args.path)
    text = path.read_text()
    if args.rename:
        old, new = args.rename
        if old not in text:
            print(f"no occurrences of '{old}' in {path}", file=sys.stderr)
            sys.exit(1)
        new_text = text.replace(old, new)
        changed = new_text != text
        if args.in_place and changed:
            path.write_text(new_text)
            print(f"updated: {_rel(path)}")
        elif changed:
            print(new_text)
        else:
            print("no changes", file=sys.stderr)
        return

    if args.extract_function and args.from_line and args.to_line:
        # naive: print a suggested function wrapper
        lines = text.splitlines()
        start = max(1, args.from_line)
        end = min(len(lines), args.to_line)
        snippet = lines[start - 1 : end]
        indent = "    "
        print("Suggested refactor:")
        print("def extracted():")
        for line in snippet:
            print(indent + line)
        print()
        print("Replace original block with:")
        print("    extracted()")
        return

    print("refactor: use --rename OLD NEW or --extract-function --from N --to M")


# ============================================================================
# docs
# ============================================================================
def _module_doc(path: Path) -> str:
    text = path.read_text(errors="ignore")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return f"# {_rel(path)}\n\n<!-- invalid python -->"

    lines = [f"# `{_rel(path)}`", ""]
    for node in tree.body:
        if isinstance(node, ast.Module) and (node.body):
            pass
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            lines.append(node.value.s.strip())
            lines.append("")
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            sig = _func_sig(node)
            doc = ast.get_docstring(node) or ""
            lines.append(f"### {node.name}")
            lines.append("")
            lines.append("```python")
            lines.append(sig)
            lines.append("```")
            lines.append("")
            if doc:
                lines.append(doc.strip())
            lines.append("")
        elif isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or ""
            lines.append(f"## `class {node.name}`")
            lines.append("")
            if doc:
                lines.append(doc.strip())
            lines.append("")
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
            if bases:
                lines.append("Bases: " + ", ".join(bases))
                lines.append("")
    return "\n".join(lines)


def _func_sig(node: ast.AST) -> str:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    args = []
    defaults_offset = len(node.args.args) - len(node.args.defaults)
    for i, a in enumerate(node.args.args):
        arg = a.arg
        if i >= defaults_offset:
            try:
                d = ast.get_source_segment(node, node.args.defaults[i - defaults_offset]) or "..."
                arg += f"={d}"
            except Exception:
                arg += "=..."
        args.append(arg)
    body_preview = ""
    if node.body:
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            body_preview = ""
    sig = f"{prefix}def {node.name}({', '.join(args)})"
    if node.returns:
        try:
            ret = ast.get_source_segment(node, node.returns) or "..."
        except Exception:
            ret = "..."
        sig += f" -> {ret}"
    sig += ":"
    return sig


def cmd_docs(args: argparse.Namespace) -> int:
    files = _python_files([args.path])
    if not files:
        print("// no python files", file=sys.stderr)
        return 1
    for path in files:
        print(_module_doc(path))
    return 0


# ============================================================================
# prompt
# ============================================================================
def cmd_prompt(args: argparse.Namespace):
    path = Path(args.path)
    text = path.read_text(errors="ignore")
    rel = _rel(path)
    style = args.style or "implementation"

    prompt_parts = [
        f"Style: {style}",
        f"Target file: {rel}",
        "",
        "Constraints:",
        "- match existing conventions in this repo",
        "- avoid new dependencies without discussion",
        "- keep functions short and testable",
        "",
        "Source code:",
        "```python",
        text[:8000],
        "```",
    ]
    print("\n".join(prompt_parts))


# ============================================================================
# agent
# ============================================================================
AGENT_TEMPLATES = {
    "cron": (
        "Scaffolded cron agent: {name}\n"
        "--------------------------------\n"
        "Add to your cron config:\n"
        "  name: {name}\n"
        "  schedule: '0 9 * * *'\n"
        "  prompt: |\n"
        "    You are {name}. Do the assigned task and report concise results.\n"
        "  skills:\n"
        "    - terminal\n"
        "    - file\n"
        "  toolsets:\n"
        "    - terminal\n"
        "    - file\n"
    ),
    "task": (
        "Scaffolded task agent: {name}\n"
        "----------------------------\n"
        "Spawn with:\n"
        "  delegate_task(\n"
        "    role='leaf',\n"
        "    goal='TODO: describe goal',\n"
        "    toolsets=['terminal', 'file', 'web'],\n"
        "  )\n"
    ),
    "skill": (
        "Scaffolded skill: {name}\n"
        "------------------------\n"
        "Create files:\n"
        "  ~/.hermes/skills/{name}/SKILL.md\n"
        "  ~/.hermes/skills/{name}/references/\n"
        "  ~/.hermes/skills/{name}/scripts/\n"
        "\n"
        "SKILL.md must include YAML frontmatter with name + description.\n"
    ),
}


def cmd_agent(args: argparse.Namespace):
    name = args.name
    atype = args.type or "task"
    tpl = AGENT_TEMPLATES.get(atype)
    if not tpl:
        print(f"unknown agent type: {atype}")
        print("available:", ", ".join(AGENT_TEMPLATES.keys()))
        sys.exit(1)
    print(tpl.format(name=name))


# ============================================================================
# docker
# ============================================================================
DOCKERFILE = """\
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT={port}
EXPOSE {port}

CMD ["python", "main.py"]
"""

COMPOSE = """\
version: "3.9"
services:
  {service}:
    build: .
    ports:
      - "{port}:{port}"
    volumes:
      - .:/app
    environment:
      - NODE_ENV=development
"""


def cmd_docker(args: argparse.Namespace):
    service = args.service or "app"
    port = args.port or 8000
    print(DOCKERFILE.format(port=port))
    print("\n--- docker-compose.yml ---\n")
    print(COMPOSE.format(service=service, port=port))


# ============================================================================
# bugs
# ============================================================================
BUG_PATTERNS: List[Tuple[str, str]] = [
    (r"except\s*:", "bare except: catches everything, including SystemExit"),
    (r"except\s+Exception\s*:", "catching Exception is often too broad"),
    (r"eval\(", "eval() is unsafe"),
    (r"exec\(", "exec() is unsafe"),
    (r"import \*", "star import pollutes namespace"),
    (r"os\.system\(", "prefer subprocess.run over os.system"),
    (r"==\s*None", "use 'is None' instead of '== None'"),
    (r"!=\s*None", "use 'is not None' instead of '!= None'"),
]


def _check_file(path: Path) -> List[Tuple[int, str]]:
    hits: List[Tuple[int, str]] = []
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except Exception:
        return hits
    for i, line in enumerate(lines, 1):
        if len(line) > 120:
            hits.append((i, f"line too long ({len(line)} chars)"))
        for pat, msg in BUG_PATTERNS:
            if re.search(pat, line):
                hits.append((i, msg))
    try:
        tree = ast.parse(path.read_text(errors="ignore"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("requests", "urllib2", "md5"):
                        hits.append((node.lineno, f"consider {alias.name} alternatives"))
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                if not node.body:
                    hits.append((node.lineno, "empty test body"))
    except Exception:
        pass
    return hits


def cmd_bugs(args: argparse.Namespace) -> int:
    paths = _python_files(args.paths or ["backend", "frontend", "scripts"])
    exit_code = 0
    for path in paths:
        hits = _check_file(path)
        if hits:
            exit_code = 1
            print(f"{_rel(path)}:")
            for lineno, msg in hits:
                print(f"  L{lineno}: {msg}")
    return exit_code


# ============================================================================
# CLI
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="atreyu IDE assistant")
    sub = parser.add_subparsers(dest="command")

    p_comp = sub.add_parser("complete")
    p_comp.add_argument("path")

    p_ref = sub.add_parser("refactor")
    p_ref.add_argument("path")
    p_ref.add_argument("--rename", nargs=2, metavar=("OLD", "NEW"))
    p_ref.add_argument("--extract-function", action="store_true")
    p_ref.add_argument("--from-line", type=int, dest="from_line")
    p_ref.add_argument("--to-line", type=int, dest="to_line")
    p_ref.add_argument("--in-place", action="store_true")

    p_docs = sub.add_parser("docs")
    p_docs.add_argument("path", nargs="?", default=".")

    p_pr = sub.add_parser("prompt")
    p_pr.add_argument("path")
    p_pr.add_argument("--style", default="implementation")

    p_ag = sub.add_parser("agent")
    p_ag.add_argument("--name", required=True)
    p_ag.add_argument("--type", choices=["cron", "task", "skill"], default="task")

    p_dk = sub.add_parser("docker")
    p_dk.add_argument("--service", default="app")
    p_dk.add_argument("--port", type=int, default=8000)

    p_bug = sub.add_parser("bugs")
    p_bug.add_argument("paths", nargs="*", default=[])

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        raise SystemExit(1)

    if args.command == "complete":
        cmd_complete(args)
    elif args.command == "refactor":
        cmd_refactor(args)
    elif args.command == "docs":
        raise SystemExit(cmd_docs(args))
    elif args.command == "prompt":
        cmd_prompt(args)
    elif args.command == "agent":
        cmd_agent(args)
    elif args.command == "docker":
        cmd_docker(args)
    elif args.command == "bugs":
        raise SystemExit(cmd_bugs(args))


if __name__ == "__main__":
    main()
