class_name DiplomacyRules
extends RefCounted

static func acceptance(state: Dictionary, owner: String, target: String) -> Dictionary:
	var score=0;var reasons: Array=[]
	for other in state.factions:
		if StateAccess.hostile(state,owner,other.id) and StateAccess.hostile(state,target,other.id):score+=35;reasons.append("共同敌人 +35");break
	var ours=state.units.filter(func(u):return u.owner_id==owner).size();var theirs=state.units.filter(func(u):return u.owner_id==target).size()
	if ours>=theirs:score+=25;reasons.append("实力威胁 +25")
	if state.cities.any(func(c):return c.owner_id==owner and c.port):score+=15;reasons.append("交通互补 +15")
	var relation=StateAccess.relation(state,owner,target)
	if relation.get("last_aid_round",-10)>=state.round-3:score+=10;reasons.append("近期援助 +10")
	if relation.get("betrayal_until_round",0)>=state.round:score-=50;reasons.append("近期毁约 −50")
	if relation.state=="WAR":score-=30;reasons.append("领土冲突 −30")
	return {"score":score,"accepted":score>=50,"reasons":reasons}

static func act(state: Dictionary, owner: String, command: Dictionary, events: Array) -> void:
	var target=command.target_faction_id;var r=StateAccess.relation(state,owner,target);var f=StateAccess.faction(state,owner)
	match command.action:
		"declare_war":
			f.war_orders_left-=1;r.state="WAR";r.passage=false;r.supply=false
		"break":r.break_at_round=state.round+2;r.betrayal_until_round=state.round+10;f.diplomacy_orders_left-=1
		"aid":
			f.aid_orders_left-=1;StateAccess.pay(state,owner,command.resources,events,"外交援助")
			state.pending_aid.append({"id":StateBuilder.next_id(state,"aid"),"sender_id":owner,"receiver_id":target,"resources":command.resources.duplicate(),"arrival_owner_phase":StateAccess.faction(state,target).own_phase_index+1});r.last_aid_round=state.round
		"truce","alliance":
			f.diplomacy_orders_left-=1;var answer=acceptance(state,owner,target)
			if answer.accepted:
				r.state="TRUCE" if command.action=="truce" else "ALLIANCE";r.passage=command.get("passage",false);r.supply=command.get("supply",false);r.minimum_until_round=state.round+(3 if command.action=="truce" else 6)
			events.append({"type":"DiplomacyResponse","accepted":answer.accepted,"score":answer.score,"owner_id":target})
	events.append({"type":"DiplomacyChanged","action":command.action,"owner_id":owner,"target_id":target})

static func settle_aid(state: Dictionary, owner: String, events: Array) -> void:
	for a in state.pending_aid.duplicate():
		var recipient=StateAccess.faction(state,a.receiver_id)
		if recipient.eliminated:
			var refund={}
			for key in a.resources:refund[key]=int(a.resources[key]/2)
			StateAccess.add_resources(state,a.sender_id,refund,events,"援助退回");state.pending_aid.erase(a)
		elif a.receiver_id==owner and a.arrival_owner_phase<=recipient.own_phase_index:
			StateAccess.add_resources(state,owner,a.resources,events,"援助到账");state.pending_aid.erase(a)
