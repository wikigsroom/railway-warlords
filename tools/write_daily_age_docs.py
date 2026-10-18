"""Maintain scoped documentation; preserve the hand-written bilingual README."""
import json,re,shutil
from pathlib import Path
P=Path(__file__).resolve().parents[1]

def main():
 life=json.loads((P/'presentation/data/general_lifespans.json').read_text(encoding='utf-8'))['generals']
 lines=['# 每日历法与四阶段人物肖像 · 0.2.22','',
 '本版将全部61个剧本统一为每日制，并为全部33位人物登记、生产和接入四个生涯阶段。135张肖像由原有12张、此次补全123张构成；其中132张对应33×4阶段，另3张为保留的年代补充图。全部为独立Sub2原图，不通过复制、镜像、染色、拼接或裁切充数。','',
 '## 每回合一天','',
 '同一天内各存活阵营依次行动；一个阵营结束操作只切换行动阶段。所有阵营完成一轮后，回合数增加1，公历日期增加1天。月份长短、闰年和跨年由公历运算处理。天气预报展示接下来的三个连续日，而非三个星期或月份。','',
 '带有真实日期的历史事件以日期为准，旧的回合提示不能提前触发。事件条件、局势分支与一次性触发记录继续有效；读档不会重复执行已经发生的事件。仅为演习设置且没有日期的触发器保留回合语义。日期推进不是逐日历史天气复原，作战与经济仍为游戏规则。','',
 '各阵营每天恢复行动、结算收入和军需，并推进建设、修理及援助队列。现有单位能力、经济数值和任务回合上限未被伪称为史实日均值；每日制下的长局平衡仍需继续实玩调整。80回合对应80天、180回合对应180天，起始日算第1天。','',
 '规则版本升级为schema 2 / ruleset 10。旧ruleset 9战局不按新历法解释，请新开对局；原有档案不被覆盖。生涯成长与个人设置仍按其自身存档格式读取。','',
 '## 四个生涯阶段','',
 '指挥部的将领名册和战法/勋章页提供青年、壮年、中年、暮年四阶段切换。阵亡较早的人物将第四阶段标为“生前晚期”。战场检查面板和派遣名册按当前对局日期自动选图，无需玩家手选。','',
 '仅核实到生卒年的人物显示“约N岁”；生日核实到日的按生日计算实岁。出生前不显示成人肖像，16岁以前显示未到青年阶段；成年后的早期年份可使用青年阶段插画，但不会倒用中年或晚年脸。阶段图的参考年是插画设定，并非声称照片拍摄于当年。逝世后展示生前最后阶段并停止增龄，不据此开放其在后续年代的任命。','',
 '李德胜在1917年生日以前为23岁、生日当日起为24岁，自动采用青年形象；1947年为53至54岁，采用中年形象。1947及其后的图片属于人物生涯素材准备，当前游戏时间锚点仍止于1940，未新增1947解放战争战役。','',
 '洪秀全的四阶段已补全。其外貌采用文字记述和后世纪念形象参照绘制，不能称作已认证的生前肖像；不以误认木刻或后世纪念画冒充当时写生。其他人物亦不宣称所有阶段已经独立历史肖似度批准。','',
 '| 人物 | 生卒年 | 青年参考年 | 壮年参考年 | 中年参考年 | 第四阶段参考年 | 日期资料 |',
 '| --- | --- | --- | --- | --- | --- | --- |']
 for gid,r in life.items():
  years=[str(s['reference_year'])+'（约'+str(s['approximate_age'])+'岁）' for s in r['stages']]
  lines.append('| '+r['name']+' | '+str(r['birth_year'])+'—'+str(r['death_year'])+' | '+' | '.join(years)+' | [来源]('+r['reference_urls'][0]+') |')
 lines+=['','李宗仁采用所查黄埔同学会及故宫图书的1891年记载，保留部分英文资料1890年的分歧。陈炯明采用国立公共资讯图书馆的1878年，保留1877年的异说与生日差异。卡列金仅采用生卒年，避免混用俄历与公历死亡日期。齐燮元、郭松龄和瓦德西的部分年表仍待进一步一手资料校核；来源类型和未完成状态保存在general_lifespans.json。','',
 '## 原图与审核记录','',
 '栅格生产只使用指定sub2-image-gen / gpt-image-2.5 / high路线，每次直接生成一张完整肖像。原图、提示词和SHA256绑定；20张存在年代发式或年龄问题的早期原图不接入游戏，保留生产历史。运行时只由Godot导入设置生成512像素上限及mipmap缓存，assets内PNG保持原始字节。','',
 '原有两份提示词含旧显示名：原始UTF-8字节以可逆Base64封存并保留原SHA256，阅读副本统一使用李德胜。游戏、说明和新提示词使用已指定显示名；不改写旧Git历史或工作区原始生产记录。','',
 '[四阶段登记表](../presentation/data/general_portraits.json) · [生卒年与资料精度](../presentation/data/general_lifespans.json) · [素材来源索引](asset-provenance/index.json) · [原图审核](../reports/general_portrait_source_review.json)','',
 '## 原生程序画面','',
 '以下均来自0.2.22 Windows导出程序的完整Godot视口，没有拼接或叠字。手机比例测试运行于桌面，不能替代Motorola X30物理验收。','',
 '![洪秀全中年形象与人物页](media/hong-middle-v0222.png)','',
 '![李德胜青年形象](media/lidesheng-young-v0222.png)','',
 '![李德胜1947年中年形象](media/lidesheng-middle-v0222.png)','',
 '## English implementation notes','',
 'Every complete round advances exactly one Gregorian day, after all living factions finish their phases. Dated historical events follow their calendar date and retain one-shot state across save/load. All 61 scenarios declare one day per round. Existing ruleset 9 matches require a new game under ruleset 10. Economy and movement remain game abstractions; long-match daily balance has not received complete manual acceptance.','',
 'All 33 people now have four independently generated living-life-stage portraits. The library contains135 originals:132 stage anchors and3 retained extra dates. Actual match dates choose the appearance; the headquarters and character pages provide stage controls. Lifespans use documented precision and explicitly retain disputed dates. Early deaths use the last living period instead of hypothetical old age. Post-1940 art is preparation, not a new1947 scenario. Portraits are interpretive game illustrations, not authenticated photographs or independently approved historical likenesses.','']
 (P/'docs/40_每日历法与四阶段人物肖像.md').write_text('\n'.join(lines),encoding='utf-8')
 cases=[('growth_hong_xiuquan_middle','hong-middle-v0222'),('growth_mao_zedong_young','lidesheng-young-v0222'),('growth_mao_zedong_middle','lidesheng-middle-v0222')]
 media=json.loads((P/'docs/media/manifest.json').read_text(encoding='utf-8'))
 for surface,name in cases:
  source=P/'reports/screenshots/general_portraits_native/windows'/(surface+'.png');target=P/'docs/media'/(name+'.png');shutil.copyfile(source,target);shutil.copyfile(source.with_suffix('.json'),target.with_suffix('.json'))
  import hashlib
  media['screenshots']=[r for r in media['screenshots'] if r['file']!=target.relative_to(P).as_posix()]
  media['screenshots'].append(dict(file=target.relative_to(P).as_posix(),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),native_source=source.relative_to(P).as_posix(),metadata=target.with_suffix('.json').relative_to(P).as_posix(),version='0.2.22',description=surface))
 (P/'docs/media/manifest.json').write_text(json.dumps(media,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 for relative in ['README.md','README.en.md']:
  path=P/relative;text=path.read_text(encoding='utf-8')
  text=text.replace('**0.2.21 可玩测试版**','**0.2.22 可玩测试版**').replace('**0.2.21, a playable test build**','**0.2.22, a playable test build**').replace('schema 2 / ruleset 9','schema 2 / ruleset 10').replace('1,176','1,299')
  if relative=='README.md':
   text=text.replace('推演日期是游戏日历，不是逐日战史。','每个完整回合推进公历1天；各阵营行动阶段不各自增加一天。日期不是逐日战史天气复原。')
   intro='0.2.22已统一每日制，并补全33人×4个生涯阶段，共135张肖像。对局按日期自动换形象，名册支持阶段预览；李德胜1917年用青年、1947年用中年图。1947素材为准备内容，未新增该年剧本。详见[每日历法与四阶段人物肖像](docs/40_每日历法与四阶段人物肖像.md)。\n\n![洪秀全人物页 · 0.2.22原生画面](docs/media/hong-middle-v0222.png)\n\n'
   text=text.replace('<a id="contents"></a>',intro+'<a id="contents"></a>')
   text=text.replace('27 组、5,084 项检查通过','29组回归见当前报告；新增每日历法与人物阶段专项').replace('27 组、5,084 项覆盖','0.2.21的27组、5,084项覆盖').replace('当前 EXE 另通过','0.2.21 EXE 另通过').replace('142张当前EXE原生截图','142张0.2.21 EXE原生截图').replace('当前报告是原工作区 0.2.21 验证快照','该节旧地图报告是原工作区0.2.21验证快照；0.2.22专项见新增说明').replace('### 0.2.21 当前满载实测','### 0.2.21 历史满载实测').replace('0.2.21 完成度','0.2.22完成度')
  else:
   intro='Version0.2.22 uses one calendar day per complete round and provides four living age-stage originals for every one of33 people,135 portraits in total. Match dates select the appearance automatically. Li Desheng uses a youthful1917 appearance and a middle-aged1947 appearance; post-1940 art does not add a new1947 scenario. See [daily calendar and age-stage implementation](docs/40_每日历法与四阶段人物肖像.md).\n\n![Hong Xiuquan in the native0.2.22 character page](docs/media/hong-middle-v0222.png)\n\n'
   text=text.replace('<a id="contents"></a>',intro+'<a id="contents"></a>')
   text=text.replace('**27 groups / 5,084 passing checks**','**29 regression groups; see current scoped evidence**').replace('Twenty-seven groups / 5,084 checks cover','The0.2.21 snapshot has twenty-seven groups /5,084 checks covering').replace('The current EXE also passes','That0.2.21 EXE also passes').replace('142 current EXE native captures','142 version0.2.21 native captures').replace('Current reports are original-workspace 0.2.21 snapshots','The older map reports are original-workspace0.2.21 snapshots; current calendar/portrait evidence is described separately').replace('### Current version 0.2.21 full-load measurements','### Historical version0.2.21 full-load measurements').replace('the 0.2.21 assessment','the0.2.22 assessment')
  path.write_text(text,encoding='utf-8')
 print('Daily/age manual and bilingual README additions written without image editing.')

if __name__=='__main__':main()
