"""Distribution integrity checks; run with python3 -m unittest discover -s tests."""
from pathlib import Path
import hashlib
import json
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / 'site/downloads'
VERSION = '0.1.1'

class Packages(unittest.TestCase):
    def test_downloads_preserve_canonical_sources_and_licenses(self):
        expected = {
            'protocol.md': ROOT / 'ask-giorgio/references/protocol.md',
            'ask-giorgio-profile.md': ROOT / 'ask-giorgio/references/visitor-profile-template.md',
            'LICENSE': ROOT / 'LICENSE',
            'LICENSE-CONTENT.txt': ROOT / 'LICENSE-CONTENT.txt',
            'README.txt': ROOT / 'packaging/README.txt',
        }
        for name, source in expected.items():
            with self.subTest(name=name):
                self.assertTrue((DOWNLOADS / name).is_file(), f'Missing public download: {name}')
                self.assertEqual((DOWNLOADS / name).read_bytes(), source.read_bytes())
        for kind in ['skill', 'universal']:
            archive = DOWNLOADS / f'ask-giorgio-{kind}-v{VERSION}.zip'
            self.assertTrue(archive.is_file(), archive.name)
            mapping = ({
                'ask-giorgio/SKILL.md': ROOT / 'ask-giorgio/SKILL.md',
                'ask-giorgio/references/protocol.md': expected['protocol.md'],
                'ask-giorgio/references/visitor-profile-template.md': expected['ask-giorgio-profile.md'],
                'ask-giorgio/LICENSE': expected['LICENSE'],
                'ask-giorgio/LICENSE-CONTENT.txt': expected['LICENSE-CONTENT.txt'],
            } if kind == 'skill' else {
                'ask-giorgio-universal/' + name: source for name, source in expected.items()
            })
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(sorted(z.namelist()), sorted(mapping))
                self.assertIsNone(z.testzip())
                for name, source in mapping.items():
                    self.assertEqual(z.read(name), source.read_bytes(), name)
        manifest = json.loads((DOWNLOADS / 'manifest.json').read_text())
        files = {p.name for p in DOWNLOADS.iterdir() if p.is_file() and p.name != 'manifest.json'}
        self.assertEqual(set(manifest), files)
        for name, entry in manifest.items():
            data = (DOWNLOADS / name).read_bytes()
            self.assertEqual(entry, {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})

if __name__ == '__main__':
    unittest.main()
