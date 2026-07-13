"""
Modify the system-wide (global) git proxy based on proxy.yaml.

This script edits the global git config file (~/.gitconfig) via
`git config --global`, affecting every repository for the current user.

How to use:
    Edit proxy.yaml, then at the bottom of this file (the __main__ block)
    uncomment the function you want to run:

        proxy_set()      # apply proxy from proxy.yaml to global git config
        proxy_clear()    # remove global git http/https proxy
        proxy_status()   # show current global git proxy settings

The script uses a tiny built-in YAML reader so it has no third-party
dependencies (PyYAML is used automatically if it is installed).
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def log(msg: str, level: str = "INFO") -> None:
    """Unified logging output."""
    print(f"[{level}] {msg}")


# --------------------------------------------------------------------------- #
# YAML loading
# --------------------------------------------------------------------------- #
def _load_yaml_pyyaml(path: Path) -> Optional[Dict[str, Any]]:
    """Load YAML using PyYAML if available, else return None."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _coerce(value: str) -> Any:
    """Convert a raw scalar string into bool / int / None / str."""
    if value == "":
        return None
    low = value.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "none", "~"):
        return None
    if value.isdigit():
        return int(value)
    # strip surrounding quotes if present
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _load_yaml_simple(path: Path) -> Dict[str, Any]:
    """
    Minimal YAML reader supporting only the structure used by proxy.yaml:
    a top-level mapping key with one level of indented key: value pairs.
    """
    root: Dict[str, Any] = {}
    stack = [(-1, root)]  # (indent, container)

    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            # drop comments (only when # is not inside quotes; simple case)
            if "#" in line:
                line = line.split("#", 1)[0]
            if not line.strip():
                continue

            indent = len(line) - len(line.lstrip(" "))
            key, sep, val = line.strip().partition(":")
            if not sep:
                continue
            key = key.strip()
            val = val.strip()

            # unwind stack to the correct parent based on indentation
            while stack and indent <= stack[-1][0]:
                stack.pop()
            parent = stack[-1][1]

            if val == "":
                # start of a nested mapping
                child: Dict[str, Any] = {}
                parent[key] = child
                stack.append((indent, child))
            else:
                parent[key] = _coerce(val)

    return root


def load_config(path: Path) -> Dict[str, Any]:
    """Load proxy.yaml, preferring PyYAML but falling back to a simple parser."""
    if not path.is_file():
        log(f"Config file not found: {path}", "ERROR")
        sys.exit(1)

    data = _load_yaml_pyyaml(path)
    if data is None:
        data = _load_yaml_simple(path)

    proxy = data.get("proxy")
    if not isinstance(proxy, dict):
        log("Missing top-level 'proxy' mapping in proxy.yaml", "ERROR")
        sys.exit(1)
    return proxy


# --------------------------------------------------------------------------- #
# git helpers
# --------------------------------------------------------------------------- #
def run_git(args: list) -> subprocess.CompletedProcess:
    """Run a git command and return the completed process."""
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
    )


def build_proxy_url(proxy: Dict[str, Any]) -> str:
    """Construct the proxy URL from the config mapping."""
    scheme = str(proxy.get("scheme") or "http")
    host = proxy.get("host")
    port = proxy.get("port")

    if not host or not port:
        log("Both 'host' and 'port' must be set in proxy.yaml", "ERROR")
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
# commands
# --------------------------------------------------------------------------- #
CONFIG_PATH = Path(__file__).resolve().parent / "proxy.yaml"


def proxy_set() -> None:
    """Apply proxy settings from proxy.yaml to the global git config."""
    proxy = load_config(CONFIG_PATH)
    url = build_proxy_url(proxy)
    apply_http = proxy.get("http", True)
    apply_https = proxy.get("https", True)

    if not apply_http and not apply_https:
        log("Neither http nor https is enabled in proxy.yaml; nothing to do.", "WARN")
        return

    if apply_http:
        result = run_git(["config", "--global", "http.proxy", url])
        if result.returncode == 0:
            log(f"Set http.proxy  = {url}", "SET")
        else:
            log(f"Failed to set http.proxy: {result.stderr.strip()}", "ERROR")

    if apply_https:
        result = run_git(["config", "--global", "https.proxy", url])
        if result.returncode == 0:
            log(f"Set https.proxy = {url}", "SET")
        else:
            log(f"Failed to set https.proxy: {result.stderr.strip()}", "ERROR")


def proxy_clear() -> None:
    """Remove global git http/https proxy settings."""
    for key in ("http.proxy", "https.proxy"):
        result = run_git(["config", "--global", "--unset", key])
        if result.returncode == 0:
            log(f"Cleared {key}", "CLEAR")
        elif result.returncode == 5:
            # 5 = key was not set
            log(f"{key} was not set", "SKIP")
        else:
            log(f"Failed to clear {key}: {result.stderr.strip()}", "ERROR")


def proxy_status() -> None:
    """Show current global git proxy settings."""
    found = False
    for key in ("http.proxy", "https.proxy"):
        result = run_git(["config", "--global", "--get", key])
        value = result.stdout.strip()
        if result.returncode == 0 and value:
            log(f"{key} = {value}", "STATUS")
            found = True
    if not found:
        log("No global git proxy is currently set.", "STATUS")


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Uncomment the action you want to run:
    # proxy_set()
    # proxy_clear()
    proxy_status()
