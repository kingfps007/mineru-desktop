"""
MinerU 云端解析脚本 (mineru_parser.py)
=======================================
读取 Zotero BetterBibTeX JSON 导出的 references.json，
通过 MinerU 精准解析 API (v4) 批量解析本地 PDF，
将结果保存到 parsed_papers/{citationKey}/ 目录下。

流程：
  1. 解析 references.json 提取 citationKey + PDF 路径
  2. 调用 /api/v4/file-urls/batch 获取预签名上传链接
  3. PUT 上传 PDF 到 OSS
  4. 轮询 /api/v4/extract-results/batch/{batch_id} 获取结果
  5. 下载 zip 包，解压 Markdown 到本地

使用方法:
    python mineru_parser.py
"""

import json
import os
import sys
import time
import zipfile
import io
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================
# 配置
# ============================================
MINERU_API_KEY = os.getenv("MINERU_API_KEY")
MINERU_BASE = "https://mineru.net/api/v4"
OUTPUT_DIR = Path("parsed_papers")
REFERENCES_FILE = "260528阶段所有文献导出的条目部分含html.json"

POLL_INTERVAL = 15      # 轮询间隔（秒）
MAX_POLL_TIME = 1800    # 单个任务最长等待 30 分钟
MAX_BATCH_SIZE = 10     # 单次批量最大文件数（小批次防超时）


# ============================================
# 1. 解析 references.json
# ============================================
def load_references() -> list[dict]:
    """
    解析 Zotero BetterBibTeX JSON 格式。
    提取 citationKey 和本地 PDF 绝对路径。
    """
    if not os.path.exists(REFERENCES_FILE):
        print(f"[ERROR] 未找到 {REFERENCES_FILE}")
        print("  请在 Zotero 中: 选中文献 → 右键 → Export Items → Better BibTeX JSON")
        sys.exit(1)

    with open(REFERENCES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # BetterBibTeX JSON 顶层可能是 list 或 {"items": [...]}
    items = data if isinstance(data, list) else data.get("items", [])

    papers = []
    for item in items:
        # 获取 citationKey
        ck = (
            item.get("citationKey")
            or item.get("citation-key")
            or item.get("id", "unknown")
        )

        # 提取 PDF 和 HTML 路径
        pdf_path = None
        html_path = None

        for att in item.get("attachments", []):
            p = att.get("path", "")
            if p.lower().endswith(".pdf"):
                pdf_path = p
            if p.lower().endswith(".html") or p.lower().endswith(".htm"):
                html_path = p

        if not pdf_path:
            # 方式2: file 字段
            file_field = item.get("file", "")
            if file_field:
                for part in file_field.replace("\\:", "\x00").split(":"):
                    part = part.replace("\x00", ":")
                    if part.strip().lower().endswith(".pdf"):
                        pdf_path = part.strip()
                        break

        if not pdf_path:
            print(f"  [跳过] {ck}: 无 PDF 附件")
            continue

        if not os.path.isfile(pdf_path):
            print(f"  [跳过] {ck}: PDF 不存在 → {pdf_path}")
            continue

        papers.append({
            "citation_key": ck,
            "pdf_path": pdf_path,
            "html_path": html_path,
            "title": item.get("title", "")[:80],
        })

    return papers


# ============================================
# 2. 批量获取上传链接 + 上传 + 提交解析
# ============================================
def batch_upload_and_parse(papers: list[dict]) -> str:
    """
    调用 /api/v4/file-urls/batch 获取上传链接，
    上传文件后系统自动触发解析。
    返回 batch_id。
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MINERU_API_KEY}",
    }

    # 构造请求体
    file_names = [os.path.basename(p["pdf_path"]) for p in papers]
    files_payload = [{"name": fn} for fn in file_names]

    payload = {
        "files": files_payload,
        "enable_formula": True,
        "enable_table": True,
        "model_version": "vlm",
        "language": "en",
    }

    print(f"\n[2] 请求批量上传链接 ({len(papers)} 个文件)...")
    resp = requests.post(
        f"{MINERU_BASE}/file-urls/batch",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"  [ERROR] 请求失败 HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)

    result = resp.json()
    if result.get("code") != 0:
        print(f"  [ERROR] API 返回错误: {result}")
        sys.exit(1)

    data = result["data"]
    batch_id = data.get("batch_id")
    file_urls = data.get("file_urls", [])

    print(f"  batch_id: {batch_id}")
    print(f"  获得 {len(file_urls)} 个上传链接")

    # 逐个上传文件
    print(f"\n[3] 上传 PDF 文件...")
    for i, (paper, url_info) in enumerate(zip(papers, file_urls), 1):
        # url_info 可能是字符串(直接URL)或字典({"put_url": "...", ...})
        if isinstance(url_info, str):
            put_url = url_info
        elif isinstance(url_info, dict):
            put_url = url_info.get("put_url") or url_info.get("url")
        else:
            print(f"  [{i}/{len(papers)}] 无法解析上传链接，跳过")
            continue
        pdf_path = paper["pdf_path"]
        fname = os.path.basename(pdf_path)
        fsize = os.path.getsize(pdf_path) / (1024 * 1024)

        success = False
        for attempt in range(3):
            try:
                with open(pdf_path, "rb") as f:
                    put_resp = requests.put(put_url, data=f, timeout=600)
                if put_resp.status_code in (200, 201):
                    print(f"  [{i}/{len(papers)}] {fname[:60]} ({fsize:.1f} MB)... OK")
                    success = True
                    break
                else:
                    print(f"  [{i}/{len(papers)}] HTTP {put_resp.status_code} (try {attempt+1}/3)", end=" ")
            except Exception as e:
                print(f"  [{i}/{len(papers)}] err (try {attempt+1}/3)", end=" ")
            if attempt < 2:
                time.sleep(10)
        if not success:
            print(f"\n  [{i}/{len(papers)}] {fname[:60]}... FAILED after 3 attempts")

    return batch_id


# ============================================
# 3. 单文件模式（逐个处理，备用方案）
# ============================================
def single_file_parse(paper: dict) -> str | None:
    """
    如果批量接口不适用，逐个用 /api/v4/extract/task 处理。
    需要先上传到能公开访问的 URL。
    这里用 file-urls/batch 单文件版本。
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MINERU_API_KEY}",
    }

    payload = {
        "files": [{"name": os.path.basename(paper["pdf_path"])}],
        "enable_formula": True,
        "enable_table": True,
        "model_version": "vlm",
        "language": "en",
    }

    resp = requests.post(
        f"{MINERU_BASE}/file-urls/batch",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code != 200:
        return None

    result = resp.json()
    if result.get("code") != 0:
        return None

    data = result["data"]
    batch_id = data.get("batch_id")
    file_urls = data.get("file_urls", [])

    if not file_urls:
        return None

    # 上传
    put_url = file_urls[0].get("put_url") or file_urls[0].get("url")
    with open(paper["pdf_path"], "rb") as f:
        put_resp = requests.put(put_url, data=f, timeout=300)

    if put_resp.status_code not in (200, 201):
        return None

    return batch_id


# ============================================
# 4. 轮询结果
# ============================================
def poll_batch_results(batch_id: str) -> dict | None:
    """
    轮询 /api/v4/extract-results/batch/{batch_id}。
    返回批次结果。
    """
    headers = {
        "Authorization": f"Bearer {MINERU_API_KEY}",
    }

    start = time.time()
    print(f"\n[4] 轮询解析状态 (batch_id={batch_id})...")

    while True:
        elapsed = time.time() - start
        if elapsed > MAX_POLL_TIME:
            print(f"\n  [TIMEOUT] 超过 {MAX_POLL_TIME}s，终止等待")
            return None

        resp = requests.get(
            f"{MINERU_BASE}/extract-results/batch/{batch_id}",
            headers=headers,
            timeout=30,
        )

        if resp.status_code != 200:
            # 可能接口路径不同，尝试备用路径
            resp = requests.get(
                f"{MINERU_BASE}/extract/batch/{batch_id}",
                headers=headers,
                timeout=30,
            )

        if resp.status_code != 200:
            print(f"\r  [等待] {elapsed:.0f}s (HTTP {resp.status_code})...", end="", flush=True)
            time.sleep(POLL_INTERVAL)
            continue

        result = resp.json()
        if result.get("code") != 0:
            print(f"\r  [等待] {elapsed:.0f}s (code={result.get('code')})...", end="", flush=True)
            time.sleep(POLL_INTERVAL)
            continue

        data = result.get("data", {})
        # 批量结果在 extract_result (单数) 列表中
        extract_list = data.get("extract_result", [])

        if not extract_list:
            print(f"\r  [等待] {elapsed:.0f}s 等待结果...        ", end="", flush=True)
            time.sleep(POLL_INTERVAL)
            continue

        # 检查每个文件的状态
        states = [item.get("state", "") for item in extract_list]
        done_count = sum(1 for s in states if s == "done")
        failed_count = sum(1 for s in states if s == "failed")

        if done_count == len(extract_list):
            print(f"\n  [完成] 全部解析完毕 ({elapsed:.0f}s)")
            return data
        elif failed_count > 0:
            print(f"\n  [部分失败] {failed_count}/{len(extract_list)} 个文件解析失败")
            return data
        else:
            done_info = f" ({done_count}/{len(extract_list)} done)" if done_count else ""
            print(f"\r  [等待] {elapsed:.0f}s 状态: {states[0]}{done_info}        ", end="", flush=True)
            time.sleep(POLL_INTERVAL)


def poll_single_task(task_id: str) -> dict | None:
    """轮询单个任务结果。"""
    headers = {"Authorization": f"Bearer {MINERU_API_KEY}"}
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > MAX_POLL_TIME:
            return None

        resp = requests.get(
            f"{MINERU_BASE}/extract/task/{task_id}",
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            time.sleep(POLL_INTERVAL)
            continue

        result = resp.json()
        data = result.get("data", {})
        state = data.get("state", "")

        if state == "done":
            return data
        elif state == "failed":
            return None
        else:
            print(f"\r  [等待] {elapsed:.0f}s 状态: {state}        ", end="", flush=True)
            time.sleep(POLL_INTERVAL)


# ============================================
# 5. 下载并解压结果
# ============================================
def download_results(batch_data: dict, papers: list[dict]):
    """
    从结果中下载 zip 包，解压 Markdown + 图片到 parsed_papers/{citationKey}/
    """
    print(f"\n[5] 下载解析结果...")
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 批量结果在 extract_result (单数) 列表中
    results_list = batch_data.get("extract_result", [])

    # 如果是单结果格式
    if not results_list and batch_data.get("full_zip_url"):
        results_list = [batch_data]

    if not results_list:
        # 尝试 task_ids 格式
        task_ids = batch_data.get("task_ids", [])
        if task_ids:
            headers = {"Authorization": f"Bearer {MINERU_API_KEY}"}
            for tid in task_ids:
                task_data = poll_single_task(tid)
                if task_data:
                    results_list.append(task_data)

    for i, (paper, res) in enumerate(zip(papers, results_list)):
        ck = paper["citation_key"]
        out_dir = OUTPUT_DIR / ck
        out_dir.mkdir(parents=True, exist_ok=True)

        zip_url = res.get("full_zip_url") or res.get("zip_url") or res.get("result_url")
        md_url = res.get("markdown_url") or res.get("md_url")

        if zip_url:
            print(f"  [{i+1}] {ck}: 下载...", end=" ")
            success = False
            for attempt in range(5):
                try:
                    zip_resp = requests.get(zip_url, timeout=120)
                    if zip_resp.status_code == 200:
                        with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
                            for name in zf.namelist():
                                content = zf.read(name)
                                target = out_dir / Path(name).name
                                if name.endswith("/"):
                                    continue
                                if name.lower().endswith(".md"):
                                    target = out_dir / f"{ck}.md"
                                elif any(name.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".svg"]):
                                    img_dir = out_dir / "images"
                                    img_dir.mkdir(exist_ok=True)
                                    target = img_dir / Path(name).name
                                target.write_bytes(content)
                        print("OK (zip)")
                        success = True
                        break
                    else:
                        print(f"HTTP {zip_resp.status_code}", end=" ")
                except Exception as e:
                    if attempt < 4:
                        time.sleep(5 * (attempt + 1))
                if attempt < 4:
                    time.sleep(5)
            if not success:
                # fallback to md_url
                if md_url:
                    print("fallback md...", end=" ")
                    for attempt in range(3):
                        try:
                            md_resp = requests.get(md_url, timeout=60)
                            if md_resp.status_code == 200:
                                (out_dir / f"{ck}.md").write_text(md_resp.text, encoding="utf-8")
                                print("OK (md)")
                                break
                        except Exception:
                            time.sleep(3)
                else:
                    print("FAILED")
        else:
            print(f"  [{i+1}] {ck}: 无下载链接，跳过")


# ============================================
# 6. 复制 HTML 参考快照
# ============================================
import shutil

def copy_html_reference(paper: dict):
    """将 Zotero 网页快照复制到输出目录作为参考"""
    if not paper.get("html_path"):
        return
    html_src = paper["html_path"]
    if not os.path.isfile(html_src):
        return
    out_dir = OUTPUT_DIR / paper["citation_key"]
    out_dir.mkdir(parents=True, exist_ok=True)
    ref_dir = out_dir / "_reference"
    ref_dir.mkdir(exist_ok=True)
    target = ref_dir / os.path.basename(html_src)
    if not target.exists():
        shutil.copy2(html_src, target)


# ============================================
# 主流程
# ============================================
def main():
    print("=" * 60)
    print("  MinerU 云端精准解析脚本 (v4 VLM)")
    print("  公式识别+表格识别: ON")
    print("=" * 60)

    if not MINERU_API_KEY:
        print("\n[ERROR] 请在 .env 中配置 MINERU_API_KEY")
        sys.exit(1)

    # 1. 加载文献
    print(f"\n[1] 解析 {REFERENCES_FILE}...")
    papers = load_references()
    n_pdf = len(papers)
    n_html = sum(1 for p in papers if p.get("html_path"))
    print(f"  共 {n_pdf} 篇 PDF, 其中 {n_html} 篇有 HTML 快照参考")

    if not papers:
        print("[ERROR] 无可处理文献")
        sys.exit(1)

    # 复制 HTML 参考
    if n_html > 0:
        print(f"\n[1.5] 复制 HTML 参考快照...")
        for p in papers:
            copy_html_reference(p)
        print(f"  完成: {n_html} 个参考快照")

    # 过滤已解析的
    todo = [p for p in papers if not (OUTPUT_DIR / p["citation_key"] / f"{p['citation_key']}.md").exists()]
    done = n_pdf - len(todo)
    if done > 0:
        print(f"\n  已解析: {done}, 待处理: {len(todo)}")

    if not todo:
        print("\n[INFO] 所有文献已解析完毕！")
        _print_summary(papers)
        return

    # 分批处理 (MAX_BATCH_SIZE)
    total_batches = (len(todo) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
    batch_num = 0
    original_todo = list(todo)

    while todo:
        batch_num += 1
        chunk = todo[:MAX_BATCH_SIZE]
        todo = todo[MAX_BATCH_SIZE:]

        print(f"\n{'─' * 50}")
        print(f"  批次 {batch_num}/{total_batches}: {len(chunk)} 篇")
        print(f"{'─' * 50}")

        # 上传
        batch_id = batch_upload_and_parse(chunk)
        if not batch_id:
            print("[ERROR] 批次上传失败，跳过...")
            continue

        # 轮询
        batch_data = poll_batch_results(batch_id)
        if not batch_data:
            print("[ERROR] 解析失败或超时，跳过...")
            continue

        # 下载
        download_results(batch_data, chunk)

    # 汇总
    _print_summary(papers)


def _print_summary(papers):
    parsed = sum(1 for p in papers if (OUTPUT_DIR / p["citation_key"] / f"{p['citation_key']}.md").exists())
    md_total = 0
    img_total = 0
    for p in papers:
        out_dir = OUTPUT_DIR / p["citation_key"]
        md_file = out_dir / f"{p['citation_key']}.md"
        if md_file.exists():
            md_total += md_file.stat().st_size
        img_dir = out_dir / "images"
        if img_dir.exists():
            img_total += len(list(img_dir.iterdir()))
    html_ref_count = sum(1 for p in papers if (OUTPUT_DIR / p["citation_key"] / "_reference").exists())
    print(f"\n{'=' * 60}")
    print(f"  完成！已解析 {parsed}/{len(papers)} 篇")
    print(f"  Markdown 总量: {md_total/1024:.0f} KB")
    print(f"  图片总数: {img_total}")
    print(f"  HTML 参考: {html_ref_count} 篇")
    print(f"  输出目录: {OUTPUT_DIR.resolve()}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
