"""
Unified git configuration tool.

Reads everything from config.yaml and provides two groups of actions:

GLOBAL PROXY  (from the `proxy:` section, applied via `git config --global`)
    set_global_proxy()      apply proxy to the global git config (~/.gitconfig)
    clear_global_proxy()    remove global git http/https proxy
    global_proxy_status()   show current global git proxy settings

PER-REPO CONFIG  (from the `repos:` list)
    set_repos_config()      for every git repo found under each `repos[].path`:
                              - set user.name  / user.email
                              - embed the PAT into the `origin` https github url
                              - if the entry has `proxy: true`, also write a
                                repo-level http.proxy / https.proxy (NOT global)
    clear_repos_config()    strip the PAT from origin urls and unset the
                            repo-level proxy (optionally user.name/email too)
    repos_config_status()   show name / email / masked origin url / repo proxy

Only the `origin` remote is touched, and only when it is an https github.com
url. SSH remotes and non-github hosts are left untouched. Injecting the PAT is
idempotent: an existing token / userinfo in the url is stripped and replaced.

Configuration is loaded via config_loader.py (PyYAML if available, otherwise a
tiny built-in parser; no third-party dependency required).
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config_loader import load_config, log


# --------------------------------------------------------------------------- #
# config loading
# --------------------------------------------------------------------------- #
def load_proxy() -> Dict[str, Any]:
    """Load the `proxy` mapping from config.yaml."""
    data = load_config()
    proxy = data.get("proxy")
    if not isinstance(proxy, dict):
        log("Missing top-level 'proxy' mapping in config.yaml", "ERROR")
        sys.exit(1)
    return proxy


def load_repos() -> List[Dict[str, Any]]:
    """Load and validate the `repos` list from config.yaml."""
    data = load_config()
    repos = data.get("repos")
    if not isinstance(repos, list) or not repos:
        log("Missing or empty 'repos' list in config.yaml", "ERROR")
        sys.exit(1)

    valid: List[Dict[str, Any]] = []
    for i, entry in enumerate(repos):
        if not isinstance(entry, dict) or "path" not in entry:
            log(f"repos[{i}] is missing a 'path'; skipping", "WARN")
            continue
        valid.append(entry)
    if not valid:
        log("No usable repos entries found in config.yaml", "ERROR")
        sys.exit(1)
    return valid


def build_proxy_url(proxy: Dict[str, Any]) -> str:
    """Construct the proxy URL from the proxy config mapping."""
    scheme = str(proxy.get("scheme") or "http")
    host = proxy.get("host")
    port = proxy.get("port")

    if not host or not port:
        log("Both 'host' and 'port' must be set in config.yaml", "ERROR")
        sys.exit(1)

    username = proxy.get("username")
    password = proxy.get("password")

    auth = ""
    if username:
        auth = str(username)
        if password:
            auth += f":{password}"
        auth += "@"

    return f"{scheme}://{auth}{host}:{port}"


# --------------------------------------------------------------------------- #
# git helpers
# --------------------------------------------------------------------------- #
def run_git(args: List[str], repo: Optional[Path] = None) -> subprocess.CompletedProcess:
    """
    Run a git command and return the completed process.

    If `repo` is given the command is scoped to that repository (`git -C`);
    otherwise it runs in the current context (used for --global operations).
    """
    cmd = ["git"]
    if repo is not None:
        cmd += ["-C", str(repo)]
    cmd += args
    return subprocess.run(cmd, capture_output=True, text=True)


def find_repos(base: Path) -> List[Path]:
    """Return every git repository directory found under `base`."""
    found: List[Path] = []
    if not base.exists():
        log(f"Path does not exist: {base}", "WARN")
        return found
    for git_dir in base.rglob(".git"):
        if git_dir.is_dir():
            found.append(git_dir.parent)
    return sorted(found)


# --------------------------------------------------------------------------- #
# url rewriting
# --------------------------------------------------------------------------- #
# https[://][userinfo@]github.com/owner/repo...
_HTTPS_GITHUB = re.compile(
    r"^(?P<scheme>https://)"          # scheme
    r"(?:[^/@]+@)?"                   # optional existing userinfo (token/user:pass)
    r"(?P<host>github\.com)"          # host, github.com only
    r"(?P<rest>/.*)$",                # /owner/repo(.git)
    re.IGNORECASE,
)


def is_https_github(url: str) -> bool:
    return bool(_HTTPS_GITHUB.match(url or ""))


def url_with_pat(url: str, pat: str) -> Optional[str]:
    """Return `url` with `pat` as userinfo (replacing any existing). None if not github https."""
    m = _HTTPS_GITHUB.match(url or "")
    if not m:
        return None
    return f"{m.group('scheme')}{pat}@{m.group('host')}{m.group('rest')}"


def url_without_pat(url: str) -> Optional[str]:
    """Return `url` with any userinfo stripped. None if not github https."""
    m = _HTTPS_GITHUB.match(url or "")
    if not m:
        return None
    return f"{m.group('scheme')}{m.group('host')}{m.group('rest')}"


def mask_url(url: str) -> str:
    """Mask any token/userinfo in an https url for safe display."""
    m = _HTTPS_GITHUB.match(url or "")
    if not m:
        return url
    if "@" in url.split("//", 1)[-1].split("/", 1)[0]:
        return f"{m.group('scheme')}***@{m.group('host')}{m.group('rest')}"
    return url


def get_origin_url(repo: Path) -> Optional[str]:
    result = run_git(["config", "--get", "remote.origin.url"], repo=repo)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def set_origin_url(repo: Path, url: str) -> bool:
    result = run_git(["remote", "set-url", "origin", url], repo=repo)
    if result.returncode != 0:
        log(f"Failed to set origin url: {result.stderr.strip()}", "ERROR")
        return False
    return True


# --------------------------------------------------------------------------- #
# global proxy commands
# --------------------------------------------------------------------------- #
def set_global_proxy() -> None:
    """Apply proxy settings from config.yaml to the global git config."""
    proxy = load_proxy()
    url = build_proxy_url(proxy)
    apply_http = proxy.get("http", True)
    apply_https = proxy.get("https", True)

    if not apply_http and not apply_https:
        log("Neither http nor https is enabled in config.yaml; nothing to do.", "WARN")
        return

    if apply_http:
        result = run_git(["config", "--global", "http.proxy", url])
        if result.returncode == 0:
            log(f"Set global http.proxy  = {url}", "SET")
        else:
            log(f"Failed to set http.proxy: {result.stderr.strip()}", "ERROR")

    if apply_https:
        result = run_git(["config", "--global", "https.proxy", url])
        if result.returncode == 0:
            log(f"Set global https.proxy = {url}", "SET")
        else:
            log(f"Failed to set https.proxy: {result.stderr.strip()}", "ERROR")


def clear_global_proxy() -> None:
    """Remove global git http/https proxy settings."""
    for key in ("http.proxy", "https.proxy"):
        result = run_git(["config", "--global", "--unset", key])
        if result.returncode == 0:
            log(f"Cleared global {key}", "CLEAR")
        elif result.returncode == 5:
            log(f"global {key} was not set", "SKIP")
        else:
            log(f"Failed to clear {key}: {result.stderr.strip()}", "ERROR")


def global_proxy_status() -> None:
    """Show current global git proxy settings."""
    found = False
    for key in ("http.proxy", "https.proxy"):
        result = run_git(["config", "--global", "--get", key])
        value = result.stdout.strip()
        if result.returncode == 0 and value:
            log(f"global {key} = {value}", "STATUS")
            found = True
    if not found:
        log("No global git proxy is currently set.", "STATUS")


# --------------------------------------------------------------------------- #
# repo-level proxy helpers
# --------------------------------------------------------------------------- #
def set_repo_proxy(repo: Path, proxy_url: str, apply_http: bool, apply_https: bool) -> None:
    """Write repo-level http/https proxy (scoped to this repo, not global)."""
    if apply_http:
        if run_git(["config", "http.proxy", proxy_url], repo=repo).returncode == 0:
            log(f"repo http.proxy  = {proxy_url}", "PROXY")
    if apply_https:
        if run_git(["config", "https.proxy", proxy_url], repo=repo).returncode == 0:
            log(f"repo https.proxy = {proxy_url}", "PROXY")


def clear_repo_proxy(repo: Path) -> None:
    """Remove repo-level http/https proxy settings."""
    for key in ("http.proxy", "https.proxy"):
        result = run_git(["config", "--unset", key], repo=repo)
        if result.returncode == 0:
            log(f"Cleared repo {key}", "CLEAR")
        elif result.returncode == 5:
            log(f"repo {key} was not set", "SKIP")


# --------------------------------------------------------------------------- #
# per-repo operations
# --------------------------------------------------------------------------- #
def set_repo(repo: Path, entry: Dict[str, Any], proxy_url: Optional[str],
             apply_http: bool, apply_https: bool) -> None:
    name = entry.get("name")
    email = entry.get("email")
    pat = entry.get("pat")
    use_proxy = bool(entry.get("proxy"))

    log(f"Repo: {repo}", "REPO")

    if name:
        run_git(["config", "user.name", str(name)], repo=repo)
        log(f"user.name  = {name}", "SET")
    if email:
        run_git(["config", "user.email", str(email)], repo=repo)
        log(f"user.email = {email}", "SET")

    # origin url + PAT
    origin = get_origin_url(repo)
    if origin is None:
        log("No 'origin' remote; skipping url rewrite", "SKIP")
    elif not is_https_github(origin):
        log(f"origin is not an https github url; skipping: {origin}", "SKIP")
    elif not pat:
        log("No 'pat' provided; skipping url rewrite", "SKIP")
    else:
        new_url = url_with_pat(origin, str(pat))
        if new_url == origin:
            log(f"origin already has this PAT: {mask_url(origin)}", "SKIP")
        elif new_url and set_origin_url(repo, new_url):
            log(f"origin -> {mask_url(new_url)}", "URL")

    # repo-level proxy
    if use_proxy:
        if proxy_url:
            set_repo_proxy(repo, proxy_url, apply_http, apply_https)
        else:
            log("proxy: true but proxy config is incomplete; skipping", "WARN")


def clear_repo(repo: Path, clear_user: bool = False) -> None:
    log(f"Repo: {repo}", "REPO")

    origin = get_origin_url(repo)
    if origin and is_https_github(origin):
        stripped = url_without_pat(origin)
        if stripped is not None and stripped != origin and set_origin_url(repo, stripped):
            log(f"origin -> {stripped}", "URL")
        else:
            log("origin had no PAT to strip", "SKIP")
    else:
        log("No https github origin; skipping url", "SKIP")

    clear_repo_proxy(repo)

    if clear_user:
        for key in ("user.name", "user.email"):
            result = run_git(["config", "--unset", key], repo=repo)
            if result.returncode == 0:
                log(f"Unset {key}", "CLEAR")
            elif result.returncode == 5:
                log(f"{key} was not set", "SKIP")


def status_repo(repo: Path) -> None:
    name = run_git(["config", "--get", "user.name"], repo=repo).stdout.strip()
    email = run_git(["config", "--get", "user.email"], repo=repo).stdout.strip()
    origin = get_origin_url(repo) or "(no origin)"
    http_proxy = run_git(["config", "--get", "http.proxy"], repo=repo).stdout.strip()
    https_proxy = run_git(["config", "--get", "https.proxy"], repo=repo).stdout.strip()
    log(f"Repo: {repo}", "REPO")
    log(f"user.name  = {name or '(unset)'}", "STATUS")
    log(f"user.email = {email or '(unset)'}", "STATUS")
    log(f"origin     = {mask_url(origin)}", "STATUS")
    if http_proxy or https_proxy:
        log(f"http.proxy  = {http_proxy or '(unset)'}", "STATUS")
        log(f"https.proxy = {https_proxy or '(unset)'}", "STATUS")


# --------------------------------------------------------------------------- #
# repos commands
# --------------------------------------------------------------------------- #
def _iter_repos(action) -> None:
    entries = load_repos()
    for entry in entries:
        base = Path(str(entry["path"]))
        log(f"Group: {entry.get('name', '?')}  ({base})", "GROUP")
        found = find_repos(base)
        if not found:
            log("No git repos found under this path.", "WARN")
        for repo in found:
            action(repo, entry)
            print("-" * 60)
        print("=" * 60)


def set_repos_config() -> None:
    """Set user.name/email, embed PAT into origin, and apply repo-level proxy."""
    proxy = load_proxy()
    proxy_url = build_proxy_url(proxy)
    apply_http = proxy.get("http", True)
    apply_https = proxy.get("https", True)
    _iter_repos(lambda repo, entry: set_repo(repo, entry, proxy_url, apply_http, apply_https))


def clear_repos_config(clear_user: bool = False) -> None:
    """Strip PATs from origin urls and clear repo-level proxy.

    Pass clear_user=True to also unset user.name / user.email.
    """
    _iter_repos(lambda repo, entry: clear_repo(repo, clear_user=clear_user))


def repos_config_status() -> None:
    """Show name / email / masked origin url / repo proxy for every repo."""
    _iter_repos(lambda repo, entry: status_repo(repo))


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Uncomment the action you want to run:

    # --- global proxy ---
    # set_global_proxy()
    # clear_global_proxy()
    # global_proxy_status()

    # --- per-repo config (PAT / name / email / repo-level proxy) ---
    set_repos_config()
    # clear_repos_config()               # unset pat, proxy
    # clear_repos_config(clear_user=True)  # unset pat, proxy, name, email
    # repos_config_status()