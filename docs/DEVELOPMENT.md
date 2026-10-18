# 独立仓库开发 / Standalone development

[中文入口](../README.md#development) · [English entry](../README.en.md#development)

## 运行所需 / Required to run

游戏使用 Godot 4.7.2、GDScript 与 Compatibility 渲染器。完整运行资源和编译后地图位于本仓库。通过 Godot 项目管理器导入 `project.godot` 后运行；不需素材网关、Python、Android SDK 或原电脑的 `.toolchain`。

The game uses Godot 4.7.2, GDScript and Compatibility rendering. All runtime assets and compiled geography are included. Import `project.godot` in the project manager. Running the desktop project does not need Python, the image gateway, Android SDK or the original `.toolchain`.

```powershell
godot --headless --path . --editor --import --quit
godot --path .
```

Godot 依靠 `.godot/global_script_class_cache.cfg` 识别 `class_name`；先导入再直接运行测试脚本。缓存不进入 Git。导入参数 `*.import` 和稳定资源 ID `*.uid` 保留在 Git。

Godot discovers named script classes during import. Import before invoking a test script directly. Cache files are excluded; `*.import` settings and `*.uid` resource IDs stay tracked.

## 工具层级 / Tool tiers

| 层级 / Tier | 依赖 / Requirements | 范围 / Scope |
| --- | --- | --- |
| 游戏运行 / Game runtime | Godot 4.7.2 | 不需要 Python / No Python required |
| GDScript 回归 / Rules | Godot + completed import | 直接运行 `tests/*.gd` / Run individual test scripts |
| Python 数据／素材检查 / Data and art tools | Python + script-specific libraries | 部分工具为标准库，图片工具常用 Pillow / Many are stdlib-only; image tools use Pillow |
| 地理资料重建 / Geography rebuild | Original datasets + native GIS Python environment | Uses NumPy, PyShp, Shapely, PyProj as required by each script |
| 控制区矢量编译 / Control clipping | Python + Shapely 2.2.0 / GEOS 3.14.1 | `tools/compile_control_land_clip.py --check`; 输入已在仓库 / Input is included |
| 当前 README 媒体 / Current README media | Python + Pillow, current native EXE evidence | `tools/refresh_terrain_repository.py`; 复制原生图字节 / Copies native image bytes |
| Windows 导出 / Windows export | Matching Godot templates | Preset: `Windows` |
| Android 导出 / Android export | Matching templates, JDK 21, Android SDK, own keys | Preset: `Android`; physical-device testing |

原工作区部分资料处理使用单独的本机 Python 环境；本机默认 Python 的已安装包不等同于所有地理重建依赖已齐。按具体脚本导入项配置自己的环境，不将原电脑路径当成通用安装器。

Some original data processing uses a separate native Python environment. Packages installed in the default interpreter do not establish that all GIS dependencies are present. Configure the environment required by each script; workstation paths are not a universal installer.

## 原工作区与独立克隆 / Workspace and clone

`tools/build_release.py` 和多项归档／生成助手仍通过 `P.parents[1]` 查找原工作区，并含原电脑的 Godot、Java 或 SDK 路径。独立克隆的用户先使用 README 的原生 Godot 导出命令。需要这些助手时，先把引擎、SDK、私有签名和外部资料路径改为自己的配置。

`build_release.py` and several archival/generation helpers retain `P.parents[1]` workspace assumptions and original Godot/Java/SDK paths. For a standalone clone, use the native Godot commands in the README. Configure these helpers before using them on another workstation.

不包含在 Git 的原档案包括：原始地理 Shapefile／GeoTIFF、设计与历史交付 ZIP、原工作区生成任务日志、引擎程序、SDK、个人存档和私有凭据。它们仍保留在原工作区。运行 PNG 本身就是字节相同的生成原图，提示词在本仓库 `docs/asset-prompts/`，无需为每张图再复制一个同样的 `source.png`。

Excluded archives include raw geographic Shapefiles/GeoTIFFs, design/release ZIPs, original generation logs, engine binaries, SDKs, personal saves and credentials. They remain in the original workspace. Runtime PNGs are byte-identical generated originals; prompts live in `docs/asset-prompts/`, avoiding a second duplicate image tree.

## 原生验证 / Native verification

```powershell
godot --headless --path . --script tests/run_tests.gd
godot --headless --path . --script tests/acceptance_test.gd
godot --headless --path . --script tests/transaction_test.gd
godot --headless --path . --script tests/asia_content_test.gd
```

全部26组名称和通过范围见[测试与验收](05_测试与验收.md)，包含 `tests/terrain_surfaces_test.gd` 和`tests/river_surface_test.gd`及`tests/control_land_clip_test.gd`。`reports/` 只提交选定快照和原生画面；旧机器路径、时间戳和指纹反映证据产生环境，不代表克隆后的新测试。

All 26 groups and their scope are in the validation chapter, including `tests/terrain_surfaces_test.gd` `tests/river_surface_test.gd` and `tests/control_land_clip_test.gd`. Selected reports preserve their original paths, timestamps and fingerprints as evidence, not as newly executed tests on the clone.

## 文档和媒体维护 / Documentation maintenance

中文与英文入口人工同步维护，当前状态生成工具不会覆盖双语 README。菜单示意用 Mermaid，不生成伪 UI 图；PNG 使用完整原生视口。GIF 从原生 MP4 连续时间段直接转换，保留正常速度、完整画幅和来源记录。

The two READMEs are maintained together and protected from status-generator overwrites. Navigation diagrams use Mermaid. Screenshots remain full native viewports. GIFs convert continuous native MP4 excerpts at normal speed, retaining the complete frame and provenance.

```powershell
# 核对全部当前原图、提示词副本和来源：
# Verify current immutable originals and portable prompts:
python tools/refresh_terrain_repository.py --provenance-only
# 原工作区完成当前 EXE 原生验收后，复制当前界面/地表截图：
# Copy current native UI/terrain captures after the exported EXE passes QA:
python tools/capture_terrain_update.py
python tools/refresh_terrain_repository.py
```

`prepare_repository_media.py` 保留为 0.2.12 媒体制作流程，不能用它覆盖当前0.2.21截图。旧战斗录像与 GIF 明确保留 0.2.12 身份；当前新地表/UI使用本版原生证据。

`prepare_repository_media.py` preserves the 0.2.12 workflow. Do not use it to replace current screenshots. Existing battle GIFs retain their old version; current terrain/UI has its own native proof.

独立克隆内已有提示词副本；外部原始提示词目录可用时会核对并复制，不可用时核对仓库副本。重新捕获主菜单需使用原生导出或编辑器运行：

Existing portable prompts work without the original workspace. When the original prompt tree is available it is copied and checked. Capture the menu with the actual engine/export:

```powershell
godot --path . --resolution 1920x1080 -- --qa-session --capture --capture-path res://docs/media/menu.png
```

## 私有配置与许可 / Private configuration and licensing

签名密码、网关 API 凭据和个人文件不进入 Git。保留第三方许可、字体许可和地理署名；本仓库没有为全部原创内容擅自选择开源许可证。详见[许可说明](../LICENSE-NOTICE.md)。

Do not commit keys, passwords, gateway credentials or personal files. Retain third-party/font/geographic notices. No blanket license has been selected on behalf of the project owner; see the license notice.

本项目禁止本地 Docker、WSL、虚拟机和模拟器。若使用浏览器，工作结束关闭无用标签页。

Local Docker, WSL, VMs and emulators are prohibited. Close unused browser tabs after browser work.

0.2.17连续材质原生复核：在当前双端导出后运行 `python tools/verify_ground_continuity.py`，使用最终Windows EXE比较20个完整导入源、相邻地格覆盖、三材质交界与平移相位；结果为独立渲染夹具证据，不能替代真实地图的人工画面检查。

0.2.18 图符专项在当前双端导出后运行 `python tools/verify_map_symbols.py`。它直接运行 Windows EXE，在两种桌面视口中检查正式亚洲与山海关剧本的可见编队 ID、双向小幅跨阈值缩放、邻近城市的点选、选中对象恢复素材和完整状态/RNG 不变性，保存 32 张完整原生视口。

The 0.2.18 symbol checks run the current Windows EXE in two desktop viewports, using published Asia and Shanhaiguan scenarios. They verify individual formation draw identities, small zoom crossings in both directions, precise selection near cities, selected-source restoration and unchanged state/RNG. The 32 whole native captures are not physical-phone or commercial-art approval.

本版连续光影专项：`python tools/verify_relief_shading.py`，要求当前Windows导出。11项检查、4张完整数值夹具视口单列记录；它们不是历史地图或手机验收。

Current relief check: `python tools/verify_relief_shading.py`, after a verified Windows export. Eleven checks and four whole numerical fixture viewports are separate from historical-map and physical-device acceptance.

0.2.20 连续底材生产入口是 `tools/generate_ground_identity.py`，完整提示词计划为 `presentation/data/ground_identity_plan.json`。仅通过指定Sub2路线生成；安装前要求20张完整原图的检查记录，安装时采用新ID并保留旧20张原图。已登记原图或提示词不一致时拒绝覆盖。独立克隆已带原图与便携提示词，游玩无需重新生成或连接网关。安装应先于导入、源码封存、回归与双端构建，避免构建中改变素材身份。完整范围见[37](37_二十类地表材质形态重制.md)。

The 0.2.20 material producer uses the required Sub2 route and installs new IDs only after all twenty complete originals have a review record. It retains the previous twenty originals and rejects mismatched existing source bytes or prompts. Playing the clone needs neither regeneration nor gateway access. Complete installation and imports before freezing, testing and exporting the source.
