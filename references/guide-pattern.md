# 我的世界整合包指南规则

## 本地输入

- `mods/*.jar`：Mod 清单和元数据主来源。
- `options.txt`：只在包含 `key_...` 行时作为真实按键来源。
- `config/`、`defaultconfigs/`：判断整合包实际修改后的行为。
- `manifest.json`、启动器实例配置：判断 Minecraft、加载器和整合包版本。
- 任务配置、脚本与配方：判断当前整合包的实际进度，不照搬原 Mod 默认玩法。
- `logs/latest.log`、`crash-reports/`：判断实际加载失败和崩溃根因，优先级高于静态推测。
- KubeJS、CraftTweaker、数据包和配方脚本：判断默认玩法是否被整合包改写。
- 现有 HTML：只作视觉参考；存在生成器时修改生成器。

## 元数据和环境

加载器与来源必须分开：Forge/NeoForge/Fabric/Quilt 是加载器，Modrinth/CurseForge/BBSMC/GitHub 是来源。

- NeoForge：读取 `META-INF/neoforge.mods.toml`。
- Forge：用 TOML 解析 `META-INF/mods.toml` 的 `[[mods]]` 和 `[[dependencies.<modid>]]`，兼容单引号多行简介。
- Fabric：读取 `fabric.mod.json` 的 `id`、`name`、`description`、`contact.homepage`。
- Quilt：读取 `quilt.mod.json` 的对应字段。
- 缺少元数据时才清洗 jar 文件名作为名称。

优先用 jar SHA-1 调用 Modrinth `GET /version_file/{hash}?algorithm=sha1` 精确识别版本，并读取其游戏版本、加载器和依赖类型。哈希无结果时，使用清洗后的 jar 名搜索 Modrinth，筛选 `project_type=mod`、当前 Minecraft 版本和加载器。仍无可靠结果时再搜索 CurseForge 的 Mod 分类；多个结果默认取第一个，并核对版本与加载器。之后可查 BBSMC 的 Mod 或整合包页面，补充中文名称、中文说明、整合修改、更新日志和社区反馈；BBSMC 不替代 jar、Modrinth、CurseForge 或作者资料中的精确版本事实。

清洗名称时去掉游戏版本、Mod 版本、加载器和发布阶段。例如 `Argentina's delight 1.20.1 (3.0 beta).jar` 应得到 `Argentina's delight`。

## 可运行性与冲突

按证据强度依次检查：

- 实际日志或崩溃报告中的加载失败、缺失依赖、Mixin/类加载根因。
- jar 元数据中的必需依赖、`breaks`、`conflicts`、`incompatible`、`discouraged`。
- Modrinth 精确版本的加载器、游戏版本、环境和 `incompatible` 依赖。
- 作者 issue tracker、官方 Wiki、CurseForge 页面中的版本化说明。
- BBSMC 中能匹配项目、版本和加载器的更新日志、讨论或反馈；只匹配到名称时作为待核实线索。
- 根据功能重叠和本地配置推断的玩法风险。

报告分为“可运行性阻断、已知不兼容、玩法重叠/平衡风险、操作提示”。已知问题必须保留版本与来源；推断只能标成“高风险”或“需关注”。

玩法复核只比较高影响重叠组：配方查看器、地图、背包/存储、墓碑、连锁挖掘、库存整理、世界生成/维度、经济、难度、任务进度和大规模性能改写。两个 Mod 功能相似不等于冲突；继续检查配置开关、整合脚本和作者兼容说明。

## 玩家入口检查

首次游玩优先检查任务入口和材料查询方式；按键仅在影响核心操作时提升优先级：

- 任务书的物品、背包界面按钮、快捷键或命令入口。
- JEI/REI 的配方与用途查看方式，以及整合包是否改过默认键。
- 地图、路径点、背包、连锁挖掘、模式切换和远程终端。
- 同键多功能、未绑定功能和仅在特定界面生效的按键。

只写当前整合包中实际存在的入口，不列通用键位猜测。

## 快捷键提取

先读 `assets/*/lang/zh_cn.json` 或旧版 `zh_cn.lang`，再用 `en_us.json`/`en_us.lang` 补齐缺失键。候选键通常以 `key.`、`keybind.`、`create.keyinfo.`、`artifacts.key.` 开头或包含 `.key.`。过滤物品、方块、实体、提示、音效、进度和纯分类文本。

找不到 `options.txt` 真实绑定时显示 `未绑定`，同时保留 Mod 声明名称。多个功能使用同一真实绑定时标记为操作提示，不自动给出新键位，也不盖过可运行性和玩法问题。

## 离线 HTML

默认生成单个离线文件：

- CSS 和 JS 内联，不依赖网络字体或运行时库。
- 使用响应式布局、顶部导航、搜索框和分类筛选。
- 导航顺序为“环境与风险、开始游玩、核心玩法、操作手册、Mod 索引、资料来源”。
- 首屏直接展示当前整合包名称、版本环境和开始入口，不制作宣传落地页。

## Mod 卡片

每个 Mod 独立成卡，保留原页面的信息结构。按来源存在的内容提取：功能简介、重要物品/方块/实体/系统、按键与控制、使用方式、前置条件及版本化兼容说明。

英文内容翻成简体中文，保留专名、命令、ID、键名和版本号。共享机制只在基础 Mod 卡片中解释；附属只写新增内容。库/API 使用“无需操作；后台前置”。来源与当前游戏版本不匹配时省略版本相关结论。

## 验收

- HTML 包含 UTF-8 meta。
- 卡片数与去重后的 modId 数一致。
- 内联 JS 可用 `new Function(script)` 解析。
- 搜索词不会因通用建议造成大面积误命中。
- 前十张卡片优先是实际玩法内容。
- 抽查任务入口、JEI/REI、地图和高频按键的状态。
- 确认阻断问题优先展示，且每条已知冲突注明双方、版本、现象、处理建议和来源。
