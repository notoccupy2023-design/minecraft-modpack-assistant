# 我的世界整合包助手

一个面向 Codex 的中文 Skill：扫描本地 Minecraft 整合包，生成 Mod 索引、可运行性与冲突报告，并据此制作可离线打开的中文游玩指南。

## 主要能力

- 读取 Forge、NeoForge、Fabric、Quilt jar 元数据。
- 从 jar 文件名清除游戏版本、Mod 版本、加载器和发布阶段后缀。
- 计算每个 jar 的 SHA-1，生成 Modrinth 精确版本查询地址。
- 生成 Modrinth 和 CurseForge 的 Mod 分类搜索地址。
- 读取 Mod 版本、运行环境、必需前置和元数据声明的不兼容项。
- 识别重复 jar、重复 modId、加载器混用、缺失前置和损坏元数据。
- 读取 `options.txt` 的真实绑定，并从新旧语言文件补充 Mod 声明的快捷键名称。
- 结合日志、官方资料与整合配置分析已知冲突、玩法重叠和进度风险。
- 生成简体中文、UTF-8、单文件离线 HTML 指南。

## 来源优先级

- 首选：使用 jar SHA-1 查询 Modrinth 精确版本。
- 次选：在 Modrinth 中按 Mod 类型、Minecraft 版本和加载器搜索。
- 补充：采用 jar 元数据中的精确项目主页。
- 回退：搜索 CurseForge 的 Mod 分类；多个结果默认取第一个，并核对版本与加载器。
- 已知问题：继续核对作者 issue tracker、官方 Wiki 和版本化说明。

扫描脚本本身保持离线，不会自动请求外部平台。它负责输出 SHA-1、`modrinthVersionLookup`、`modrinthSearch` 和 `curseForgeSearch`；联网检索与中文整理由 Skill 工作流执行。

## 冲突分析

报告按影响顺序组织：

- **可运行性阻断**：加载器不匹配、重复 modId、缺失必需前置、明确声明不兼容、空 `mods` 目录。
- **实际故障**：优先分析 `logs/latest.log` 和 `crash-reports/` 中的首个根因。
- **已知不兼容**：核对 Modrinth 精确版本依赖、作者 issue 和官方说明，保留冲突双方、版本、现象、处理方式与来源。
- **玩法重叠/平衡风险**：检查地图、配方查看器、背包/存储、墓碑、连锁挖掘、世界生成、经济、难度和任务进度等高影响重叠组。
- **操作提示**：按键冲突和未绑定功能放在最后，不盖过启动与玩法问题。

功能相似不等于冲突。没有版本匹配或可靠来源时，只能标记为“高风险”或“需关注”，不能写成已知问题。

## 环境要求

- Python 3.11 或更高版本。
- 仅使用 Python 标准库，无需安装额外依赖。
- 整合包根目录至少包含 `mods/`。

可选输入：

```text
options.txt
config/
defaultconfigs/
manifest.json
modrinth.index.json
mmc-pack.json
minecraftinstance.json
logs/latest.log
crash-reports/
kubejs/
scripts/
```

## 快速使用

在本仓库目录运行：

```powershell
python scripts/modpack_scan.py --self-check
python scripts/modpack_scan.py "D:\Minecraft\Instances\示例整合包" --report
```

也可以直接传入 `mods` 目录；省略路径时扫描当前目录。

保存 UTF-8 报告：

```powershell
chcp 65001
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
python scripts/modpack_scan.py "D:\Minecraft\Instances\示例整合包" --report | Set-Content -Encoding UTF8 scan-report.json
```

## 命令参数

| 参数 | 作用 |
| --- | --- |
| `--report` | 输出摘要、阻断/警告/提示以及完整 Mod 数据 |
| `--json` | 只输出去重后的 Mod 清单 |
| `--self-check` | 验证名称清洗、TOML、语言文件、按键和报告逻辑 |
| 无参数 | 输出便于快速查看的 CSV |

`--report` 的主要结构：

```json
{
  "summary": {
    "modCount": 0,
    "minecraftVersion": "1.20.1",
    "loader": "forge",
    "issueCount": 0,
    "blockingIssueCount": 0
  },
  "issues": [],
  "mods": []
}
```

## Mod 索引规则

- 每个 Mod 独立介绍，尽量保持原项目页的信息结构。
- 提取简介、重要物品/方块/实体、控制、交互方式、前置和版本化兼容说明。
- 英文内容翻译成简体中文；专名、命令、ID、键名和版本号保持原样。
- 基础机制只在基础 Mod 中解释一次，附属卡片只写自己的新增内容。
- 库/API 使用“无需操作；后台前置”。
- 没有真实按键绑定时显示 `未绑定`，并保留 Mod 声明的快捷键名称。

## 安全原则

- 不删除、移动或修改 `mods/` 内的 jar。
- 不自动修改玩家配置或按键。
- 不把论坛猜测写成已知冲突。
- 生成的 HTML 和 JSON 是输出物；jar、本地配置、任务与脚本是事实来源。

Skill 的完整执行规则见 [SKILL.md](SKILL.md)，HTML 与内容规范见 [references/guide-pattern.md](references/guide-pattern.md)。
