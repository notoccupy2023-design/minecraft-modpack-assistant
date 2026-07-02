# Minecraft Modpack Assistant

一个用于分析 Minecraft 整合包并生成中文游玩指南的 Codex Skill。

## 能做什么

- 扫描 `mods/*.jar`，读取 Forge/Fabric/Quilt 元数据。
- 区分加载器和来源提示，例如 CurseForge、Modrinth、GitHub。
- 提取 Mod 声明的快捷键名称。
- 读取客户端 `options.txt` 中的真实快捷键绑定。
- 生成面向玩家的中文整合包指南，包括推荐路线、操作手册、Mod 索引和资料来源。

## 快速使用

在 Codex 中处理 Minecraft 整合包项目时启用本 Skill。项目目录通常应包含：

```text
mods/
options.txt
config/
```

需要重新扫描 Mod 清单或快捷键声明时，可运行：

```powershell
python scripts/modpack_scan.py <整合包目录> --json
```
