import xml.etree.ElementTree as ET
import sys
from pathlib import Path

xml_path = Path('pytest_results.xml')
if not xml_path.exists():
    print('pytest_results.xml not found. Run pytest with --junitxml=pytest_results.xml', file=sys.stderr)
    sys.exit(2)

root = ET.parse(xml_path).getroot()

# Find all testcase elements
testcases = root.findall('.//testcase')
if not testcases:
    print('No testcases found in junit xml', file=sys.stderr)
    sys.exit(2)

# Group by module (module derived from classname)
modules = []
module_map = {}
total = 0
for tc in testcases:
    total += 1
    classname = tc.attrib.get('classname', '')
    parts = classname.split('.') if classname else []
    if parts and parts[0] == 'tests' and len(parts) >= 3:
        module_name = '.'.join(parts[:3])
    elif parts and parts[0] == 'tests' and len(parts) == 2:
        module_name = '.'.join(parts[:2])
    else:
        # fallback to full classname
        module_name = classname

    if module_name not in module_map:
        module_map[module_name] = {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
        modules.append(module_name)

    module_map[module_name]['tests'] += 1
    # Check for failure/error/skip children under testcase
    if tc.find('failure') is not None:
        module_map[module_name]['failures'] += 1
    if tc.find('error') is not None:
        module_map[module_name]['errors'] += 1
    if tc.find('skipped') is not None:
        module_map[module_name]['skipped'] += 1

# Print per-module (file) status in original order
running = 0
for mod in modules:
    info = module_map[mod]
    tests = info['tests']
    failures = info['failures']
    errors = info['errors']
    status = 'PASSED' if (failures + errors) == 0 else 'FAILED'
    running += tests
    pct = int((running / total) * 100) if total > 0 else 100
    # convert module name to path-like
    if mod.startswith('tests.'):
        path = mod.replace('.', '/') + '.py'
    else:
        path = mod
    print(f"{path} {status} [{pct:3d}%]")

print()
print(f"Total: {total} tests — {running} processed")
