extends "res://presentation/map_view.gd"

static var legacy=false
static var recording=false
static var timings: Array=[]

func draw_static_atlas(view: Rect2) -> void:
	var began=Time.get_ticks_usec()
	if legacy:legacy_draw_static_atlas(view)
	else:super.draw_static_atlas(view)
	if recording:timings.append((Time.get_ticks_usec()-began)/1000.0)

func legacy_draw_static_atlas(view: Rect2) -> void:
	terrain_scenery_draw_count=0
	grounded_scenery_draw_count=0
	operation_grid_drawn_hexes=0
	if territory_qa_mode:
		draw_territory_qa_atlas(view)
		return
	draw_landscape(view)
	if show_terrain and zoom>=(.025 if atlas_preview else .10):
		var scenery=relief.visible_features(view)
		if MapArtBank.available():
			scenery.append_array(map_details.visible_features(view,zoom))
			scenery.sort_custom(func(a,b):return a.position.y<b.position.y if a.position.y!=b.position.y else a.asset_id<b.asset_id)
		for feature in scenery:
			var image=assets.texture("scenery",feature.asset_id)
			var has_original=image!=null
			if image==null:image=assets.texture("scenery","scenery_atlas_ridge_01" if feature.terrain_id in ["mountain","peak"] else "scenery_atlas_hill_01")
			if image!=null:
				terrain_scenery_draw_count+=1
				# Preserve the painterly 2.5D source while letting the surveyed
				# terrain mesh, cell texture and faction wash remain visible through
				# the lower silhouette.  This is a presentation tint only.
				var feature_alpha=.98 if feature.terrain_id in ["mountain","peak"] else .94
				if state.map.get("strategic_scale",false):feature_alpha+=.04
				if feature.has("texture_rect") and has_original:
					var rectangle: Rect2=feature.texture_rect;rectangle.position+=feature.position
					var grounded=feature.terrain_id in ["hill","mountain","peak"] and material!=null
					if grounded:grounded=GroundMaterialBlend.draw_grounded_feature(self,image,rectangle,feature.asset_id,minf(feature_alpha,1.0))
					if grounded:grounded_scenery_draw_count+=1
					else:draw_texture_rect(image,rectangle,false,Color(1.0,1.0,.98,minf(feature_alpha,1.0)))
				else:sprite(image,feature.position,feature.bounds,Color(1.0,1.0,.98,minf(feature_alpha,1.0)))
	if show_control and not state.map.get("strategic_scale",false):draw_control_zones(view,true)
	for points in region_lines:
		if points.size()>1:draw_polyline(points,Color(.95,.96,.84,.38),1.6/zoom,true);draw_polyline(points,Color(.22,.31,.30,.42 if zoom<.52 else .22),.7/zoom,true)
	if show_rail and not territory_qa_mode:
		for edge in state.map.rail_edges:
			if state.date<edge.active_from:continue
			var points=PackedVector2Array()
			for position in edge.path_hexes:points.append(HexGrid.to_world(HexGrid.coordinate(position)))
			if points.size()<2:continue
			points=rounded_track(points)
			var color=Color("a65438") if edge.damage!="intact" else (Color("242823") if MovementRules.rail_available(state,edge) else Color("898574"))
			draw_polyline(points,Color(.93,.86,.67,.83),maxf(7,2.4/zoom),true);draw_polyline(points,color,maxf(4.2,1.1/zoom),true)
			for i in range(points.size()-1):
				if zoom<.32:break
				var delta=points[i+1]-points[i];var perpendicular=delta.normalized().orthogonal()*3.8
				for step in range(int(delta.length()/9)):
					var p=points[i]+delta.normalized()*step*9;draw_line(p-perpendicular,p+perpendicular,color,1.3,true)
				var normal=delta.normalized().orthogonal()*1.3;draw_line(points[i]+normal,points[i+1]+normal,Color("d4cdb3"),.7,true);draw_line(points[i]-normal,points[i+1]-normal,Color("d4cdb3"),.7,true)
			if edge.damage!="intact":
				var center=points[points.size()/2];draw_line(center-Vector2(10,12),center+Vector2(10,12),Color("a74336"),4,true);draw_line(center+Vector2(-10,12),center+Vector2(10,-12),Color("a74336"),4,true)
	# Known terrain and intelligence-grid outlines are cached; commands remain dynamic.
	# At full-map scale a subpixel grid obscures surveyed coastlines. Tactical
	# zoom keeps the same 48px hex; visit only axial coordinates in this viewport.
	if zoom>=.20:
		var bounds=visible_hex_bounds(view);var low=bounds[0];var high=bounds[1]
		for q in range(low.x,high.x+1):
			for r in range(low.y,high.y+1):
				var cell=presentation_cells.get(Vector2i(q,r),{})
				if cell.is_empty() or (not show_grid and not visible_ids.has(cell.id)):continue
				var p=HexGrid.to_world(Vector2i(q,r))
				if not view.has_point(p):continue
				var outline=HexGrid.corners(p,48);outline.append(outline[0])
				# Keep the operational hex visible without letting the lattice overpower
				# surveyed coastlines, terrain objects and semi-transparent control fields.
				draw_polyline(outline,Color(.94,.97,.94,.16 if show_grid else .065),.55/zoom,true)
				operation_grid_drawn_hexes+=1


func draw_cell_surface_variants(view: Rect2) -> void:
	if legacy:legacy_draw_cell_surface_variants(view)
	else:super.draw_cell_surface_variants(view)

func legacy_draw_cell_surface_variants(view: Rect2) -> void:
	# Regional source geometry chooses a visible seamless ground material.
	# Feathered edges retain the continuous surveyed land underneath, while
	# ownership remains its own translucent layer above the ground.
	terrain_surface_variant_draw_count=0
	var strategic=state.map.get("strategic_scale",false)
	var threshold=0.0 if atlas_preview else .10
	if zoom<threshold:
		# Far overview still draws the relief mesh. Bind its numerical sampler
		# even when the detailed ground-material batches are omitted.
		var ground=map_details.ground_material(strategic) if MapArtBank.available() else null
		relief.shade_field.bind_to(ground,continuous_relief_enabled);material=ground
		return
	if MapArtBank.available():
		var ground=map_details.ground_material(strategic)
		relief.shade_field.bind_to(ground,continuous_relief_enabled)
		material=ground
		var fine_details=zoom>=(.20 if strategic else .28)
		if ground==null and not fine_details:return
		var entries=visible_terrain_entries(view) if fine_details else []
		var batches=map_details.surface_meshes(entries,strategic,12000,ground!=null,true,ground==null)
		# Canvas drawing keeps mesh RIDs. Keep the owning resources alive for
		# the entire cached draw, including textures evicted from the asset LRU.
		ground_material_batches=[]
		var macro_count=0
		if ground!=null:
			var chunks=map_details.continuous_macro_meshes(view);macro_count=chunks.count
			ground_material_batches.append_array(chunks.batches)
		ground_material_batches.append_array(batches.batches)
		for batch in ground_material_batches:
			if batch.get("continuous",false):draw_mesh(batch.mesh,null)
			else:
				var source_texture=assets.texture("tile",batch.asset_id)
				if source_texture!=null:
					batch["texture"]=source_texture
					draw_mesh(batch.mesh,source_texture)
		terrain_surface_variant_draw_count=maxi(batches.count,macro_count)
		return
	var texture=assets.texture("tile","tile_plain_02")
	if texture==null:return
	var max_variants=1500 if strategic else 1900
	for entry in visible_terrain_entries(view):
		if terrain_surface_variant_draw_count>=max_variants:break
		var cell: Dictionary=entry.cell;var kind: String=entry.kind
		if kind!="plain" or not cell.get("render_land_covered",false):continue
		# Deterministic half-density keeps the atlas legible while ensuring the
		# normal play camera never shows a perfectly flat uninterrupted field.
		if absi(hash(str(cell.get("id",HexGrid.key(entry.hex)))))%2!=0:continue
		var center=HexGrid.to_world(entry.hex);var polygon=HexGrid.corners(center,46.0)
		var uvs=PackedVector2Array()
		for index in range(polygon.size()):
			var angle=float(index)*PI/3.0;uvs.append(Vector2(.5+.5*cos(angle),.5+.5*sin(angle)))
		var alpha=.025 if strategic else .04
		var colors=PackedColorArray()
		for index in range(polygon.size()):colors.append(Color(1,1,1,alpha))
		draw_polygon(polygon,colors,uvs,texture);terrain_surface_variant_draw_count+=1


func prefetch_map_scenery() -> void:
	if not legacy:super.prefetch_map_scenery()
