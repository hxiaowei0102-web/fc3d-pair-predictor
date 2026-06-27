#!/usr/bin/env python3
"""
自动预测管线 — 每日拉数据→预测→更新HTML
用法: python auto_predict.py
数据源(v12.3 借鉴五胆码): 灰鸟 > cjcp.cn > 接口盒子 > c133.com > cloudscraper > 官网curl > kjapi.com > 硬编码兜底
"""
import json, os, sys, urllib.request, urllib.error, subprocess, time, re
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

# 可选依赖
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ============================================================
# 通用工具
# ============================================================

def fetch_via_curl(url, timeout=30):
    """用curl命令行获取JSON数据"""
    try:
        result = subprocess.run([
            'curl', '-s', '--max-time', str(timeout),
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '-H', 'Accept: application/json, text/plain, */*',
            '-H', 'Accept-Language: zh-CN,zh;q=0.9',
            url
        ], capture_output=True, text=True, timeout=timeout+5)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception as e:
        print(f"  [curl异常] {str(e)[:80]}")
    return None

# ============================================================
# 解析器
# ============================================================

def parse_draws_official(data):
    """解析官网API"""
    draws = []
    rows = data.get('result', data.get('data', []))
    if isinstance(rows, dict):
        rows = rows.get('list', rows.get('records', []))
    if not isinstance(rows, list):
        rows = [rows] if rows else []
    for row in rows:
        issue = str(row.get('code', row.get('issue', '')))
        red = str(row.get('red', row.get('number', row.get('openCode', '')))).replace(',', ' ').strip()
        parts = red.split()
        if len(parts) >= 3 and issue:
            draws.append({'issue': issue, 'digits': [int(p) for p in parts[:3]]})
    return draws

def parse_huiniao(data):
    """解析灰鸟API"""
    draws = []
    lst = data.get('data', {}).get('data', {}).get('list', [])
    for row in lst:
        code = str(row.get('code', ''))
        one, two, three = row.get('one'), row.get('two'), row.get('three')
        if code and one is not None and two is not None and three is not None:
            draws.append({'issue': code, 'digits': [int(one), int(two), int(three)]})
    return draws

def parse_apihz(data):
    """解析接口盒子API"""
    draws = []
    nums = str(data.get('number', '')).split('|')
    qihao = str(data.get('qihao', ''))
    if len(nums) >= 3 and qihao:
        try:
            draws.append({'issue': qihao, 'digits': [int(n) for n in nums[:3]]})
        except ValueError:
            pass
    return draws

# ============================================================
# 源1: 灰鸟API — JSON, 免费, 无key (优先) ⭐
# ============================================================

def fetch_huiniao(limit=200):
    url = f'http://api.huiniao.top/interface/home/lotteryHistory?type=fcsd&page=1&limit={limit}'
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data.get('code') == 1:
            return data
    except Exception as e:
        print(f"  [灰鸟] {str(e)[:60]}")
    return None

# ============================================================
# 源2: cjcp.cn — 彩经网HTML抓取 (借鉴五胆码) ⭐
# ============================================================

def fetch_cjcp():
    """HTML抓取彩经网 — gbk解码, 多期数据"""
    try:
        url = 'https://www.cjcp.cn/3dkaijiang/'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            text = raw.decode('gbk', errors='replace')
            pattern = r'福彩3D第(\d{7})期开奖结果</div>\s*<div class="date">(\d{4}-\d{2}-\d{2})[^<]*</div>.*?num-ball[^>]*>(\d)<.*?num-ball[^>]*>(\d)<.*?num-ball[^>]*>(\d)<'
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                draws = []
                for issue, date_str, d1, d2, d3 in matches[:30]:
                    draws.append({'issue': issue, 'digits': [int(d1), int(d2), int(d3)]})
                if draws:
                    print(f"  [cjcp.cn] ✓ 获取{len(draws)}条, 最新: {draws[0]['issue']}={draws[0]['digits']}")
                    return draws
    except Exception as e:
        print(f"  [cjcp.cn] {str(e)[:60]}")
    return []

# ============================================================
# 源3: 接口盒子 — 多IP, 公共key
# ============================================================

def fetch_apihz():
    urls = [
        'http://101.35.2.25/api/caipiao/fucai3d.php',
        'http://124.222.204.22/api/caipiao/fucai3d.php',
        'http://43.142.65.209/api/caipiao/fucai3d.php',
        'https://cn.apihz.cn/api/caipiao/fucai3d.php',
    ]
    params = '?id=88888888&key=88888888'
    for url in urls:
        try:
            req = urllib.request.Request(url + params, headers={
                'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'
            })
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            if data.get('code') == 200:
                return data
        except Exception:
            continue
    return None

# ============================================================
# 源4: c133.com — HTML抓取 (借鉴五胆码) ⭐
# ============================================================

def fetch_c133():
    """HTML抓取c133.com — 获取最新1条"""
    try:
        url = 'http://c133.com/'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('utf-8', errors='replace')
            pattern = r'<strong>福彩3D</strong>.*?<td class="td-period">(\d+)</td>.*?ball-blue">(\d)</span>.*?ball-blue">(\d)</span>.*?ball-blue">(\d)</span>'
            m = re.search(pattern, text, re.DOTALL)
            if m:
                issue, d1, d2, d3 = m.group(1), m.group(2), m.group(3), m.group(4)
                digits = [int(d1), int(d2), int(d3)]
                print(f"  [c133.com] ✓ {issue}={digits}")
                return [{'issue': issue, 'digits': digits}]
    except Exception as e:
        print(f"  [c133.com] {str(e)[:60]}")
    return []

# ============================================================
# 源5: cloudscraper — 绕过Cloudflare (借鉴五胆码) ⭐
# ============================================================

def fetch_cloudscraper():
    """cloudscraper绕过Cloudflare访问官网API"""
    if not HAS_CLOUDSCRAPER:
        return None
    try:
        scraper = cloudscraper.create_scraper()
        url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=10"
        r = scraper.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get('state') == 0:
                draws = parse_draws_official(data)
                if draws:
                    print(f"  [cloudscraper] ✓ 获取{len(draws)}条")
                    return draws
    except Exception as e:
        print(f"  [cloudscraper] {str(e)[:60]}")
    return None

# ============================================================
# 源6: kjapi.com — HTML抓取 (借鉴五胆码) ⭐
# ============================================================

def fetch_kjapi():
    """HTML抓取kjapi.com — 当天开奖数据"""
    if not HAS_REQUESTS:
        return []
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"https://www.kjapi.com/hallhistoryDetail/fc3d/{today}"
        r = _requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }, timeout=15)
        if r.status_code == 200:
            issue_match = re.findall(r'(\d{7})', r.text)
            num_match = re.findall(r'<li[^>]*>(\d)</li>', r.text)
            if issue_match and len(num_match) >= 3:
                issue = issue_match[0]
                digits = [int(n) for n in num_match[:3]]
                print(f"  [kjapi.com] ✓ {today}: {issue}={digits}")
                return [{'issue': issue, 'digits': digits}]
    except Exception as e:
        print(f"  [kjapi.com] {str(e)[:60]}")
    return []

# ============================================================
# 源7: 官网curl + requests (保留作为后备)
# ============================================================

def fetch_cwl_requests():
    """requests直连官网"""
    if not HAS_REQUESTS:
        return None
    try:
        url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=200"
        r = _requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.cwl.gov.cn/',
        }, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('state') == 0:
                draws = parse_draws_official(data)
                if draws:
                    print(f"  [官网requests] ✓ 获取{len(draws)}条")
                    return draws
    except Exception as e:
        print(f"  [官网requests] {str(e)[:60]}")
    return None

# ============================================================
# 主数据获取 — 8源容错
# ============================================================

def fetch_latest_data():
    """多源获取最新数据 — 8重保障 (借鉴五胆码架构)"""
    
    # 优先级: 第三方稳定 > HTML抓取 > 第三方补位 > cloudscraper > 官网API > 兜底
    sources = [
        # ⭐ 第三方免费JSON API (最稳定)
        ('灰鸟API', fetch_huiniao, parse_huiniao),
        # ⭐ HTML抓取 (不同域名, 互补)
        ('cjcp.cn', fetch_cjcp, None),  # None = 直接返回list
        # 第三方JSON (多IP容错)
        ('接口盒子', fetch_apihz, parse_apihz),
        # HTML抓取 (独立站点)
        ('c133.com', fetch_c133, None),
        # cloudscraper绕过Cloudflare
        ('cloudscraper', fetch_cloudscraper, None),
        # 官网API (requests直连)
        ('官网requests', fetch_cwl_requests, None),
        # kjapi.com HTML
        ('kjapi.com', fetch_kjapi, None),
        # 官网curl (GitHub Actions备选)
        ('官网curl', lambda: fetch_via_curl(
            'https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=200'
        ), parse_draws_official),
    ]
    
    for name, fetcher, parser in sources:
        for attempt in range(2):
            try:
                if attempt > 0:
                    time.sleep(2)
                data = fetcher()
                if data:
                    if parser is None:
                        # fetcher返回的已经是draws列表
                        draws = data
                    else:
                        draws = parser(data)
                    if draws:
                        if parser is None or isinstance(data, list):
                            print(f"[API] {name} ✓ 获取{len(draws)}条")
                        return draws
                    else:
                        if attempt == 0:
                            print(f"[API] {name} 返回空数据")
            except Exception as e:
                if attempt == 0:
                    print(f"[API] {name} 失败: {str(e)[:60]}, 重试...")
        print(f"[API] {name} 最终失败")
    
    print("[API] ⚠ 全部8源失败，使用硬编码兜底数据")
    return None

def merge_data(existing, new_draws):
    """合并新旧数据,去重排序"""
    seen = set(d['issue'] for d in existing)
    new_count = 0
    for d in new_draws:
        if d['issue'] not in seen:
            seen.add(d['issue'])
            existing.append(d)
            new_count += 1
    existing.sort(key=lambda x: x['issue'])
    print(f"[合并] 新增{new_count}期, 总计{len(existing)}期")
    return existing

def run_prediction():
    """主预测流程"""
    print(f"\n{'='*50}")
    print(f"  自动预测管线 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    # 1. 加载现有数据
    from predict_v12 import load_all_data
    history = load_all_data()
    
    # 2. 尝试获取最新API数据
    new = fetch_latest_data()
    if new:
        history = merge_data(history, new)
    
    # 3. 运行V12预测
    from predict_v12 import predict, backtest
    preds = predict(history)
    latest = history[-1]
    next_issue = str(int(latest['issue']) + 1)
    
    print(f"\n最新: {latest['issue']} 开奖{''.join(str(d) for d in latest['digits'])}")
    print(f"预测: {next_issue}")
    for i, p in enumerate(preds, 1):
        print(f"  #{i} [{p['algo']}] {p['pair_str']} 遗漏{p['last_seen']}期")
    
    # 4. 回测
    bt_r, bt_c, bt_t, bt_a, algo_s, _ = backtest(history, 100)
    print(f"\n100期回测: {bt_c}/{bt_t} = {bt_a}%")
    
    # 5. 输出JSON
    output = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '12.0.0-auto',
        'total_draws': len(history),
        'latest': {'issue': latest['issue'], 'digits': ''.join(str(d) for d in latest['digits'])},
        'next_issue': next_issue,
        'predictions': preds,
        'algorithm': {
            'name': 'V12 DIGIT→MOM→WAKEUP',
            'algorithms': {
                'DIGIT': '数字投影: 指数衰减数字热度，6冷池选对',
                'MOM': '数字动量: 避热号+冷对优先',
                'WAKEUP': '唤醒检测: 识别长冷后突现模式',
            }
        },
        'backtest': {
            'total_periods': bt_t, 'correct': bt_c, 'accuracy': bt_a,
            'algo_accuracy': {a: round(s['c']/s['t']*100, 1) if s['t']>0 else 0 for a, s in algo_s.items()},
            'results': bt_r,
        }
    }
    
    json_path = os.path.join(BASE, 'prediction_v12.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[JSON] {json_path}")
    
    # 6. 构建HTML
    result = subprocess.run(
        [sys.executable, os.path.join(BASE, 'build_html.py')],
        capture_output=True, text=True, cwd=BASE, timeout=30,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    )
    if result.stdout: print(result.stdout.strip())
    if result.stderr: print(result.stderr.strip()[:200])
    
    # 7. 同步刷新兜底数据: 更新history.csv + 硬编码EM字符串
    try:
        # 7a. 更新 history.csv 兜底
        csv_path = os.path.join(BASE, 'history.csv')
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write('issue,date,digits\n')
            for d in history:
                digits_str = ''.join(str(x) for x in d['digits'])
                f.write(f"{d['issue']},,{digits_str}\n")
        
        # 7b. 更新 predict_v12.py 硬编码EM (终极兜底)
        em_parts = []
        for d in history:
            digits_str = ''.join(str(x) for x in d['digits'])
            em_parts.append(f"{d['issue']},{digits_str}")
        new_em = ' '.join(em_parts)
        
        v12_path = os.path.join(BASE, 'predict_v12.py')
        with open(v12_path, 'r', encoding='utf-8') as f:
            v12_code = f.read()
        new_v12_code = re.sub(r'EM = "[^"]*"', f'EM = "{new_em}"', v12_code)
        if new_v12_code != v12_code:
            with open(v12_path, 'w', encoding='utf-8') as f:
                f.write(new_v12_code)
            print(f"[兜底] 已刷新硬编码数据: {len(history)}期")
    except Exception as e:
        print(f"[兜底] 更新失败(不影响预测): {str(e)[:80]}")
    
    return output

if __name__ == '__main__':
    run_prediction()
    print("\n自动预测完成")
