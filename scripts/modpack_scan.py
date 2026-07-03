#!/usr/bin/env python3
"""Scan Minecraft mod jars for metadata and declared keybind labels.

Usage:
  python modpack_scan.py <modpack-root> [--json]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from urllib.parse import quote_plus
import zipfile
from pathlib import Path


def read_toml_value(text: str, key: str) -> str:
    m = re.search(rf'(?m)^\s*{re.escape(key)}\s*=\s*"([^"]*)"', text)
    return m.group(1) if m else ""


def read_triple_toml_value(text: str, key: str) -> str:
    m = re.search(rf'(?ms)^\s*{re.escape(key)}\s*=\s*"""(.*?)"""', text)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def clean_name(filename: str) -> str:
    name = re.sub(r"\.jar$", "", filename, flags=re.I)
    name = re.sub(r"[\[\]（）()]", " ", name)
    name = re.sub(r"[-_+]?(forge|fabric|mc)?v?\d[\w.\-+ ]*$", "", name, flags=re.I)
    return re.sub(r"\s+", " ", name).strip(" -_") or filename


def metadata_from_jar(jar: Path, real_bindings: dict[str, str] | None = None) -> dict:
    search_name = clean_name(jar.name)
    result = {
        "jar": jar.name,
        "loader": "unknown",
        "sourceHint": "unknown",
        "homepage": "",
        "modId": "",
        "name": "",
        "searchName": search_name,
        "curseForgeSearch": f"https://www.curseforge.com/minecraft/search?search={quote_plus(search_name)}",
        "description": "",
        "keybinds": [],
    }
    try:
        with zipfile.ZipFile(jar) as zf:
            names = set(zf.namelist())
            if "META-INF/mods.toml" in names:
                result["loader"] = "forge"
                text = zf.read("META-INF/mods.toml").decode("utf-8", errors="replace")
                first = text.split("[[dependencies.", 1)[0]
                result["modId"] = read_toml_value(first, "modId")
                result["name"] = read_toml_value(first, "displayName")
                result["description"] = read_triple_toml_value(first, "description") or read_toml_value(first, "description")
                result["homepage"] = read_toml_value(first, "displayURL")
            elif "fabric.mod.json" in names:
                result["loader"] = "fabric"
                data = json.loads(zf.read("fabric.mod.json").decode("utf-8", errors="replace"))
                result["modId"] = data.get("id", "")
                result["name"] = data.get("name", "")
                result["description"] = data.get("description", "")
                result["homepage"] = data.get("contact", {}).get("homepage", "") if isinstance(data.get("contact"), dict) else ""
            elif "quilt.mod.json" in names:
                result["loader"] = "quilt"
                data = json.loads(zf.read("quilt.mod.json").decode("utf-8", errors="replace"))
                q = data.get("quilt_loader", data)
                result["modId"] = q.get("id", "")
                result["name"] = q.get("metadata", {}).get("name", "")
                result["description"] = q.get("metadata", {}).get("description", "")
                result["homepage"] = q.get("metadata", {}).get("contact", {}).get("homepage", "") if isinstance(q.get("metadata", {}).get("contact"), dict) else ""
            result["keybinds"] = keybinds_from_zip(zf, real_bindings or {})
            result["sourceHint"] = source_hint(result["homepage"], jar.name)
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError):
        pass
    if not result["modId"]:
        result["modId"] = clean_name(jar.name).lower().replace(" ", "_")
    if not result["name"]:
        result["name"] = clean_name(jar.name)
    return result


def source_hint(homepage: str, filename: str) -> str:
    text = f"{homepage} {filename}".lower()
    if "curseforge" in text:
        return "curseforge"
    if "modrinth" in text:
        return "modrinth"
    if "github" in text:
        return "github"
    return "unknown"


def read_options_keybinds(root: Path) -> dict[str, str]:
    options = root / "options.txt"
    if not options.exists():
        return {}
    bindings = {}
    for line in options.read_text(encoding="utf-8", errors="replace").splitlines():
        name, sep, value = line.partition(":")
        if not sep or not name.startswith("key_"):
            continue
        key = name.removeprefix("key_")
        if value and value != "key.keyboard.unknown":
            bindings[key] = value
    return bindings


def keybinds_from_zip(zf: zipfile.ZipFile, real_bindings: dict[str, str]) -> list[dict]:
    found = []
    for lang in ("zh_cn", "en_us"):
        for entry in zf.namelist():
            if not re.match(rf"assets/.*/lang/{lang}\.json$", entry):
                continue
            try:
                data = json.loads(zf.read(entry).decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            for key, label in data.items():
                if is_keybind_key(key) and isinstance(label, str) and "\n" not in label:
                    found.append({
                        "key": key,
                        "label": label,
                        "declaredName": label,
                        "binding": real_bindings.get(key, "未绑定"),
                        "lang": lang,
                    })
        if found:
            break
    dedup = []
    seen = set()
    for item in found:
        if item["key"] in seen or "categor" in item["key"].lower():
            continue
        seen.add(item["key"])
        dedup.append(item)
    return dedup[:12]


def is_keybind_key(key: str) -> bool:
    if key.startswith(("item.", "block.", "entity.", "tooltip.", "sound.", "advancements.", "gui.")):
        return False
    return key.startswith(("key.", "keybind.", "create.keyinfo.", "artifacts.key.")) or ".key." in key


def scan(root: Path) -> list[dict]:
    mods = root / "mods"
    if not mods.exists():
        raise SystemExit(f"mods folder not found: {mods}")
    real_bindings = read_options_keybinds(root)
    rows = [metadata_from_jar(path, real_bindings) for path in sorted(mods.glob("*.jar"), key=lambda p: p.name.lower())]
    deduped = []
    seen = set()
    for row in rows:
        key = (row.get("modId") or row["searchName"]).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rows = scan(args.root)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    writer = csv.DictWriter(sys.stdout, fieldnames=["jar", "loader", "sourceHint", "modId", "name", "description", "keybind_count"])
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in ("jar", "loader", "sourceHint", "modId", "name", "description")} | {"keybind_count": len(row["keybinds"])})


if __name__ == "__main__":
    main()
