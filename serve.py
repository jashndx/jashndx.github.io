import os
import re
import sys
import glob
import time
import datetime
import http.server
import socketserver
import webbrowser
from pathlib import Path

PORT = 4000
SITE_DIR = Path("_site")

def parse_frontmatter(content):
    frontmatter = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2]
            for line in fm_text.strip().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    frontmatter[key] = val
    return frontmatter, body.strip()

def md_to_html(text):
    lines = text.splitlines()
    html_lines = []
    in_code = False
    code_lines = []

    for line in lines:
        if line.startswith("```"):
            if in_code:
                in_code = False
                html_lines.append(f"<pre><code>{''.join(code_lines)}</code></pre>")
                code_lines = []
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line + "\n")
            continue

        if line.startswith("# "):
            html_lines.append(f"<h1>{inline_md(line[2:])}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{inline_md(line[3:])}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{inline_md(line[4:])}</h3>")
        elif line.strip() == "":
            continue
        elif line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            html_lines.append(f"<p><em>{inline_md(line[1:-1])}</em></p>")
        else:
            html_lines.append(f"<p>{inline_md(line)}</p>")

    return "\n".join(html_lines)

def inline_md(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    return text

def build_site():
    if not SITE_DIR.exists():
        SITE_DIR.mkdir(parents=True, exist_ok=True)

    # Read layout
    layout_path = Path("_layouts/default.html")
    if layout_path.exists():
        layout = layout_path.read_text(encoding="utf-8")
    else:
        layout = "<html><body>{{ content }}</body></html>"

    # Process posts
    posts = []
    post_files = sorted(glob.glob("_posts/*.md"), reverse=True)

    for pf in post_files:
        p_path = Path(pf)
        content_raw = p_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content_raw)

        # Parse date from filename YYYY-MM-DD-title.md
        fname = p_path.stem
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})-(.*)', fname)
        if date_match:
            date_str = date_match.group(1)
            slug = date_match.group(2)
        else:
            date_str = "2026-08-16"
            slug = fname

        post_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        title = fm.get("title", slug.replace("-", " ").title())
        desc = fm.get("description", "")
        
        # Post URL
        year, month, day = date_str.split("-")
        post_url = f"/{year}/{month}/{day}/{slug}.html"

        posts.append({
            "title": title,
            "date": post_date,
            "date_str": date_str,
            "url": post_url,
            "description": desc,
            "body": body,
            "slug": slug,
            "year": year,
            "month": month,
            "day": day
        })

    # Render each post
    for post in posts:
        post_html_content = md_to_html(post["body"])
        
        # Apply layout
        page_title = post["title"]
        page_date_fmt = post["date"].strftime("%B %d, %Y")

        html = layout
        html = re.sub(r'\{\{\s*page\.title\s*\|\s*default:\s*"([^"]+)"\s*\}\}', page_title, html)
        html = re.sub(r'\{\{\s*page\.title\s*\}\}', page_title, html)

        # Handle {% if page.date %} ... {% endif %}
        date_block = f'<div class="post-date">{page_date_fmt}</div>'
        html = re.sub(r'\{%\s*if page\.date\s*%\}.*?\{%\s*endif\s*%\}', date_block, html, flags=re.DOTALL)

        html = html.replace("{{ content }}", post_html_content)

        # Output to _site/YYYY/MM/DD/slug.html
        out_dir = SITE_DIR / post["year"] / post["month"] / post["day"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{post['slug']}.html").write_text(html, encoding="utf-8")
        
        # Also alias to _site/posts/slug.html and _site/slug/index.html
        alias_dir = SITE_DIR / post["slug"]
        alias_dir.mkdir(parents=True, exist_ok=True)
        (alias_dir / "index.html").write_text(html, encoding="utf-8")

    # Render index.md
    index_path = Path("index.md")
    if index_path.exists():
        index_raw = index_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(index_raw)

        # Process site.posts loop
        loop_match = re.search(r'\{%\s*for post in site\.posts\s*%\}(.*?)\{%\s*endfor\s*%\}', body, re.DOTALL)
        if loop_match:
            item_template = loop_match.group(1)
            items_rendered = []
            for post in posts:
                item_html = item_template
                item_html = item_html.replace('{{ post.date | date: "%b %d, %Y" }}', post["date"].strftime("%b %d, %Y"))
                item_html = item_html.replace('{{ post.url }}', post["url"])
                item_html = item_html.replace('{{ post.title }}', post["title"])
                item_html = item_html.replace('{{ post.description }}', post["description"])
                items_rendered.append(item_html)
            index_content = "".join(items_rendered)
        else:
            index_content = md_to_html(body)

        # Apply layout to index
        html = layout
        html = re.sub(r'\{\{\s*page\.title\s*\|\s*default:\s*"([^"]+)"\s*\}\}', "Jashandeep Singh", html)
        html = re.sub(r'\{\{\s*page\.title\s*\}\}', "Jashandeep Singh", html)
        html = re.sub(r'\{%\s*if page\.date\s*%\}.*?\{%\s*endif\s*%\}', "", html, flags=re.DOTALL)
        html = html.replace("{{ content }}", index_content)

        (SITE_DIR / "index.html").write_text(html, encoding="utf-8")

    print("[SUCCESS] Blog built successfully into _site/")

class AutoRebuildHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def do_GET(self):
        build_site()
        return super().do_GET()

def run_server():
    build_site()
    handler = AutoRebuildHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Serving Jekyll blog preview at http://localhost:{PORT}")
        webbrowser.open(f"http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")

if __name__ == "__main__":
    run_server()
