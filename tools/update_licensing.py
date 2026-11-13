#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Maintain provenance inventory and corresponding-source archive; never auto-license new assets."""
from pathlib import Path
import argparse, datetime, hashlib, json, shutil, zipfile

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'asset-manifest.json'
ARCHIVE = ROOT / 'releases' / 'saimoncity-fuente.zip'
NOTICES = ['LICENSE', 'LICENSE.md', 'NOTICE.md', 'MARCA.md', 'CONTRIBUTING.md',
           'THIRD-PARTY-NOTICES.md', 'BLOCKCHAIN-Y-PROPIEDAD.md',
           'MANTENIMIENTO-LICENCIAS.md', 'CREDITOS-RECURSOS.md',
           'ADOPCION.md', 'asset-manifest.json', 'source-manifest.json']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files():
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if set(rel.parts) & {'.git', '__pycache__', 'releases', 'previews', 'Respaldos', '.venv', 'node_modules'}:
            continue
        if p.name == '.DS_Store' or p.name == 'lifein.json' or p.name.startswith('.env') or p.suffix in {'.pyc', '.pyo', '.pem', '.key'}:
            continue
        allowed_dirs = {'play', 'movil', 'graphics', 'tools', 'LICENSES'}
        allowed_root = set(NOTICES) | {'README.md', 'SCHEMA.md', 'server.py', 'jugar.sh', 'render.yaml', '.python-version', '.gitignore'}
        if rel.parts[0] not in allowed_dirs and rel.as_posix() not in allowed_root and rel.as_posix() not in {'data/el-jardin.json', 'data/el-jardin.js', 'data/el-jardin.json.license', 'data/el-jardin.js.license', 'README.md.license', 'SCHEMA.md.license'}:
            continue
        yield p, rel


def build_source_archive():
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    temp = ARCHIVE.with_suffix('.zip.tmp')
    try:
        with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED) as package:
            for p, rel in source_files():
                package.write(p, Path('SaimonCity') / rel)
        temp.replace(ARCHIVE)
    finally:
        if temp.exists():
            temp.unlink()
    return ARCHIVE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Only report; do not write files')
    parser.add_argument('--build-source-only', action='store_true', help='Build the source archive without changing licensing or backups')
    args = parser.parse_args()
    if args.build_source_only:
        print(build_source_archive())
        return 0
    state = json.loads(STATE.read_text(encoding='utf-8'))
    old = {a['path']: a for a in state['assets']}
    new, changes = [], []
    for p in sorted((ROOT / 'graphics').rglob('*')):
        if not p.is_file() or p.name.endswith('.license') or p.name == '.DS_Store':
            continue
        rel, sha = p.relative_to(ROOT).as_posix(), digest(p)
        entry = dict(old.pop(rel, {}))
        if not entry:
            entry = {'path': rel, 'sha256': sha, 'author': None, 'source': None,
                     'release_approved': False, 'license': None, 'status': 'pending-provenance'}
            if rel.startswith('graphics/brand/'):
                entry.update(license='LicenseRef-Saimon-Brand-Reserved', status='brand-excluded')
            changes.append({'path': rel, 'change': 'new'})
        elif entry['sha256'] != sha:
            state.setdefault('previous_versions', []).append(dict(entry))
            entry.update(sha256=sha, release_approved=False,
                         status='brand-excluded' if rel.startswith('graphics/brand/') else 'changed-review-required')
            entry['review_note'] = 'Review new material; permissions on previously licensed versions and portions are unchanged.'
            changes.append({'path': rel, 'change': 'modified'})
        new.append(entry)
    for entry in old.values():
        state.setdefault('previous_versions', []).append(dict(entry))
        changes.append({'path': entry['path'], 'change': 'removed'})
    if args.check:
        print(json.dumps({'inventory_changes': changes, 'source_archive_exists': ARCHIVE.is_file(),
                          'assets': len(new)}, ensure_ascii=False, indent=2))
        return 1 if changes or not ARCHIVE.is_file() else 0
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = ROOT.parent / 'Respaldos' / ('licencias-' + stamp)
    backup.mkdir(parents=True, exist_ok=False)
    for name in NOTICES:
        p = ROOT / name
        if p.is_file():
            shutil.copy2(p, backup / name)
    if (ROOT / 'LICENSES').is_dir():
        shutil.copytree(ROOT / 'LICENSES', backup / 'LICENSES')
    if ARCHIVE.exists():
        shutil.copy2(ARCHIVE, backup / ARCHIVE.name)
    state['assets'] = new
    if changes:
        state['last_inventory_update'] = datetime.date.today().isoformat()
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for item in changes:
        if item['change'] == 'removed':
            continue
        p = ROOT / (item['path'] + '.license')
        if not p.exists():
            p.write_text('New asset: provenance and rights review required. No new license automatically granted.\n', encoding='utf-8')
    build_source_archive()
    print(json.dumps({'updated_assets': len(new), 'changes_requiring_review': changes,
                      'source_archive': str(ARCHIVE), 'backup': str(backup)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
