"""Conservative source dependencies for native headless regression freshness."""
from pathlib import Path
import hashlib
import re
from functools import lru_cache

P = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def script_classes():
    scripts = list(P.rglob('*.gd'))
    scripts = [p for p in scripts if not any(part in {'.godot', 'build'} for part in p.relative_to(P).parts)]
    classes = {}
    for path in scripts:
        match = re.search(r'^class_name\s+(\w+)', path.read_text(encoding='utf-8'), re.M)
        if match:
            classes[match.group(1)] = path
    return classes


@lru_cache(maxsize=None)
def dependencies(check):
    classes = script_classes()
    pending = [P / 'tests' / (check + '.gd')]
    used = set()
    while pending:
        path = pending.pop()
        if path in used:
            continue
        if not path.is_file():
            raise ValueError('Missing regression dependency: ' + str(path))
        used.add(path)
        text = path.read_text(encoding='utf-8')
        # Include even references in comments/strings: excess dependencies are
        # safer than missing a dynamically selected class or resource.
        tokens = set(re.findall(r'\b\w+\b', text))
        pending.extend(source for name, source in classes.items() if name in tokens)
        for relative in re.findall(r'res://([^\s\"\'()]+\.(?:gd|tscn))', text):
            pending.append(P / relative)
    used.update([P / 'project.godot', P / 'export_presets.cfg'])
    for folder in ('content', 'presentation/data', 'schemas', 'tests/fixtures', 'assets'):
        used.update(path for path in (P / folder).rglob('*') if path.is_file()
                    and path.suffix in {'.json', '.png', '.wav', '.otf', '.ttf', '.tres', '.gdshader'})
    return sorted(used)


def identity(check):
    paths = dependencies(check)
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(P).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest(), max(path.stat().st_mtime for path in paths)


def modified(check):
    return max(path.stat().st_mtime for path in dependencies(check))
