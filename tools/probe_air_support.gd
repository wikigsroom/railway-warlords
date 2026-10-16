extends SceneTree
func _init() -> void:
	var content=ContentRegistry.new();if not content.load_all():quit(1);return
	var s=StateBuilder.create(content,"campaign_1924_03","zhili",{});var kernel=CommandKernel.new(content);var planner=AIPlanner.new(content,kernel);var active_owner=""
	var city=StateAccess.find(s,"cities","shanhaiguan")
	var build=VisualPlaytest.command(s,"Build",{"city_id":city.id,"def_id":"airfield"})
	var built=kernel.resolve(s,build);print("ACTUAL_BUILD ",built.valid," ",built.get("reason",""));if not built.valid:quit(1);return
	s=built.state
	for i in range(240):
		city=StateAccess.find(s,"cities",city.id)
		if s.status!="playing":print("EARLY_STATUS ",s.status);quit(1);return
		if s.turn_order[s.phase_index]==s.player_faction_id and EconomyRules.building_level(city,"airfield")>0:break
		if active_owner!=s.turn_order[s.phase_index]:active_owner=s.turn_order[s.phase_index];planner=AIPlanner.new(content,kernel)
		var c=planner.choose(s)
		if active_owner==s.player_faction_id and c.type not in ["Move","Attack","ActivateSkill","Reinforce","RailTransport","EndPhase"]:c=VisualPlaytest.command(s,"EndPhase",{})
		var r=kernel.resolve(s,c);if not r.valid:print(r.reason);quit(1);return
		s=r.state
	var targets=[]
	for target in s.units+s.cities:
		if target.position==null or not StateAccess.hostile(s,s.player_faction_id,target.owner_id):continue
		if kernel.preview(s,VisualPlaytest.command(s,"AirRecon",{"city_id":city.id,"target_hex":target.position})).valid:targets.append(target.id)
	print("REAL_BUILT_FIELD ",city.id," round ",s.round," status ",s.status," targets ",targets," resources ",StateAccess.faction(s,s.player_faction_id).resources);quit(0 if not targets.is_empty() else 1)
