#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html as html_mod
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

EXAMPLES_NAMESPACE = uuid.UUID("c1a4f8c0-1f6e-4f1a-bf6f-2ad9e7f6c0fe")

ISA_DISPLAY = {
    "risc-iv-32": "risc-iv-32",
    "vliw-iv": "vliw-iv",
    "f32a": "f32a",
    "acc32": "acc32",
    "m68k": "m68k",
}


@dataclass(frozen=True)
class Example:
    isa: str
    source: str
    config: str
    example_root: Path

    @property
    def source_path(self) -> Path:
        return self.example_root / self.isa / self.source

    @property
    def config_path(self) -> Path:
        return self.example_root / self.isa / self.config

    @property
    def display_name(self) -> str:
        return f"{self.source} + {self.config}"

    @property
    def repo_path(self) -> str:
        return f"example/{self.isa}/{self.source}"

    @property
    def repo_config(self) -> str:
        return f"example/{self.isa}/{self.config}"

    @property
    def guid(self) -> uuid.UUID:
        key = f"wrench-example:{self.isa}/{self.source}+{self.config}"
        return uuid.uuid5(EXAMPLES_NAMESPACE, key)


def discover_examples(example_root: Path) -> list[Example]:
    examples: list[Example] = []
    if not example_root.is_dir():
        return examples

    for isa_dir in sorted(p.name for p in example_root.iterdir() if p.is_dir()):
        d = example_root / isa_dir
        sources = sorted(p.name for p in d.iterdir() if p.suffix == ".s")
        configs = sorted(p.name for p in d.iterdir() if p.suffix == ".yaml")
        source_stems = {Path(s).stem for s in sources}

        yaml_task: dict[str, str] = {}
        for y in configs:
            parts = Path(y).stem.split("-")
            while parts:
                candidate = "-".join(parts)
                if candidate in source_stems:
                    yaml_task[y] = candidate
                    break
                parts.pop()

        for s in sources:
            s_stem = Path(s).stem
            matched = [
                y
                for y, task in yaml_task.items()
                if s_stem == task or s_stem.startswith(task + "-")
            ]
            for y in sorted(matched):
                examples.append(Example(isa_dir, s, y, example_root))
    return examples


def wrench_cmd(wrench: str) -> list[str]:
    parts = wrench.split()
    return parts if parts else ["wrench"]


def wrench_version(wrench: str) -> str:
    try:
        proc = subprocess.run(
            wrench_cmd(wrench) + ["--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except FileNotFoundError:
        pass
    return "unknown"


def run_wrench(wrench: str, args: list[str]) -> tuple[int, str, str, str]:
    cmd = wrench_cmd(wrench) + args
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    cmd_str = " ".join(cmd)
    return proc.returncode, proc.stdout, proc.stderr, cmd_str


def crop_log(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return "LOG TOO LONG, CROPPED\n\n" + text[-limit:]


def render_status_log(
    *, version: str, cmd: str, exit_code: int, stderr: str
) -> str:
    return "\n".join(
        [
            "$ wrench --version",
            version,
            cmd,
            f"ExitCode {exit_code}",
            stderr,
        ]
    )


def build_one_example(
    ex: Example, *, storage_dir: Path, wrench: str, version: str, log_limit: int
) -> bool:
    isa = ex.isa
    out_dir = storage_dir / str(ex.guid)
    out_dir.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(ex.source_path, out_dir / "source.s")
    shutil.copyfile(ex.config_path, out_dir / "config.yaml")

    (out_dir / "name.txt").write_text("wrench")
    (out_dir / "variant.txt").write_text(f"example {ex.display_name}", encoding="utf-8")
    (out_dir / "comment.txt").write_text(
        "\n".join(
            [
                f"Source: {ex.repo_path}",
                f"Config: {ex.repo_config}",
                f"ISA:    {isa}",
            ]
        ),
        encoding="utf-8",
    )
    (out_dir / "wrench-version.txt").write_text(version, encoding="utf-8")
    (out_dir / "test_cases_status.log").write_text("", encoding="utf-8")
    (out_dir / "test_cases_result.log").write_text("", encoding="utf-8")

    args = [
        "--isa",
        isa,
        str(ex.source_path),
        "-c",
        str(ex.config_path),
    ]
    rc, stdout, stderr, cmd_str = run_wrench(wrench, args)
    (out_dir / "result.log").write_text(crop_log(stdout, log_limit), encoding="utf-8")
    (out_dir / "status.log").write_text(
        render_status_log(version=version, cmd=cmd_str, exit_code=rc, stderr=stderr),
        encoding="utf-8",
    )

    dump_args = [*args, "-S"]
    _, dump_out, dump_err, _ = run_wrench(wrench, dump_args)
    (out_dir / "dump.txt").write_text(
        dump_out + ("\n" + dump_err if dump_err else ""), encoding="utf-8"
    )

    return rc == 0


def render_examples_html(
    template: str, examples: Iterable[Example], *, success: dict[Example, bool]
) -> str:
    groups: dict[str, list[Example]] = {}
    for ex in examples:
        groups.setdefault(ex.isa, []).append(ex)

    parts: list[str] = []
    for isa in sorted(groups.keys()):
        title = ISA_DISPLAY.get(isa, isa)
        parts.append('<div class="mb-8">')
        parts.append(
            f'<h2 class="mb-3 pb-1 border-b border-zinc-700 text-[var(--c-grey)] text-xl">'
            f"/* {html_mod.escape(title)} */</h2>"
        )
        parts.append('<ul class="space-y-1">')
        for ex in sorted(groups[isa], key=lambda e: (e.source, e.config)):
            href = f"/report/{ex.guid}"
            ok = success.get(ex, True)
            status_class = (
                "text-[var(--c-green)]" if ok else "text-[var(--c-orange)]"
            )
            status_label = "ok" if ok else "fail"
            parts.append(
                '<li class="flex flex-wrap items-baseline gap-x-2">'
                f'<span class="{status_class}">[{status_label}]</span>'
                f'<a href="{html_mod.escape(href)}" '
                'class="hover:bg-[var(--c-fuschia)] pt-[0.2ch] pb-[0.2ch] '
                'text-[var(--c-fuschia)] hover:text-[var(--c-black)] cursor-pointer">'
                f"[{html_mod.escape(ex.display_name)}]</a>"
                "</li>"
            )
        parts.append("</ul>")
        parts.append("</div>")

    return template.replace("{{examples}}", "\n".join(parts))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrench", default="wrench")
    parser.add_argument("--example-root", type=Path, default=Path("example"))
    parser.add_argument(
        "--template", type=Path, default=Path("static/examples.template.html")
    )
    parser.add_argument("--output", type=Path, default=Path("build/examples"))
    parser.add_argument("--log-limit", type=int, default=10000)
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="exit non-zero if any example fails to run",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    template_path: Path = args.template
    template = template_path.read_text(encoding="utf-8")

    storage_dir: Path = args.output / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)

    examples = discover_examples(args.example_root)
    if not examples:
        print(f"No examples discovered under {args.example_root}", file=sys.stderr)
        return 1

    version = wrench_version(args.wrench)
    print(f"Using wrench: {args.wrench} ({version})")
    print(f"Discovered {len(examples)} example(s).")

    success: dict[Example, bool] = {}
    failed: list[Example] = []
    for ex in examples:
        ok = build_one_example(
            ex,
            storage_dir=storage_dir,
            wrench=args.wrench,
            version=version,
            log_limit=args.log_limit,
        )
        success[ex] = ok
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {ex.isa}/{ex.display_name} -> {ex.guid}")
        if not ok:
            failed.append(ex)

    html_out = render_examples_html(template, examples, success=success)
    (args.output / "examples.html").write_text(html_out, encoding="utf-8")
    print(f"Wrote {args.output / 'examples.html'}")

    if failed and args.fail_fast:
        print(f"{len(failed)} example(s) failed.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
