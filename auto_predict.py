#!/usr/bin/env python3
"""
自动预测管线 — 每日拉数据→预测→更新HTML
用法: python auto_predict.py
可被定时任务调用
"""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

def fetch_latest_data():
    """尝试从福彩API获取最新数据"""
    try:
        url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=200"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.cwl.gov.cn/'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        
        new_draws = []
        for row in data.get('result', data.get('data', [])):
            issue = str(row.get('code', row.get('issue', '')))
            red = str(row.get('red', row.get('number', ''))).replace(',', ' ').strip()
            parts = red.split()
            if len(parts) >= 3 and issue:
                new_draws.append({'issue': issue, 'digits': [int(p) for p in parts[:3]]})
        
        if new_draws:
            print(f"[API] 获取{len(new_draws)}条最新数据")
            return new_draws
    except Exception as e:
        print(f"[API] 获取失败: {e}")
    return None

def merge_data(existing, new_draws):
    """合并新旧数据,去重排序"""
    seen = set(d['issue'] for d in existing)
    for d in new_draws:
        if d['issue'] not in seen:
            seen.add(d['issue'])
            existing.append(d)
    existing.sort(key=lambda x: x['issue'])
    print(f"[合并] 总计{len(existing)}期")
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
    import subprocess
    result = subprocess.run(
        [sys.executable, os.path.join(BASE, 'build_html.py')],
        capture_output=True, text=True, cwd=BASE, timeout=30,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    )
    if result.stdout: print(result.stdout.strip())
    if result.stderr: print(result.stderr.strip()[:200])

    
    return output

if __name__ == '__main__':
    run_prediction()
    print("\n✓ 自动预测完成")
