extends ScrollContainer

# Godot 4.7's ScrollContainer drag path consumes mouse events. The game handles
# map touch/pinch directly and disables mouse emulation, so scroll surfaces also
# need a direct touch path. Normal mouse wheel, focus and scrollbar behavior stay
# native. Child GUI signals preserve normal hit testing, clipping and modal order.
var touch_index=-1
var touch_origin=Vector2.ZERO
var scroll_origin=Vector2.ZERO
var touch_scrolling=false

func _ready() -> void:watch(self)

func watch(node: Node) -> void:
	if node!=self and node is ScrollContainer:return
	if node.get_meta("direct_touch_scroll",0)==get_instance_id():return
	node.set_meta("direct_touch_scroll",get_instance_id())
	node.child_entered_tree.connect(watch)
	if node is Control:node.gui_input.connect(func(event):route_touch(event,node))
	for child in node.get_children():watch(child)

func route_touch(event: InputEvent, source: Control) -> void:
	if not is_visible_in_tree() or event.device==InputEvent.DEVICE_ID_EMULATION:return
	if event is InputEventScreenTouch:
		if event.pressed:
			if touch_index>=0:return
			var at=source.get_global_transform()*event.position
			if not get_global_rect().has_point(at):return
			touch_index=event.index;touch_origin=at
			scroll_origin=Vector2(scroll_horizontal,scroll_vertical);touch_scrolling=false
		elif event.index==touch_index:
			if touch_scrolling:
				propagate_notification(Control.NOTIFICATION_SCROLL_END);scroll_ended.emit()
				get_viewport().set_input_as_handled()
			touch_index=-1;touch_scrolling=false
	elif event is InputEventScreenDrag and event.index==touch_index:
		var delta=source.get_global_transform()*event.position-touch_origin
		if not touch_scrolling and delta.length()>maxf(10,scroll_deadzone):
			touch_scrolling=true
			# Native buttons cancel their pending press when scrolling begins.
			propagate_notification(Control.NOTIFICATION_SCROLL_BEGIN);scroll_started.emit()
		if touch_scrolling:
			if horizontal_scroll_mode!=ScrollContainer.SCROLL_MODE_DISABLED:scroll_horizontal=roundi(scroll_origin.x-delta.x)
			if vertical_scroll_mode!=ScrollContainer.SCROLL_MODE_DISABLED:scroll_vertical=roundi(scroll_origin.y-delta.y)
			get_viewport().set_input_as_handled()

func _notification(what: int) -> void:
	if what==NOTIFICATION_VISIBILITY_CHANGED and not is_visible_in_tree():
		touch_index=-1;touch_scrolling=false
