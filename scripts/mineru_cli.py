#!/usr/bin/env python3
"""
MinerU CLI — 轻量命令行解析工具（含全功能安装向导+仪表盘）
用法: python mineru_cli.py  /  双击 MinerU_CLI.exe
"""
import os, sys, json, subprocess, time, shutil, re, tempfile, webbrowser
from pathlib import Path
from datetime import datetime

# ═══════════ 终端颜色 ═══════════
C = {'R': '\033[91m', 'G': '\033[92m', 'Y': '\033[93m', 'B': '\033[94m', 'M': '\033[95m',
     'C': '\033[96m', 'W': '\033[97m', 'D': '\033[90m', 'X': '\033[0m', 'BOLD': '\033[1m'}
def cc(color, text): return f"{C.get(color, '')}{text}{C['X']}"

CONFIG_PATH = Path.home() / "mineru_desktop_config.json"

# ═══════════ 语言选择 ═══════════
def choose_language():
    print(cc('BOLD', cc('B', '\n═══════════════════════════════════')))
    print(cc('BOLD', cc('B', '  MinerU CLI v4.0.0 — PDF Batch Parser')))
    print(cc('BOLD', cc('B', '  MinerU CLI v4.0.0 — PDF 批量解析工具')))
    print(cc('BOLD', cc('B', '═══════════════════════════════════')))
    print('\n  [1] 中文 (Chinese)')
    print('  [2] English')
    while True:
        c = input(cc('Y', '  Language / 语言 [1-2]: ')).strip()
        if c == '1': return 'zh'
        if c == '2': return 'en'

def T(lang, zh, en):
    return zh if lang == 'zh' else en

# ═══════════ 系统检测 ═══════════
def detect_system(lang):
    info = {}
    try:
        import psutil
        info['cpu_pct'] = psutil.cpu_percent(interval=0.5)
        info['cpu_count'] = psutil.cpu_count()
        info['ram'] = psutil.virtual_memory()
        info['ram_ok'] = info['ram'].percent < 90
    except: pass

    # GPU
    info['has_nvidia'] = False
    info['gpu_name'] = T(lang, '未检测到', 'Not detected')
    try:
        r = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu',
                           '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            parts = [p.strip() for p in r.stdout.split(',')]
            info['has_nvidia'] = True
            info['gpu_vram_total'] = int(parts[1])
            info['gpu_vram_used'] = int(parts[2])
            info['gpu_name'] = parts[0]
    except: pass

    # Conda
    info['conda_exe'] = None
    for p in [Path("C:/ProgramData/miniconda3/Scripts/conda.exe"),
              Path.home() / "miniconda3/Scripts/conda.exe"]:
        if p.exists():
            info['conda_exe'] = str(p)
            break

    # MinerU env
    info['mineru_python'] = None
    info['mineru_exe'] = None
    for d in [Path("C:/ProgramData/miniconda3/envs/MinerU"),
              Path.home() / ".conda/envs/MinerU"]:
        py = d / "python.exe"
        me = d / "Scripts" / "mineru.exe"
        if py.exists():
            info['mineru_python'] = str(py)
        if me.exists():
            info['mineru_exe'] = str(me)

    # Torch
    info['torch_ok'] = False
    if info['mineru_python']:
        try:
            r = subprocess.run([info['mineru_python'], '-c', 'import torch; print(torch.cuda.is_available())'],
                              capture_output=True, text=True, timeout=15)
            info['torch_ok'] = r.returncode == 0
        except: pass

    # MinerU installed
    info['mineru_installed'] = False
    if info['mineru_python']:
        try:
            r = subprocess.run([info['mineru_python'], '-c', 'import mineru; print("ok")'],
                              capture_output=True, text=True, timeout=10)
            info['mineru_installed'] = r.returncode == 0 and 'ok' in r.stdout
        except: pass

    # Models
    info['model_pipeline'] = False
    info['model_vlm'] = False
    cache = Path.home() / '.cache/modelscope/hub/models/OpenDataLab'
    if (cache / 'PDF-Extract-Kit-1___0').exists(): info['model_pipeline'] = True
    if (cache / 'MinerU2___5-Pro-2604-1___2B').exists(): info['model_vlm'] = True

    # CUDA enabled
    info['cuda_enabled'] = False
    cfg = Path.home() / 'mineru.json'
    if cfg.exists():
        try:
            c = json.loads(cfg.read_text(encoding='utf-8'))
            if c.get('device-mode') == 'cuda': info['cuda_enabled'] = True
        except: pass

    # Display
    print(cc('BOLD', T(lang, '\n📊 系统仪表盘', '\n📊 System Dashboard')))
    cpu_line = f'CPU: {info.get("cpu_pct",0):.0f}% ({info.get("cpu_count",0)} cores)'
    if info.get('ram'):
        ram = info['ram']
        cpu_line += f'  |  RAM: {ram.used/(1024**3):.1f}/{ram.total/(1024**3):.0f}GB ({ram.percent:.0f}%)'
    print(f'  {cpu_line}')
    print(f'  GPU: {info["gpu_name"]}  |  NVIDIA: {cc("G","✅") if info["has_nvidia"] else cc("R","❌")}')
    print(f'  Conda: {cc("G","✅") if info["conda_exe"] else cc("R","❌")}  |  MinerU环境: {cc("G","✅") if info["mineru_python"] else cc("D","❌")}')
    print(f'  PyTorch: {cc("G","✅") if info["torch_ok"] else cc("D","❌")}  |  MinerU包: {cc("G","✅") if info["mineru_installed"] else cc("D","❌")}')
    print(f'  Pipeline模型: {cc("G","✅") if info["model_pipeline"] else cc("D","❌")}  |  VLM模型: {cc("G","✅") if info["model_vlm"] else cc("D","❌")}')
    print(f'  CUDA加速: {cc("G","✅") if info["cuda_enabled"] else cc("D","❌")}')

    return info

# ═══════════ 十步安装向导 ═══════════
def run_setup_wizard(info, lang):
    steps = [
        (0, 'check_env', T(lang, '环境扫描', 'Environment Scan'),
         T(lang, '检测已安装的工具链', 'Detect installed toolchain'),
         lambda: True, None),
        (1, 'install_conda', T(lang, '安装 Miniconda', 'Install Miniconda'),
         T(lang, '轻量 Python 环境管理器 (~400MB)', 'Lightweight Python env manager (~400MB)'),
         lambda: info['conda_exe'] is not None, None),
        (2, 'create_env', T(lang, '创建 MinerU 环境', 'Create MinerU Env'),
         T(lang, 'Python 3.10 虚拟环境', 'Python 3.10 virtual environment'),
         lambda: info['mineru_python'] is not None, None),
        (3, 'install_torch', T(lang, '安装 PyTorch CUDA', 'Install PyTorch CUDA'),
         T(lang, 'GPU 加速框架 (~2.5GB)', 'GPU acceleration framework (~2.5GB)'),
         lambda: info['torch_ok'], lambda: not info['has_nvidia']),
        (4, 'install_mineru', T(lang, '安装 MinerU 程序包', 'Install MinerU Package'),
         T(lang, 'PDF 解析引擎 (~500MB)', 'PDF parsing engine (~500MB)'),
         lambda: info['mineru_installed'], None),
        (5, 'download_pipeline', T(lang, '下载 Pipeline 模型', 'Download Pipeline Model'),
         T(lang, '布局分析+表格+公式 (~4GB)', 'Layout+table+formula (~4GB)'),
         lambda: info['model_pipeline'], None),
        (6, 'download_vlm', T(lang, '下载 VLM 模型', 'Download VLM Model'),
         T(lang, '视觉大模型 (~2.2GB, 仅NVIDIA)', 'Vision LLM (~2.2GB, NVIDIA only)'),
         lambda: info['model_vlm'], lambda: not info['has_nvidia']),
        (7, 'install_zotero', T(lang, '安装 Zotero', 'Install Zotero'),
         T(lang, '文献管理软件 (~227MB)', 'Reference manager (~227MB)'),
         lambda: True, None),
        (8, 'install_bbt', T(lang, '安装 Zotero 插件', 'Install Zotero Plugin'),
         T(lang, 'Better BibTeX 导出插件', 'Better BibTeX export plugin'),
         lambda: True, None),
        (9, 'enable_cuda', T(lang, '启用 GPU 加速', 'Enable GPU Acceleration'),
         T(lang, '修改 mineru.json 使用 CUDA', 'Set mineru.json to CUDA'),
         lambda: info['cuda_enabled'], lambda: not info['has_nvidia']),
        (10, 'set_api_key', T(lang, '配置云端 API Key', 'Configure Cloud API Key'),
         T(lang, 'MinerU 在线解析 API 密钥', 'MinerU Cloud API token'),
         lambda: _check_api_key(), None),
    ]

    while True:
        # Display steps
        print(cc('BOLD', T(lang, '\n🔧 安装向导 (步骤 0-10)', '\n🔧 Setup Wizard (Steps 0-10)')))
        print(cc('D', T(lang, '  已完成步骤不再显示，输入 X 完成安装开始解析', '  Completed steps hidden. Enter X to finish and start parsing')))
        print()

        available = []
        for num, sid, name, desc, done_fn, skip_fn in steps:
            if skip_fn and skip_fn():
                print(f'  {cc("D", "["+str(num)+"]")} {name} — {desc}  {cc("D", T(lang, "(不适用/跳过)", "(N/A)"))}')
                continue
            if done_fn():
                print(f'  {cc("G", "✅")} {name} — {desc}')
                continue
            available.append((num, sid, name))
            print(f'  {cc("Y", "["+str(num)+"]")} {name} — {desc}')

        if not available:
            print(cc('G', T(lang, '\n✅ 所有步骤已完成！', '\n✅ All steps complete!')))
            break

        print(cc('Y', f'\n  [X] {T(lang, "完成安装，开始解析", "Finish & Start Parsing")}'))
        choice = input(cc('Y', T(lang, '  选择步骤 [X/0-10]: ', '  Select step [X/0-10]: '))).strip()

        if choice.upper() == 'X': break

        try:
            num = int(choice)
            found = None
            for n, sid, name in available:
                if n == num:
                    found = sid
                    break
            if not found:
                print(cc('R', T(lang, '  无效选择', '  Invalid choice')))
                continue

            # Execute step
            exec_setup_step(found, info, lang)
            # Refresh detection
            info = detect_system(lang)
        except ValueError:
            print(cc('R', T(lang, '  无效输入', '  Invalid input')))

    return info

def _check_api_key():
    for p in [CONFIG_PATH, Path.home() / '.env']:
        if p.exists():
            try:
                cfg = json.loads(p.read_text(encoding='utf-8')) if p.suffix == '.json' else {}
                if cfg.get('api_key'):
                    return True
            except: pass
    return False

def exec_setup_step(sid, info, lang):
    print(cc('BOLD', f'\n▶ {sid}'))

    if sid == 'check_env':
        info = detect_system(lang)

    elif sid == 'install_conda':
        print(T(lang, '  打开下载页: https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/', '  Opening: https://docs.conda.io/en/latest/miniconda.html'))
        webbrowser.open('https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/')

    elif sid == 'create_env':
        if not info['conda_exe']:
            print(cc('R', T(lang, '  需要先安装 Miniconda', '  Miniconda required first')))
            return
        print(T(lang, '  创建 MinerU 环境 (Python 3.10)...', '  Creating MinerU env (Python 3.10)...'))
        r = subprocess.run([info['conda_exe'], 'create', '-n', 'MinerU', 'python=3.10', '-y'], capture_output=True, text=True, timeout=300)
        print(cc('G', T(lang, '  ✅ 完成', '  ✅ Done')) if r.returncode == 0 else cc('R', f'  ❌ {r.stderr[-200:]}'))

    elif sid == 'install_torch':
        py = info.get('mineru_python') or 'python'
        print(T(lang, '  安装 PyTorch CUDA 12.1...', '  Installing PyTorch CUDA 12.1...'))
        r = subprocess.run([py, '-m', 'pip', 'install', 'torch', 'torchvision', '--index-url', 'https://download.pytorch.org/whl/cu121'],
                          capture_output=True, text=True, timeout=600)
        print(cc('G', T(lang, '  ✅ 完成', '  ✅ Done')) if r.returncode == 0 else cc('R', f'  ❌ {r.stderr[-200:]}'))

    elif sid == 'install_mineru':
        py = info.get('mineru_python') or 'python'
        print(T(lang, '  安装 MinerU + hf_xet...', '  Installing MinerU + hf_xet...'))
        for pkg in ['magic-pdf', 'hf-xet']:
            r = subprocess.run([py, '-m', 'pip', 'install', pkg], capture_output=True, text=True, timeout=300)
            print(f'  {pkg}: {"✅" if r.returncode==0 else "❌"}')

    elif sid == 'download_pipeline':
        py = info.get('mineru_python') or 'python'
        print(T(lang, '  下载 Pipeline 模型...', '  Downloading Pipeline model...'))
        r = subprocess.run([py, '-m', 'mineru', 'download', '--model', 'pipeline'],
                          capture_output=True, text=True, timeout=600)
        print(cc('G', T(lang, '  ✅ 完成', '  ✅ Done')) if r.returncode==0 else cc('R', '  ❌'))

    elif sid == 'download_vlm':
        py = info.get('mineru_python') or 'python'
        print(T(lang, '  下载 VLM 模型...', '  Downloading VLM model...'))
        r = subprocess.run([py, '-m', 'mineru', 'download', '--model', 'vlm'],
                          capture_output=True, text=True, timeout=600)
        print(cc('G', T(lang, '  ✅ 完成', '  ✅ Done')) if r.returncode==0 else cc('R', '  ❌'))

    elif sid == 'install_zotero':
        print(T(lang, '  打开 Zotero 下载页...', '  Opening Zotero download...'))
        webbrowser.open('https://www.zotero.org/download/')

    elif sid == 'install_bbt':
        print(T(lang, '  打开 Zotero 中文插件商店...', '  Opening Zotero CN plugin store...'))
        webbrowser.open('https://zotero-chinese.com/')

    elif sid == 'enable_cuda':
        cfg = Path.home() / 'mineru.json'
        data = {}
        if cfg.exists():
            data = json.loads(cfg.read_text(encoding='utf-8'))
        data['device-mode'] = 'cuda'
        cfg.write_text(json.dumps(data, indent=2), encoding='utf-8')
        print(cc('G', T(lang, '  ✅ CUDA 已启用', '  ✅ CUDA enabled')))

    elif sid == 'set_api_key':
        key = input(cc('Y', T(lang, '  输入 MinerU API Key: ', '  Enter MinerU API Key: '))).strip()
        if key:
            cfg = {}
            if CONFIG_PATH.exists():
                cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
            cfg['api_key'] = key
            CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
            print(cc('G', T(lang, '  ✅ 已保存', '  ✅ Saved')))

    input(cc('D', T(lang, '\n  按回车继续...', '\n  Press Enter to continue...')))

# ═══════════ 解析后端选择 ═══════════
def choose_backend(info, lang):
    print(cc('BOLD', T(lang, '\n🔧 选择解析方式', '\n🔧 Select Parse Mode')))
    opts = []

    opts.append(('1', 'pipeline', 'local', T(lang, 'Pipeline (快速, CPU/GPU适用)', 'Pipeline (Fast, CPU/GPU)')))
    opts.append(('2', 'pipeline', 'cloud', T(lang, '🌐 MinerU Cloud API (在线, Pipeline)', '🌐 MinerU Cloud API (Online, Pipeline)')))

    if info['has_nvidia'] and info['torch_ok'] and info['model_vlm']:
        opts.append(('3', 'vlm-auto-engine', 'local', T(lang, 'VLM (精准, 需 NVIDIA 8GB+)', 'VLM (Precise, NVIDIA 8GB+)')))
        opts.append(('4', 'hybrid-auto-engine', 'local', T(lang, 'Hybrid (Pipeline + VLM)', 'Hybrid (Pipeline + VLM)')))
    if info['has_nvidia'] or _check_api_key():
        opts.append(('5', 'vlm-auto-engine', 'cloud', T(lang, '🌐 MinerU Cloud API (在线, VLM)', '🌐 MinerU Cloud API (Online, VLM)')))

    for n, _, _, desc in opts:
        print(f'  [{n}] {desc}')

    while True:
        c = input(cc('Y', T(lang, '  选择: ', '  Select: '))).strip()
        for n, be, mo, _ in opts:
            if c == n:
                return be, mo
        print(cc('R', T(lang, '  无效选择', '  Invalid')))

# ═══════════ 输入/输出/范围 ═══════════
def parse_range(s, max_n):
    if not s.strip(): return list(range(max_n))
    indices = set()
    for part in s.split(','):
        part = part.strip()
        if '-' in part:
            a, _, b = part.partition('-')
            try:
                start = max(1, int(a.strip() or '1'))
                end = min(max_n, int(b.strip() or str(max_n)))
                for i in range(start, end+1): indices.add(i-1)
            except ValueError: pass
        else:
            try:
                i = int(part.strip())
                if 1 <= i <= max_n: indices.add(i-1)
            except ValueError: pass
    return sorted(indices)

def select_range(pdfs, lang):
    total = len(pdfs)
    print(cc('BOLD', T(lang, f'\n📋 {total} PDFs found / 共 {total} 篇', f'\n📋 {total} PDFs found')))
    print(cc('D', T(lang,
        '  示例: 11-108         → 解析第11到108篇',
        '  Example: 11-108      → papers 11 through 108')))
    print(cc('D', T(lang,
        '  示例: 1,3,5-10,15   → 解析第1,3,5-10,15篇',
        '  Example: 1,3,5-10,15 → papers 1, 3, 5-10, 15')))
    print(cc('D', T(lang,
        '  回车/Enter = 全部',
        '  Enter = all')))
    s = input(cc('Y', '  范围: ')).strip()
    indices = parse_range(s, total)
    selected = [pdfs[i] for i in indices]
    if indices:
        print(cc('G', f'  {len(selected)}/{total} selected [{indices[0]+1}-{indices[-1]+1}]'))
    return selected

def extract_pdfs_from_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    pdfs = []
    for item in data.get('items', []):
        ck = item.get('citationKey', '') or item.get('itemKey', '')
        title = (item.get('title', '') or '')[:60]
        for att in item.get('attachments', []):
            path = att.get('path', '')
            if path and os.path.exists(path) and path.lower().endswith('.pdf'):
                pdfs.append({'path': path, 'citekey': ck, 'title': title}); break
    return pdfs

def extract_pdfs_from_folder(folder):
    return [{'path': os.path.join(folder,f), 'citekey': f.replace('.pdf',''), 'title': f}
            for f in sorted(os.listdir(folder)) if f.lower().endswith('.pdf')]

# ═══════════ 解析 ═══════════
def run_local_parse(pdfs, backend, output_dir, lang):
    total = len(pdfs)
    t0 = time.time()
    batch_dir = Path(output_dir) / f'_batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_out = batch_dir / '_mineru_output'

    name_map = {}
    print(T(lang, f'\n📋 准备 {total} 篇 PDF...', f'\n📋 Preparing {total} PDFs...'))
    for i, pdf in enumerate(pdfs):
        safe = re.sub(r'[<>:"/\\|?*]', '_', pdf['citekey'])[:80]
        try:
            shutil.copy2(pdf['path'], batch_dir / f'{safe}.pdf')
            name_map[safe] = pdf['citekey']
        except Exception as e:
            print(cc('R', f'  ✗ {safe}: {e}'))

    # 使用 conda 环境中的 mineru.exe 完整路径
    mineru_exe = None
    for d in [Path("C:/ProgramData/miniconda3/envs/MinerU/Scripts/mineru.exe"),
              Path.home() / ".conda/envs/MinerU/Scripts/mineru.exe"]:
        if d.exists():
            mineru_exe = str(d)
            break
    if not mineru_exe:
        print(cc('R', 'mineru.exe not found! Check conda MinerU environment.'))
        return

    cmd = [mineru_exe, '-p', str(batch_dir), '-o', str(batch_out), '-b', backend, '-l', lang]
    print(cc('BOLD', T(lang, f'\n🚀 模型加载一次，处理全部 {total} 篇...', f'\n🚀 Processing all {total} PDFs (single model load)...')))
    print(f'  {" ".join(cmd[:5])} ...')

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding='utf-8', errors='replace')
        for line in proc.stdout:
            line = line.rstrip()
            if any(kw in line for kw in ['%','batch','pages','完成','done','Error','error','✓']):
                print(f'  {line[:150]}')
        proc.wait(timeout=7200)
        success = 0
        if proc.returncode == 0:
            for safe_name, citekey in name_map.items():
                out_dir = Path(output_dir) / citekey
                out_dir.mkdir(parents=True, exist_ok=True)
                found = False
                for sd in [batch_out] + list(batch_out.rglob('*')):
                    if not sd.is_dir(): continue
                    for md_file in sd.glob(f'{safe_name}*.md'):
                        shutil.move(str(md_file), str(out_dir / f'{citekey}.md')); found = True
                    for img_dir in sd.glob('images'):
                        if img_dir.is_dir() and not (out_dir / 'images').exists():
                            shutil.copytree(str(img_dir), str(out_dir / 'images'))
                if found: success += 1
            elapsed = time.time() - t0
            print(cc('BOLD', cc('G', T(lang, f'\n✅ {success}/{total} 成功 | {elapsed:.0f}s ({elapsed/total:.0f}s/篇)',
                                      f'\n✅ {success}/{total} done | {elapsed:.0f}s ({elapsed/total:.0f}s/paper)'))))
        else:
            print(cc('R', f'\n❌ mineru exit={proc.returncode}'))
    except Exception as e:
        print(cc('R', f'\n❌ {e}'))
    finally:
        shutil.rmtree(batch_dir, ignore_errors=True)

# ═══════════ 主入口 ═══════════
def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    # 1. 界面语言
    ui_lang = choose_language()

    # 2. 仪表盘
    info = detect_system(ui_lang)

    # 3. 安装向导
    info = run_setup_wizard(info, ui_lang)

    # 4. 刷新检测
    info = detect_system(ui_lang)

    # 5. 选择后端
    backend, mode = choose_backend(info, ui_lang)

    # 6. 解析语言（区别于界面语言）
    print(cc('BOLD', T(ui_lang, '\n🌐 解析语言', '\n🌐 Parse Language')))
    print(T(ui_lang, '  选择被解析论文的语言:', '  Select language of papers to parse:'))
    print(T(ui_lang, '  [1] 中文论文', '  [1] Chinese papers'))
    print(T(ui_lang, '  [2] English papers', '  [2] English papers'))
    parse_lang = 'en' if input(cc('Y', '  > ')).strip() == '2' else 'zh'

    # 7. 输入
    print(cc('BOLD', T(ui_lang, '\n📂 输入', '\n📂 Input')))
    print(T(ui_lang, '  [1] Zotero BBT JSON', '  [1] Zotero BBT JSON'))
    print(T(ui_lang, '  [2] PDF 文件夹', '  [2] PDF folder'))
    c = input(cc('Y', '  > ')).strip()
    if c == '2':
        folder = input(cc('Y', T(ui_lang, '  文件夹路径: ', '  Folder path: '))).strip().strip('"')
        pdfs = extract_pdfs_from_folder(folder)
    else:
        jpath = input(cc('Y', T(ui_lang, '  JSON路径: ', '  JSON path: '))).strip().strip('"')
        pdfs = extract_pdfs_from_json(jpath)

    if not pdfs:
        print(cc('R', T(ui_lang, '❌ 无PDF', '❌ No PDFs found'))); return
    for i, p in enumerate(pdfs[:3]):
        print(f'  {i+1}. {p["citekey"][:40]}')
    if len(pdfs) > 3: print(f'  ... {len(pdfs)} total')

    # 8. 范围
    pdfs = select_range(pdfs, ui_lang)

    # 9. 输出
    print(cc('BOLD', T(ui_lang, '\n📁 输出', '\n📁 Output')))
    while True:
        out = input(cc('Y', T(ui_lang, '  输出目录 (必填): ', '  Output dir (required): '))).strip().strip('"')
        if out:
            os.makedirs(out, exist_ok=True); break
        print(cc('R', T(ui_lang, '  必须输入', '  Required')))

    # 10. 确认
    print(cc('BOLD', T(ui_lang, '\n📋 确认', '\n📋 Confirm')))
    print(f'  {T(ui_lang, "模式", "Mode")}: {mode} | {T(ui_lang, "后端", "Backend")}: {backend} | {T(ui_lang, "解析语言", "Parse Lang")}: {parse_lang}')
    print(f'  {len(pdfs)} PDFs → {out}')
    if input(cc('Y', T(ui_lang, '\n  开始? [Y/n]: ', '\n  Start? [Y/n]: '))).strip().lower() not in ('', 'y'):
        return

    # 11. 跑
    if mode == 'cloud':
        print(T(ui_lang, '⚠ 云端模式需 API Key，先用本地 Pipeline 解析', '⚠ Cloud mode needs API Key, using local Pipeline'))
        run_local_parse(pdfs, 'pipeline', out, parse_lang)
    else:
        run_local_parse(pdfs, backend, out, parse_lang)

    print(cc('G', T(ui_lang, '\n🎉 全部完成!', '\n🎉 All done!')))
    input(cc('D', T(ui_lang, '\n按回车退出...', '\nPress Enter to exit...')))

if __name__ == '__main__':
    main()
