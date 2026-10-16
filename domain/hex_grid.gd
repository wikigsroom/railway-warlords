class_name HexGrid
extends RefCounted

const DIRECTIONS: Array[Vector2i] = [Vector2i(1,0), Vector2i(1,-1), Vector2i(0,-1), Vector2i(-1,0), Vector2i(-1,1), Vector2i(0,1)]
const RADIUS: float = 48.0

static func coordinate(position: Dictionary) -> Vector2i:
	return Vector2i(int(position.q), int(position.r))

static func position(hex: Vector2i) -> Dictionary:
	return {"q": hex.x, "r": hex.y}

static func key(hex: Vector2i) -> String:
	return "%d,%d" % [hex.x, hex.y]

static func from_key(value: String) -> Vector2i:
	var pieces=value.split(",")
	return Vector2i(int(pieces[0]),int(pieces[1]))

static func distance(a: Vector2i, b: Vector2i) -> int:
	var d = a - b
	return int((absi(d.x) + absi(d.y) + absi(d.x + d.y)) / 2)

static func to_world(hex: Vector2i) -> Vector2:
	return Vector2(1.5 * RADIUS * hex.x, sqrt(3.0) * RADIUS * (hex.y + hex.x * 0.5))

static func from_world(point: Vector2) -> Vector2i:
	var q = point.x * (2.0 / 3.0) / RADIUS
	var r = (-point.x / 3.0 + sqrt(3.0) * point.y / 3.0) / RADIUS
	var cube = Vector3(q, -q-r, r)
	var rounded = Vector3(round(cube.x), round(cube.y), round(cube.z))
	var difference = (rounded - cube).abs()
	if difference.x > difference.y and difference.x > difference.z:
		rounded.x = -rounded.y - rounded.z
	elif difference.y > difference.z:
		rounded.y = -rounded.x - rounded.z
	else:
		rounded.z = -rounded.x - rounded.y
	return Vector2i(int(rounded.x), int(rounded.z))

static func corners(center: Vector2, radius: float = RADIUS) -> PackedVector2Array:
	var result := PackedVector2Array()
	for i in range(6):
		result.append(center + Vector2.from_angle(i * PI / 3.0) * radius)
	return result

static func line(a: Vector2i, b: Vector2i) -> Array:
	var result: Array = []
	var steps = distance(a, b)
	for i in range(steps + 1):
		var t = float(i) / maxf(1.0, steps)
		result.append(from_world(to_world(a).lerp(to_world(b), t)))
	return result
