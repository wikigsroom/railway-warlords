extends SceneTree

# A headless component fixture, not a gameplay screenshot or historical setup.
# Exercise the actual HUD labels as changing state values invalidate the cache.
class SummaryAssets extends RefCounted:
	var font: Font=ThemeDB.fallback_font
	func unit_texture(_unit: Dictionary) -> Texture2D:return null

class SummaryHost extends Control:
	var content
	var assets=SummaryAssets.new()
	var settings={"ui_scale":1.0}
	var match_controller={}
	var selected_unit_id=""
	var selected_city_id=""
	var selected_poi_id=""
	var selected_terrain_hex=null
	func clear(parent: Node) -> void:
		for child in parent.get_children():parent.remove_child(child);child.queue_free()

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)
func text(node: Node) -> String:
	var result=node.text+"\n" if node is Label else ""
	for child in node.get_children():result+=text(child)
	return result

func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"component_loads_actual_definitions")
	var original=StateBuilder.create(content,"legion_07","zhili",{},"normal")
	var original_hash=ContentRegistry.fingerprint(original)
	var fixture=original.duplicate(true)
	var host=SummaryHost.new();host.content=content;host.match_controller={"state":fixture};root.add_child(host)
	var hud=BattleHUD.new();hud.app=host;hud.selection=Button.new();host.add_child(hud.selection)
	var city=StateAccess.find(fixture,"cities","hankou")
	host.selected_city_id=city.id;hud.refresh_summary()
	verify(text(hud.selection).contains("城防 %d/%d"%[city.fort_hp,city.fort_max_hp]),"initial_city_summary_uses_actual_defense")
	city.fort_hp-=7;hud.refresh_summary()
	verify(text(hud.selection).contains("城防 %d/%d"%[city.fort_hp,city.fort_max_hp]),"city_damage_invalidates_summary")
	city.fort_max_hp+=40;hud.refresh_summary()
	verify(text(hud.selection).contains("城防 %d/%d"%[city.fort_hp,city.fort_max_hp]),"city_defense_capacity_invalidates_summary")
	var retained=hud.selection.get_child(0);hud.refresh_summary()
	verify(hud.selection.get_child(0)==retained,"unchanged_summary_keeps_existing_controls")
	var unit=StateAccess.find(fixture,"units",str(fixture.units[0].id));unit.general_id=null
	host.selected_city_id="";host.selected_unit_id=unit.id;hud.refresh_summary()
	verify(text(hud.selection).contains("兵力 %d/%d"%[unit.hp,unit.max_hp]),"initial_unit_summary_uses_actual_capacity")
	unit.max_hp+=10;hud.refresh_summary()
	verify(text(hud.selection).contains("兵力 %d/%d"%[unit.hp,unit.max_hp]),"unit_capacity_invalidates_summary")
	for definition in content.tables.units:
		if definition.id!=unit.def_id:unit.def_id=definition.id;break
	hud.refresh_summary()
	verify(text(hud.selection).contains(content.definition("units",unit.def_id).name),"unit_definition_invalidates_summary")
	verify(ContentRegistry.fingerprint(original)==original_hash,"fixture_does_not_modify_published_initial_state")
	verify(fixture.combat_random==original.combat_random,"summary_refresh_does_not_consume_random_draws")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"headless_component_fixture":true,"synthetic_gameplay_evidence":false,"physical_android_device_tested":false,"hud_source_sha256":FileAccess.get_sha256("res://presentation/battle_hud.gd")}
	var path="res://reports/battle_summary_tests.json";var args=OS.get_cmdline_user_args()
	if "--evidence-path" in args:path=args[args.find("--evidence-path")+1]
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file=FileAccess.open(path,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("BATTLE_SUMMARY_COMPONENT ",checks.size()," checks / ",failures.size()," failures")
	quit(0 if failures.is_empty() else 1)
