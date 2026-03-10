# coding=utf-8
"""
NewsNow 风格 HTML 报告渲染模块 — V2 像素精确版

严格对齐 NewsNow 暗色模式设计 Token (来自 card.tsx + uno.config.ts + globals.css):
  - 页面背景: bg-base dark => bg-dark-600 (#1e1e1e)
  - sprinkle: radial-gradient(ellipse 80% 80% at 50% -30%, rgba(color-400,0.3), transparent)
  - 卡片外壳: h-500px rounded-2xl p-4 bg-{color} bg-op-40!
  - 卡片内容: bg-base bg-op-70! rounded-2xl p-2 (即 rgba(30,30,30,0.70))
  - 网格: gap 24px, minmax(350px, 1fr)
  - 列表项: flex gap-2, hover:bg-neutral-400/10 rounded-md, 无 border-bottom
  - 序号: bg-neutral-400/10 min-w-6 rounded-md text-sm (圆角 6px)
  - 标题: text-base (16px), visited: text-neutral-400
  - 滚动条: rgba(255,255,255,0.44)
  - 动画: stagger fadeUp, 0.08s 间隔
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from trendradar.report.helpers import html_escape
from trendradar.ai.formatter import render_ai_analysis_html_rich


# ---------------------------------------------------------------------------
# 平台颜色映射（对齐 NewsNow shared/sources 配色）
# ---------------------------------------------------------------------------
PLATFORM_COLORS = {
    "zhihu": "#1e80ff", "知乎": "#1e80ff",
    "weibo": "#ff8200", "微博": "#ff8200",
    "baidu": "#306cff", "百度": "#306cff",
    "douyin": "#111111", "抖音": "#111111",
    "bilibili": "#fb7299", "b站": "#fb7299",
    "toutiao": "#ff0000", "头条": "#ff0000",
    "wallstreetcn": "#3a83f7", "华尔街": "#3a83f7",
    "cls": "#f4451e", "财联社": "#f4451e",
    "thepaper": "#eb1a1a", "澎湃": "#eb1a1a",
    "ithome": "#d32f2f", "it之家": "#d32f2f",
    "eastmoney": "#cf1322", "东方财富": "#cf1322",
    "sspai": "#da282a", "少数派": "#da282a",
    "coolapk": "#11ab60", "酷安": "#11ab60",
    "tieba": "#4e6ef2", "贴吧": "#4e6ef2",
    "36kr": "#0084ff", "36氪": "#0084ff",
    "gelonghui": "#0084ff", "格隆汇": "#0084ff",
    "huxiu": "#e71a0f", "虎嗅": "#e71a0f",
    "juejin": "#2080ff", "掘金": "#2080ff",
}


def _to_rgba(hex_color: str, alpha: float) -> str:
    """HEX -> rgba()"""
    color = (hex_color or "#6366f1").strip("#")
    if len(color) != 6:
        return f"rgba(99, 102, 241, {alpha})"
    r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def _get_platform_color(label: str) -> str:
    source = (label or "").lower()
    for key, value in PLATFORM_COLORS.items():
        if key in source:
            return value
    return "#6366f1"


def _rank_badge(title_data: Dict) -> str:
    ranks = title_data.get("ranks", [])
    if not ranks:
        return ""
    min_rank = min(ranks)
    max_rank = max(ranks)
    threshold = title_data.get("rank_threshold", 10)
    rank_class = ""
    if min_rank <= 3:
        rank_class = "top"
    elif min_rank <= threshold:
        rank_class = "high"
    rank_text = str(min_rank) if min_rank == max_rank else f"{min_rank}-{max_rank}"
    return f'<span class="rank-num {rank_class}">{rank_text}</span>'


def _title_line(title_data: Dict) -> str:
    escaped_title = html_escape(title_data.get("title", ""))
    link_url = title_data.get("mobile_url") or title_data.get("url", "")
    if link_url:
        return f'<a href="{html_escape(link_url)}" target="_blank" class="news-link">{escaped_title}</a>'
    return escaped_title


def _news_row(title_data: Dict, idx: int, display_mode: str) -> str:
    is_new = title_data.get("is_new", False)
    new_tag = '<span class="new-badge">NEW</span>' if is_new else ""
    extra_bits: list[str] = []
    if display_mode == "keyword":
        sn = title_data.get("source_name", "")
        if sn:
            extra_bits.append(f'<span class="extra-info">{html_escape(sn)}</span>')
    else:
        kw = title_data.get("matched_keyword", "")
        if kw:
            extra_bits.append(f'<span class="extra-info">[{html_escape(kw)}]</span>')
    rank_html = _rank_badge(title_data)
    if rank_html:
        extra_bits.append(rank_html)
    time_display = title_data.get("time_display", "")
    if time_display:
        simple_time = time_display.replace(" ~ ", "~").replace("[", "").replace("]", "")
        extra_bits.append(f'<span class="extra-info time-info">{html_escape(simple_time)}</span>')
    count_info = title_data.get("count", 1)
    if count_info and count_info > 1:
        extra_bits.append(f'<span class="extra-info hot-count">{count_info}次</span>')
    extra_html = ""
    if extra_bits:
        extra_html = f'<span class="row-extra">{" ".join(extra_bits)}</span>'
    return (
        f'<a class="news-row">'
        f'<span class="row-idx">{idx}</span>'
        f'<span class="row-body">'
        f'<span class="row-title">{_title_line(title_data)}{new_tag}</span>'
        f'{extra_html}'
        f'</span></a>'
    )


def _regroup_by_source(stats: List[Dict]) -> List[Dict]:
    grouped: Dict[str, List[Dict]] = {}
    for stat in stats:
        word = stat.get("word", "")
        for td in stat.get("titles", []):
            sn = td.get("source_name", "未知来源")
            item = dict(td)
            item.setdefault("matched_keyword", word)
            grouped.setdefault(sn, []).append(item)
    result = [
        {"word": sn, "count": len(titles), "percentage": 0, "titles": titles}
        for sn, titles in grouped.items()
    ]
    result.sort(key=lambda x: x["count"], reverse=True)
    return result


def _card(label: str, count: int, idx: int, total: int,
          items_html: str, color: str) -> str:
    shell_bg = _to_rgba(color, 0.40)
    sprinkle = (
        f"radial-gradient(ellipse 80% 80% at 50% -30%, "
        f"{_to_rgba(color, 0.30)}, rgba(255,255,255,0))"
    )
    sub_text = f"{idx}/{total}" if total > 0 else ""
    delay = (idx - 1) * 0.08 if idx > 0 else 0
    return (
        f'<section class="card-shell" '
        f'style="background:{shell_bg};animation-delay:{delay:.2f}s">'
        f'<div class="card-head">'
        f'<div class="card-head-left">'
        f'<span class="card-name-wrap">'
        f'<span class="card-name">{html_escape(label)}</span>'
        f'<span class="card-sub">{sub_text}</span>'
        f'</span></div>'
        f'<span class="card-count">{count} 条</span>'
        f'</div>'
        f'<div class="card-inner" style="background-image:{sprinkle}">'
        f'<ol class="card-list">{items_html}</ol>'
        f'</div></section>'
    )


def _cards_grid(stats: List[Dict], display_mode: str) -> str:
    if not stats:
        return ""
    total = len(stats)
    cards = []
    for idx, stat in enumerate(stats, 1):
        label = stat.get("word", "未命名")
        count = stat.get("count", 0)
        color = _get_platform_color(label)
        items_html = "".join(
            _news_row(td, i, display_mode)
            for i, td in enumerate(stat.get("titles", []), 1)
        )
        cards.append(_card(label, count, idx, total, items_html, color))
    return f'<div class="cards-grid">{"".join(cards)}</div>'


def _render_new_section(new_titles: List[Dict]) -> str:
    if not new_titles:
        return ""
    source_cards = []
    for idx, source_data in enumerate(new_titles, 1):
        sn = source_data.get("source_name", "未知来源")
        color = _get_platform_color(sn)
        titles = source_data.get("titles", [])
        items = "".join(
            f'<a class="news-row">'
            f'<span class="row-idx">{i}</span>'
            f'<span class="row-body"><span class="row-title">{_title_line(td)}</span></span>'
            f'</a>'
            for i, td in enumerate(titles, 1)
        )
        source_cards.append(_card(sn, len(titles), idx, len(new_titles), items, color))
    return (
        '<section class="panel-block">'
        '<h2 class="panel-title">🆕 本次新增热点</h2>'
        f'<div class="cards-grid">{"".join(source_cards)}</div>'
        '</section>'
    )


def _render_rss(rss_stats: List[Dict], title: str, display_mode: str) -> str:
    if not rss_stats:
        return ""
    cards = []
    total = len(rss_stats)
    for idx, group in enumerate(rss_stats, 1):
        label = group.get("word", "RSS")
        count = group.get("count", 0)
        items_html = "".join(
            _news_row(td, i, display_mode)
            for i, td in enumerate(group.get("titles", []), 1)
        )
        cards.append(_card(label, count, idx, total, items_html, "#10b981"))
    return (
        '<section class="panel-block">'
        f'<h2 class="panel-title">📰 {html_escape(title)}</h2>'
        f'<div class="cards-grid">{"".join(cards)}</div>'
        '</section>'
    )


# ===================================================================
# 主渲染函数
# ===================================================================
def render_newsnow_html_content(
    report_data: Dict,
    total_titles: int,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    *,
    region_order: Optional[List[str]] = None,
    get_time_func: Optional[Callable[[], datetime]] = None,
    rss_items: Optional[List[Dict]] = None,
    rss_new_items: Optional[List[Dict]] = None,
    display_mode: str = "keyword",
    standalone_data: Optional[Dict] = None,
    ai_analysis: Optional[Any] = None,
    show_new_section: bool = True,
) -> str:
    """渲染 NewsNow 风格的暗色卡片 HTML 报告。"""
    default_region_order = ["hotlist", "rss", "new_items", "standalone", "ai_analysis"]
    if region_order is None:
        region_order = default_region_order

    stats = report_data.get("stats", [])
    if display_mode != "platform":
        stats = _regroup_by_source(stats)

    now = get_time_func() if get_time_func else datetime.now()

    mode_map = {
        "daily": "全天汇总",
        "current": "当前榜单",
        "incremental": "增量分析",
    }
    mode_text = mode_map.get(mode, mode)
    hot_news_count = sum(len(stat.get("titles", [])) for stat in stats)

    # -- 构建各区块 --
    sections: Dict[str, str] = {}

    sections["hotlist"] = (
        f'<section class="panel-block">'
        f'<h2 class="panel-title">🔥 热点新闻</h2>'
        f'{_cards_grid(stats, display_mode)}'
        f'</section>'
    ) if stats else ""

    rss_section = ""
    if rss_items:
        rss_title = "RSS 订阅统计" if display_mode == "keyword" else "RSS 订阅更新"
        rss_section += _render_rss(rss_items, rss_title, display_mode)
    if rss_new_items:
        rss_section += _render_rss(rss_new_items, "RSS 新增更新", display_mode)
    sections["rss"] = rss_section

    new_titles_html = ""
    if show_new_section and report_data.get("new_titles"):
        new_titles_html = _render_new_section(report_data["new_titles"])
    sections["new_items"] = new_titles_html

    if standalone_data:
        standalone_stats = standalone_data.get("platforms", [])
        if standalone_stats:
            sections["standalone"] = (
                f'<section class="panel-block">'
                f'<h2 class="panel-title">📌 独立展示区</h2>'
                f'{_cards_grid(standalone_stats, "keyword")}'
                f'</section>'
            )
        else:
            sections["standalone"] = ""
    else:
        sections["standalone"] = ""

    if ai_analysis:
        ai_body = render_ai_analysis_html_rich(ai_analysis)
        sections["ai_analysis"] = (
            f'<section class="panel-block ai-block">'
            f'<h2 class="panel-title">🤖 AI 分析</h2>'
            f'<div class="ai-content">{ai_body}</div>'
            f'</section>'
        )
    else:
        sections["ai_analysis"] = ""

    ordered_content = "\n".join(
        sections.get(region, "") for region in region_order if sections.get(region, "")
    )

    failed_html = ""
    if report_data.get("failed_ids"):
        failed_items = "".join(
            f'<li class="error-item">{html_escape(item)}</li>'
            for item in report_data["failed_ids"]
        )
        failed_html = (
            f'<section class="error-section">'
            f'<div class="error-title">⚠️ 请求失败的平台</div>'
            f'<ul class="error-list">{failed_items}</ul>'
            f'</section>'
        )

    update_html = ""
    if update_info and update_info.get("has_update"):
        update_html = (
            f'<div class="update-tip">'
            f'发现新版本 {html_escape(update_info.get("remote_version", ""))}，'
            f'当前版本 {html_escape(update_info.get("current_version", ""))}'
            f'</div>'
        )

    # ---------------------------------------------------------------
    # 完整 HTML 输出 — CSS 严格对齐 NewsNow 暗色模式
    # ---------------------------------------------------------------

    # ---------------------------------------------------------------
    # 完整 HTML 输出 — CSS 严格对齐 NewsNow 暗色模式
    # ---------------------------------------------------------------
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TrendRadar · 热点新闻分析</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
<style>
*,*::before,*::after{{ box-sizing:border-box; margin:0; padding:0; }}
html{{ color-scheme:dark; }}
body{{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: #1e1e1e;
  color: #d4d4d4;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  background-image: radial-gradient(ellipse 80% 50% at 50% -20%,
    rgba(248,113,113,0.08), rgba(255,255,255,0));
}}
a{{ color:inherit; text-decoration:none; }}
ol,ul{{ list-style:none; }}

::-webkit-scrollbar{{ width:8px; }}
::-webkit-scrollbar-track{{ background:transparent; }}
::-webkit-scrollbar-thumb{{
  background: rgba(255,255,255,0.44);
  border-radius: 8px;
}}
::-webkit-scrollbar-thumb:hover{{ background: rgba(255,255,255,0.55); }}

.container{{
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px 16px 32px;
}}

.topbar{{
  position: sticky;
  top: 8px;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  background: rgba(30,30,30,0.78);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 14px 20px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  margin-bottom: 20px;
}}
.brand{{
  font-family: "Baloo 2", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.02em;
}}
.brand .accent{{ color: #f87171; }}
.meta{{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 2px;
}}
.pill{{
  font-size: 12px;
  color: #a3a3a3;
  background: rgba(163,163,163,0.12);
  border: 1px solid rgba(163,163,163,0.25);
  border-radius: 999px;
  padding: 3px 10px;
}}
.save-buttons{{ display:flex; gap:8px; }}
.save-btn{{
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15);
  color: #d4d4d4;
  padding: 7px 14px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 12px;
  transition: background .2s;
}}
.save-btn:hover{{ background: rgba(255,255,255,0.18); }}

.panel-block{{ margin-top: 24px; }}
.panel-title{{
  font-size: 16px;
  font-weight: 700;
  color: #e5e5e5;
  margin: 0 0 12px;
}}

.cards-grid{{
  display: grid;
  gap: 24px;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
}}

.card-shell{{
  display: flex;
  flex-direction: column;
  height: 500px;
  border-radius: 16px;
  padding: 16px;
  cursor: default;
  animation: fadeUp .4s ease both;
}}
@keyframes fadeUp{{
  from{{ opacity:0; transform:translateY(18px); }}
  to{{ opacity:1; transform:translateY(0); }}
}}

.card-head{{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 0 8px 8px;
}}
.card-head-left{{
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}}
.card-name-wrap{{
  display: flex;
  flex-direction: column;
}}
.card-name{{
  font-size: 20px;
  font-weight: 700;
  color: #fafafa;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.card-sub{{
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}}
.card-count{{
  font-size: 12px;
  color: #d4d4d4;
  background: rgba(255,255,255,0.08);
  padding: 3px 10px;
  border-radius: 999px;
  flex-shrink: 0;
}}

.card-inner{{
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  border-radius: 16px;
  padding: 8px;
  background-color: rgba(30,30,30,0.70);
  background-repeat: no-repeat;
}}
.card-list{{
  display: flex;
  flex-direction: column;
  gap: 2px;
}}

.news-row{{
  display: flex;
  gap: 8px;
  align-items: stretch;
  padding: 1px;
  border-radius: 6px;
  cursor: pointer;
  transition: background .15s;
  text-decoration: none;
  color: inherit;
}}
.news-row:hover{{
  background: rgba(163,163,163,0.10);
}}

.row-idx{{
  background: rgba(163,163,163,0.10);
  min-width: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 6px;
  font-size: 14px;
  color: #a3a3a3;
  flex-shrink: 0;
}}

.row-body{{
  flex: 1;
  min-width: 0;
  align-self: start;
  line-height: 1.4;
  padding: 2px 0;
}}
.row-title{{
  font-size: 16px;
  color: #d4d4d4;
}}
.news-link{{
  color: #d4d4d4;
  text-decoration: none;
  transition: color .15s;
}}
.news-link:hover{{ color: #fafafa; }}
.news-link:visited{{ color: #a3a3a3; }}

.row-extra{{
  display: inline;
  margin-left: 8px;
}}
.extra-info{{
  font-size: 12px;
  color: rgba(163,163,163,0.80);
  vertical-align: middle;
}}
.time-info{{ color: #737373; font-size: 11px; }}
.hot-count{{ color: #34d399; font-weight: 600; }}

.new-badge{{
  display: inline-block;
  background: #fbbf24;
  color: #7c2d12;
  font-size: 9px;
  font-weight: 800;
  padding: 1px 5px;
  border-radius: 6px;
  margin-left: 4px;
  vertical-align: middle;
}}

.rank-num{{
  display: inline-block;
  color: #fff;
  background: #525252;
  font-size: 10px;
  font-weight: 700;
  border-radius: 6px;
  padding: 1px 5px;
  vertical-align: middle;
}}
.rank-num.top{{ background: #dc2626; }}
.rank-num.high{{ background: #ea580c; }}

.error-section{{
  margin-top: 16px;
  background: rgba(127,29,29,0.25);
  border: 1px solid rgba(248,113,113,0.40);
  border-radius: 12px;
  padding: 12px 16px;
}}
.error-title{{ color: #fca5a5; font-size: 13px; font-weight: 700; margin-bottom: 6px; }}
.error-list{{ padding-left: 18px; list-style: disc; }}
.error-item{{ color: #fecaca; font-size: 12px; }}

.ai-block .ai-content{{
  background: rgba(15,23,42,0.6);
  border: 1px solid rgba(59,130,246,0.30);
  border-radius: 12px;
  padding: 16px;
  font-size: 14px;
  line-height: 1.7;
}}

.footer{{
  margin-top: 28px;
  text-align: center;
  padding: 16px 10px 8px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  color: #525252;
}}
.footer a{{ color: #737373; }}
.footer a:hover{{ color: #a3a3a3; }}
.update-tip{{ color: #fbbf24; margin-top: 4px; font-size: 12px; }}

@media (min-width: 768px){{
  .container{{ padding: 20px 40px 36px; }}
}}
@media (min-width: 1280px){{
  .container{{ padding: 24px 96px 40px; }}
}}
@media (max-width: 640px){{
  .cards-grid{{ grid-template-columns: 1fr; }}
  .card-shell{{ height: 460px; }}
  .topbar{{ flex-direction: column; align-items: flex-start; }}
  .save-buttons{{ width: 100%; justify-content: flex-start; }}
}}
</style>
</head>
<body>
<div class="container">
  <header class="topbar">
    <div>
      <div class="brand"><span class="accent">T</span>rend<span class="accent">R</span>adar</div>
      <div class="meta">
        <span class="pill">{html_escape(mode_text)}</span>
        <span class="pill">总新闻 {total_titles} 条</span>
        <span class="pill">热点 {hot_news_count} 条</span>
        <span class="pill">{now.strftime('%m-%d %H:%M')}</span>
      </div>
    </div>
    <div class="save-buttons">
      <button class="save-btn" onclick="saveAsImage(event)">📷 保存为图片</button>
      <button class="save-btn" onclick="saveAsMultipleImages(event)">📑 分段保存</button>
    </div>
  </header>

  {failed_html}
  {ordered_content}

  <footer class="footer">
    由 TrendRadar 生成 · <a href="https://github.com/sansan0/TrendRadar" target="_blank">GitHub</a>
    {update_html}
  </footer>
</div>

<script>
async function saveAsImage(event) {{
  const btn = event.target;
  const original = btn.textContent;
  try {{
    btn.disabled = true;
    btn.textContent = '生成中...';
    const canvas = await html2canvas(document.querySelector('.container'), {{
      backgroundColor: '#1e1e1e',
      scale: 1.5,
      useCORS: true,
      logging: false,
    }});
    const link = document.createElement('a');
    const now = new Date();
    const ts = `${{now.getFullYear()}}${{String(now.getMonth()+1).padStart(2,'0')}}${{String(now.getDate()).padStart(2,'0')}}_${{String(now.getHours()).padStart(2,'0')}}${{String(now.getMinutes()).padStart(2,'0')}}`;
    link.download = `TrendRadar_NewsNow_${{ts}}.png`;
    link.href = canvas.toDataURL('image/png', 1.0);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    btn.textContent = '✓ 已保存';
  }} catch (e) {{
    btn.textContent = '保存失败';
    console.error(e);
  }} finally {{
    setTimeout(() => {{ btn.disabled = false; btn.textContent = original; }}, 1500);
  }}
}}

async function saveAsMultipleImages(event) {{
  const btn = event.target;
  const original = btn.textContent;
  try {{
    btn.disabled = true;
    btn.textContent = '分段生成中...';
    const root = document.querySelector('.container');
    const blocks = Array.from(document.querySelectorAll('.panel-block, .topbar, .footer, .error-section'));
    if (!blocks.length) {{ await saveAsImage(event); return; }}
    const rootRect = root.getBoundingClientRect();
    const sections = blocks.map(el => {{
      const rect = el.getBoundingClientRect();
      return {{ top: rect.top - rootRect.top + root.scrollTop, bottom: rect.bottom - rootRect.top + root.scrollTop }};
    }});
    const maxHeight = 3200;
    const ranges = [];
    let start = sections[0].top;
    let end = start;
    for (const sec of sections) {{
      if (sec.bottom - start > maxHeight) {{
        ranges.push([start, end]);
        start = sec.top;
      }}
      end = sec.bottom;
    }}
    ranges.push([start, end]);
    for (let i = 0; i < ranges.length; i++) {{
      const [yStart, yEnd] = ranges[i];
      const canvas = await html2canvas(root, {{
        backgroundColor: '#1e1e1e',
        scale: 1.5,
        useCORS: true,
        logging: false,
        y: yStart,
        height: Math.max(200, yEnd - yStart),
        windowWidth: document.documentElement.clientWidth,
        windowHeight: document.documentElement.clientHeight,
      }});
      const link = document.createElement('a');
      link.download = `TrendRadar_NewsNow_part${{i+1}}.png`;
      link.href = canvas.toDataURL('image/png', 1.0);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }}
    btn.textContent = '✓ 分段已保存';
  }} catch (e) {{
    btn.textContent = '分段保存失败';
    console.error(e);
  }} finally {{
    setTimeout(() => {{ btn.disabled = false; btn.textContent = original; }}, 1500);
  }}
}}
</script>
</body>
</html>"""
