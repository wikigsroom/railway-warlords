# 兵种数值表 / Unit reference

Version 0.2.28; retained base values verified against current runtime JSON. Base values from runtime JSON; terrain, skills, morale and stacks modify actual results.

基础数值来自运行数据，实际结果还受地形、技能、士气、编队等影响。最早年代还必须通过具体剧本白名单。

| ID | 名称 / Unit | HP | Attack | Defense | AP | Range | Cash / Food / Arms | Earliest era | Occupy |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |
| `militia` | 地方守备队 / Local garrison | 85 | 24 | 16 | 3 | 1–1 | 45 / 5 / 12 | 1840 | Yes |
| `rifle` | 步兵团 / Rifle regiment | 100 | 34 | 20 | 4 | 1–1 | 80 / 8 / 20 | 1840 | Yes |
| `assault` | 突击营 / Assault battalion | 110 | 40 | 24 | 4 | 1–1 | 125 / 12 / 40 | 1917 | Yes |
| `machine_gun` | 机枪营 / Machine-gun battalion | 100 | 31 | 22 | 3 | 1–1 | 110 / 10 / 35 | 1890 | Yes |
| `cavalry` | 骑兵团 / Cavalry regiment | 105 | 35 | 20 | 6 | 1–1 | 115 / 15 / 25 | 1840 | Yes |
| `engineer` | 工兵营 / Engineer battalion | 100 | 22 | 20 | 4 | 1–1 | 90 / 8 / 25 | 1840 | Yes |
| `field_artillery` | 野战炮营 / Field artillery | 90 | 48 | 14 | 3 | 2–2 | 150 / 10 / 55 | 1840 | No |
| `heavy_artillery` | 重炮营 / Heavy artillery | 95 | 62 | 15 | 2 | 2–3 | 240 / 15 / 90 | 1900 | No |
| `armored_car` | 装甲汽车队 / Armored cars | 115 | 42 | 30 | 6 | 1–1 | 200 / 15 / 80 | 1917 | Yes |
| `armored_train` | 装甲列车 / Armored train | 160 | 56 | 36 | 6 | 1–2 | 300 / 20 / 130 | 1900 | No |
| `river_gunboat` | 江防炮艇 / River gunboat | 120 | 40 | 24 | 5 | 1–2 | 180 / 10 / 65 | 1860 | No |
| `transport_ship` | 运输船 / Transport ship | 95 | 0 | 12 | 5 | 0–0 | 120 / 10 / 30 | 1840 | No |
| `coastal_gunship` | 沿海炮舰 / Coastal gunship | 150 | 50 | 30 | 4 | 1–2 | 260 / 15 / 100 | 1840 | No |

Source: [units.json](../content/definitions/units.json).

These values are balance parameters, not historical force statistics. A stack is not an archival battalion/regiment/brigade.
