#!/usr/bin/env python3
"""扫描 Minecraft Mod jar 的元数据、来源提示和快捷键。

用法：
  python modpack_scan.py [整合包目录或 mods 目录] [--json]
"""
from __future__ import annotations

import argparse
import csv
from io import BytesIO
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
    name = re.sub(
        r"\s*[\[（(][^\]）)]*(?:\d|forge|neoforge|fabric|quilt|alpha|beta|release|snapshot)[^\]）)]*[\]）)]\s*$",
        "",
        name,
        flags=re.I,
    )
    suffix = re.compile(
        r"(?:[-_+ ]+(?:(?:mc)?v?\d+(?:\.\d+)+(?:[-+._a-z0-9]*)?|neoforge|forge|fabric|quilt|alpha|beta|release|snapshot|client|server))$",
        re.I,
    )
    while suffix.search(name):
        name = suffix.sub("", name)
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
            forge_meta = next((p for p in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml") if p in names), "")
            if forge_meta:
                result["loader"] = "neoforge" if "neoforge" in forge_meta else "forge"
                text = zf.read(forge_meta).decode("utf-8", errors="replace")
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
    found = {}
    for lang in ("zh_cn", "en_us"):
        for entry in zf.namelist():
            if not re.match(rf"assets/.*/lang/{lang}\.json$", entry):
                continue
            try:
                data = json.loads(zf.read(entry).decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            for key, label in data.items():
                if key not in found and is_keybind_key(key) and isinstance(label, str) and "\n" not in label:
                    found[key] = {
                        "key": key,
                        "label": label,
                        "declaredName": label,
                        "binding": real_bindings.get(key, "未绑定"),
                        "lang": lang,
                        "conflict": False,
                    }
    dedup = []
    for item in found.values():
        if "categor" in item["key"].lower():
            continue
        dedup.append(item)
    return dedup[:12]


def is_keybind_key(key: str) -> bool:
    if key.startswith(("item.", "block.", "entity.", "tooltip.", "sound.", "advancements.", "gui.")):
        return False
    return key.startswith(("key.", "keybind.", "create.keyinfo.", "artifacts.key.")) or ".key." in key


def scan(root: Path) -> list[dict]:
    root = root.expanduser()
    if root.name.lower() == "mods" and root.is_dir():
        root = root.parent
    mods = root / "mods"
    if not mods.exists():
        raise SystemExit(f"未找到 mods 目录：{mods}")
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
    bindings = {}
    for row in deduped:
        for item in row["keybinds"]:
            if item["binding"] != "未绑定":
                bindings.setdefault(item["binding"], []).append(item)
    for items in bindings.values():
        if len(items) > 1:
            for item in items:
                item["conflict"] = True
    return deduped


def self_check() -> None:
    assert clean_name("Argentina's delight 1.20.1 (3.0 beta).jar") == "Argentina's delight"
    assert clean_name("example-mod-neoforge-1.21.1-2.4.0.jar") == "example-mod"
    assert source_hint("https://modrinth.com/mod/example", "example.jar") == "modrinth"
    jar = BytesIO()
    with zipfile.ZipFile(jar, "w") as zf:
        zf.writestr("assets/demo/lang/zh_cn.json", json.dumps({"key.demo.open": "打开"}))
        zf.writestr("assets/demo/lang/en_us.json", json.dumps({"key.demo.open": "Open", "key.demo.mode": "Mode"}))
    with zipfile.ZipFile(jar) as zf:
        keys = keybinds_from_zip(zf, {"key.demo.open": "key.keyboard.g"})
    assert [(item["key"], item["binding"]) for item in keys] == [
        ("key.demo.open", "key.keyboard.g"),
        ("key.demo.mode", "未绑定"),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="扫描 Minecraft 整合包中的 Mod、来源和快捷键")
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd(), help="整合包目录或 mods 目录，默认当前目录")
    parser.add_argument("--json", action="store_true", help="输出 UTF-8 JSON")
    parser.add_argument("--self-check", action="store_true", help="运行内置自检")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        print("自检通过")
        return
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
