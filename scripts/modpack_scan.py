#!/usr/bin/env python3
"""扫描 Minecraft Mod jar 的元数据、来源提示和快捷键。

用法：
  python modpack_scan.py [整合包目录或 mods 目录] [--report]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from io import BytesIO
import json
import re
import sys
from pathlib import Path
import tomllib
from urllib.parse import quote_plus
import zipfile


def http_urls(*values: object) -> list[str]:
    return list(dict.fromkeys(
        value for value in values
        if isinstance(value, str) and value.startswith(("https://", "http://"))
    ))


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
        "sourceUrls": [],
        "modId": "",
        "providedModIds": [],
        "name": "",
        "version": "",
        "environment": "both",
        "requiredDependencies": [],
        "declaredIncompatibilities": [],
        "sha1": "",
        "modrinthVersionLookup": "",
        "searchName": search_name,
        "modrinthSearch": f"https://modrinth.com/discover/mods?q={quote_plus(search_name)}",
        "curseForgeSearch": (
            "https://www.curseforge.com/minecraft/search"
            f"?class=mc-mods&page=1&pageSize=20&search={quote_plus(search_name)}&sortBy=relevancy"
        ),
        "description": "",
        "keybinds": [],
        "duplicateJars": [],
        "scanError": "",
    }
    try:
        with jar.open("rb") as stream:
            result["sha1"] = hashlib.file_digest(stream, "sha1").hexdigest()
        result["modrinthVersionLookup"] = (
            f"https://api.modrinth.com/v2/version_file/{result['sha1']}?algorithm=sha1"
        )
        with zipfile.ZipFile(jar) as zf:
            names = set(zf.namelist())
            forge_meta = next((p for p in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml") if p in names), "")
            if forge_meta:
                result["loader"] = "neoforge" if "neoforge" in forge_meta else "forge"
                text = zf.read(forge_meta).decode("utf-8-sig", errors="replace")
                data = tomllib.loads(text)
                mods = data.get("mods", [])
                mod = mods[0] if isinstance(mods, list) and mods else {}
                result["providedModIds"] = [
                    str(item["modId"]) for item in mods
                    if isinstance(item, dict) and item.get("modId")
                ]
                result["modId"] = str(mod.get("modId", ""))
                result["name"] = str(mod.get("displayName", ""))
                result["version"] = str(mod.get("version", ""))
                result["environment"] = "client" if data.get("clientSideOnly") is True else "both"
                result["description"] = re.sub(r"\s+", " ", str(mod.get("description", ""))).strip()
                result["sourceUrls"] = http_urls(
                    mod.get("displayURL"),
                    data.get("issueTrackerURL"),
                )
                dependency_groups = data.get("dependencies", {})
                dependencies = [
                    dependency
                    for mod_id in result["providedModIds"]
                    for dependency in dependency_groups.get(mod_id, [])
                ] if isinstance(dependency_groups, dict) else []
                for dependency in dependencies:
                    if not isinstance(dependency, dict) or not dependency.get("modId"):
                        continue
                    item = {
                        "modId": str(dependency["modId"]),
                        "version": str(dependency.get("versionRange", "")),
                        "side": str(dependency.get("side", "BOTH")).lower(),
                        "reason": str(dependency.get("reason", "")),
                    }
                    dependency_type = str(dependency.get("type", "")).lower()
                    required = dependency.get("mandatory", dependency_type in ("", "required"))
                    if required:
                        result["requiredDependencies"].append(item)
                    if dependency_type in ("incompatible", "discouraged"):
                        result["declaredIncompatibilities"].append(item | {"type": dependency_type})
            elif "fabric.mod.json" in names:
                result["loader"] = "fabric"
                data = json.loads(zf.read("fabric.mod.json").decode("utf-8-sig", errors="replace"))
                result["modId"] = data.get("id", "")
                result["providedModIds"] = [result["modId"]] if result["modId"] else []
                result["name"] = data.get("name", "")
                result["version"] = str(data.get("version", ""))
                result["environment"] = {"*": "both"}.get(data.get("environment"), data.get("environment", "both"))
                result["description"] = data.get("description", "")
                contact = data.get("contact", {}) if isinstance(data.get("contact"), dict) else {}
                result["sourceUrls"] = http_urls(contact.get("homepage"), contact.get("sources"), contact.get("issues"))
                for dependency_id, version in data.get("depends", {}).items():
                    result["requiredDependencies"].append({
                        "modId": dependency_id,
                        "version": version,
                        "side": result["environment"],
                        "reason": "",
                    })
                for field, dependency_type in (("breaks", "incompatible"), ("conflicts", "conflict")):
                    for dependency_id, version in data.get(field, {}).items():
                        result["declaredIncompatibilities"].append({
                            "modId": dependency_id,
                            "version": version,
                            "side": result["environment"],
                            "reason": "",
                            "type": dependency_type,
                        })
            elif "quilt.mod.json" in names:
                result["loader"] = "quilt"
                data = json.loads(zf.read("quilt.mod.json").decode("utf-8-sig", errors="replace"))
                q = data.get("quilt_loader", data)
                result["modId"] = q.get("id", "")
                result["providedModIds"] = [result["modId"]] if result["modId"] else []
                result["version"] = str(q.get("version", ""))
                metadata = q.get("metadata", {}) if isinstance(q.get("metadata"), dict) else {}
                result["name"] = metadata.get("name", "")
                result["description"] = metadata.get("description", "")
                contact = metadata.get("contact", {}) if isinstance(metadata.get("contact"), dict) else {}
                result["sourceUrls"] = http_urls(contact.get("homepage"), contact.get("sources"), contact.get("issues"))
                for dependency in q.get("depends", []):
                    if isinstance(dependency, dict) and dependency.get("id"):
                        result["requiredDependencies"].append({
                            "modId": str(dependency["id"]),
                            "version": dependency.get("versions", ""),
                            "side": "both",
                            "reason": str(dependency.get("reason", "")),
                        })
                for dependency in q.get("breaks", []):
                    if isinstance(dependency, dict) and dependency.get("id"):
                        result["declaredIncompatibilities"].append({
                            "modId": str(dependency["id"]),
                            "version": dependency.get("versions", ""),
                            "side": "both",
                            "reason": str(dependency.get("reason", "")),
                            "type": "incompatible",
                        })
            result["homepage"] = result["sourceUrls"][0] if result["sourceUrls"] else ""
            result["keybinds"] = keybinds_from_zip(zf, real_bindings or {})
            result["sourceHint"] = source_hint(" ".join(result["sourceUrls"]), jar.name)
    except (
        OSError,
        AttributeError,
        TypeError,
        zipfile.BadZipFile,
        json.JSONDecodeError,
        tomllib.TOMLDecodeError,
    ) as exc:
        result["scanError"] = f"无法读取元数据（{type(exc).__name__}）"
    if not result["modId"]:
        result["modId"] = clean_name(jar.name).lower().replace(" ", "_")
    if not result["providedModIds"]:
        result["providedModIds"] = [result["modId"]]
    if not result["name"]:
        result["name"] = clean_name(jar.name)
    return result


def source_hint(homepage: str, filename: str) -> str:
    text = f"{homepage} {filename}".lower()
    if "modrinth" in text:
        return "modrinth"
    if "curseforge" in text:
        return "curseforge"
    if "github" in text:
        return "github"
    return "unknown"


def read_options_keybinds(root: Path) -> dict[str, str]:
    options = root / "options.txt"
    if not options.exists():
        return {}
    bindings = {}
    for line in options.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        name, sep, value = line.partition(":")
        if not sep or not name.startswith("key_"):
            continue
        key = name.removeprefix("key_")
        if value and value != "0" and not value.startswith("key.keyboard.unknown"):
            bindings[key] = value
    return bindings


def read_lang_file(zf: zipfile.ZipFile, entry: str) -> dict:
    text = zf.read(entry).decode("utf-8-sig", errors="replace")
    if entry.endswith(".json"):
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    data = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key and not key.lstrip().startswith("#"):
            data[key.strip()] = value.strip()
    return data


def keybinds_from_zip(zf: zipfile.ZipFile, real_bindings: dict[str, str]) -> list[dict]:
    found = {}
    for lang in ("zh_cn", "en_us"):
        for entry in zf.namelist():
            if not re.match(rf"assets/.*/lang/{lang}\.(?:json|lang)$", entry):
                continue
            try:
                data = read_lang_file(zf, entry)
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
                        "conflictsWith": [],
                    }
    dedup = []
    for item in found.values():
        if "categor" in item["key"].lower():
            continue
        dedup.append(item)
    return dedup


def is_keybind_key(key: str) -> bool:
    if key.startswith(("item.", "block.", "entity.", "tooltip.", "sound.", "advancements.", "gui.")):
        return False
    return key.startswith(("key.", "keybind.", "create.keyinfo.", "artifacts.key.")) or ".key." in key


def mark_conflicts(rows: list[dict], real_bindings: dict[str, str]) -> None:
    users = {}
    for key, binding in real_bindings.items():
        users.setdefault(binding, []).append(key)
    for row in rows:
        for item in row["keybinds"]:
            item["conflictsWith"] = [
                key for key in users.get(item["binding"], [])
                if key != item["key"]
            ]
            item["conflict"] = bool(item["conflictsWith"])


def normalize_root(root: Path) -> Path:
    root = root.expanduser()
    return root.parent if root.name.lower() == "mods" and root.is_dir() else root


def detect_pack_environment(root: Path) -> dict:
    root = normalize_root(root)
    result = {"minecraftVersion": "", "loader": "", "loaderVersion": "", "source": ""}
    for filename in ("modrinth.index.json", "manifest.json", "mmc-pack.json", "minecraftinstance.json"):
        path = root / filename
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        if filename == "modrinth.index.json":
            dependencies = data.get("dependencies", {})
            dependencies = dependencies if isinstance(dependencies, dict) else {}
            result["minecraftVersion"] = str(dependencies.get("minecraft", ""))
            for key in ("neoforge", "forge", "fabric-loader", "quilt-loader"):
                if key in dependencies:
                    result["loader"] = key.removesuffix("-loader")
                    result["loaderVersion"] = str(dependencies[key])
                    break
        elif filename == "manifest.json":
            minecraft = data.get("minecraft", {})
            minecraft = minecraft if isinstance(minecraft, dict) else {}
            result["minecraftVersion"] = str(minecraft.get("version", ""))
            loaders = minecraft.get("modLoaders", [])
            loader_id = str(loaders[0].get("id", "")) if loaders and isinstance(loaders[0], dict) else ""
            if "-" in loader_id:
                result["loader"], result["loaderVersion"] = loader_id.split("-", 1)
        elif filename == "mmc-pack.json":
            components = {
                item.get("uid"): str(item.get("version", ""))
                for item in data.get("components", [])
                if isinstance(item, dict)
            }
            result["minecraftVersion"] = components.get("net.minecraft", "")
            for uid, loader in (
                ("net.neoforged", "neoforge"),
                ("net.minecraftforge", "forge"),
                ("net.fabricmc.fabric-loader", "fabric"),
                ("org.quiltmc.quilt-loader", "quilt"),
            ):
                if uid in components:
                    result["loader"] = loader
                    result["loaderVersion"] = components[uid]
                    break
        else:
            result["minecraftVersion"] = str(data.get("gameVersion", ""))
            base_loader = data.get("baseModLoader", {})
            base_loader = base_loader if isinstance(base_loader, dict) else {}
            loader_id = str(base_loader.get("name", ""))
            if "-" in loader_id:
                result["loader"], result["loaderVersion"] = loader_id.split("-", 1)
        result["source"] = filename
        if result["minecraftVersion"] or result["loader"]:
            break
    return result


def scan(root: Path) -> list[dict]:
    root = normalize_root(root)
    mods = root / "mods"
    if not mods.is_dir():
        raise SystemExit(f"未找到 mods 目录：{mods}")
    real_bindings = read_options_keybinds(root)
    rows = [metadata_from_jar(path, real_bindings) for path in sorted(mods.glob("*.jar"), key=lambda p: p.name.lower())]
    deduped = []
    seen = {}
    for row in rows:
        key = (row.get("modId") or row["searchName"]).lower()
        if key in seen:
            seen[key]["duplicateJars"].append(row["jar"])
            continue
        seen[key] = row
        deduped.append(row)
    mark_conflicts(deduped, real_bindings)
    return deduped


def analyze(rows: list[dict], environment: dict | None = None) -> dict:
    environment = environment or {}
    platform_ids = {"minecraft", "java", "forge", "neoforge", "fabricloader", "quilt_loader"}
    installed = {
        mod_id.lower()
        for row in rows
        for mod_id in row.get("providedModIds", [row["modId"]])
    }
    issues = []
    if not rows:
        issues.append({
            "severity": "错误",
            "type": "empty-mods",
            "mods": [],
            "message": "mods 目录中没有可扫描的 jar。",
        })
    providers = {}
    for row in rows:
        for mod_id in row.get("providedModIds", [row["modId"]]):
            providers.setdefault(mod_id.lower(), []).append(row["name"])
    for mod_id, names in providers.items():
        if len(names) > 1:
            issues.append({
                "severity": "错误",
                "type": "duplicate-mod-id",
                "mods": names,
                "message": f"多个 jar 同时提供 modId {mod_id}：{', '.join(names)}",
            })
    loaders = sorted({row["loader"] for row in rows if row["loader"] != "unknown"})
    if len(loaders) > 1:
        issues.append({
            "severity": "警告",
            "type": "mixed-loaders",
            "mods": [],
            "message": f"检测到多种加载器元数据：{', '.join(loaders)}；请确认是否使用了兼容层或放错 jar。",
        })
    pack_loader = environment.get("loader", "")
    mismatched = [
        row["name"] for row in rows
        if pack_loader and row["loader"] not in ("unknown", pack_loader)
    ]
    if mismatched:
        issues.append({
            "severity": "错误" if pack_loader in ("forge", "neoforge") else "警告",
            "type": "loader-mismatch",
            "mods": mismatched,
            "message": f"整合包加载器为 {pack_loader}，但以下 jar 元数据不匹配：{', '.join(mismatched)}",
        })
    for row in rows:
        if row["scanError"]:
            issues.append({
                "severity": "警告",
                "type": "scan-error",
                "mods": [row["name"]],
                "message": f"{row['jar']}：{row['scanError']}",
            })
        if row["duplicateJars"]:
            issues.append({
                "severity": "错误",
                "type": "duplicate-mod",
                "mods": [row["name"]],
                "message": f"同一 modId 出现多个 jar：{row['jar']}, {', '.join(row['duplicateJars'])}",
            })
        for dependency in row["requiredDependencies"]:
            dependency_id = dependency["modId"].lower()
            if dependency_id not in platform_ids and dependency_id not in installed:
                issues.append({
                    "severity": "警告",
                    "type": "missing-dependency",
                    "mods": [row["name"], dependency["modId"]],
                    "message": (
                        f"{row['name']} 声明需要 {dependency['modId']}"
                        f" {dependency['version']}，当前 mods 目录未识别到；需确认是否为内嵌前置。"
                    ).strip(),
                })
        for conflict in row["declaredIncompatibilities"]:
            if conflict["modId"].lower() in installed:
                issues.append({
                    "severity": "错误" if conflict["type"] == "incompatible" else "警告",
                    "type": "declared-incompatibility",
                    "mods": [row["name"], conflict["modId"]],
                    "message": (
                        f"{row['name']} 声明与 {conflict['modId']} {conflict['type']}。"
                        f" {conflict['reason']}"
                    ).strip(),
                })
    seen_bindings = set()
    for row in rows:
        for item in row["keybinds"]:
            if not item["conflict"] or item["binding"] in seen_bindings:
                continue
            seen_bindings.add(item["binding"])
            users = sorted({item["key"], *item["conflictsWith"]})
            issues.append({
                "severity": "提示",
                "type": "keybind-conflict",
                "mods": [row["name"]],
                "message": f"{item['binding']} 同时绑定：{', '.join(users)}",
            })
    severity_order = {"错误": 0, "警告": 1, "提示": 2}
    issues.sort(key=lambda item: (severity_order[item["severity"]], item["type"], item["message"]))
    return {
        "summary": {
            "modCount": len(rows),
            "loaders": loaders,
            "minecraftVersion": environment.get("minecraftVersion", ""),
            "loader": pack_loader,
            "loaderVersion": environment.get("loaderVersion", ""),
            "issueCount": len(issues),
            "blockingIssueCount": sum(item["severity"] == "错误" for item in issues),
        },
        "issues": issues,
        "mods": rows,
    }


def self_check() -> None:
    assert clean_name("Argentina's delight 1.20.1 (3.0 beta).jar") == "Argentina's delight"
    assert clean_name("example-mod-neoforge-1.21.1-2.4.0.jar") == "example-mod"
    assert source_hint("https://curseforge.com https://modrinth.com", "example.jar") == "modrinth"
    parsed = tomllib.loads("[[mods]]\nmodId='demo'\ndescription='''第一行\n第二行'''\n")
    assert parsed["mods"][0]["description"] == "第一行\n第二行"
    jar = BytesIO()
    with zipfile.ZipFile(jar, "w") as zf:
        zf.writestr("assets/demo/lang/zh_cn.json", json.dumps({"key.demo.open": "打开"}))
        zf.writestr("assets/demo/lang/en_us.json", json.dumps({"key.demo.open": "Open", "key.demo.mode": "Mode"}))
        zf.writestr("assets/legacy/lang/en_us.lang", "key.demo.legacy=Legacy\n")
    with zipfile.ZipFile(jar) as zf:
        keys = keybinds_from_zip(zf, {"key.demo.open": "key.keyboard.g"})
    assert [(item["key"], item["binding"]) for item in keys] == [
        ("key.demo.open", "key.keyboard.g"),
        ("key.demo.mode", "未绑定"),
        ("key.demo.legacy", "未绑定"),
    ]
    rows = [{"keybinds": [keys[0]]}]
    mark_conflicts(rows, {
        "key.demo.open": "key.keyboard.g",
        "key.attack": "key.keyboard.g",
    })
    assert keys[0]["conflictsWith"] == ["key.attack"]
    sample = {
        "loader": "fabric",
        "providedModIds": ["demo"],
        "modId": "demo",
        "name": "Demo",
        "jar": "demo.jar",
        "scanError": "",
        "duplicateJars": [],
        "requiredDependencies": [{
            "modId": "missing-lib",
            "version": ">=1",
            "side": "both",
            "reason": "",
        }],
        "declaredIncompatibilities": [],
        "keybinds": [],
    }
    report = analyze([sample], {"loader": "fabric", "minecraftVersion": "1.20.1"})
    assert report["issues"][0]["type"] == "missing-dependency"
    assert report["summary"]["minecraftVersion"] == "1.20.1"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="扫描 Minecraft 整合包中的 Mod、来源和快捷键")
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd(), help="整合包目录或 mods 目录，默认当前目录")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="只输出 Mod 清单 JSON")
    output.add_argument("--report", action="store_true", help="输出可运行性与冲突分析报告 JSON")
    parser.add_argument("--self-check", action="store_true", help="运行内置自检")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        print("自检通过")
        return
    rows = scan(args.root)
    if args.report:
        print(json.dumps(analyze(rows, detect_pack_environment(args.root)), ensure_ascii=False, indent=2))
        return
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    writer = csv.DictWriter(sys.stdout, fieldnames=["jar", "loader", "sourceHint", "modId", "name", "description", "keybind_count"])
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in ("jar", "loader", "sourceHint", "modId", "name", "description")} | {"keybind_count": len(row["keybinds"])})


if __name__ == "__main__":
    main()
