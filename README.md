# git-config-manager

> A small toolkit for managing git configuration across many local repositories
> from one place.

If you keep dozens of git repositories on disk (often split across several
GitHub accounts), keeping their configuration consistent is tedious: setting the
right `user.name` / `user.email` per account, authenticating pushes over https,
and toggling a proxy. This toolkit drives all of that from a single
**`config.yaml`**, so you configure once and apply to every repo in bulk.

What it does:

- **Bulk identity & auth** — set `user.name` / `user.email` and embed a GitHub
  **PAT** into each repo's `origin` url, so `git push` needs no interactive
  login and each account's repos are configured correctly.
- **Proxy management** — set / clear the **global** git proxy, and optionally a
  **per-repo** proxy for selected directories.
- **Config collection** — gather every repo's `.git/config` via symlinks into
  one folder for easy inspection.

All settings live in a single **`config.yaml`**. Copy `config.example.yaml`
to `config.yaml` and edit it. `config.yaml` is git-ignored because it contains
secrets (GitHub PATs).

## Project layout

```
git-config-manager/
├── src/
│   ├── config_loader.py      # shared YAML loader
│   ├── link_git_configs.py   # collect .git/config via symlinks
│   └── set_git_configs.py    # global proxy + per-repo PAT / identity / proxy
├── config.example.yaml       # template (committed)
├── config.yaml               # real config (git-ignored, holds PATs)
├── output/                   # generated (git-ignored)
│   ├── repos/                # symlinks to each .git/config
│   └── summary/              # per-target summary tables
├── LICENSE
└── README.md
```

## How it works

```mermaid
flowchart LR
    CFG["config.yaml<br/>(proxy + repos)"]

    subgraph LINK["src/link_git_configs.py"]
        L["Scan repos[].path<br/>for git repositories"]
        L2["Symlink each .git/config<br/>into output/repos/ + write output/summary/"]
        L --> L2
    end

    subgraph SET["src/set_git_configs.py"]
        direction TB
        G["Global proxy<br/>set / clear / status<br/>(git config --global)"]
        R["Per-repo config: for every repo<br/>- user.name / user.email<br/>- PAT into origin url<br/>- repo-level proxy (if proxy: true)"]
    end

    CFG --> LINK
    CFG --> SET

    L2 -.-> OUT["output/repos/ &amp; output/summary/"]
    G -.-> GC["~/.gitconfig"]
    R -.-> RC["each repo's .git/config"]
```

Run the scripts from the project root:

```bash
py src/link_git_configs.py    # collect .git/config into output/
py src/set_git_configs.py     # apply proxy / per-repo config
```

| Script                    | Role                                                                             |
| ------------------------- | -------------------------------------------------------------------------------- |
| `src/link_git_configs.py` | **Read-only collector.** Finds every repo under `repos[].path` and symlinks its `.git/config` into `output/repos/`, with an `output/summary/` table. |
| `src/set_git_configs.py`  | **Writer.** Manages the global git proxy, and injects PAT / name / email / repo proxy into each repo's `.git/config`. |
| `src/config_loader.py`    | Shared YAML loader (uses PyYAML if installed, else a tiny built-in parser).      |

## License

MIT License. Copyright (c) Orekiyuta.

