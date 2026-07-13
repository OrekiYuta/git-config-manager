import shutil
from pathlib import Path
from typing import List


def log(msg: str, level: str = "INFO", indent: int = 0) -> None:
    """Unified logging output with optional indentation"""
    prefix = "│   " * indent
    print(f"{prefix}[{level}] {msg}")


def ensure_symlink(src: Path, dst: Path) -> str:
    """
    Ensure that a symbolic link exists and points to the correct target.
    Returns:
        "SKIP"    -> Already correct link
        "REPLACE" -> Existing link points elsewhere
        "REMOVE"  -> Existing file is not a link
        "NEW"     -> No existing file/link
    """
    if dst.is_symlink():
        if dst.resolve() == src.resolve():
            return "SKIP"
        else:
            dst.unlink()
            return "REPLACE"
    elif dst.exists():
        dst.unlink()
        return "REMOVE"
    return "NEW"


def process_repo(repo_path: Path, target_base: Path, output_base: Path, summary: List[str]) -> None:
    """
    Process a single git repository: create target dir, create symlink, log info.
    """
    git_config = repo_path / ".git" / "config"
    if not git_config.is_file():
        log(f"No config file found in {repo_path}", "WARN")
        return

    relative_path = repo_path.relative_to(target_base)
    dest_repo_dir = output_base / target_base.name / relative_path

    log(f"Git repo: {repo_path}", "FOUND")
    log(f"Relative path: {relative_path}", "INFO", indent=1)
    log(f"Will create: {dest_repo_dir}", "INFO", indent=1)

    dest_repo_dir.mkdir(parents=True, exist_ok=True)
    link_path = dest_repo_dir / "config"

    action = ensure_symlink(git_config, link_path)

    if action == "SKIP":
        log(f"Already linked: {link_path}", "SKIP", indent=1)
    else:
        if action in ("REPLACE", "REMOVE"):
            log(f"{action} existing: {link_path}", "REMOVE", indent=1)
        link_path.symlink_to(git_config)
        log(f"Linked {git_config} -> {link_path}", "LINKED", indent=1)

    summary.append(f"{link_path} -> {git_config}")
    print("-" * 60)


def scan_target(target_dir: Path, output_base: Path) -> List[str]:
    """
    Scan a target directory for git repositories and process each.
    Returns a summary list for this target_dir.
    """
    summary: List[str] = []

    log(f"Scanning target: {target_dir}")
    log(f"Target exists? {target_dir.exists()}")
    log(f"Output base: {output_base}")
    print("-" * 60)

    for repo_path in target_dir.rglob(".git"):
        if repo_path.is_dir():
            process_repo(repo_path.parent, target_dir, output_base, summary)

    return summary


def write_summary(summary: List[str], summary_base: Path, target_dir: Path) -> None:
    """
    Write summary.txt in aligned table format for a specific target_dir.
    """
    if not summary:
        return

    summary_base.mkdir(parents=True, exist_ok=True)
    summary_file = summary_base / f"{target_dir.name}_summary.txt"
    formatted = [(Path(link).parent.name, f"config -> {target}") for link, target in
                 (item.split(" -> ") for item in summary)]
    formatted.sort(key=lambda x: x[0])
    max_len = max(len(r[0]) for r in formatted)

    with summary_file.open("w", encoding="utf-8") as f:
        f.write(f"[SUMMARY] Git config links for {target_dir.name}\n")
        f.write("=" * 70 + "\n")
        f.write(f"{'Repo'.ljust(max_len)}   Link Path\n")
        f.write("-" * 70 + "\n")
        for repo, link_info in formatted:
            f.write(f"{repo.ljust(max_len)}   {link_info}\n")
        f.write("=" * 70 + "\n")

    log(f"Summary written to {summary_file}")
    print("\n")


def clean_output(output_base: Path) -> None:
    """
    Remove the existing output directory so that stale links to repos that
    no longer exist are not left behind. Recreated fresh on the next scan.
    """
    if output_base.exists():
        shutil.rmtree(output_base)
        log(f"Cleaned existing output dir: {output_base}", "CLEAN")
    output_base.mkdir(parents=True, exist_ok=True)
    print("-" * 60)


def main() -> None:
    target_dirs = [
        Path(r"/Users/elias/repo1"),
        Path(r"/Users/elias/repo2"),
        Path(r"/Users/elias/repo3")
    ]

    project_root = Path(__file__).resolve().parent
    output_base = project_root / "repos"
    summary_base = project_root / "summary"

    clean_output(output_base)

    for target_dir in target_dirs:
        summary = scan_target(target_dir, output_base)
        write_summary(summary, summary_base, target_dir)


if __name__ == "__main__":
    main()
