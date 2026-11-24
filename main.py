"""
Run the git-config-manager workflow in one go.

This top-level entry point runs, in order:

    src/set_git_configs.py    -> apply per-repo git config (name / email / PAT / proxy)
    src/link_git_configs.py   -> symlink each repo's .git/config into output/git_config/

The optional hook steps install a lowercase commit-msg hook and collect links
to the hooks; they are disabled by default.

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
    run_step("link_git_configs", link_git_configs.main)

    # Optional: install a hook that lowercases commit messages, then collect
    # links to commit-msg hooks. Both steps are disabled by default.
    # run_step("set_git_hooks", set_git_hooks.set_hooks)
    # run_step("link_git_hooks", link_git_hooks.main)

    log("Full workflow finished.", "DONE")


if __name__ == "__main__":
    main()
