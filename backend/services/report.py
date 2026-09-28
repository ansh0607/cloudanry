"""Shareable HTML report generator (feature 11).

One GET returns a donor-presentable, self-contained HTML page: project info,
media gallery, before/after comparison, claim confidence scores.
Language is assessment-only: "consistent with", "contradiction detected".
"""
import html
from datetime import datetime
from typing import Any

DISCLAIMER = "This is an evidence assessment, not proof of impact."

_CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f6f8f7;color:#1a2b22}
.wrap{max-width:960px;margin:0 auto;padding:32px 20px}
h1{font-size:26px;margin:0 0 4px} h2{font-size:19px;margin:32px 0 12px;border-bottom:2px solid #d8e5de;padding-bottom:6px}
.meta{color:#5b6f64;font-size:13px;margin-bottom:24px}
.banner{background:#fff7e0;border:1px solid #e7d28a;border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}
.card{background:#fff;border:1px solid #e2e8e4;border-radius:10px;overflow:hidden;font-size:12px}
.card img{width:100%;height:120px;object-fit:cover;background:#eef2f0}
.card .pad{padding:8px 10px}
.badge{display:inline-block;padding:2px 8px;border-radius:99px;font-weight:600;font-size:11px}
.b-green{background:#dcf5e4;color:#14683a}.b-amber{background:#fdf1d2;color:#8a6116}.b-red{background:#fde2e2;color:#8f2f2f}
.claim{background:#fff;border:1px solid #e2e8e4;border-left:5px solid #6b7280;border-radius:10px;padding:14px 16px;margin-bottom:12px}
.claim.s-green{border-left-color:#22a05c}.claim.s-amber{border-left-color:#e0a63c}.claim.s-red{border-left-color:#e05252}
.score{font-size:34px;font-weight:700;line-height:1}
.row{display:flex;justify-content:space-between;gap:12px;align-items:baseline}
table{width:100%;border-collapse:collapse;font-size:13px;background:#fff;border:1px solid #e2e8e4;border-radius:10px}
td,th{padding:8px 10px;text-align:left;border-bottom:1px solid #eef2f0}
ul{margin:8px 0;padding-left:18px;font-size:13px}
.foot{margin-top:36px;color:#8aa094;font-size:12px;border-top:1px solid #e2e8e4;padding-top:12px}
"""


def _badge(score: Any) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return '<span class="badge b-amber">no score</span>'
    cls = "b-green" if s > 75 else ("b-amber" if s >= 40 else "b-red")
    return f'<span class="badge {cls}">relevance {s:.0f}</span>'


def _score_class(score: Any) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "s-amber"
    return "s-green" if s > 80 else ("s-amber" if s >= 60 else "s-red")


def _media_card(m: dict[str, Any]) -> str:
    thumb = m.get("thumbnail_url") or m.get("cloudinary_url") or ""
    desc = html.escape(str(m.get("image_description") or "")[:160])
    date = html.escape(str(m.get("capture_date") or "unknown date"))
    gps = m.get("gps") or {}
    loc = f"{gps.get('lat'):.4f}, {gps.get('lng'):.4f}" if gps else "no GPS"
    tags = ", ".join((m.get("ai_tags") or [])[:6])
    return (
        f'<div class="card"><img src="{html.escape(thumb)}" loading="lazy" onerror="this.style.visibility=\'hidden\'">'
        f'<div class="pad"><strong>{date}</strong> · {html.escape(loc)}<br>'
        f"{_badge(m.get('relevance_score'))}<br>"
        f'<span style="color:#5b6f64">{desc}</span><br>'
        f'<span style="color:#8aa094">{html.escape(tags)}</span></div></div>'
    )


def _claim_card(c: dict[str, Any]) -> str:
    score = c.get("confidence_score")
    text = html.escape(str(c.get("claim_text") or ""))
    supporting = c.get("supporting_signals") or []
    adversarial = c.get("adversarial_signals") or []
    sup_li = "".join(
        f"<li>{html.escape(str(s.get('description','')))} <em>(strength {s.get('strength')})</em></li>"
        for s in supporting
    )
    adv_li = "".join(
        f"<li>{html.escape(str(s.get('description','')))} <em>(severity {s.get('severity')})</em></li>"
        for s in adversarial
    )
    return (
        f'<div class="claim {_score_class(score)}"><div class="row">'
        f"<div><strong>{text}</strong></div><div class=\"score\">{score if score is not None else '—'}</div></div>"
        f"<div style='font-size:12px;color:#5b6f64'>confidence score (evidence assessment)</div>"
        f"<h3 style='font-size:13px;margin:10px 0 2px'>Supporting signals</h3><ul>{sup_li or '<li>none</li>'}</ul>"
        f"<h3 style='font-size:13px;margin:10px 0 2px'>Adversarial signals</h3><ul>{adv_li or '<li>none</li>'}</ul>"
        f"</div>"
    )


def _compare_section(comparison: dict[str, Any] | None, media_a: dict[str, Any] | None, media_b: dict[str, Any] | None) -> str:
    if not comparison:
        return "<p style='color:#5b6f64;font-size:13px'>Fewer than two dated media items — no before/after pair available yet.</p>"
    ma = media_a or {}
    mb = media_b or {}
    img_a = ma.get("cloudinary_url") or ""
    img_b = mb.get("cloudinary_url") or ""
    delta = comparison.get("green_ratio_delta_percent")
    direction = "increase" if (delta or 0) >= 0 else "decrease"
    return f"""
    <div style="display:flex;gap:12px;flex-wrap:wrap">
      <figure style="margin:0;flex:1;min-width:240px"><img src="{html.escape(str(img_a))}" style="width:100%;border-radius:10px;border:1px solid #e2e8e4"><figcaption style="font-size:12px;color:#5b6f64">Before · {html.escape(str(comparison.get('capture_date_a') or ''))}</figcaption></figure>
      <figure style="margin:0;flex:1;min-width:240px"><img src="{html.escape(str(img_b))}" style="width:100%;border-radius:10px;border:1px solid #e2e8e4"><figcaption style="font-size:12px;color:#5b6f64">After · {html.escape(str(comparison.get('capture_date_b') or ''))}</figcaption></figure>
    </div>
    <table style="margin-top:12px"><tr><td>Green-pixel ratio (vegetation proxy)</td><td>{comparison.get('green_ratio_a')} → {comparison.get('green_ratio_b')} ({direction} of {abs(delta or 0)} pp)</td></tr>
    <tr><td>Overall pixel change</td><td>{comparison.get('pixel_diff_percent')}%</td></tr></table>
    <p style="font-size:12px;color:#5b6f64">Metric is a simple color-threshold proxy. Change is "consistent with" project activity — it does not by itself prove cause.</p>"""


def generate_report(
    project: dict[str, Any],
    media: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    comparison: dict[str, Any] | None,
    media_a: dict[str, Any] | None,
    media_b: dict[str, Any] | None,
) -> str:
    loc = project.get("location") or {}
    place = html.escape(str(loc.get("place_name") or "location not set"))
    cards = "".join(_media_card(m) for m in media) or "<p style='color:#5b6f64;font-size:13px'>No media uploaded yet.</p>"
    claim_cards = "".join(_claim_card(c) for c in claims) or "<p style='color:#5b6f64;font-size:13px'>No claims recorded yet.</p>"
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidence Report — {html.escape(str(project.get('project_name') or 'Project'))}</title>
<style>{_CSS}</style></head><body><div class="wrap">
<div class="banner">⚠ {DISCLAIMER} AI outputs use assessment language ("consistent with", "contradiction detected") and never assert verification.</div>
<h1>{html.escape(str(project.get('project_name') or 'Project'))}</h1>
<div class="meta">{place} · {html.escape(str(project.get('expected_activity_type') or 'activity type not set'))} · generated {generated}</div>
<p style="font-size:14px;max-width:720px">{html.escape(str(project.get('description') or ''))}</p>

<h2>Media gallery ({len(media)})</h2>
<div class="grid">{cards}</div>

<h2>Before / after</h2>
{_compare_section(comparison, media_a, media_b)}

<h2>Claims &amp; confidence</h2>
{claim_cards}

<div class="foot">Evidence Graph · every figure traces to source media and logged transformations · {DISCLAIMER}</div>
</div></body></html>"""
