# git-config-manager

> A small toolkit for managing git configuration across multiple repositories.

It contains two independent scripts:

| Script                 | Purpose                                                                 |
| ---------------------- | ----------------------------------------------------------------------- |
| `link_git_configs.py`  | Scan multiple directories for git repos and symlink their `.git/config` |
| `git_global_proxy.py`  | Set / clear / inspect the **global** git proxy based on `proxy.yaml`    |

> On Windows the Python launcher `py` is used in the examples below. Substitute
> `python` / `python3` as appropriate for your environment.

---

## 1. `link_git_configs.py` — collect `.git/config` via symlinks

Scan target directories for Git repositories, mirror their structure, create
symbolic links to each repository's `.git/config`, and generate a formatted
summary for each target directory.

### Features

- Scan multiple target directories for Git repositories.
- Automatically create directories mirroring repository structure.
- Create symbolic links to each repository's `.git/config`.
- Generate a formatted `*_summary.txt` for each target directory.
- Log operations with clear, indented output.

### Usage

Edit the `main()` function in `link_git_configs.py` to set your target
directories:

```python
from pathlib import Path

target_dirs = [
    Path(r"C:\Dev\personal_repos"),
    Path(r"C:\Dev\team_repos"),
]
```

Then run:

```bash
py link_git_configs.py
```

This will:

1. Scan all Git repositories under the target directories.
2. Create a folder structure in `repos/` mirroring the repositories.
3. Generate symbolic links to `.git/config` files.
4. Write `*_summary.txt` files into `summary/`.

> Note: creating symbolic links on Windows may require Developer Mode to be
> enabled, or running the script from an elevated (Administrator) terminal.

### Example

After running, your output directory might look like this:

```
repos/
├── personal_repos/
│   ├── repo1/
│   │   └── config -> symlink to repo1/.git/config
│   └── repo2/
│       └── config -> symlink to repo2/.git/config
├── team_repos/
│   └── ...
```

And the summary file `summary/personal_repos_summary.txt`:

```
[SUMMARY] Git config links for personal_repos
======================================================================
Repo           Link Path
----------------------------------------------------------------------
repo1          config -> C:\Dev\personal_repos\repo1\.git\config
repo2          config -> C:\Dev\personal_repos\repo2\.git\config
======================================================================
```

---

## 2. `git_global_proxy.py` — manage the global git proxy

Modify the **global** git proxy (i.e. `~/.gitconfig`, via
`git config --global`) based on the settings in `proxy.yaml`. This affects
every repository for the current user.

It only touches the `http.proxy` / `https.proxy` keys and does **not** affect
the system proxy or SSH-based remotes.

### Configuration (`proxy.yaml`)

```yaml
proxy:
  # http / https / socks5 / socks5h
  scheme: http
  host: 127.0.0.1
  port: 10809

  # Optional authentication (leave empty if not needed)
  username:
  password:

  # Apply proxy to http.proxy (http remotes)
  http: true
  # Apply proxy to https.proxy (https remotes)
  https: true
```

- `host` + `port` form the proxy URL: `<scheme>://<host>:<port>`.
- If `username` / `password` are provided, the URL becomes
  `<scheme>://<username>:<password>@<host>:<port>`.
- The `http` / `https` toggles control whether `http.proxy` / `https.proxy`
  are written respectively.

No third-party dependencies are required: a tiny built-in YAML reader is used,
and PyYAML is used automatically if it happens to be installed.

### Usage

Edit `proxy.yaml`, then open the `__main__` block at the bottom of
`git_global_proxy.py` and uncomment the action you want:

```python
if __name__ == "__main__":
    # Uncomment the action you want to run:
    proxy_set()       # apply proxy from proxy.yaml to global git config
    # proxy_clear()   # remove global git http/https proxy
    # proxy_status()  # show current global git proxy settings
```

Then run:

```bash
py git_global_proxy.py
```

### Example output

```
[SET] Set http.proxy  = http://127.0.0.1:10809
[SET] Set https.proxy = http://127.0.0.1:10809
```

Clearing the proxy (`proxy_clear()`):

```
[CLEAR] Cleared http.proxy
[CLEAR] Cleared https.proxy
```

Checking the status (`proxy_status()`) when nothing is set:

```
[STATUS] No global git proxy is currently set.
```

## Installation

Clone this repository:

```bash
git clone https://github.com/your-username/git-config-manager.git
cd git-config-manager
```
