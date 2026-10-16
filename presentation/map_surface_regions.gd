class_name MapSurfaceRegions
extends RefCounted

# Potential biogeographic regions guide representative ground art. This layer
# never claims historical land-use/soil surveying, or creates forest/water.
static var catalog: Dictionary={}

static func data() -> Dictionary:
	if catalog.is_empty() and FileAccess.file_exists("res://presentation/data/surface_regions.json"):
		var parsed=JSON.parse_string(FileAccess.get_file_as_string("res://presentation/data/surface_regions.json"))
		if parsed is Dictionary:catalog=parsed
	return catalog

static func apply(cells: Dictionary, map_id: String) -> Dictionary:
	var source=data();var rows: Dictionary=source.get("maps",{}).get(map_id,{})
	var counts: Dictionary={};var assigned=0
	for hex in cells:
		var cell: Dictionary=cells[hex]
		var row=rows.get(str(cell.get("id","")),[])
		if row.size()!=2 or TerrainVisuals.kind_for_cell(cell)!="plain":continue
		cell["presentation_surface_family"]=str(row[0])
		cell["presentation_ecoregion_id"]=int(row[1])
		counts[row[0]]=int(counts.get(row[0],0))+1;assigned+=1
	return {"source_id":source.get("source_id",""),"source_year":source.get("source_year",0),"material_assignments":assigned,"families":counts,"source_scope":"biogeographic_ground_material_reference","historical_landuse_survey":false,"rule_maps_modified":false,"water_or_forest_added":false}

static func material_label(cell: Dictionary) -> String:
	var surface_label=MapTerrainSurfaces.label_for(cell)
	if not surface_label.is_empty():return surface_label
	var names={"meadow":"草土地表","dry_grass":"草原旱草","sandy_ground":"细沙地表","arid_gravel":"荒漠砾土","alluvial_soil":"平原与河谷土","wetland_ground":"草甸湿土","rocky_ground":"岩质地表","woodland_floor":"林下腐土","sea_water":"水面"}
	return str(names.get(MapArtBank.material_family(cell),""))
