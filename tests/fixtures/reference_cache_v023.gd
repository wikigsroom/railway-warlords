extends RefCounted

# Archived and current algorithms use different private index key formats.
# Their comparison must not read each other's derived, non-state indexes.
static var context=RulesQueryCache.new()

static func current() -> RulesQueryCache:
	return context
