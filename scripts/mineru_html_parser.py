"""
MinerU HTML 网页快照解析脚本
==============================
读取 Zotero BetterBibTeX JSON 中的 HTML 快照路径，
通过 MinerU v4 API (MinerU-HTML 模型) 解析，
输出到 parsed_papers_html/{citationKey}/

与 PDF 解析的区别:
- model_version: "MinerU-HTML" (非 vlm)
- 不需要 enable_formula/enable_table/language 参数
- 输出包含 full.md + main.html (提取后的正文HTML)
"""
import json, os, sys, time, zipfile, io, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MINERU_API_KEY = os.getenv("MINERU_API_KEY")
MINERU_BASE = "https://mineru.net/api/v4"
OUTPUT_DIR = Path("parsed_papers_html")
REFERENCES_FILE = "前三web导出的条目.json"
POLL_INTERVAL = 10
MAX_POLL_TIME = 1200


def load_web_references() -> list[dict]:
    """从 Zotero BetterBibTeX JSON 提取 HTML 快照路径"""
    if not os.path.exists(REFERENCES_FILE):
        print(f"[ERROR] {REFERENCES_FILE} 不存在")
        sys.exit(1)

    with open(REFERENCES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data if isinstance(data, list) else data.get("items", [])
    papers = []

    for item in items:
        ck = item.get("citationKey") or item.get("citation-key") or item.get("id", "unknown")
        title = item.get("title", "")[:80]

        html_path = None
        for att in item.get("attachments", []):
            p = att.get("path", "")
            if p.lower().endswith(".html") or p.lower().endswith(".htm"):
                html_path = p
                # 确认是快照类型
                if "Snapshot" in att.get("title", "") or "snapshot" in att.get("title", ""):
                    break

        if not html_path:
            print(f"  [跳过] {ck}: 无 HTML 快照")
            continue

        if not os.path.isfile(html_path):
            print(f"  [跳过] {ck}: HTML 不存在 -> {html_path}")
            continue

        fsize = os.path.getsize(html_path) / (1024 * 1024)
        papers.append({
            "citation_key": ck,
            "html_path": html_path,
            "title": title,
            "size_mb": fsize,
        })

    return papers


def batch_upload_html(papers: list[dict]) -> str:
    """上传 HTML 文件到 MinerU (MinerU-HTML 模型)"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MINERU_API_KEY}",
    }

    files_payload = [
        {"name": os.path.basename(p["html_path"])}
        for p in papers
    ]

    payload = {
        "files": files_payload,
        "model_version": "MinerU-HTML",
    }

    n = len(papers)
    total_mb = sum(p["size_mb"] for p in papers)
    print(f"\n[1] 请求批量上传链接 ({n} 个 HTML, 共 {total_mb:.1f} MB)...")

    resp = requests.post(
        f"{MINERU_BASE}/file-urls/batch",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"  [ERROR] HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)

    result = resp.json()
    if result.get("code") != 0:
        print(f"  [ERROR] API 返回: {result}")
        sys.exit(1)

    data = result["data"]
    batch_id = data.get("batch_id")
    file_urls = data.get("file_urls", [])

    print(f"  batch_id: {batch_id}")
    print(f"  获得 {len(file_urls)} 个上传链接")

    # 上传
    print(f"\n[2] 上传 HTML 文件...")
    for i, (paper, url_info) in enumerate(zip(papers, file_urls), 1):
        if isinstance(url_info, str):
            put_url = url_info
        elif isinstance(url_info, dict):
            put_url = url_info.get("put_url") or url_info.get("url")
        else:
            print(f"  [{i}/{n}] 无法解析链接，跳过")
            continue

        html_path = paper["html_path"]
        fname = paper["title"][:60]
        print(f"  [{i}/{n}] {fname} ({paper['size_mb']:.1f} MB)...", end=" ")

        with open(html_path, "rb") as f:
            put_resp = requests.put(put_url, data=f, timeout=300)

        if put_resp.status_code in (200, 201):
            print("OK")
        else:
            print(f"FAILED ({put_resp.status_code})")

    return batch_id


def poll_html_batch(batch_id: str) -> dict | None:
    """轮询 HTML 批量解析结果"""
    headers = {"Authorization": f"Bearer {MINERU_API_KEY}"}
    start = time.time()

    print(f"\n[3] 轮询解析状态 (batch_id={batch_id})...")

    while True:
        elapsed = time.time() - start
        if elapsed > MAX_POLL_TIME:
            print(f"\n  [TIMEOUT] 超过 {MAX_POLL_TIME}s")
            return None

        resp = requests.get(
            f"{MINERU_BASE}/extract-results/batch/{batch_id}",
            headers=headers,
            timeout=30,
        )

        if resp.status_code != 200:
            print(f"\r  [{elapsed:.0f}s] HTTP {resp.status_code}...", end="", flush=True)
            time.sleep(POLL_INTERVAL)
            continue

        result = resp.json()
        if result.get("code") != 0:
            print(f"\r  [{elapsed:.0f}s] code={result.get('code')}...", end="", flush=True)
            time.sleep(POLL_INTERVAL)
            continue

        data = result.get("data", {})
        extract_list = data.get("extract_result", [])

        if not extract_list:
            print(f"\r  [{elapsed:.0f}s] 等待...", end="", flush=True)
            time.sleep(POLL_INTERVAL)
            continue

        states = [item.get("state", "") for item in extract_list]
        done_count = sum(1 for s in states if s == "done")
        failed_count = sum(1 for s in states if s == "failed")

        if done_count == len(extract_list):
            print(f"\n  [完成] 全部解析完毕 ({elapsed:.0f}s)")
            return data
        elif failed_count > 0:
            print(f"\n  [部分失败] {failed_count}/{len(extract_list)}")
            return data
        else:
            print(f"\r  [{elapsed:.0f}s] {done_count}/{len(extract_list)} done...", end="", flush=True)
            time.sleep(POLL_INTERVAL)


def download_html_results(batch_data: dict, papers: list[dict]):
    """下载 HTML 解析结果: full.md + main.html + images"""
    print(f"\n[4] 下载解析结果...")
    OUTPUT_DIR.mkdir(exist_ok=True)

    extract_list = batch_data.get("extract_result", [])

    for i, (paper, res) in enumerate(zip(papers, extract_list)):
        ck = paper["citation_key"]
        out_dir = OUTPUT_DIR / ck
        out_dir.mkdir(parents=True, exist_ok=True)

        zip_url = res.get("full_zip_url")
        if not zip_url:
            print(f"  [{i+1}] {ck}: 无下载链接")
            continue

        print(f"  [{i+1}] {ck}: 下载 zip...", end=" ")
        try:
            zip_resp = requests.get(zip_url, timeout=120)
            if zip_resp.status_code != 200:
                print(f"FAILED ({zip_resp.status_code})")
                continue

            with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
                for name in zf.namelist():
                    content = zf.read(name)
                    if name.endswith("/"):
                        continue

                    fname = Path(name).name
                    if fname.lower() == "full.md":
                        target = out_dir / f"{ck}.md"
                    elif fname.lower() == "main.html":
                        target = out_dir / f"{ck}_body.html"
                    elif any(fname.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".svg"]):
                        img_dir = out_dir / "images"
                        img_dir.mkdir(exist_ok=True)
                        target = img_dir / fname
                    else:
                        target = out_dir / fname

                    target.write_bytes(content)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")


def main():
    print("=" * 60)
    print("  MinerU HTML 网页快照解析脚本")
    print("  模型: MinerU-HTML | API: v4")
    print("=" * 60)

    if not MINERU_API_KEY:
        print("\n[ERROR] 请在 .env 中配置 MINERU_API_KEY")
        sys.exit(1)

    print(f"\n[0] 解析 {REFERENCES_FILE}...")
    papers = load_web_references()
    print(f"  共提取 {len(papers)} 个 HTML 快照")
    for p in papers:
        print(f"    - {p['citation_key']}: {p['size_mb']:.1f} MB")

    if not papers:
        print("[ERROR] 无可处理文件")
        sys.exit(1)

    todo = [p for p in papers if not (OUTPUT_DIR / p["citation_key"] / f"{p['citation_key']}.md").exists()]
    done = len(papers) - len(todo)
    if done > 0:
        print(f"  已解析: {done}, 待处理: {len(todo)}")
    if not todo:
        print("\n[INFO] 全部已解析！")
        return

    batch_id = batch_upload_html(todo)
    batch_data = poll_html_batch(batch_id)
    if not batch_data:
        print("[ERROR] 解析失败或超时")
        sys.exit(1)

    download_html_results(batch_data, todo)

    parsed_count = sum(1 for p in papers if (OUTPUT_DIR / p["citation_key"] / f"{p['citation_key']}.md").exists())
    print(f"\n{'=' * 60}")
    print(f"  全部完成！已解析 {parsed_count}/{len(papers)} 篇")
    print(f"  输出目录: {OUTPUT_DIR.resolve()}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
