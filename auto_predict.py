#!/usr/bin/env python3
"""
自动预测管线 — 每日拉数据→预测→更新HTML
用法: python auto_predict.py
可被定时任务调用
"""
import json, os, sys, urllib.request, urllib.error, subprocess, time, re
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

def fetch_via_curl(url, timeout=30):
    """用curl命令行获取JSON数据 (GitHub Actions runner更可靠)"""
    try:
        result = subprocess.run([
            'curl', '-s', '--max-time', str(timeout),
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '-H', 'Accept: application/json, text/plain, */*',
            '-H', 'Accept-Language: zh-CN,zh;q=0.9',
            '-H', 'Referer: https://www.cwl.gov.cn/',
            url
        ], capture_output=True, text=True, timeout=timeout+5)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        if result.stderr:
            print(f"  [curl stderr] {result.stderr[:100]}")
    except Exception as e:
        print(f"  [curl异常] {str(e)[:80]}")
    return None

def fetch_via_urllib(url, timeout=20):
    """用urllib获取JSON数据"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://www.cwl.gov.cn/ygkj/wqkjgg/ssq/',
        'Origin': 'https://www.cwl.gov.cn',
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))

def parse_draws(data):
    """解析开奖数据"""
    new_draws = []
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
            new_draws.append({'issue': issue, 'digits': [int(p) for p in parts[:3]]})
    return new_draws

def fetch_latest_data():
    """多源API获取最新数据 — curl+urllib双引擎"""
    
    OFFICIAL_URL = 'https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=200'
    
    fetch_methods = [
        ('curl→官网', lambda: fetch_via_curl(OFFICIAL_URL)),
        ('urllib→官网', lambda: fetch_via_urllib(OFFICIAL_URL)),
        ('curl→官网(备用)', lambda: fetch_via_curl(OFFICIAL_URL + '&pageNo=1&pageSize=200')),
        ('curl→灰鸟API', lambda: fetch_via_curl('http://152.136.21.34:8000/api/fc3d/latest?count=200')),
    ]
    
    for name, fetcher in fetch_methods:
        for attempt in range(2):
            try:
                if attempt > 0:
                    time.sleep(5)
                data = fetcher()
                if data:
                    new_draws = parse_draws(data)
                    if new_draws:
                        print(f"[API] {name} 获取{len(new_draws)}条 ✓")
                        return new_draws
                    else:
                        print(f"[API] {name} 返回空数据")
            except Exception as e:
                err = str(e)[:80]
                if attempt == 0:
                    print(f"[API] {name} 失败: {err}, 重试...")
        print(f"[API] {name} 最终失败")
    
    print("[API] 所有源均失败，使用现有数据")
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
