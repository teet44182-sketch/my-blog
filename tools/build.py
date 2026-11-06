from __future__ import annotations

import html
import math
import os
import re
import shutil
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
TEMPLATES = SRC / 'templates'
CONTENT = ROOT / 'content' / 'posts'
DIST = ROOT / 'dist'
SITE_URL = os.environ.get('SITE_URL', 'https://teet44182-sketch.github.io/my-blog').rstrip('/')
SITE_TITLE = 'my-blog'
SITE_DESCRIPTION = 'Pentest labs, CTF writeups, and attack notes — measured, repeatable, documented.'
BASE_PATH = os.environ.get('SITE_BASE', '').rstrip('/')
if BASE_PATH and not BASE_PATH.startswith('/'):
    BASE_PATH = f'/{BASE_PATH}'
PLATFORMS = {
    'hack-the-box': {
        'name': 'Hack The Box',
        'short': 'HTB',
        'description': 'Hack The Box machines and challenges — recon to root, documented.',
    },
    'portswigger': {
        'name': 'PortSwigger',
        'short': 'PortSwigger',
        'description': 'PortSwigger Web Security Academy writeups and web exploitation notes.',
    },
    'ctf': {
        'name': 'CTF / Competition',
        'short': 'CTF',
        'description': 'CTF and competition writeups — challenges, tooling, lessons learned.',
    },
}
PLATFORM_ORDER = ['hack-the-box', 'portswigger', 'ctf']


def slugify(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text).strip().lower()
    text = re.sub(r'[^\w\s\-ก-๏]', '', text, flags=re.UNICODE)
    text = re.sub(r'[\s_\-]+', '-', text).strip('-')
    return text or 'section'


def inline_format(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r'!\[([^\]]*)\]\((https?://[^)\s]+|/[^)\s]+)\)', lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" loading="lazy">', text)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]+|mailto:[^)\s]+)\)', lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return text


def render_table(rows: list[str]) -> str:
    parsed = []
    for row in rows:
        cells = [cell.strip() for cell in row.strip().strip('|').split('|')]
        parsed.append(cells)
    if len(parsed) < 2:
        return ''.join(f'<p>{inline_format(row)}</p>' for row in rows)

    header = parsed[0]
    body = parsed[2:] if re.fullmatch(r'[:\-|\s]+', parsed[1][0]) or all(re.fullmatch(r'[:\-]+', cell) for cell in parsed[1]) else parsed[1:]
    out = ['<div class="table-wrap"><table><thead><tr>']
    out += [f'<th>{inline_format(cell)}</th>' for cell in header]
    out.append('</tr></thead><tbody>')
    for row in body:
        out.append('<tr>' + ''.join(f'<td>{inline_format(cell)}</td>' for cell in row) + '</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


def render_markdown(md: str) -> tuple[str, list[dict[str, str]]]:
    code_blocks: list[tuple[str, str]] = []

    def stash_code(match: re.Match[str]) -> str:
        code = match.group(1) or match.group(2)
        lang = (match.group(1) or '').strip()
        placeholder = f'@@CODE_BLOCK_{len(code_blocks)}@@'
        code_blocks.append((lang, code))
        return f'\n{placeholder}\n'

    md = re.sub(r'```(\w*)\n(.*?)\n```', lambda m: stash_code(m), md, flags=re.DOTALL)
    md = re.sub(r'```(.*?)```', stash_code, md, flags=re.DOTALL)

    toc: list[dict[str, str]] = []
    html_blocks: list[str] = []
    blocks = re.split(r'\n\s*\n', md.strip())

    for block in blocks:
        lines = [line for line in block.strip('\n').splitlines() if line.strip()]
        if not lines:
            continue

        placeholder = re.fullmatch(r'@@CODE_BLOCK_(\d+)@@', lines[0].strip())
        if placeholder:
            lang, code = code_blocks[int(placeholder.group(1))]
            code_html = html.escape(code, quote=False)
            lang_class = f' class="language-{html.escape(lang, quote=True)}"' if lang else ''
            html_blocks.append(f'<pre><code{lang_class}>{code_html}</code></pre>')
            continue

        if all(re.fullmatch(r'@@CODE_BLOCK_\d+@@', line.strip()) for line in lines):
            for line in lines:
                index = int(re.fullmatch(r'@@CODE_BLOCK_(\d+)@@', line.strip()).group(1))  # type: ignore[union-attr]
                lang, code = code_blocks[index]
                code_html = html.escape(code, quote=False)
                lang_class = f' class="language-{html.escape(lang, quote=True)}"' if lang else ''
                html_blocks.append(f'<pre><code{lang_class}>{code_html}</code></pre>')
            continue

        if lines[0].startswith('#'):
            level = len(lines[0]) - len(lines[0].lstrip('#'))
            level = min(max(level, 1), 4)
            text = lines[0].lstrip('#').strip()
            heading_id = slugify(text)
            html_blocks.append(f'<h{level} id="{heading_id}">{inline_format(text)}</h{level}>')
            if level in (2, 3):
                toc.append({'id': heading_id, 'text': re.sub(r'<[^>]+>', '', inline_format(text))})
            continue

        if len(lines) >= 2 and lines[0].lstrip().startswith('|') and lines[1].lstrip().startswith('|'):
            html_blocks.append(render_table(lines))
            continue

        if all(re.match(r'^\s*[-*]\s+', line) for line in lines):
            items = [re.sub(r'^\s*[-*]\s+', '', line).strip() for line in lines]
            html_blocks.append('<ul>' + ''.join(f'<li>{inline_format(item)}</li>' for item in items) + '</ul>')
            continue

        if all(re.match(r'^\s*\d+\.\s+', line) for line in lines):
            items = [re.sub(r'^\s*\d+\.\s+', '', line).strip() for line in lines]
            html_blocks.append('<ol>' + ''.join(f'<li>{inline_format(item)}</li>' for item in items) + '</ol>')
            continue

        if lines[0].startswith('> '):
            quote = ' '.join(line.removeprefix('> ').strip() for line in lines)
            html_blocks.append(f'<div class="callout">{inline_format(quote)}</div>')
            continue

        html_blocks.append(f'<p>{inline_format(" ".join(line.strip() for line in lines))}</p>')

    return '\n'.join(html_blocks), toc


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', text, flags=re.DOTALL)
    if not match:
        return {}, text
    data = yaml.safe_load(match.group(1)) or {}
    return data, match.group(2)


def platform_from_path(path: Path) -> str:
    relative = path.relative_to(CONTENT)
    if len(relative.parts) < 2:
        return ''
    first = relative.parts[0]
    return first if first in PLATFORMS else ''


def normalize_platform(value: object, path: Path) -> str:
    raw = str(value or '').strip().lower().replace('_', '-').replace(' ', '-')
    aliases = {
        'htb': 'hack-the-box',
        'hackthebox': 'hack-the-box',
        'hack-the-box': 'hack-the-box',
        'portswigger': 'portswigger',
        'port-swigger': 'portswigger',
        'web-security-academy': 'portswigger',
        'ctf': 'ctf',
        'capture-the-flag': 'ctf',
        'competition': 'ctf',
    }
    key = aliases.get(raw, raw)
    if key in PLATFORMS:
        return key

    inferred = platform_from_path(path)
    if inferred:
        return inferred
    if not raw:
        raise ValueError(f'{path}: missing valid platform; expected one of {", ".join(PLATFORM_ORDER)}')
    raise ValueError(f'{path}: unknown platform {value!r}; expected one of {", ".join(PLATFORM_ORDER)}')


def normalize_post(path: Path) -> dict:
    raw = path.read_text(encoding='utf-8')
    meta, markdown = parse_frontmatter(raw)

    slug = meta.get('slug') or path.stem
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', slug):
        raise ValueError(f'{path}: slug must use lowercase letters, numbers and hyphens only')

    platform = normalize_platform(meta.get('platform'), path)
    platform_info = PLATFORMS[platform]
    content_html, toc = render_markdown(markdown)
    words = len(re.findall(r'\S+', markdown))
    read_time = max(1, math.ceil(words / 220))

    raw_date = meta.get('date')
    if isinstance(raw_date, datetime):
        parsed_date = raw_date.date()
    elif isinstance(raw_date, date):
        parsed_date = raw_date
    else:
        parsed_date = datetime.strptime(str(raw_date), '%Y-%m-%d').date()

    return {
        'title': meta['title'],
        'slug': slug,
        'url': f'{BASE_PATH}/writeups/{platform}/{slug}/',
        'section_url': f'{BASE_PATH}/writeups/{platform}/',
        'date': parsed_date.isoformat(),
        'display_date': parsed_date.strftime('%d %b %Y'),
        'category': platform_info['name'],
        'platform': platform,
        'platform_name': platform_info['name'],
        'section': platform_info['name'],
        'source_path': path.relative_to(ROOT).as_posix(),
        'tags': [str(tag) for tag in meta.get('tags', [])],
        'difficulty': str(meta.get('difficulty', 'Unknown')),
        'status': str(meta.get('status', 'Draft')),
        'summary': str(meta.get('summary', '')),
        'content': content_html,
        'toc': toc,
        'read_time': read_time,
        'words': words,
    }


def urlencode(value: object) -> str:
    from urllib.parse import quote
    return quote(str(value), safe='')


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copytree(SRC / 'assets', DIST / 'assets')

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters['urlencode'] = urlencode

    posts = [normalize_post(path) for path in sorted(CONTENT.rglob('*.md'))]
    posts.sort(key=lambda post: post['date'], reverse=True)

    all_categories = Counter(post['category'] for post in posts)
    tags = Counter(tag for post in posts for tag in post['tags'])
    platforms = []
    for key in PLATFORM_ORDER:
        count = sum(1 for post in posts if post['platform'] == key)
        platforms.append({
            'key': key,
            'name': PLATFORMS[key]['name'],
            'short': PLATFORMS[key]['short'],
            'description': PLATFORMS[key]['description'],
            'count': count,
            'url': f'{BASE_PATH}/writeups/{key}/',
        })

    common = {
        'posts': posts,
        'platforms': platforms,
        'categories': dict(sorted(all_categories.items(), key=lambda item: (-item[1], item[0]))),
        'tags': dict(sorted(tags.items(), key=lambda item: (-item[1], item[0]))),
        'site_url': SITE_URL,
        'site_title': SITE_TITLE,
        'base': BASE_PATH,
    }

    write(DIST / 'index.html', env.get_template('home.html').render(
        title=SITE_TITLE,
        description=SITE_DESCRIPTION,
        nav='home',
        **common,
    ))

    write(DIST / 'writeups' / 'index.html', env.get_template('writeups.html').render(
        title=f'Writeups — {SITE_TITLE}',
        description='Pentest writeups grouped by platform: Hack The Box, PortSwigger, and CTF.',
        nav='writeups',
        page_heading='Writeups',
        page_eyebrow='All writeups / archive',
        page_intro='All writeups, searchable by platform, tag, difficulty, and title. Use / to focus search and Esc to clear.',
        active_platform=None,
        filtered_posts=posts,
        **common,
    ))
    write(DIST / 'archive' / 'index.html', (DIST / 'writeups' / 'index.html').read_text(encoding='utf-8'))

    for platform in platforms:
        filtered = [post for post in posts if post['platform'] == platform['key']]
        write(DIST / 'writeups' / platform['key'] / 'index.html', env.get_template('writeups.html').render(
            title=f"{platform['name']} — {SITE_TITLE}",
            description=platform['description'],
            nav='writeups',
            page_heading=platform['name'],
            page_eyebrow=f"Writeups / {platform['short']}",
            page_intro=platform['description'],
            active_platform=platform['key'],
            filtered_posts=filtered,
            **common,
        ))

    for index, post in enumerate(posts):
        same_platform = [candidate for candidate in posts if candidate['platform'] == post['platform']]
        position = same_platform.index(post)
        prev_post = same_platform[position + 1] if position + 1 < len(same_platform) else None
        next_post = same_platform[position - 1] if position > 0 else None
        write(DIST / 'writeups' / post['platform'] / post['slug'] / 'index.html', env.get_template('post.html').render(
            title=f"{post['title']} — {SITE_TITLE}",
            description=post['summary'] or SITE_DESCRIPTION,
            nav='writeups',
            post=post,
            prev_post=prev_post,
            next_post=next_post,
            **common,
        ))

    about_skills = [
        {'name': 'Web Exploitation', 'value': 85},
        {'name': 'Linux / PrivEsc', 'value': 80},
        {'name': 'Network Recon', 'value': 78},
        {'name': 'Active Directory', 'value': 72},
        {'name': 'Documentation', 'value': 88},
    ]
    write(DIST / 'about' / 'index.html', env.get_template('about.html').render(
        title=f'About — {SITE_TITLE}',
        description='About my-blog and how these pentest writeups are organized.',
        nav='about',
        skills=about_skills,
        **common,
    ))

    write(DIST / '404.html', env.get_template('404.html').render(
        title=f'404 — {SITE_TITLE}',
        description='Page not found.',
        nav='',
        **common,
    ))

    rss_items = '\n'.join(
        f'    <item><title>{html.escape(post["title"])}</title><link>{SITE_URL}{post["url"]}</link>'
        f'<guid isPermaLink="true">{SITE_URL}{post["url"]}</guid>'
        f'<description>{html.escape(post["summary"])}</description>'
        f'<pubDate>{datetime.strptime(post["date"], "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 GMT")}</pubDate></item>'
        for post in posts
    )
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{html.escape(SITE_TITLE)}</title>
    <description>{html.escape(SITE_DESCRIPTION)}</description>
    <link>{SITE_URL}/</link>
    <language>th</language>
{rss_items}
  </channel>
</rss>
'''
    write(DIST / 'rss.xml', rss)

    urls = ['/', '/writeups/', '/about/'] + [platform['url'] for platform in platforms] + [post['url'] for post in posts]
    urlset = '\n'.join(f'  <url><loc>{SITE_URL}{url}</loc></url>' for url in urls)
    write(DIST / 'sitemap.xml', f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urlset}
</urlset>
''')
    write(DIST / 'robots.txt', f'User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n')

    print(f'Built {len(posts)} posts -> {DIST}')


if __name__ == '__main__':
    main()
