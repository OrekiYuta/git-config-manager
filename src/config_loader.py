"""
Shared configuration loader for git-config-manager.

All scripts (link_git_configs.py, set_git_configs.py) read their settings from
a single ``config.yaml`` located at the project root (one level above src/).

PyYAML is used automatically if it is installed; otherwise a small built-in
parser is used. The built-in parser supports the subset of YAML used by
``config.yaml``:

    - top-level mappings
    - nested mappings (indented ``key: value``)
    - block sequences of scalars           (``- value``)
    - block sequences of mappings          (``- key: value`` then indented keys)

That is enough for ``proxy`` (mapping) and ``repos`` (list of mappings).
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Project root is the parent of this src/ directory; config.yaml lives there.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

Node = Union[Dict[str, Any], List[Any]]


def log(msg: str, level: str = "INFO") -> None:
    """Unified logging output."""
    print(f"[{level}] {msg}")


# --------------------------------------------------------------------------- #
# scalar coercion
# --------------------------------------------------------------------------- #
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
    if value.lstrip("-").isdigit():
        return int(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _split_key_value(text: str):
    """
    If `text` starts with a YAML mapping key (``key:`` followed by a space or
    end of string), return (key, value). Otherwise return None.

    This deliberately requires a space after the colon so Windows paths such as
    ``F:\\Code`` are treated as plain scalars, not ``{F: \\Code}``.
    """
    in_single = in_double = False
    for i, ch in enumerate(text):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == ":" and not in_single and not in_double:
            rest = text[i + 1:]
            if rest == "" or rest[0] == " ":
                return text[:i].strip(), rest.strip()
    return None


def _strip_comment(line: str) -> str:
    """Remove an unquoted trailing comment from a line."""
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


# --------------------------------------------------------------------------- #
# PyYAML path
# --------------------------------------------------------------------------- #
def _load_yaml_pyyaml(path: Path) -> Optional[Dict[str, Any]]:
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# --------------------------------------------------------------------------- #
# built-in fallback parser
# --------------------------------------------------------------------------- #
class _Line:
    __slots__ = ("indent", "content")

    def __init__(self, indent: int, content: str) -> None:
        self.indent = indent
        self.content = content


def _read_lines(path: Path) -> List[_Line]:
    lines: List[_Line] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = _strip_comment(raw.rstrip("\n")).rstrip()
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(" "))
            lines.append(_Line(indent, line.strip()))
    return lines


def _parse_block(lines: List[_Line], idx: int, indent: int) -> (Node, int):
    """
    Parse a block starting at lines[idx] whose items are indented at >= `indent`.
    Returns (node, next_index). A block is either a mapping or a sequence.
    """
    if idx >= len(lines):
        return {}, idx

    is_seq = lines[idx].content.startswith("- ") or lines[idx].content == "-"

    if is_seq:
        return _parse_sequence(lines, idx, indent)
    return _parse_mapping(lines, idx, indent)


def _parse_mapping(lines: List[_Line], idx: int, indent: int) -> (Dict[str, Any], int):
    mapping: Dict[str, Any] = {}
    while idx < len(lines) and lines[idx].indent == indent:
        line = lines[idx]
        kv = _split_key_value(line.content)
        if kv is None:
            break
        key, val = kv
        if val == "":
            # Could be a nested mapping/sequence, or an empty value.
            if idx + 1 < len(lines) and lines[idx + 1].indent > indent:
                child, idx = _parse_block(lines, idx + 1, lines[idx + 1].indent)
                mapping[key] = child
                continue
            # nested block for a sequence at the SAME indent (block seq under key)
            if idx + 1 < len(lines) and lines[idx + 1].indent == indent \
                    and lines[idx + 1].content.startswith("-"):
                child, idx = _parse_sequence(lines, idx + 1, indent)
                mapping[key] = child
                continue
            mapping[key] = None
            idx += 1
        else:
            mapping[key] = _coerce(val)
            idx += 1
    return mapping, idx


def _parse_sequence(lines: List[_Line], idx: int, indent: int) -> (List[Any], int):
    seq: List[Any] = []
    while idx < len(lines) and lines[idx].indent == indent \
            and (lines[idx].content.startswith("- ") or lines[idx].content == "-"):
        line = lines[idx]
        rest = line.content[1:].strip()  # drop the leading '-'
        if rest == "":
            # item is a nested block on following lines
            if idx + 1 < len(lines) and lines[idx + 1].indent > indent:
                child, idx = _parse_block(lines, idx + 1, lines[idx + 1].indent)
                seq.append(child)
            else:
                seq.append(None)
                idx += 1
            continue

        if _split_key_value(rest) is not None:
            # sequence of mappings; first key sits on the dash line.
            # Treat the dash-content column as the mapping indent.
            item_indent = line.indent + 2
            # Build a temporary line for the first key at item_indent, then let
            # the mapping parser consume subsequent keys at the same indent.
            first = _Line(item_indent, rest)
            patched = [first] + lines[idx + 1:]
            mp, consumed = _parse_mapping(patched, 0, item_indent)
            # consumed counts within `patched`; -1 for the synthetic first line.
            idx = idx + 1 + (consumed - 1)
            seq.append(mp)
        else:
            seq.append(_coerce(rest))
            idx += 1
    return seq, idx


def _load_yaml_simple(path: Path) -> Dict[str, Any]:
    lines = _read_lines(path)
    if not lines:
        return {}
    root, _ = _parse_mapping(lines, 0, lines[0].indent)
    return root


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """Load config.yaml, preferring PyYAML but falling back to a simple parser."""
    if not path.is_file():
        log(f"Config file not found: {path}", "ERROR")
        log("Copy config.example.yaml to config.yaml and edit it.", "HINT")
        sys.exit(1)

    data = _load_yaml_pyyaml(path)
    if data is None:
        data = _load_yaml_simple(path)

    if not isinstance(data, dict):
        log("Top level of config.yaml must be a mapping.", "ERROR")
        sys.exit(1)
    return data


if __name__ == "__main__":
    import json

    cfg = load_config()
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
