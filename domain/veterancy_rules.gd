class_name VeterancyRules
extends RefCounted

# Match-local combat experience. These are game balance values, not historical
# formation grades or a claim about the abilities of any real army.
const THRESHOLDS=[20,50,80]
const ATTACK_BONUS=[0,30,60,100]
const NAMES=["新兵","历战","精熟","老兵"]

static func rank_for(experience: int) -> int:
	var rank=0
	for threshold in THRESHOLDS:
		if experience>=threshold:rank+=1
	return rank

static func bonus(unit: Dictionary) -> int:return ATTACK_BONUS[rank_for(int(unit.get("experience",0)))]

static func credit(unit: Dictionary, amount: int, events: Array) -> void:
	if unit.hp<=0:return
	var previous=rank_for(int(unit.get("experience",0)))
	unit.experience=mini(80,int(unit.get("experience",0))+amount)
	var rank=rank_for(unit.experience)
	if rank>previous:events.append({"type":"UnitPromoted","unit_id":unit.id,"owner_id":unit.owner_id,"position":unit.position.duplicate(),"rank":rank,"name":NAMES[rank]})
