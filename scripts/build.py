"""Build static site assets and reproducible experimental distribution packages."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.1'  # Distribution version; guide protocol remains 0.1.0.
SITE = ROOT / 'site'
DOWNLOADS = SITE / 'downloads'


def make_zip(path, files):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, source in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main():
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    files = {
        'protocol.md': ROOT / 'ask-giorgio/references/protocol.md',
        'ask-giorgio-profile.md': ROOT / 'ask-giorgio/references/visitor-profile-template.md',
        'LICENSE': ROOT / 'LICENSE',
        'LICENSE-CONTENT.txt': ROOT / 'LICENSE-CONTENT.txt',
        'README.txt': ROOT / 'packaging/README.txt',
    }
    for name, source in files.items():
        (DOWNLOADS / name).write_bytes(source.read_bytes())
    make_zip(DOWNLOADS / f'ask-giorgio-universal-v{VERSION}.zip', {
        'ask-giorgio-universal/' + name: source for name, source in files.items()
    })
    make_zip(DOWNLOADS / f'ask-giorgio-skill-v{VERSION}.zip', {
        'ask-giorgio/SKILL.md': ROOT / 'ask-giorgio/SKILL.md',
        'ask-giorgio/references/protocol.md': files['protocol.md'],
        'ask-giorgio/references/visitor-profile-template.md': files['ask-giorgio-profile.md'],
        'ask-giorgio/LICENSE': files['LICENSE'],
        'ask-giorgio/LICENSE-CONTENT.txt': files['LICENSE-CONTENT.txt'],
    })
    manifest = {}
    for path in sorted(DOWNLOADS.iterdir()):
        if path.is_file() and path.name != 'manifest.json':
            data = path.read_bytes()
            manifest[path.name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    (DOWNLOADS / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    html = (ROOT / 'website/index.template.html').read_text()
    script = (ROOT / 'website/guide.template.js').read_text()
    assert script.count('__PROTOCOL__') == 1
    script = script.replace('__PROTOCOL__', json.dumps(files['protocol.md'].read_text(), ensure_ascii=False))
    (SITE / 'index.html').write_text(html.replace('__VERSION__', VERSION))
    (SITE / 'guide.js').write_text(script)
    (SITE / 'credits.html').write_bytes((ROOT / 'website/credits.html').read_bytes())
    print(f'Built distribution {VERSION}: static website and {len(manifest)} download files')


if __name__ == '__main__':
    main()
