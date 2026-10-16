class_name ProfileRepository
extends RefCounted

var content: ContentRegistry
var storage: SaveService
var profile: Dictionary={}
var error: String=""

func _init(registry: ContentRegistry, save_service: SaveService) -> void:
	content=registry;storage=save_service
	profile=storage.load_slot("profile")
	if profile.is_empty():
		profile={"schema_version":2,"merit":200,"research":90,"tech_ranks":{},"general_ranks":{},"skill_ranks":{},"general_xp":{},"medals":[],"elite_unlocks":[],"reward_ledger":[],"victories":{},"achievements":[],"stats":{},"campaign_unlocked":["campaign_1920_01","campaign_1922_01","campaign_1924_01"]}
		storage.write("profile",profile)
	refresh_victory_stats(profile)

func commit(next: Dictionary) -> bool:
	if not storage.write("profile",next):error=storage.error;return false
	profile=next;error="";return true

func upgrade_tech(id: String) -> bool:
	var d=content.definition("technologies",id);var rank=int(profile.tech_ranks.get(id,0))
	if d.is_empty() or rank>=3:error="科技已满级";return false
	for prerequisite in d.prerequisite:
		if int(profile.tech_ranks.get(prerequisite.id,0))<prerequisite.rank:error="前置科技尚未完成";return false
	var cost=int(d.cost_research_by_rank[rank])
	if profile.research<cost:error="研究点不足";return false
	var next=profile.duplicate(true);next.research-=cost;next.tech_ranks[id]=rank+1
	return commit(next)

func upgrade_general(id: String) -> bool:
	if content.definition("generals",id).is_empty():error="将领无效";return false
	var rank=int(profile.general_ranks.get(id,0))
	if rank>=6:error="军衔已满级";return false
	var merit=int(content.rules.progression.general_rank_cost_merit[rank]);var xp=int(content.rules.progression.general_rank_xp[rank])
	if profile.merit<merit or int(profile.general_xp.get(id,0))<xp:error="功勋或将领经验不足";return false
	var next=profile.duplicate(true);next.merit-=merit;next.general_xp[id]-=xp;next.general_ranks[id]=rank+1;return commit(next)

func upgrade_skill(general_id: String, skill_id: String) -> bool:
	var g=content.definition("generals",general_id)
	if g.is_empty() or (skill_id not in [g.passive_skill,g.active_skill] and not(skill_id=="cavalry_sweep" and g.stars.cavalry>=3)):error="战法不属于此将领";return false
	var key=general_id+":"+skill_id;var rank=int(profile.skill_ranks.get(key,1))
	if rank>=3:error="战法已满级";return false
	var merit=int(content.rules.progression.skill_upgrade_cost_merit[rank-1]);var xp=int(content.rules.progression.skill_upgrade_cost_xp[rank-1])
	if profile.merit<merit or int(profile.general_xp.get(general_id,0))<xp:error="功勋或经验不足";return false
	var next=profile.duplicate(true);next.merit-=merit;next.general_xp[general_id]-=xp;next.skill_ranks[key]=rank+1;return commit(next)

func choose_active_skill(general_id: String, skill_id: String) -> bool:
	var d=content.definition("generals",general_id)
	if d.is_empty() or (skill_id!=d.active_skill and not(skill_id=="cavalry_sweep" and d.stars.cavalry>=3)):error="战法与将领专长不符";return false
	var next=profile.duplicate(true);var loadouts=next.get("active_skills",{});loadouts[general_id]=skill_id;next.active_skills=loadouts;return commit(next)

func equip_medal(general_id: String, medal_id: String, rank: int) -> bool:
	var d=content.definition("medals",medal_id)
	if d.is_empty() or rank<1 or rank>3:return false
	var owned=profile.medals.filter(func(m):return m.general_id==general_id)
	if owned.size()>=2:error="将领最多装备两枚勋章";return false
	for m in owned:
		if m.medal_id==medal_id:error="同类勋章不可叠加";return false
	var cost=int(d.cost_merit[rank-1])
	if profile.merit<cost:error="功勋不足";return false
	var next=profile.duplicate(true);next.merit-=cost;next.medals.append({"general_id":general_id,"medal_id":medal_id,"rank":rank});return commit(next)

func unequip_medal(general_id: String, medal_id: String) -> bool:
	var next=profile.duplicate(true);next.medals=next.medals.filter(func(m):return not(m.general_id==general_id and m.medal_id==medal_id));return commit(next)

func settle(state: Dictionary) -> Dictionary:
	if state.get("status","") not in ["won","lost"]:return {"error":"战局尚未结束","merit":0,"research":0}
	if not content.scenarios.has(state.get("scenario_id","")) or state.get("content_hash","")!=content.content_hash:return {"error":"战报内容版本不匹配","merit":0,"research":0}
	var match_key="match:"+state.match_id
	if profile.reward_ledger.has(match_key):return {"merit":0,"research":0,"repeat":true}
	if state.get("debug_match",false) or state.get("surrendered",false):return {"merit":0,"research":0,"excluded":true,"repeat":false}
	var next=profile.duplicate(true);var won=state.status=="won";var merit=0;var research=0
	var key=state.scenario_id+":"+state.difficulty+(":"+state.player_faction_id if state.mode=="conquest" else "")
	var first=won and not next.reward_ledger.has("victory:"+key)
	var previous_stars=int(next.victories.get(key,0));var stars=clampi(int(state.get("result_stars",1)),1,3)
	var rewards=content.tables.reward_rules
	if first:
		var base=rewards.campaign[state.difficulty]
		if state.mode=="legion":
			var challenge=content.definition("challenges",state.scenario_id)
			base={"merit":challenge.first_win_merit,"research":challenge.first_win_research}
		if state.mode=="conquest":base=rewards.conquest_first_win
		merit=int(base.merit);research=int(base.research)
		next.reward_ledger.append("victory:"+key)
		if state.mode=="campaign":
			var m=content.definition("missions",state.scenario_id)
			for candidate in content.tables.missions:
				if candidate.unlock_after.has(m.id) and candidate.unlock_after.all(func(id):return next.victories.keys().any(func(k):return k.get_slice(":",0)==id) or id==state.scenario_id) and not next.campaign_unlocked.has(candidate.id):next.campaign_unlocked.append(candidate.id)
			if state.scenario_id.ends_with("_06"):
				for elite in content.tables.elite_variants:
					if not next.elite_unlocks.has(elite.id):next.elite_unlocks.append(elite.id)
	if won:
		if state.mode=="conquest":
			var bonus_key="three_stars:"+key
			if stars>=3 and previous_stars<3 and not next.reward_ledger.has(bonus_key):
				merit+=int(rewards.conquest_three_star_bonus.merit);research+=int(rewards.conquest_three_star_bonus.research);next.reward_ledger.append(bonus_key)
		elif state.mode=="campaign" and stars>maxi(1,previous_stars):
			for star in range(maxi(1,previous_stars)+1,stars+1):
				var tier_key="star:%s:%d"%[key,star]
				if not next.reward_ledger.has(tier_key):
					merit+=int(rewards.campaign.additional_star.merit);research+=int(rewards.campaign.additional_star.research);next.reward_ledger.append(tier_key)
		next.victories[key]=maxi(previous_stars,stars)
	var records=next.get("career_records",[])
	var record={"match_id":state.match_id,"scenario_id":state.scenario_id,"difficulty":state.difficulty,"faction_id":state.player_faction_id,"mode":state.mode,"won":won,"rounds":state.round,"stars":stars,"losses":state.metrics.losses,"captures":state.metrics.captures,"normalized":state.get("normalized",state.difficulty=="challenge" or state.mode=="legion"),"content_hash":state.content_hash,"ruleset_version":state.ruleset_version}
	records.append(record)
	if records.size()>200:records.pop_front()
	next.career_records=records
	refresh_victory_stats(next)
	for g in state.generals:
		if g.owner_id==state.player_faction_id:next.general_xp[g.id]=int(next.general_xp.get(g.id,0))+clampi(int(g.earned_xp),0,int(rewards.repeat_win_general_xp_cap) if won and not first else int(rewards.general_match_xp_cap))
	for metric in state.metrics:next.stats[metric]=int(next.stats.get(metric,0))+maxi(0,int(state.metrics[metric]))
	next.stats.matches=int(next.stats.get("matches",0))+1
	if won:next.stats.wins=int(next.stats.get("wins",0))+1
	# Conditions read committed action metrics, never UI button presses or previews.
	for a in content.tables.achievements:
		if next.achievements.has(a.id):continue
		if achievement_complete(a,next,state):next.achievements.append(a.id);merit+=int(a.reward_merit)
	next.merit+=merit;next.research+=research;next.reward_ledger.append(match_key)
	if not commit(next):return {"error":error,"merit":0,"research":0}
	return {"merit":merit,"research":research,"repeat":not first,"star_improved":won and stars>previous_stars}

func refresh_victory_stats(next: Dictionary) -> void:
	var unique_wins=next.victories.keys()
	next.stats.first_campaign_win=unique_wins.filter(func(k):return k.begins_with("campaign_")).size()
	next.stats.first_conquest_win=unique_wins.filter(func(k):return k.begins_with("conq_")).size()
	var three_star_missions={}
	for k in unique_wins:
		if k.begins_with("campaign_") and next.victories[k]>=3:three_star_missions[k.get_slice(":",0)]=true
	next.stats.campaign_three_star_wins=three_star_missions.size()
	next.stats.campaign_all_normal_wins=unique_wins.filter(func(k):return k.begins_with("campaign_") and k.ends_with(":normal")).size()
	for index in range(3):
		var year=[1920,1922,1924][index];var mission_ids={}
		for k in unique_wins:
			if k.begins_with("campaign_%d_"%year):mission_ids[k.get_slice(":",0)]=true
		next.stats["chapter_%d_complete"%(index+1)]=mission_ids.size()
		var conquest_ids={}
		for k in unique_wins:
			if k.begins_with("conq_%d:"%year):conquest_ids[k]=true
		next.stats["conquest_%d_wins"%year]=conquest_ids.size()
	var weak={};var normalized={};var legions={}
	for k in unique_wins:
		var recipe=content.scenarios.get(k.get_slice(":",0),{})
		if k.begins_with("conq_") and recipe.get("weak_faction_ids",[]).has(k.get_slice(":",2)):weak[k.get_slice(":",2)]=true
		if k.begins_with("conq_") and ":challenge:" in k:normalized[k.get_slice(":",0)]=true
		if k.begins_with("legion_"):legions[k.get_slice(":",0)]=true
	next.stats.distinct_weak_faction_conquest_wins=weak.size();next.stats.normalized_conquest_wins=normalized.size();next.stats.legion_challenges_won=legions.size()

func ranking_groups() -> Array:
	var groups={}
	for record in profile.get("career_records",[]):
		if not record.won or not record.normalized or record.get("content_hash","")!=content.content_hash or int(record.get("ruleset_version",0))!=ContentRegistry.RUNTIME_RULESET_VERSION:continue
		var key="%s:%s:%s:%s:%s"%[record.scenario_id,record.difficulty,record.faction_id,record.content_hash,record.ruleset_version]
		if not groups.has(key):groups[key]={"key":key,"scenario_id":record.scenario_id,"difficulty":record.difficulty,"faction_id":record.faction_id,"records":[]}
		groups[key].records.append(record)
	var result=groups.values();result.sort_custom(func(a,b):return str(a.key)<str(b.key))
	for group in result:
		group.records.sort_custom(func(a,b):
			if a.rounds!=b.rounds:return a.rounds<b.rounds
			if a.losses!=b.losses:return a.losses<b.losses
			if a.stars!=b.stars:return a.stars>b.stars
			return str(a.match_id)<str(b.match_id))
	return result

func achievement_complete(a: Dictionary, p: Dictionary, state: Dictionary) -> bool:
	var condition=a.criterion
	return int(p.stats.get(condition.metric,0))>=int(condition.value)
