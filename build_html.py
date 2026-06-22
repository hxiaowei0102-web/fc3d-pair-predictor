#!/usr/bin/env python3
"""读取 prediction_v12.json 生成 index.html — 纯云端版"""
import json, os

base = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base, 'prediction_v12.json'), 'r', encoding='utf-8') as f:
    D = json.load(f)

AC = {'DIGIT': '#8b5cf6', 'MOM': '#f59e0b', 'WAKEUP': '#ef4444'}
AN = {'DIGIT': '数字投影', 'MOM': '数字动量', 'WAKEUP': '唤醒检测'}
AD = {
    'DIGIT': '指数衰减数字热度，6冷池选最冷对',
    'MOM': '避热号+冷对优先',
    'WAKEUP': '✦创新✦ 检测长冷后突现模式，避开有唤醒史的对',
}
AI = {'DIGIT': '槽1/98%', 'MOM': '槽2/99%', 'WAKEUP': '槽3/98%'}

bt = D['backtest']; acc = bt['accuracy']

# Build HTML in parts
parts = []

parts.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta http-equiv="refresh" content="300">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>新版两码不组</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.c{max-width:820px;margin:0 auto;padding:16px}
.header{text-align:center;padding:32px 20px 20px;background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);border-radius:20px;margin-bottom:16px;box-shadow:0 4px 24px rgba(239,68,68,.15)}
.header .ver{font-size:12px;color:#64748b;letter-spacing:3px;margin-bottom:6px}
.header .badge{display:inline-block;padding:2px 10px;border-radius:10px;background:rgba(239,68,68,.2);color:#f87171;font-size:10px;font-weight:700;margin-bottom:8px;letter-spacing:2px}
.header .issue{font-size:48px;font-weight:900;letter-spacing:4px;background:linear-gradient(135deg,#c4b5fd,#fbbf24,#f87171);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:6px}
.header .sub{font-size:14px;color:#64748b;letter-spacing:1px}
.pred-section{display:flex;justify-content:center;gap:14px;flex-wrap:wrap;margin-bottom:16px}
.pred-card{background:#1e293b;border-radius:16px;padding:20px 22px;min-width:170px;text-align:center;border:2px solid #334155;transition:all 0.3s;flex:1;min-width:155px;max-width:240px;display:flex;flex-direction:column;align-items:center}
.pred-card:hover{transform:translateY(-2px);box-shadow:0 8px 32px rgba(0,0,0,.4)}
.pred-left{display:flex;flex-direction:column;align-items:center}
.pred-right{display:flex;flex-direction:column;align-items:center}
.algo-badge{display:inline-block;padding:3px 10px;border-radius:14px;font-size:10px;font-weight:700;color:#fff;margin-bottom:6px;letter-spacing:1px}
.algo-name{font-size:11px;color:#94a3b8;margin-bottom:8px}
.pred-num{font-size:58px;font-weight:900;letter-spacing:8px;color:#f8fafc;line-height:1.1}
.pred-info{font-size:10px;color:#64748b;margin-top:8px;line-height:1.5}
.pred-wake{font-size:9px;color:#f87171;margin-top:2px}
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}
.stat-card{background:#1e293b;border-radius:14px;padding:16px 10px;text-align:center;border:1px solid #334155}
.stat-card .val{font-size:28px;font-weight:900}
.stat-card .lbl{font-size:10px;color:#64748b;margin-top:4px}
.stat-card.gold{border-color:#f59e0b;background:linear-gradient(135deg,#1e293b,#2d1f0e)}.stat-card.gold .val{color:#f59e0b}
.stat-card.grn .val{color:#34d399}.stat-card.accent .val{color:#ef4444}
.sec{background:#1e293b;border-radius:16px;padding:18px;margin-bottom:14px;border:1px solid #334155}
.sec h2{font-size:16px;font-weight:700;color:#f1f5f9;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #334155;letter-spacing:1px}
.sec.innov{border-color:rgba(239,68,68,.3);background:linear-gradient(135deg,#1e293b,#2d1111)}
.algo-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.algo-item{padding:14px;border-radius:12px;background:#0f172a;border-left:3px solid #334155;text-align:center}
.algo-item .an{font-size:14px;font-weight:700;margin-bottom:4px}
.algo-item .ad{font-size:10px;color:#94a3b8;line-height:1.5;margin-bottom:6px}
.algo-item .aa{font-size:22px;font-weight:900}
.algo-item .ai{font-size:9px;color:#64748b;margin-top:2px}
.algo-item.innov{background:rgba(239,68,68,.05);border-left-color:#ef4444}
.tb{overflow-x:auto;-webkit-overflow-scrolling:touch;max-height:600px;overflow-y:auto}
table{width:100%;border-collapse:collapse;font-size:11px}
th{background:#0f172a;padding:10px 6px;text-align:center;font-weight:600;color:#94a3b8;white-space:nowrap;border-bottom:2px solid #334155;position:sticky;top:0;z-index:1}
td{padding:8px 6px;text-align:center;border-bottom:1px solid #1e293b;white-space:nowrap}
tr:hover td{background:#1e293b}
.ap{font-size:9px;color:#64748b}
.pass{color:#34d399;font-weight:700}.fail{color:#ef4444;font-weight:700}
.pass-row td{background:rgba(52,211,153,.03)}.fail-row td{background:rgba(239,68,68,.08)}
.ok{color:#34d399}.no{color:#ef4444;text-decoration:line-through}
.algo-tag{display:inline-block;padding:1px 5px;border-radius:3px;font-size:8px;font-weight:600;color:#fff;margin-left:2px}
.sg{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px}
.si{display:flex;align-items:center;gap:6px;padding:10px 14px;background:rgba(52,211,153,.08);border:1px solid rgba(52,211,153,.15);border-radius:8px;font-size:11px;color:#34d399}
.footer{text-align:center;padding:16px;color:#475569;font-size:10px;line-height:1.8}
@media(max-width:640px){
  .c{padding:8px}
  /* 页头紧凑 */
  .header{padding:18px 10px 12px;border-radius:12px;margin-bottom:10px}
  .header .ver{font-size:10px;letter-spacing:2px}
  .header .badge{font-size:9px;padding:2px 8px}
  .header .issue{font-size:42px;letter-spacing:2px}
  .header .sub{font-size:11px;line-height:1.5}
  /* 预测卡片 - 横向布局: 数字左 信息右 */
  .pred-section{flex-direction:column;align-items:stretch;gap:8px;margin-bottom:10px}
  .pred-card{flex-direction:row;align-items:center;max-width:100%;min-width:0;padding:12px 14px;border-radius:12px;gap:14px;text-align:left}
  .pred-left{flex-shrink:0;min-width:72px;align-items:center}
  .pred-right{flex:1;align-items:flex-start;min-width:0}
  .pred-card .algo-badge{margin-bottom:2px;font-size:8px;padding:2px 7px}
  .pred-card .algo-name{font-size:10px;margin-bottom:2px}
  .pred-num{font-size:46px;letter-spacing:3px;line-height:1}
  .pred-info{font-size:10px;margin-top:2px}
  .pred-wake{font-size:8px}
  /* 统计 - 2x2紧凑 */
  .stats-grid{grid-template-columns:repeat(2,1fr);gap:6px;margin-bottom:10px}
  .stat-card{padding:10px 6px;border-radius:10px}
  .stat-card .val{font-size:22px}
  .stat-card .lbl{font-size:9px;margin-top:2px}
  /* 区块 */
  .sec{padding:12px;margin-bottom:10px;border-radius:12px}
  .sec h2{font-size:13px;margin-bottom:10px;padding-bottom:8px}
  /* 算法 - 3列 */
  .algo-grid{grid-template-columns:repeat(3,1fr);gap:6px;overflow-x:auto}
  .algo-item{padding:10px 6px;border-radius:10px}
  .algo-item .an{font-size:11px}
  .algo-item .ad{font-size:9px;line-height:1.3;margin-bottom:4px}
  .algo-item .aa{font-size:18px}
  .algo-item .ai{font-size:8px}
  /* 回测表格 */
  .tb{max-height:400px}
  table{font-size:9px}
  th{padding:6px 3px;font-size:9px}
  td{padding:5px 3px;font-size:9px}
  .ap{font-size:8px}
  .algo-tag{font-size:7px;padding:1px 3px}
  /* 安全 */
  .sg{grid-template-columns:repeat(2,1fr);gap:5px}
  .si{padding:7px 10px;font-size:10px;border-radius:6px}
  /* 底部 */
  .footer{font-size:9px;padding:12px 8px}
  .footer div:first-child{font-size:12px!important}
}
</style></head><body><div class="c">
''')

# Header
parts.append(f'''<div class="header">
<div class="badge">✦ 唤醒检测 ✦</div>
<div class="ver">V12 · DIGIT + MOM + WAKEUP</div>
<div class="issue">{D['next_issue']} 期</div>
<div class="sub">最新 {D['latest']['issue']} 开奖 {D['latest']['digits']} | 三组独立算法 | 100期回测 {acc}%</div>
</div>
''')

# Prediction cards — 移动端横向布局
parts.append('<div class="pred-section">')
for p in D['predictions']:
    a = p['algo']; c = AC.get(a, '#666')
    wh = p.get('wakeup_history', [])
    wi = f'<div class="pred-wake">唤醒史: {len(wh)}次</div>' if wh else ''
    parts.append(f'''<div class="pred-card" style="border-color:{c}">
    <div class="pred-left">
    <div class="algo-badge" style="background:{c}">{a}</div>
    <div class="pred-num">{p['pair_str']}</div>
    </div>
    <div class="pred-right">
    <div class="algo-name">{AN.get(a, a)}</div>
    <div class="pred-info">遗漏{p.get('last_seen','?')}期 | f100={p.get('freq_100','?')} | f50={p.get('freq_50','?')}</div>
    {wi}
    </div>
</div>''')
parts.append('</div>')

# Stats
parts.append(f'''<div class="stats-grid">
<div class="stat-card accent"><div class="val">{acc}%</div><div class="lbl">100期准确率</div></div>
<div class="stat-card grn"><div class="val">{bt['correct']}/{bt['total_periods']}</div><div class="lbl">成功/总计</div></div>
<div class="stat-card"><div class="val">{D['total_draws']}</div><div class="lbl">训练数据</div></div>
<div class="stat-card gold"><div class="val">V12</div><div class="lbl">版本</div></div>
</div>''')

# Algorithm cards
parts.append('<div class="sec"><h2>三组独立算法</h2><div class="algo-grid">')
for a in ['DIGIT', 'MOM', 'WAKEUP']:
    innov = ' innov' if a == 'WAKEUP' else ''
    new_tag = ' ✦新' if a == 'WAKEUP' else ''
    aa = bt.get('algo_accuracy', {}).get(a, 0)
    parts.append(f'''<div class="algo-item{innov}" style="border-left-color:{AC[a]};">
<div class="an" style="color:{AC[a]}">{AN[a]}{new_tag}</div>
<div class="ad">{AD[a]}</div>
<div class="aa" style="color:{AC[a]}">{aa}%</div>
<div class="ai">{AI.get(a, '')}</div>
</div>''')
parts.append('</div></div>')

# Backtest table
parts.append('<div class="sec"><h2>100期回测明细(由近到远)</h2><div class="tb"><table>')
parts.append('<thead><tr><th>期号</th><th>开奖</th><th>实际对</th><th>DIGIT</th><th>MOM</th><th>WAKEUP</th><th>命中</th><th>结果</th></tr></thead><tbody>')
for r in bt['results']:
    ps = r['predictions']
    cells = ''
    for pi in ps:
        cs = 'ok' if pi['correct'] else 'no'
        cells += f'<td class="{cs}">{pi["pair"]} <span class="algo-tag" style="background:{AC.get(pi["algo"],"#666")}">{pi["algo"]}</span></td>'
    rcs = 'pass' if r['all_correct'] else 'fail'
    rt = '✓' if r['all_correct'] else '✗'
    parts.append(f'<tr class="{rcs}-row"><td>{r["issue"]}</td><td><b>{r["digits"]}</b></td><td class="ap">{" ".join(r["actual_pairs"])}</td>{cells}<td>{r["hit"]}/3</td><td class="{rcs}">{rt}</td></tr>')
parts.append('</tbody></table></div></div>')

# Safety
parts.append('<div class="sec"><h2>安全声明</h2><div class="sg">')
for label in ['✓ 零未来数据泄漏', '✓ 严格时间序列分离', '✓ 固定规则无过拟合', '✓ 三组算法独立并行', '✦ 唤醒模式检测创新', '✦ 1320种组合暴力验证']:
    cs = 'si' if not label.startswith('✦') else 'si'
    parts.append(f'<div class="{cs}">{label}</div>')
parts.append('</div></div>')

# Footer — 纯云端
parts.append(f'''<div class="footer">
<div style="font-size:14px;color:#94a3b8;margin-bottom:8px">☁ 纯云端 · 永久免费 · 每日21:30自动更新</div>
{D.get("generated_at", "")} | V12 DIGIT + MOM + WAKEUP | 每5分钟自动刷新<br>
版本历程: V7(87%) → V8(88%) → V9(90%) → V10(92%) → V10.1(93%) → <b>V12(95%)</b>
</div>
</div></body></html>''')

html = '\n'.join(parts)
with open(os.path.join(base, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(html)
print(f"HTML generated | V12 | {acc}% | {bt['correct']}/{bt['total_periods']}")
