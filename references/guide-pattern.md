# Minecraft Modpack Guide Pattern

## Local Inputs

- `mods/*.jar`: primary inventory.
- `options.txt`: only useful for real keybinds if it contains `key_...` lines.
- `config/` and `defaultconfigs/`: useful for mod behavior, rarely for keybinds.
- Existing generated HTML: visual target only; update the generator when possible.

## Metadata Extraction

Distinguish loader from source. Forge/Fabric/Quilt are loaders. CurseForge/Modrinth/GitHub are source or hosting hints.

For Forge jars, read `META-INF/mods.toml` and capture the first mod block before dependencies. Useful fields: `modId`, `displayName`, `description`, `displayURL`, `issueTrackerURL`.

For Fabric/Quilt jars, parse `fabric.mod.json` or `quilt.mod.json` and capture `id`, `name`, `description`, `contact.homepage` if present.

If metadata is missing, derive a readable name from the jar filename and mark confidence low in internal reasoning; do not expose uncertainty noisily unless it affects the guide.

## Loader and Source Hints

Detect loader from metadata files: `META-INF/mods.toml` means Forge, `fabric.mod.json` means Fabric, and `quilt.mod.json` means Quilt. Detect source hints from `displayURL`, Fabric/Quilt contact homepage, or known domains in filenames/metadata. Use `curseforge`, `modrinth`, `github`, or `unknown`. Do not label CurseForge as a loader.

## Keybind Extraction

Read `assets/*/lang/zh_cn.json` first, then `en_us.json`. Candidate key labels usually start with:

- `key.`
- `keybind.`
- mod-specific key namespaces such as `create.keyinfo.` or `artifacts.key.`

Filter out item/block/entity/tooltip/advancement text. Labels containing `%s` are often UI templates, not direct keybind names; include only when useful.

If no matching real binding is found in client `options.txt`, show the binding as `未绑定` and still show the mod-declared keybind name.

## HTML UX Pattern

Keep the HTML offline and self-contained:

- inline CSS and JS;
- responsive cards;
- sticky top navigation;
- search input plus category chips;
- no external fonts or runtime dependencies.

Recommended nav:

1. 推荐路线
2. 核心玩法
3. 操作手册
4. mod 索引
5. 资料来源

## Card Content Policy

Write for “how to play”, not just “what it is”. Each card should answer:

- What does this mod add to the pack?
- What item, block, UI, or key should the player use first?
- How does it connect to the pack route?

Libraries and APIs should be terse: “无需操作；后台前置。”

## Verification

After regenerating:

- Confirm UTF-8 meta tag exists.
- Confirm card count matches unique modIds if duplicates are merged.
- Confirm JS parses with `new Function(script)`.
- Spot-check search terms that previously overmatched.
- Spot-check first 10 cards are gameplay-relevant, not libraries.
