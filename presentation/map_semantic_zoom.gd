class_name MapSemanticZoom
extends RefCounted

# Symbols change with map scale; the geographic anchor and the rules entity do
# not. A city with a garrison keeps its city ring around the formation counter.
const DETAIL_ZOOM=.56
const REGIONAL_ZOOM=.20

static func band(zoom: float) -> String:
	return "detail" if zoom>=DETAIL_ZOOM else "regional" if zoom>=REGIONAL_ZOOM else "overview"

static func detailed(zoom: float, prominent: bool=false) -> bool:
	return zoom>=DETAIL_ZOOM or prominent and zoom>=REGIONAL_ZOOM

static func unit_size(zoom: float) -> Vector2:
	var width=clampf(42.0*zoom,8.0,15.0) if zoom>=REGIONAL_ZOOM else minf(56.0*zoom,8.0)
	return Vector2(width,width*.72)

static func unit_border(zoom: float) -> float:
	return minf(.8,unit_size(zoom).x*.12)

static func city_radius(zoom: float, rank: int) -> float:
	var radius=clampf(23.0*zoom,4.2,7.0) if zoom>=REGIONAL_ZOOM else clampf(28.0*zoom,1.7,4.0)
	return radius+(1.0 if rank>=5 and zoom>=REGIONAL_ZOOM else 0.0)
