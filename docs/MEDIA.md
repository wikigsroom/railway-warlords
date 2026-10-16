# 原生媒体记录 / Native media

[中文 README](../README.md#screenshots) · [English README](../README.en.md#screenshots) · [完整机器可读记录 / Manifest](media/manifest.json)

## 截图 / Screenshots

14 张完整 PNG 直接来自 Godot 原生视口。主菜单使用本版 Windows EXE 新截取；其他画面来自本版已核验的原生报告。复制进 `docs/media` 的 PNG 与来源逐字节相同，没有裁切、拼接、补绘或叠字。Godot 的控件、地图和独立美术资源在实际程序中正常渲染。

Fourteen complete PNGs come directly from native Godot viewports. The menu was captured anew from the current Windows executable; the others come from verified native evidence for this version. Copied PNGs are byte-identical, without cropping, stitching, repainting or text overlays. Godot renders the real controls, maps and independent assets.

| 文件 / File | 内容 / Content |
| --- | --- |
| [menu.png](media/menu.png) | 当前主菜单 / Current main menu |
| [battlefield.png](media/battlefield.png) | 战场 HUD / Battlefield HUD |
| [mountains.png](media/mountains.png) | 燕山地形与村落 / Yanshan terrain and villages |
| [coast.png](media/coast.png) | 渤海海岸 / Bohai coast |
| [tributaries.png](media/tributaries.png) | 来源山谷支流 / Sourced valley tributaries |
| [sand.png](media/sand.png) | 塔克拉玛干沙土 / Taklamakan sand |
| [gravel.png](media/gravel.png) | 戈壁砾土 / Gobi gravel |
| [wet-soil.png](media/wet-soil.png) | 沿海湿土 / Coastal wet ground |
| [yangtze.png](media/yangtze.png) | 汉口长江 / Yangtze at Hankou |
| [asia-overview.png](media/asia-overview.png) | 亚洲战略层 / Strategic Asia |
| [legion-deployment.png](media/legion-deployment.png) | 军团编组 / Legion deployment |
| [mobile-layout.png](media/mobile-layout.png) | 桌面移动布局 / Mobile layout on desktop |
| [battle-impact.png](media/battle-impact.png) | 交战与受击 / Combat impact |
| [air-recon.png](media/air-recon.png) | 航空侦察 / Air reconnaissance |

地图截图的 JSON 同时记录视口、版本、内容指纹、地表／地景等信息；战斗演示帧的共同证据见 `reports/native_visual_evidence.json`。X30 尺寸截图来自 Windows，`physical_android_device_tested` 为 false。

Associated JSON records viewport, version, content fingerprint and map information where available. Combat frames share `reports/native_visual_evidence.json`. X30-size screenshots are Windows captures with `physical_android_device_tested: false`.

## 录像与 GIF / Recording and GIFs

原生录像：[atlas_v2_native_final.mp4](../reports/atlas_v2_native_final.mp4)，1440×810、30 FPS、26.2 秒，包含声音。使用 Godot MovieWriter 录制，正式剧本部署未修改，命令重放最终状态和随机流一致。不是概念动画或生成视频。

The native recording is 1440×810, 30 FPS and 26.2 seconds with audio. Godot MovieWriter records unchanged scenario deployment. Replayed commands reach the same final state and random stream. This is not concept animation or generated video.

| GIF | 原录像片段 / Source excerpt | 输出 / Output |
| --- | --- | --- |
| [movement.gif](media/movement.gif) | 0.5–7.5 s | 960×540, 12 FPS, 1× speed, loop |
| [combat.gif](media/combat.gif) | 15–23 s | 960×540, 12 FPS, 1× speed, loop |

GIF 由 `video-cut-ffmpeg` 技能指导，通过 FFmpeg 直接转换连续时间段，保持全部画幅，无裁切、蒙太奇、叠字、补帧或变速；仅降采样帧率、等比缩放和 GIF 调色板量化。GIF 不支持原录像的声音。

Following the video-cut-ffmpeg skill, FFmpeg converts continuous excerpts with the full frame. There is no crop, montage, overlay, synthetic frame or speed change. Only frame-rate sampling, aspect-preserving scaling and GIF palette quantization are applied; GIFs omit audio.

```powershell
ffmpeg -hide_banner -loglevel error -y -ss 15 -t 8 -i reports/atlas_v2_native_final.mp4 -filter_complex "fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a" -loop 0 docs/media/combat.gif
```

完整命令参数、源文件及输出 SHA-256 见 [manifest.json](media/manifest.json)。录屏和截图原文件保持不变。

The manifest records source and output hashes and conversion parameters. Native source recordings and screenshots remain unchanged.

## 示意图与验证边界 / Diagrams and evidence scope

菜单和回合流程使用 Mermaid 文本图，不把它们当成实际画面。截图与 GIF 展示当前功能，不能替代美术发行批准、全部任务人工平衡或 Android 真机验收。

Menu and loop diagrams use Mermaid and are identified as diagrams. Native media demonstrates current functions, not final art approval, all-mission balance or physical Android acceptance.
