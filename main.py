"""
Run the full git-config-manager workflow in one go.

This top-level entry point runs, in order:

    src/set_git_configs.py    -> apply per-repo git config (name / email / PAT / proxy)
    src/set_git_hooks.py      -> install commit-msg hooks
    src/link_git_configs.py   -> symlink each repo's .git/config into output/git_config/
    src/link_git_hooks.py     -> symlink each repo's commit-msg hook into output/git_hooks/

All scripts read the same `repos[].path` list from config.yaml. Running the link
collectors after the setters ensures the generated output reflects the latest
repo state.

Usage:
    py main.py
"""

from src import link_git_configs
from src import link_git_hooks
from src import set_git_configs
from src import set_git_hooks


def log(msg: str, level: str = "INFO") -> None:
    print(f"[{level}] {msg}")


def run_step(step_name: str, action) -> None:
    log(f"Running {step_name} ...", "RUN")
    print("=" * 60)
    action()


def main() -> None:
    run_step("set_git_configs", set_git_configs.set_repos_config)
    run_step("set_git_hooks", set_git_hooks.set_hooks)
    run_step("link_git_configs", link_git_configs.main)
    run_step("link_git_hooks", link_git_hooks.main)
    log("Full workflow finished.", "DONE")


if __name__ == "__main__":
    main()

