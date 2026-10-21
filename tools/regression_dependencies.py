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
    used.update(data_dependencies())
    return sorted(used)


@lru_cache(maxsize=1)
def data_dependencies():
    used = set()
    for folder in ('content', 'presentation/data', 'schemas', 'tests/fixtures', 'assets'):
        used.update(path for path in (P / folder).rglob('*') if path.is_file()
                    and path.suffix in {'.json', '.png', '.wav', '.ogg', '.mp3', '.otf', '.ttf', '.tres', '.gdshader'})
    return sorted(used)


def identity(check):
    paths = dependencies(check)
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(P).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest(), max(path.stat().st_mtime for path in paths)


def identities(checks):
    """Read each dependency once; retain each check's exact legacy SHA preimage.

    Every dependency list is a sorted subset of the sorted union. Feeding a
    path's bytes to its subscribers in that union order is therefore identical
    to identity(check), including its path spelling and byte concatenation.
    There is no persistent digest cache or metadata substitute for file bytes.
    """
    checks = list(dict.fromkeys(checks))
    digests = {check: hashlib.sha256() for check in checks}
    changed = {check: 0.0 for check in checks}
    subscribers = {}
    for check in checks:
        for path in dependencies(check):
            subscribers.setdefault(path, []).append(check)
    for path in sorted(subscribers):
        before = path.stat()
        members = subscribers[path]
        prefix = path.relative_to(P).as_posix().encode()
        states = [digests[check] for check in members]
        for digest in states:
            digest.update(prefix)
        with path.open('rb') as stream:
            while chunk := stream.read(1024 * 1024):
                for digest in states:
                    digest.update(chunk)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('Regression dependency changed while hashing: ' + str(path))
        for check in members:
            changed[check] = max(changed[check], after.st_mtime)
    return {check: (digests[check].hexdigest(), changed[check]) for check in checks}


def modified(check):
    return max(path.stat().st_mtime for path in dependencies(check))
