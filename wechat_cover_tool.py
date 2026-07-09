#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信推文封面提取工具（本机版，零依赖）
- 支持批量链接（每行一个），自动解析每篇图文的 1:1 / 235:100 封面
- 自动命名：序号_标题_比例.jpg，支持一键打包 zip 下载
- 输入链接 -> 服务端抓取并解析 var msgList；或粘贴网页源代码（离线兜底）
运行：python wechat_cover_tool.py  然后浏览器打开 http://localhost:8765
"""
import gzip
import io
import json
import re
import urllib.parse
import urllib.request
import zlib
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8765
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>微信推文封面提取工具</title>
<style>
  :root{
    --bg:#0a1730; --panel:#0e2143; --panel2:#102a52; --line:#23406e;
    --silver:#c2cad8; --lab:#f3f6fb; --accent:#3b82f6; --accent2:#38bdf8;
    --txt:#e8eef7; --muted:#8aa0c0;
  }
  *{box-sizing:border-box}
  body{margin:0;background:radial-gradient(1200px 600px at 70% -10%,#13294f 0%,var(--bg) 60%);
       color:var(--txt);font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;min-height:100vh}
  .wrap{max-width:1000px;margin:0 auto;padding:28px 20px 60px}
  h1{font-size:22px;margin:0 0 4px;letter-spacing:.5px}
  h1 .dot{color:var(--accent2)}
  .sub{color:var(--muted);font-size:13px;margin-bottom:22px}
  .card{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);
        border-radius:14px;padding:18px;box-shadow:0 10px 30px rgba(0,0,0,.35)}
  .row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}
  textarea{width:100%;background:#08152e;border:1px solid var(--line);color:var(--lab);
        border-radius:10px;padding:12px 14px;font-size:14px;outline:none;font-family:inherit}
  textarea:focus{border-color:var(--accent)}
  textarea{min-height:120px;resize:vertical}
  button{cursor:pointer;border:none;border-radius:10px;padding:12px 18px;font-size:14px;font-weight:600;
         background:linear-gradient(180deg,var(--accent),#2563eb);color:#fff;transition:.15s;white-space:nowrap}
  button:hover{filter:brightness(1.1)}
  button.ghost{background:transparent;border:1px solid var(--line);color:var(--silver)}
  button:disabled{opacity:.5;cursor:not-allowed}
  .toggle{color:var(--accent2);font-size:13px;cursor:pointer;margin-top:14px;display:inline-block;user-select:none}
  .srcbox{display:none;margin-top:12px}
  #status{margin:16px 0;font-size:13px;color:var(--muted);min-height:18px}
  .err{color:#fca5a5}
  .ok{color:#86efac}
  .sources{display:grid;gap:22px}
  .src{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:rgba(255,255,255,.02)}
  .src .shead{padding:12px 16px;border-bottom:1px solid var(--line);background:rgba(56,189,248,.08);
             font-size:12px;color:var(--silver);word-break:break-all;display:flex;gap:8px;align-items:center}
  .src .shead .idx{background:var(--accent2);color:#06243a;border-radius:6px;padding:1px 8px;font-weight:700}
  .articles{display:grid;gap:16px;padding:16px}
  .art{border:1px solid var(--line);border-radius:12px;overflow:hidden}
  .art .head{padding:10px 14px;border-bottom:1px solid var(--line);background:rgba(59,130,246,.07)}
  .art .head .t{font-size:14px;font-weight:600;color:var(--lab);word-break:break-word}
  .imgs{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:14px}
  @media(max-width:640px){.imgs{grid-template-columns:1fr}}
  .imgbox{border:1px solid var(--line);border-radius:12px;background:#06122a;overflow:hidden;display:flex;flex-direction:column}
  .imgbox .tag{font-size:12px;color:var(--accent2);padding:8px 12px;border-bottom:1px solid var(--line)}
  .imgbox img{width:100%;display:block;background:#0b1c3a;min-height:120px;object-fit:contain}
  .imgbox .acts{padding:10px 12px;display:flex;gap:8px;border-top:1px solid var(--line)}
  .imgbox .acts a,.imgbox .acts button{flex:1;text-align:center;font-size:12px;padding:9px 8px;text-decoration:none}
  .imgbox .acts a{background:linear-gradient(180deg,var(--accent),#2563eb);color:#fff;border-radius:8px}
  .imgbox .acts button{background:transparent;border:1px solid var(--line);color:var(--silver);border-radius:8px}
  .imgbox .acts button:hover{background:rgba(255,255,255,.05)}
  .url{font-size:11px;color:var(--muted);padding:0 12px 10px;word-break:break-all;font-family:ui-monospace,monospace}
  .topbar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}
  .foot{margin-top:26px;color:var(--muted);font-size:12px;line-height:1.7}
  .foot code{background:#08152e;border:1px solid var(--line);padding:2px 6px;border-radius:6px;color:var(--silver)}
</style>
</head>
<body>
<div class="wrap">
  <h1>微信推文封面提取 <span class="dot">·</span> 1:1 &amp; 235:100</h1>
  <div class="sub">支持批量链接，自动命名，一键打包下载。数据不出本机。</div>

  <div class="card">
    <div class="topbar">
      <div style="font-size:13px;color:var(--silver)">推文链接（每行一个，支持批量）</div>
      <button id="zipBtn" class="ghost" disabled>⬇ 打包下载全部封面 (zip)</button>
    </div>
    <textarea id="urls" placeholder="https://mp.weixin.qq.com/s?__biz=...&#10;https://mp.weixin.qq.com/s?__biz=..."></textarea>
    <div class="row" style="margin-top:12px">
      <button id="go">提取</button>
      <span class="toggle" id="toggleSrc" style="margin:0">▸ 链接抓不到？粘贴网页源代码（离线兜底）</span>
    </div>
    <div class="srcbox" id="srcbox">
      <textarea id="src" placeholder="把网页源代码（右键→查看网页源代码 全选复制）粘贴到这里，可多段"></textarea>
      <div style="margin-top:10px"><button class="ghost" id="goSrc">从源代码解析</button></div>
    </div>
  </div>

  <div id="status"></div>
  <div class="sources" id="results"></div>

  <div class="foot">
    说明：<br>
    • <code>cdn_url_1_1</code> → 正方形封面（1:1）；<code>cdn_url_235_100</code> → 横幅封面（235:100）。<br>
    • 自动命名规则：<code>序号_标题_1x1.jpg</code> / <code>序号_标题_235x100.jpg</code>；批量时前缀含来源序号。<br>
    • “打包下载全部封面”会把所有图按上述规则命名后打成 zip。<br>
    • 多图文推文会列出每篇文章的两张图；若链接抓取失败，用“粘贴源代码”方式同样可用。
  </div>
</div>

<script>
const $ = s => document.querySelector(s);
const setStatus = (msg, cls) => { const e=$('#status'); e.textContent=msg; e.className=cls||''; };
const esc = s => (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const sanitize = s => (s||'cover').replace(/[\\/:*?"<>|\n\r\t]+/g,'_').replace(/\s+/g,'_').slice(0,40);

let LAST = {urls:[]};

function imgCard(srcIdx, artIdx, tag, ratio, url){
  if(!url) return '<div class="imgbox"><div class="tag">'+tag+'</div><div class="url">未找到</div></div>';
  const prox='/api/proxy?img='+encodeURIComponent(url);
  const fname=srcIdx+'_'+artIdx+'_'+sanitize(LAST.titleFor(srcIdx,artIdx))+'_'+ratio+'.jpg';
  return '<div class="imgbox">'+
    '<div class="tag">'+tag+'</div>'+
    '<img src="'+prox+'" alt="'+tag+'" loading="lazy"/>'+
    '<div class="url">'+esc(url)+'</div>'+
    '<div class="acts">'+
      '<a href="'+prox+'" download="'+esc(fname)+'">下载</a>'+
      '<button onclick="window.open(\''+prox+'\',\'_blank\')">新窗口</button>'+
    '</div></div>';
}

function render(data){
  const box=$('#results'); box.innerHTML='';
  const sources=data.sources||[];
  const allUrls=[];
  let total=0;
  LAST={urls:[],titleFor:()=> 'cover'};
  if(!sources.length){ setStatus('没有解析到结果，试试粘贴源代码方式。','err'); $('#zipBtn').disabled=true; return; }
  LAST.titleFor=(si,ai)=>{ const s=sources[si]; if(s&&s.articles&&s.articles[ai]) return s.articles[ai].title||'cover'; return 'cover'; };
  setStatus('解析完成：'+sources.length+' 个来源。','ok');
  sources.forEach((s,si)=>{
    allUrls.push(s.url);
    const src=document.createElement('div'); src.className='src';
    let head='<div class="shead"><span class="idx">'+(si+1)+'</span><span>'+esc(s.url||'')+'</span></div>';
    if(s.error){ head+='<div class="shead" style="background:rgba(252,165,165,.1);color:#fca5a5">抓取失败：'+esc(s.error)+'</div>'; }
    let body='<div class="articles">';
    (s.articles||[]).forEach((a,ai)=>{
      total++;
      body+='<div class="art"><div class="head"><div class="t">'+esc(a.title||('第 '+(ai+1)+' 篇'))+'</div></div>'+
            '<div class="imgs">'+ imgCard(si,ai,'1:1 方形','1x1',a.c11)+imgCard(si,ai,'235:100 横幅','235x100',a.c235)+'</div></div>';
    });
    body+='</div>';
    src.innerHTML=head+body; box.appendChild(src);
  });
  LAST.urls=allUrls;
  $('#zipBtn').disabled = allUrls.length===0;
  $('#zipBtn').onclick=()=>{ window.location.href='/api/zip?urls='+encodeURIComponent(allUrls.join('\n')); };
}

async function extract(){
  const urls=$('#urls').value.split('\n').map(x=>x.trim()).filter(Boolean);
  if(!urls.length){ setStatus('请先粘贴至少一个推文链接。','err'); return; }
  setStatus('正在批量抓取并解析 '+urls.length+' 个链接…');
  try{
    const r=await fetch('/api/extract',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({urls})});
    const d=await r.json();
    if(d.error){ setStatus('错误：'+d.error,'err'); return; }
    render(d);
  }catch(e){ setStatus('请求失败：'+e.message+'，可改用粘贴源代码方式。','err'); }
}
async function extractSrc(){
  const src=$('#src').value;
  if(!src.trim()){ setStatus('请先粘贴网页源代码。','err'); return; }
  setStatus('正在解析源代码…');
  try{
    const r=await fetch('/api/parse',{method:'POST',headers:{'Content-Type':'text/plain'},body:src});
    const d=await r.json();
    if(d.error){ setStatus('错误：'+d.error,'err'); return; }
    render({sources:[{url:'(粘贴的源代码)',articles:d.articles||[]}]});
  }catch(e){ setStatus('解析失败：'+e.message,'err'); }
}

$('#go').onclick=extract;
$('#goSrc').onclick=extractSrc;
$('#toggleSrc').onclick=()=>{const b=$('#srcbox');b.style.display=b.style.display==='block'?'none':'block';
  $('#toggleSrc').textContent=(b.style.display==='block'?'▾':'▸')+' 链接抓不到？粘贴网页源代码（离线兜底）';};
</script>
</body>
</html>"""


def fetch_html(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": "https://mp.weixin.qq.com/",
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "identity",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        return _decode_body(resp)


def extract_balanced(html, marker):
    i = html.find(marker)
    if i == -1:
        return None
    i += len(marker)
    while i < len(html) and html[i] in " \t\r\n":
        i += 1
    if i >= len(html):
        return None
    open_ch = html[i]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    in_str = False
    esc = False
    j = i
    while j < len(html):
        c = html[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return html[i:j + 1]
        j += 1
    return None


def parse_articles(html):
    import html as _html
    articles = []

    def pick_banner(d):
        for k in ("cdn_url_235_100", "cdn_url_235_1", "cdn_url_16_9", "cdn_url_2_1"):
            if isinstance(d, dict):
                v = d.get(k)
                if v:
                    return v
        return ""

    # 1) 优先 msgList（多图文场景）
    mlist_raw = extract_balanced(html, "var msgList = ")
    parsed = False
    if mlist_raw:
        try:
            items = json.loads(mlist_raw)
            for it in items:
                if not isinstance(it, dict):
                    continue
                entries = [it]
                ext = it.get("app_msg_ext_info") or {}
                if isinstance(ext, dict):
                    sub = ext.get("multi_app_msg_item_list") or []
                    if isinstance(sub, list):
                        entries.extend(sub)
                for e in entries:
                    if not isinstance(e, dict):
                        continue
                    sq = e.get("cdn_url_1_1") or ""
                    banner = pick_banner(e)
                    t = e.get("title") or it.get("title") or ""
                    if sq or banner:
                        articles.append({"title": t, "c11": sq, "c235": banner,
                                         "cover": e.get("cover") or e.get("img_url") or ""})
            parsed = any(a["c11"] or a["c235"] for a in articles)
        except Exception:
            parsed = False

    # 2) 回退：全局提取所有 cdn_url_X_Y 字段（兼容无 msgList / 独立 var 声明 / 单篇）
    if not parsed:
        fields = {}
        for m in re.finditer(r'(?:var\s+)?(cdn_url_\d+_\d+)\s*[:=]\s*["\']([^"\']+)["\']', html):
            fields.setdefault(m.group(1), m.group(2))
        if fields:
            title = ""
            mt = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if mt:
                title = _html.unescape(mt.group(1))
            sq = fields.get("cdn_url_1_1", "")
            banner = (fields.get("cdn_url_235_100") or fields.get("cdn_url_235_1")
                      or fields.get("cdn_url_16_9") or fields.get("cdn_url_2_1") or "")
            if sq or banner:
                articles.append({"title": title, "c11": sq, "c235": banner, "cover": ""})
                parsed = True

    # 3) 去重
    seen = set()
    out = []
    for a in articles:
        key = (a["c11"], a["c235"])
        if key in seen:
            continue
        seen.add(key)
        if a["c11"] or a["c235"]:
            out.append(a)
    return out


def _decode_body(resp):
    data = resp.read()
    enc = (resp.headers.get("Content-Encoding") or "").lower()
    if enc == "gzip":
        data = gzip.decompress(data)
    elif enc == "deflate":
        data = zlib.decompress(data)
    charset = resp.headers.get_content_charset() or "utf-8"
    return data.decode(charset, errors="replace")


def proxy_image(url):
    """抓取图片，返回 (二进制数据, Content-Type)。自动处理 gzip/deflate。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": "https://mp.weixin.qq.com/",
        "Accept": "image/webp,image/*,*/*;q=0.8",
        "Accept-Encoding": "identity",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
        if enc == "gzip":
            data = gzip.decompress(data)
        elif enc == "deflate":
            data = zlib.decompress(data)
        return data, (resp.headers.get("Content-Type") or "image/jpeg")


def sanitize(name):
    name = re.sub(r'[\\/:*?"<>|\n\r\t]+', "_", name or "cover")
    name = re.sub(r'\s+', "_", name).strip("_.")
    return name[:50] or "cover"


def collect_sources(urls):
    sources = []
    for url in urls:
        try:
            html = fetch_html(url)
            arts = parse_articles(html)
            sources.append({"url": url, "articles": arts, "error": None})
        except Exception as e:
            sources.append({"url": url, "articles": [], "error": str(e)[:300]})
    return sources


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, headers=None, binary=False):
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if binary:
            self.wfile.write(body)
        else:
            self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, PAGE, {"Content-Type": "text/html; charset=utf-8"})
            return
        if parsed.path == "/api/proxy":
            qs = urllib.parse.parse_qs(parsed.query)
            img = qs.get("img", [""])[0]
            if not img:
                self._send(400, "missing img", {})
                return
            try:
                data, cd = proxy_image(img)
                ext = ".jpg"
                mt = re.search(r"\.([a-z0-9]+)(?:\?|$)", img, re.I)
                if mt and mt.group(1).lower() in ("jpg", "jpeg", "png", "gif", "webp", "bmp"):
                    ext = "." + mt.group(1).lower()
                if ext == ".jpeg":
                    ext = ".jpg"
                self._send(200, data, {
                    "Content-Type": cd,
                    "Content-Disposition": 'attachment; filename="wechat_cover%s"' % ext,
                    "Cache-Control": "no-store",
                }, binary=True)
            except Exception as e:
                self._send(502, ("proxy error: " + str(e))[:300], {})
            return
        if parsed.path == "/api/zip":
            qs = urllib.parse.parse_qs(parsed.query)
            raw = qs.get("urls", [""])[0]
            urls = [u.strip() for u in raw.split("\n") if u.strip()]
            if not urls:
                self._send(400, "missing urls", {})
                return
            try:
                sources = collect_sources(urls)
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                    for si, s in enumerate(sources):
                        for ai, a in enumerate(s.get("articles", [])):
                            title = sanitize(a.get("title") or "cover")
                            for ratio, key in (("1x1", "c11"), ("235x100", "c235")):
                                u = a.get(key)
                                if not u:
                                    continue
                                try:
                                    imgdata, _ = proxy_image(u)
                                except Exception:
                                    continue
                                ext = ".jpg"
                                mt = re.search(r"\.([a-z0-9]+)(?:\?|$)", u, re.I)
                                if mt and mt.group(1).lower() in ("jpg", "jpeg", "png", "gif", "webp", "bmp"):
                                    ext = "." + mt.group(1).lower()
                                if ext == ".jpeg":
                                    ext = ".jpg"
                                fname = "%02d_%02d_%s_%s%s" % (si + 1, ai + 1, title, ratio, ext)
                                z.writestr(fname, imgdata)
                data = buf.getvalue()
                self._send(200, data, {
                    "Content-Type": "application/zip",
                    "Content-Disposition": 'attachment; filename="wechat_covers.zip"',
                    "Cache-Control": "no-store",
                }, binary=True)
            except Exception as e:
                self._send(500, ("zip error: " + str(e))[:300], {})
            return
        self._send(404, "not found", {})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        if parsed.path == "/api/extract":
            try:
                payload = json.loads(body.decode("utf-8", errors="replace"))
                urls = payload.get("urls") or []
                if isinstance(urls, str):
                    urls = [u.strip() for u in urls.split("\n") if u.strip()]
            except Exception:
                urls = []
            if not urls:
                self._send(400, json.dumps({"error": "缺少 urls"}, ensure_ascii=False),
                           {"Content-Type": "application/json; charset=utf-8"})
                return
            try:
                sources = collect_sources(urls)
                self._send(200, json.dumps({"sources": sources}, ensure_ascii=False),
                           {"Content-Type": "application/json; charset=utf-8"})
            except Exception as e:
                self._send(200, json.dumps({"error": str(e)[:300]}, ensure_ascii=False),
                           {"Content-Type": "application/json; charset=utf-8"})
            return
        if parsed.path == "/api/parse":
            src = body.decode("utf-8", errors="replace")
            try:
                arts = parse_articles(src)
                self._send(200, json.dumps({"articles": arts}, ensure_ascii=False),
                           {"Content-Type": "application/json; charset=utf-8"})
            except Exception as e:
                self._send(200, json.dumps({"error": str(e)[:300]}, ensure_ascii=False),
                           {"Content-Type": "application/json; charset=utf-8"})
            return
        self._send(404, "not found", {})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    srv = HTTPServer(("127.0.0.1", PORT), Handler)
    print("微信推文封面提取工具已启动 -> http://localhost:%d" % PORT)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
