---
name: minecraft-modpack-assistant
description: Build Chinese Minecraft modpack guides and mod indexes from a local mods folder. Use when the user asks Codex to analyze Minecraft Forge/Fabric/Quilt mod jars, detect loader and source hints such as CurseForge or Modrinth, identify mod names, create or update a UTF-8 offline HTML guide, add gameplay routes, keybind/control tables, mod cards, sorting/filtering/search logic, or maintain project handoff docs for a Minecraft modpack guide.
---

# Minecraft Modpack Assistant

Use this skill to turn a Minecraft modpack folder into a practical Chinese guide, not a raw mod dump.

## Workflow

1. Inspect the project first: list `mods/`, check for `options.txt`, `config/`, existing generator scripts, HTML output, and `AGENTS.md`.
2. Extract mod facts from jar metadata before guessing names. Prefer `META-INF/mods.toml`, then `fabric.mod.json`/`quilt.mod.json`, then filename fallback.
3. Detect loader separately from source: Forge/Fabric/Quilt are loaders; CurseForge/Modrinth/GitHub are source or hosting hints.
4. Use `scripts/modpack_scan.py` when a fresh mod inventory, loader/source summary, or keybind declaration list is needed.
5. Build/update a local generator script in the target project when the guide must be regenerated repeatedly. Keep the generated HTML as an output artifact, not the source of truth.
6. Generate one UTF-8 offline HTML file with inline CSS/JS unless the user asks otherwise.
7. Verify after changes: regenerate HTML, check card counts, and run a JS syntax check on the embedded script.

## Guide Content

Include these sections when producing a full guide:

- Recommended route: early/mid/late/long-term progression.
- Core gameplay: the few actions that define the pack.
- Operation manual: shortcut tables and practical steps in one navigation entry.
- Mod index: searchable/filterable cards.
- Sources: MC??, CurseForge/Modrinth/GitHub hints, loader, and local jar metadata notes.

For each mod card, prefer this structure:

- Chinese title.
- `Original: ... ? modId: ...` metadata, localized if the target page is Chinese.
- Short Chinese description.
- Key items / keys.
- Mod-declared keys, only when detected.
- How to use and advice in the same block.
- Loader/source note when helpful.
- Jar filename and external links.

For mod index descriptions:

- Build the search name from the jar filename by stripping Minecraft versions, mod versions, loader suffixes, and beta/release tags; for example `Argentina's delight 1.20.1 (3.0 beta).jar` becomes `Argentina's delight`.
- Search CurseForge with that cleaned name. If several results appear, use the first result unless local metadata gives a verified exact page.
- Keep every mod independent. Preserve the original mod page's description structure instead of summarizing the whole pack into攻略.
- Extract description, important items/blocks/entities, keys, controls, and interaction logic when present.
- Translate English source content into Chinese while keeping names, commands, item IDs, key IDs, and version numbers unchanged.
- Avoid repeated explanations across cards; describe shared mechanics once, then keep addon cards focused on their own additions.

## Sorting and Search

Prioritize actual gameplay mods over libraries:

1. Main pack theme and core helpers, e.g. Farmer's Delight, JEI, Jade, AppleSkin.
2. Kitchen/food addons.
3. Automation, storage, maps, transport, exploration, dimensions.
4. Decoration, ecology, helper UX.
5. Performance mods.
6. Libraries and APIs last.

Keep search narrow enough to avoid false positives. Index names, modId, jar filename, category, and short description. Do not index generic advice text unless the user explicitly wants full-text search.

## Keybinds

- Read complete client `options.txt` first. Real bindings appear as `key_...:key.keyboard...` lines.
- If `options.txt` lacks key lines, say so and fall back to jar language-file key declarations plus common defaults.
- Many jars declare keybind labels but not the bound key. Show these as unbound / check Controls unless a real binding or known default is available.
- When no real binding is detected, display `未绑定` plus the mod-declared keybind name.
- Do not claim server-side or resource-pack-only `options.txt` contains real client keybinds.

## Sources and Loader Detection

- Loader is detected from metadata files: `META-INF/mods.toml` => Forge, `fabric.mod.json` => Fabric, `quilt.mod.json` => Quilt.
- Source hints are detected from `displayURL`, Fabric/Quilt contact homepage, or filename/domain clues.
- CurseForge is not a loader. Treat it as a distribution/source hint.
- Use exact MC??, CurseForge, or Modrinth links only when verified or confidently mapped. Otherwise use search links.
- Summarize source facts in Chinese; do not copy long source text.

## Safety

- Do not delete, move, or modify files in `mods/` unless explicitly requested.
- Never batch-delete files or directories.
- Preserve existing user artifacts; generated HTML can be regenerated, but mod jars are source inputs.

## References

Read `references/guide-pattern.md` when implementing or revising HTML structure, loader/source display, sorting rules, or card content policy.
