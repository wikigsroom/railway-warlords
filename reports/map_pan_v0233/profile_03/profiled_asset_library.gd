extends "res://presentation/asset_library.gd"
static var recording=false
static var misses: Array=[]
static var requests=0
func texture(category: String, id: String) -> Texture2D:
    var missed=not textures.has(category+"/"+id);var began=Time.get_ticks_usec()
    var result=super.texture(category,id)
    if recording:
        requests+=1
        if missed:misses.append({"category":category,"id":id,"milliseconds":(Time.get_ticks_usec()-began)/1000.0,"cache_entries":map_texture_order.size()})
    return result
