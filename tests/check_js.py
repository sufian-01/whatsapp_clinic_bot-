import os
import re

js_dir = 'frontend/js'
exports = {}
imports = []

export_pattern = re.compile(r'export\s+(?:(?:default\s+)?(?:const|let|var|function|class)\s+([a-zA-Z0-9_$]+)|\{([^}]+)\})')
import_pattern = re.compile(r'import\s+\{([^}]+)\}\s+from\s+[\'"]([^\'"]+)[\'"]')

for root, dirs, files in os.walk(js_dir):
    for f in files:
        if f.endswith('.js'):
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            file_exports = set()
            for m in export_pattern.finditer(content):
                if m.group(1):
                    file_exports.add(m.group(1))
                if m.group(2):
                    for item in m.group(2).split(','):
                        item = item.strip().split(' as ')[0].strip()
                        if item:
                            file_exports.add(item)
            rel_path = os.path.normpath(filepath)
            exports[rel_path] = file_exports

            for m in import_pattern.finditer(content):
                imported_names = [i.strip().split(' as ')[0].strip() for i in m.group(1).split(',') if i.strip()]
                target_rel = m.group(2)
                target_path = os.path.normpath(os.path.join(root, target_rel))
                imports.append((rel_path, target_path, imported_names))

print('=== CHECKING IMPORTS ===')
found_errors = False
for src, target, names in imports:
    target_exp = exports.get(target, None)
    if target_exp is None:
        print(f'ERROR: Target not found: {target} imported from {src}')
        found_errors = True
    else:
        for name in names:
            if name not in target_exp:
                print(f'ERROR: {src} imports "{name}" from {target}, but it is NOT exported! Available: {sorted(list(target_exp))}')
                found_errors = True

if not found_errors:
    print('All imports and exports matched successfully!')

