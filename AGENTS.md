# 项目协作约束 / Project constraints

- 禁止调度本地 Docker、WSL、虚拟机或 Android 模拟器；使用原生 Windows 工具链。Do not use local virtualization.
- 若调用浏览器，完成后关闭不再使用的标签页。
- 当前方向是《铁道烽烟：军阀时代》。本仓库是原工作区 `game/railway_warlords` 的独立源码仓库。
- 栅格美术只使用用户指定的 `sub2-image-gen` 技能；原工作区技能路径为 `C:/Users/carzy/.codex/skills/sub2-image-gen/SKILL.md`。不得用其他生成路线替代。
- 完整概念图直接生成，不自行拼接、叠字、裁取或补绘。生成原图不可变；引擎副本保持原始字节。
- `assets/manifest.json` 与 `docs/asset-provenance/index.json` 记录原图和提示词。`docs/asset-prompts/` 保存提示词副本。
- README 截图必须来自实际 Godot 视口；GIF 只能从原生录像直接转换，保存来源和转换参数，不制作伪实机合成图。
- 运行数值以 `content/definitions/catalog.json` 登记的定义表和 `content/scenarios/catalog.json` 为准；设计、生产、历史复核和实机验收分开记录，不虚报完成。
- 当前 README 为人工维护的中英双语入口。状态生成工具不得覆盖其完整内容。
- Godot 缓存、构建产物、个人存档、签名密钥、网关凭据和机器配置不得提交。
- 原工作区的设计、地理原始资料和旧版本归档独立保留；不得改写旧发布状态。
