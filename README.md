# Minecraft Modpack Assistant

一个用于分析 Minecraft 整合包并生成中文游玩指南的 Codex Skill。

## 能做什么

- 扫描 `mods/*.jar`，读取 Forge/Fabric/Quilt 元数据。
- 区分加载器和来源提示，例如 CurseForge、Modrinth、GitHub。
- 从 jar 文件名提取干净的 Mod 搜索名，例如把 `Argentina's delight 1.20.1 (3.0 beta).jar` 识别为 `Argentina's delight`。
- 提取 Mod 声明的快捷键名称，并读取客户端 `options.txt` 中的真实快捷键绑定。
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

## Mod 索引简介规则

- 使用清洗后的 jar 名称进入 CurseForge 搜索。
- 如果出现多个结果，默认取第一个，除非本地元数据提供了更准确的页面。
- 每个 Mod 独立介绍，不把多个 Mod 合并成整合包攻略。
- 尽量保留原 Mod 页面的介绍结构。
- 提取简介、重要物品、按键、交互逻辑等原始信息。
- 英文内容统一翻译为中文，名称、命令、物品 ID、按键 ID 和版本号保持原样。
- 重复扫描时避免重复说明；共享机制只在基础 Mod 中说明一次。

## 快捷键规则

真实绑定只来自客户端 `options.txt` 的 `key_...:key.keyboard...` 行。

如果没有检测到真实绑定，应显示：

- `未绑定`
- Mod 声明的快捷键名称

## 安全原则

- 不删除、移动或修改 `mods/` 内的 jar 文件。
- 生成的 HTML 指南可重复生成；Mod jar 和本地配置是源输入。
- CurseForge/Modrinth/GitHub 是来源提示，不是加载器。
