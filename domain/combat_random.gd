class_name CombatRandom
extends RefCounted

# A compact, portable stream. Preview and rendering never touch this state.
# All arithmetic fits signed 64 bit; saved values fit an exact JSON integer.
const MODULUS=2147483647
const MULTIPLIER=48271
const STEP_PERMILLE=35

static func initialize(match_id: String) -> Dictionary:
	var seed_value=int(("0x"+match_id.sha256_text().substr(0,7)).hex_to_int())+1
	return {"algorithm":"park_miller_48271_v1","state":seed_value,"draws":0}

static func die(state: Dictionary) -> int:
	var stream=state.combat_random
	stream.state=(int(stream.state)*MULTIPLIER)%MODULUS
	stream.draws=int(stream.draws)+1
	return 1+((int(stream.state)-1)%6)

static func roll(state: Dictionary, attacker: Dictionary, target_id: Variant, target_position: Dictionary, events: Array, counter: bool = false, city_id: String = "") -> int:
	var attack_die=die(state);var defense_die=die(state)
	var modifier=1000+(attack_die-defense_die)*STEP_PERMILLE
	events.append({"type":"CombatDiceRolled","attacker_id":attacker.id,"target_id":target_id,"city_id":city_id,"from":attacker.position.duplicate(),"position":target_position.duplicate(),"attack_die":attack_die,"defense_die":defense_die,"modifier_permille":modifier,"counter":counter,"draw_index":state.combat_random.draws})
	return modifier

static func scaled(amount: int, modifier: int) -> int:
	return maxi(1,int((int(amount)*modifier+500)/1000)) if amount>0 else 0
