#!/usr/bin/env python3
"""
微信公众号文章发布脚本
用法: python3 publish.py --md ~/文章.md --cover ~/封面图.png [--title "标题"] [--digest "摘要"]
"""

import os, sys, json, re, argparse, urllib.request, urllib.parse, mimetypes
from pathlib import Path

APPID  = os.environ.get("WECHAT_MP_APPID", "")
SECRET = os.environ.get("WECHAT_MP_SECRET", "")
BASE   = "https://api.weixin.qq.com/cgi-bin"

# ─── 样式变量 ──────────────────────────────────────────────────────────────
P       = 'margin:0 0 1.4em 0; font-size:17px; line-height:1.9; color:#333; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",sans-serif;'
STRONG  = 'font-weight:700; color:#1a1a1a;'
H2_WRAP = 'margin:2.2em 0 1em 0;'
H2_NUM  = 'display:inline-block; background:#1a1a1a; color:#fff; font-size:12px; font-weight:700; letter-spacing:0.12em; padding:3px 10px; border-radius:2px; margin-right:8px; vertical-align:middle; font-family:monospace;'
H2_TXT  = 'font-size:22px; font-weight:700; color:#1a1a1a; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif; vertical-align:middle;'
IMG_S   = 'width:100%; border-radius:6px; margin:1.4em 0; display:block;'
QUOTE   = 'border-left:3px solid #1a1a1a; margin:1.6em 0; padding:0.8em 1.2em; background:#f7f7f7; border-radius:0 4px 4px 0;'
QUOTE_P = 'margin:0; font-size:15px; color:#555; line-height:1.8; letter-spacing:0.05em; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;'
HR_S    = 'border:none; border-top:1px solid #e8e8e8; margin:2.4em 0;'
CLOSE   = 'background:#1a1a1a; color:#fff; padding:2em 1.6em; border-radius:8px; margin:2em 0;'
CLOSE_P = 'margin:0.6em 0; font-size:16px; line-height:1.8; color:rgba(255,255,255,0.8); font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;'
FINAL   = 'margin:1.2em 0 0 0; font-size:20px; font-weight:700; color:#fff; letter-spacing:0.02em; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;'

# ─── 工具函数 ──────────────────────────────────────────────────────────────

def api_get(path, params=None):
    url = f"{BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())

def api_post(path, payload, token):
    url = f"{BASE}/{path}?access_token={token}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data,
          headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def upload_multipart(url, filepath, field="media"):
    """Multipart form upload for image files."""
    import uuid, http.client
    from urllib.parse import urlparse
    boundary = uuid.uuid4().hex
    parsed = urlparse(url)
    fp = Path(filepath)
    mime = mimetypes.guess_type(str(fp))[0] or "image/png"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{fp.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + fp.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    conn = http.client.HTTPSConnection(parsed.netloc)
    conn.request("POST", parsed.path + ("?" + parsed.query if parsed.query else ""),
                 body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    resp = conn.getresponse()
    return json.loads(resp.read())

def get_token():
    """获取 access_token，最多重试 5 次（应对多出口 IP 问题）。"""
    if not APPID or not SECRET:
        sys.exit("❌ 未设置 WECHAT_MP_APPID / WECHAT_MP_SECRET 环境变量")
    for i in range(5):
        r = api_get("token", {"grant_type": "client_credential",
                               "appid": APPID, "secret": SECRET})
        if "access_token" in r:
            print(f"✅ Token 获取成功（第{i+1}次）")
            return r["access_token"]
        err = r.get("errmsg", "")
        ip_match = re.search(r"invalid ip (\S+)", err)
        if ip_match:
            print(f"⚠️  IP {ip_match.group(1)} 未在白名单，重试...")
        else:
            sys.exit(f"❌ Token 获取失败: {r}")
    sys.exit("❌ 多次重试后仍无法获取 Token，请检查 IP 白名单配置")

def upload_article_image(token, filepath):
    """上传文章内图片，返回可用 URL。"""
    url = f"{BASE}/media/uploadimg?access_token={token}"
    r = upload_multipart(url, filepath)
    if "url" in r:
        print(f"  📷 图片上传成功: {Path(filepath).name}")
        return r["url"]
    sys.exit(f"❌ 图片上传失败: {r}")

def upload_cover(token, filepath):
    """上传封面图为永久素材，返回 media_id。"""
    url = f"{BASE}/material/add_material?access_token={token}&type=image"
    r = upload_multipart(url, filepath)
    if "media_id" in r:
        print(f"  🖼️  封面上传成功: {Path(filepath).name}")
        return r["media_id"]
    sys.exit(f"❌ 封面上传失败: {r}")

# ─── Markdown → HTML ──────────────────────────────────────────────────────

def md_to_html(md_text, img_map):
    """将 Markdown 转为微信兼容的内联样式 HTML。"""
    lines = md_text.split("\n")
    html_parts = []
    h2_counter = 0
    in_blockquote = False
    buffer = []

    def flush_p():
        if buffer:
            text = " ".join(buffer).strip()
            if text:
                html_parts.append(f'<p style="{P}">{text}</p>')
            buffer.clear()

    for line in lines:
        # 替换本地图片路径为 WeChat CDN URL
        for local_path, cdn_url in img_map.items():
            line = line.replace(local_path, cdn_url)

        # 图片行
        img_match = re.match(r'!\[.*?\]\((.+?)\)', line.strip())
        if img_match:
            flush_p()
            src = img_match.group(1)
            html_parts.append(f'<img src="{src}" style="{IMG_S}"/>')
            continue

        # H1 → 忽略（作为标题字段单独传）
        if re.match(r'^# ', line):
            continue

        # H2 → 带编号的章节头
        h2_match = re.match(r'^## (.+)', line)
        if h2_match:
            flush_p()
            h2_counter += 1
            num = str(h2_counter).zfill(2)
            title = h2_match.group(1)
            # 去掉 "01 " 前缀（如果原文已有）
            title = re.sub(r'^\d{2}\s+', '', title)
            html_parts.append(
                f'<div style="{H2_WRAP}">'
                f'<span style="{H2_NUM}">{num}</span>'
                f'<span style="{H2_TXT}">{title}</span>'
                f'</div>'
            )
            continue

        # blockquote
        bq_match = re.match(r'^> (.+)', line)
        if bq_match:
            flush_p()
            text = bq_match.group(1)
            text = apply_inline(text)
            html_parts.append(
                f'<div style="{QUOTE}"><p style="{QUOTE_P}">{text}</p></div>'
            )
            continue

        # 分割线
        if re.match(r'^---+$', line.strip()):
            flush_p()
            html_parts.append(f'<hr style="{HR_S}"/>')
            continue

        # 空行
        if not line.strip():
            flush_p()
            continue

        # 普通段落
        buffer.append(apply_inline(line.strip()))

    flush_p()
    return '\n'.join(html_parts)


def apply_inline(text):
    """处理内联 Markdown 样式（粗体、代码）。"""
    # **粗体**
    text = re.sub(r'\*\*(.+?)\*\*', f'<strong style="{STRONG}">\\1</strong>', text)
    # `代码`
    text = re.sub(r'`(.+?)`', '<code style="background:#f5f5f5; padding:2px 6px; border-radius:3px; font-family:monospace; font-size:15px;">\\1</code>', text)
    return text


def build_closing_html(last_sentence):
    """为文章最后一句创建黑底大字结尾块。"""
    parts = last_sentence.split("，", 1)
    if len(parts) == 2:
        return (f'<div style="{CLOSE}">'
                f'<p style="{CLOSE_P}">{parts[0]}，</p>'
                f'<p style="{FINAL}">{parts[1]}</p>'
                f'</div>')
    return f'<div style="{CLOSE}"><p style="{FINAL}">{last_sentence}</p></div>'

# ─── 主流程 ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="微信公众号文章发布工具")
    parser.add_argument("--md",     required=True, help="Markdown 文件路径")
    parser.add_argument("--cover",  required=True, help="封面图路径")
    parser.add_argument("--title",  default="",    help="文章标题（默认取 Markdown H1）")
    parser.add_argument("--digest", default="",    help="文章摘要（默认取正文前50字）")
    args = parser.parse_args()

    md_path = Path(args.md).expanduser()
    cover_path = Path(args.cover).expanduser()

    if not md_path.exists():
        sys.exit(f"❌ Markdown 文件不存在: {md_path}")
    if not cover_path.exists():
        sys.exit(f"❌ 封面图不存在: {cover_path}")

    md_text = md_path.read_text(encoding="utf-8")

    # 提取标题
    title = args.title
    if not title:
        h1 = re.search(r'^# (.+)', md_text, re.MULTILINE)
        title = h1.group(1).strip() if h1 else md_path.stem

    print(f"\n📝 文章：{title}")
    print("─" * 50)

    # Step 1: Token
    print("\n[1/4] 获取 access_token...")
    token = get_token()

    # Step 2: 上传文章内图片
    print("\n[2/4] 上传文章内图片...")
    img_map = {}
    for m in re.finditer(r'!\[.*?\]\((.+?)\)', md_text):
        local = m.group(1)
        if local.startswith("http"):
            continue
        lp = Path(local.replace("%20", " ").replace("%E5%B9%B4", "年")
                  .replace("%E6%9C%88", "月").replace("%E6%97%A5", "日")
                  .replace("%3A", ":").replace("%20", " "))
        # URL decode
        try:
            decoded = urllib.parse.unquote(local)
            lp = Path(decoded).expanduser()
        except:
            lp = Path(local).expanduser()
        if lp.exists():
            cdn_url = upload_article_image(token, str(lp))
            img_map[local] = cdn_url
        else:
            print(f"  ⚠️  找不到图片: {local}，跳过")

    # Step 3: 上传封面
    print("\n[3/4] 上传封面图...")
    cover_id = upload_cover(token, str(cover_path))

    # Step 4: 生成 HTML + 创建草稿
    print("\n[4/4] 生成 HTML 并创建草稿...")
    html_content = f'<section style="max-width:680px; margin:0 auto; padding:0 4px;">\n'
    html_content += md_to_html(md_text, img_map)
    html_content += '\n</section>'

    notes_dir = Path("~/doc/notes").expanduser()
    notes_dir.mkdir(parents=True, exist_ok=True)
    safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
    html_path = notes_dir / f"{safe_title}.html"
    html_path.write_text(html_content, encoding="utf-8")
    print(f"  💾 HTML 已保存: {html_path}")

    digest = args.digest or re.sub(r'[#\n\*\[\]!]', '', md_text)[:60].strip() + "..."

    payload = {
        "articles": [{
            "title": title,
            "author": "",
            "digest": digest,
            "content": html_content,
            "content_source_url": "",
            "thumb_media_id": cover_id,
            "need_open_comment": 1,
            "only_fans_can_comment": 0
        }]
    }

    result = api_post("draft/add", payload, token)

    if "media_id" in result:
        draft_id = result["media_id"]
        print(f"\n✅ 草稿创建成功！")
        print(f"   草稿 ID: {draft_id}")
        print(f"\n👉 下一步：打开 mp.weixin.qq.com → 内容 → 草稿箱 → 找到《{title}》→ 发布")
    else:
        print(f"\n❌ 草稿创建失败: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
