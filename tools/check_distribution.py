"""Check tracked publication files without reading ignored capture content."""
from pathlib import Path
import re,subprocess,sys
root=Path(__file__).resolve().parents[1]
result=subprocess.run(['git','ls-files','-z'],cwd=root,capture_output=True,check=True)
names=[n for n in result.stdout.decode().split('\0') if n]
assert names,'Stage the source files first, then run the distribution check'
blocked={'.ff','.iwd','.iwi','.uasset','.umap','.obj','.fbx','.bin','.exe','.dll','.zip','.7z','.png','.jpg','.jpeg','.pem','.key'}
errors=[]
for name in names:
    p=root/name
    if p.suffix.lower() in blocked or any(s in ('artifacts','__pycache__','audit') for s in p.parts):errors.append('Generated/private content: '+name)
    if p.stat().st_size>2_000_000:errors.append('Unexpectedly large file: '+name)
    text=p.read_text(encoding='utf-8-sig')
    if re.search(r'(?i)[A-Z]:[\\/]Users[\\/](?!YOURNAME\b)[^\\/\s]+',text):errors.append('Personal absolute path: '+name)
    if re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',text):errors.append('Credential-like content: '+name)
    if p.suffix=='.md':
        for link in re.findall(r'\]\(([^\s)]+)\)',text):
            if '://' in link or link.startswith('#'):continue
            if not (p.parent/link.split('#')[0]).exists():errors.append(f'Broken local link: {name}: {link}')
for required in ('README.md','LICENSE','CREDITS.md','pipeline/NOTICE.md','docs/PHILLIBX-MIT.txt'):
    if required not in names:errors.append('Missing notice/document: '+required)
if errors:print('\n'.join(errors));sys.exit(1)
print(f'PASS: {len(names)} tracked source/documentation files; no blocked assets, detected credentials, personal paths or broken local Markdown links.')
