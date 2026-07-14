"""
Run all git link collectors in one go.

This is a convenience entry point (at the project root) that runs both:

    src/link_git_configs.py   -> symlink each repo's .git/config into output/git_config/
    src/link_git_hooks.py     -> symlink each repo's commit-msg hook into output/git_hooks/

Both read the same `repos[].path` list from config.yaml. They write to separate
output subdirectories and to distinctly named summary files, so running them in
sequence does not interfere.

Usage:
    py link_git_all.py
"""

import sys
from pathlib import Path

# The collector modules live in src/; make them importable.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import link_git_configs
import link_git_hooks


def log(msg: str, level: str = "INFO") -> None:
    print(f"[{level}] {msg}")


def main() -> None:
    log("Running link_git_configs ...", "RUN")
    print("=" * 60)
    link_git_configs.main()

    log("Running link_git_hooks ...", "RUN")
    print("=" * 60)
    link_git_hooks.main()

    log("All link collectors finished.", "DONE")


if __name__ == "__main__":
    main()
