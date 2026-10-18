class_name DiplomacyOffice
extends RefCounted

# A selected-counterparty office. All offers still use the authoritative
# command preview/worker; no acceptance rule or hidden army is reconstructed.
const RELATIONS={"WAR":"交战","NEUTRAL":"中立","TRUCE":"停战","ALLIANCE":"同盟"}
const ACTIONS=[
	["declare_war","宣战","仅对中立势力；消耗本阶段一次宣战机会。"],
	["truce","停战提案","消耗一次提案；通过后至少维持3天。"],
	["alliance","同盟提案","消耗一次提案；通过后至少维持6天。"],
	["break","通知解约","保护期满后可通知，2天后解除条约。"],
	["aid","援助50军费","下一次对方行动阶段到账；援助间隔3天。"]
]

static func date_after_rounds(state: Dictionary, round_index: int) -> String:
	var timestamp=Time.get_unix_time_from_datetime_string(str(state.date)+"T00:00:00")
	return Time.get_date_string_from_unix_time(timestamp+maxi(0,round_index-int(state.round))*86400*TurnRules.DAYS_PER_ROUND)

static func show(app, room: WarRoomScreens, requested: String) -> String:
	var state=app.match_controller.state;var owner=str(state.player_faction_id)
	var player=StateAccess.faction(state,owner)
	var counterparts=state.factions.filter(func(f):return f.id!=owner and not f.eliminated)
	var target=requested
	if not counterparts.any(func(f):return f.id==target):
		var enemies=counterparts.filter(func(f):return StateAccess.hostile(state,owner,f.id))
		target=str((enemies[0] if not enemies.is_empty() else counterparts[0]).id) if not counterparts.is_empty() else ""
	var v=app.modal("外交事务 · 关系与条约",false)
	v.name="DiplomacyOffice"
	var budget=app.row(v)
	app.label(budget,"%s  ·  %s"%[state.date,StateAccess.faction_name(state,owner,app.content)],20,MilitaryUI.INK)
	app.label(budget,"提案 %d  /  宣战 %d  /  援助 %d  /  军费 %d"%[player.diplomacy_orders_left,player.war_orders_left,player.aid_orders_left,player.resources.cash],18,MilitaryUI.MUTED)
	app.ui_rule(v,Color("a0aaa7"))
	if counterparts.is_empty():
		app.label(v,"当前没有可交涉的在场势力。",24,MilitaryUI.INK)
		return ""
	var body=app.row(v);body.size_flags_vertical=Control.SIZE_EXPAND_FILL;body.add_theme_constant_override("separation",16)
	var roster_shell=app.ui_panel(body,"ui_hud_plate",Color.WHITE,14);roster_shell.set_meta("ui_light",false)
	roster_shell.custom_minimum_size.x=clampf(app.get_viewport_rect().size.x*.23,250*minf(room.scale(),1.25),340*minf(room.scale(),1.25))
	var roster=app.column(roster_shell);roster.name="DiplomacyRoster"
	app.ui_kicker(roster,"在场势力  /  %d"%counterparts.size(),MilitaryUI.BRASS,14)
	var list=app.scroll_column(roster)
	for faction in counterparts:
		var relation=StateAccess.relation(state,owner,faction.id)
		var button=app.button(list,"%s%s\n%s"%["▶ " if faction.id==target else "",StateAccess.faction_name(state,faction.id,app.content),RELATIONS.get(relation.state,relation.state)],func():room.show_diplomacy(faction.id))
		button.name="DiplomacyTarget_"+str(faction.id);button.set_meta("target_faction_id",faction.id)
		button.alignment=HORIZONTAL_ALIGNMENT_LEFT;button.clip_text=true
		button.add_theme_font_size_override("font_size",int(18*room.scale()))
		button.custom_minimum_size.y=maxf(room.touch_height(),78*room.scale())
		button.tooltip_text=StateAccess.faction_name(state,faction.id,app.content)+" · "+RELATIONS.get(relation.state,relation.state)
		if faction.id==target:button.add_theme_stylebox_override("normal",MilitaryUI.flat(Color("52645f"),MilitaryUI.BRASS,12))
	app.label(roster,"选择势力查看当前条约与可用事务。",15,Color("bfc9c6"))
	var details=app.column(body);details.name="DiplomacyDetails";details.size_flags_vertical=Control.SIZE_EXPAND_FILL
	var relation=StateAccess.relation(state,owner,target);var acceptance=DiplomacyRules.acceptance(state,owner,target)
	var heading=app.row(details);var strip=ColorRect.new();strip.color=MapView.TERRITORY_COLORS.get(target,Color("70838a"));strip.custom_minimum_size=Vector2(7,64);heading.add_child(strip)
	var identity=app.column(heading)
	app.label(identity,StateAccess.faction_name(state,target,app.content),29,MilitaryUI.INK).name="DiplomacySelectedName"
	app.label(identity,RELATIONS.get(relation.state,relation.state)+"  ·  当前对局关系",18,Color("915b49") if relation.state=="WAR" else Color("526e65"))
	var content=app.scroll_column(details);content.name="DiplomacyDetailScroll"
	var facts=room.grid(content,250);facts.set_meta("max_columns",3)
	var rights=room.card(facts);app.label(rights,"条约权限",20,MilitaryUI.INK)
	app.label(rights,"借道  "+("允许" if relation.passage else "未开放")+"\n补给  "+("共享" if relation.supply else "未开放"),18)
	var term=room.card(facts);app.label(term,"条约时限",20,MilitaryUI.INK)
	var protection=maxi(0,int(relation.minimum_until_round)-int(state.round))
	app.label(term,"保护期余 %d 天"%protection if protection>0 else "当前无保护期",18)
	if protection>0:app.label(term,"至 "+date_after_rounds(state,int(relation.minimum_until_round)),16)
	if relation.break_at_round>0:app.label(term,"解约 "+date_after_rounds(state,int(relation.break_at_round)),16,Color("915b49"))
	var intelligence=room.card(facts);app.label(intelligence,"已知军情",20,MilitaryUI.INK)
	var visible_units=state.units.filter(func(u):return u.owner_id==target and VisibilityRules.unit_visible(state,owner,u)).size()
	app.label(intelligence,"已侦知编队 %d"%visible_units,18).name="DiplomacyKnownUnits"
	app.label(intelligence,"依本方情报，非敌军总兵力",14,MilitaryUI.MUTED)
	var proposal=room.card(content);var answer=app.row(proposal)
	app.label(answer,"提案评分  %d / 50"%acceptance.score,21,MilitaryUI.INK)
	app.label(answer,"预计接受" if acceptance.accepted else "预计拒绝",18,Color("526e65") if acceptance.accepted else Color("915b49"))
	var meter=ProgressBar.new();meter.max_value=100;meter.value=clampf(acceptance.score,0,100);meter.show_percentage=false;meter.custom_minimum_size.y=10;proposal.add_child(meter)
	app.label(proposal," · ".join(acceptance.reasons) if not acceptance.reasons.is_empty() else "当前没有额外加分条件",16)
	if not state.cities.any(func(c):return c.owner_id==target and (c.level>=2 or c.get("command_center",false))):
		app.label(proposal,"暂无2级城市或司令部；须依靠可占领部队维持反击能力。若撤离，未送达援助退回一半。",16,Color("915b49"))
	var transfers=state.pending_aid.filter(func(a):return (a.sender_id==owner and a.receiver_id==target) or (a.receiver_id==owner and a.sender_id==target))
	if not transfers.is_empty():
		var transit=room.card(content);transit.name="DiplomacyAidTransit"
		app.label(transit,"运输中的援助",20,MilitaryUI.INK)
		for transfer in transfers:
			app.label(transit,("送往对方" if transfer.sender_id==owner else "对方送来")+" · "+room.cost_text(transfer.resources)+" · 收方下一行动阶段结算",17)
	app.label(content,"外交事务",23,MilitaryUI.INK)
	var actions=room.grid(content,320);actions.set_meta("max_columns",2)
	for entry in ACTIONS:
		var card=room.card(actions);card.set_meta("diplomacy_action",entry[0])
		app.label(card,entry[1],21,MilitaryUI.INK);app.label(card,entry[2],16,MilitaryUI.MUTED)
		var reason=room.status(card)
		var command=app.match_controller.command("Diplomacy",{"target_faction_id":target,"action":entry[0],"passage":true,"supply":true})
		if entry[0]=="aid":command.resources={"cash":50}
		var action=room.action(card,entry[1],command,reason);action.name="DiplomacyAction_"+str(entry[0])
	app.label(content,"停战或同盟提案请求借道及共享补给；最终结果由当前战局条件决定。",15,MilitaryUI.MUTED)
	return target
