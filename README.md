# git-config-manager

> Manage and unify `.git/config` files from multiple repositories by creating symlinks and generating a summary.

## Features

- Scan multiple target directories for Git repositories.
- Automatically create directories mirroring repository structure.
- Create symbolic links to each repository's `.git/config`.
- Generate a formatted `summary.txt` for each target directory.
- Log operations with clear, indented output.

## Installation

Clone this repository:

```bash
git clone https://github.com/your-username/git-config-manager.git
cd git-config-manager
````

## Usage

Edit the `main()` function in `main.py` to set your target directories:

```python
from pathlib import Path

target_dirs = [
    Path(r"C:\Dev\personal_repos"),
    Path(r"C:\Dev\team_repos")
]
output_base = Path.cwd()
```

Then run:

```bash
python main.py
```

This will:

1. Scan all Git repositories under the target directories.
2. Create a folder structure in `output_base` mirroring the repositories.
3. Generate symbolic links to `.git/config` files.
4. Write `*_summary.txt` files summarizing all links.

## Example

After running, your output directory might look like this:

```
output_base/
├── personal_repos/
│   ├── repo1/
│   │   └── config -> symlink to repo1/.git/config
│   └── repo2/
│       └── config -> symlink to repo2/.git/config
├── team_repos/
│   └── ...
```

And the summary file `personal_repos_summary.txt`:

```
[SUMMARY] Git config links for personal_repos
======================================================================
Repo           Link Path
----------------------------------------------------------------------
repo1          config -> C:\Dev\personal_repos\repo1\.git\config
repo2          config -> C:\Dev\personal_repos\repo2\.git\config
======================================================================
```



