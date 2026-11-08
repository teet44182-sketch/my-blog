from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'content' / 'posts'

PLATFORMS = {
    'hack-the-box': {'name': 'Hack The Box', 'prefix': 'htb'},
    'portswigger': {'name': 'PortSwigger', 'prefix': 'portswigger'},
    'ctf': {'name': 'CTF / Competition', 'prefix': 'ctf'},
}

DIFFICULTIES = ['Easy', 'Medium', 'Hard', 'Insane', 'Unknown']
STATUSES = ['Draft', 'Solved', 'Partial']


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text.encode('ascii', 'ignore').decode('ascii'))
    text = re.sub(r'[\s_\-]+', '-', text).strip('-')
    return text


def choose_platform(value: str | None) -> str:
    if value:
        return value
    print('เลือก platform:')
    for index, (key, info) in enumerate(PLATFORMS.items(), 1):
        print(f'  {index}. {info["name"]} ({key})')
    while True:
        choice = input('> ').strip().lower()
        if choice in PLATFORMS:
            return choice
        try:
            index = int(choice)
            if 1 <= index <= len(PLATFORMS):
                return list(PLATFORMS)[index - 1]
        except ValueError:
            pass
        print('ใส่หมายเลขหรือชื่อ platform เช่น hack-the-box')


def ask(value: str | None, label: str, required: bool = False) -> str:
    if value is not None:
        value = value.strip()
        if required and not value:
            raise SystemExit(f'{label} ห้ามว่าง')
        return value
    while True:
        value = input(f'{label}: ').strip()
        if value or not required:
            return value
        print(f'{label} ห้ามว่าง')


def choose_difficulty(value: str | None) -> str:
    if value:
        if value in DIFFICULTIES:
            return value
        raise SystemExit(f'difficulty ต้องเป็นหนึ่งใน: {", ".join(DIFFICULTIES)}')
    print('Difficulty:')
    for index, item in enumerate(DIFFICULTIES, 1):
        print(f'  {index}. {item}')
    value = input('> [Enter = Unknown] ').strip()
    if not value:
        return 'Unknown'
    try:
        index = int(value)
        if 1 <= index <= len(DIFFICULTIES):
            return DIFFICULTIES[index - 1]
    except ValueError:
        pass
    if value in DIFFICULTIES:
        return value
    raise SystemExit(f'difficulty ไม่ถูกต้อง: {value}')


def choose_status(value: str | None) -> str:
    if value:
        if value in STATUSES:
            return value
        raise SystemExit(f'status ต้องเป็นหนึ่งใน: {", ".join(STATUSES)}')
    print('Status:')
    for index, item in enumerate(STATUSES, 1):
        print(f'  {index}. {item}')
    value = input('> [Enter = Draft] ').strip()
    if not value:
        return 'Draft'
    try:
        index = int(value)
        if 1 <= index <= len(STATUSES):
            return STATUSES[index - 1]
    except ValueError:
        pass
    if value in STATUSES:
        return value
    raise SystemExit(f'status ไม่ถูกต้อง: {value}')


def parse_tags(value: str | None) -> list[str]:
    raw = value if value is not None else input('Tags (คั่นด้วย comma): ')
    tags = [tag.strip().lower() for tag in raw.split(',') if tag.strip()]
    return tags


def build_slug(platform: str, title: str, slug: str | None) -> str:
    if slug:
        candidate = slugify(slug)
    else:
        candidate = slugify(title)
        prefix = PLATFORMS[platform]['prefix']
        candidate = f'{prefix}-{candidate}' if candidate else f'{prefix}-writeup'
    if not candidate:
        raise SystemExit('slug ว่างเปล่า กรุณาใส่ title หรือ --slug')
    return candidate


def open_file(path: Path) -> None:
    code = shutil.which('code')
    if code:
        subprocess.Popen([code, '-r', str(path)])
        return
    if sys.platform.startswith('win'):
        import os
        os.startfile(path)  # type: ignore[attr-defined]
        return
    subprocess.Popen(['xdg-open', str(path)])


def parse_frontmatter_file(path: Path) -> dict:
    text = path.read_text(encoding='utf-8')
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n?', text, flags=re.DOTALL)
    if not match:
        raise SystemExit(f'{path}: ไม่เจอ YAML frontmatter')
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise SystemExit(f'{path}: YAML ไม่ถูกต้อง: {exc}') from None


def frontmatter_date(value: object) -> str:
    if hasattr(value, 'isoformat'):
        return str(value.isoformat()).split('T')[0]
    return str(value or '').strip().split('T')[0]


def main() -> None:
    parser = argparse.ArgumentParser(description='Create a new pentest writeup markdown file.')
    parser.add_argument('--platform', choices=list(PLATFORMS), help='hack-the-box | portswigger | ctf')
    parser.add_argument('--title', help='Writeup title')
    parser.add_argument('--slug', help='Custom slug (lowercase letters, numbers, hyphens)')
    parser.add_argument('--difficulty', choices=DIFFICULTIES, help='Easy | Medium | Hard | Insane | Unknown')
    parser.add_argument('--status', choices=STATUSES, help='Draft | Solved | Partial')
    parser.add_argument('--tags', default=None, help='Comma-separated tags, e.g. sqli,web,burp')
    parser.add_argument('--summary', default=None, help='Short summary for listings and history')
    parser.add_argument('--date', default=None, help='YYYY-MM-DD; default today')
    parser.add_argument('--open', action='store_true', help='Open the created file in VS Code/default editor')
    parser.add_argument('--force', action='store_true', help='Overwrite existing file')
    parser.add_argument('--language', choices=['en', 'th'], default='en', help='Output language; files become <slug>.en.md or <slug>.th.md')
    parser.add_argument('--from-en', metavar='SLUG', help='Create TH file from existing <SLUG>.en.md; only valid with --language th')
    args = parser.parse_args()

    platform = choose_platform(args.platform)
    source_meta: dict = {}
    from_en_slug = slugify(args.from_en or '')

    if args.from_en:
        if args.language != 'th':
            raise SystemExit('--from-en ใช้ได้เฉพาะกับ --language th')
        if not from_en_slug:
            raise SystemExit('--from-en ต้องเป็น slug เช่น htb-faaaround')
        if args.slug and slugify(args.slug) != from_en_slug:
            raise SystemExit('--slug ต้องตรงกับ --from-en เพื่อให้คู่ EN/TH เป็นโพสต์เดียวกัน')

        source_path = CONTENT / platform / f'{from_en_slug}.en.md'
        if not source_path.exists():
            raise SystemExit(f'ไม่เจอ English source: {source_path}')
        source_meta = parse_frontmatter_file(source_path)
        source_platform = str(source_meta.get('platform') or platform).strip().lower().replace('_', '-').replace(' ', '-')
        if source_platform != platform:
            raise SystemExit(f'platform mismatch: source เป็น {source_platform!r} แต่เลือก {platform!r}')

        slug = from_en_slug
        title = ask(args.title, 'Title (Thai)', required=True)
        post_date = args.date or frontmatter_date(source_meta.get('date')) or date.today().isoformat()
        difficulty = args.difficulty or str(source_meta.get('difficulty') or 'Unknown')
        if difficulty not in DIFFICULTIES:
            raise SystemExit(f'difficulty ใน source ไม่ถูกต้อง: {difficulty}')
        status = args.status or 'Draft'
        tags = parse_tags(args.tags) if args.tags is not None else [str(tag) for tag in (source_meta.get('tags') or [])]
        summary = ask(args.summary, 'Summary (Thai, optional)')
    else:
        title = ask(args.title, 'Title', required=True)
        difficulty = choose_difficulty(args.difficulty)
        status = choose_status(args.status)
        tags = parse_tags(args.tags)
        summary = ask(args.summary, 'Summary (optional)')
        post_date = args.date or date.today().isoformat()
        slug = build_slug(platform, title, args.slug)

    try:
        datetime_value = date.fromisoformat(post_date)
    except ValueError:
        raise SystemExit('--date ต้องเป็น YYYY-MM-DD') from None

    target = CONTENT / platform / f'{slug}.{args.language}.md'
    if target.exists() and not args.force:
        raise SystemExit(f'ไฟล์มีอยู่แล้ว: {target} (ใช้ --force ถ้าตั้งใจทับ)')

    target.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = {
        'title': title,
        'slug': slug,
        'date': datetime_value.isoformat(),
        'platform': platform,
        'category': PLATFORMS[platform]['name'],
        'language': args.language,
        'tags': tags,
        'difficulty': difficulty,
        'status': status,
        'summary': summary,
    }
    template = f'''{yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()}
---
## Scope

- Target / lab:
- Out of scope:

## Recon

-

## Exploit

-

## Result

-

## Fix / Lesson

-

'''
    target.write_text(f'---\n{template}', encoding='utf-8')

    print(f'Created: {target}')
    print(f'Next: python {ROOT / "tools" / "build.py"}')
    if args.open:
        open_file(target)


if __name__ == '__main__':
    main()
