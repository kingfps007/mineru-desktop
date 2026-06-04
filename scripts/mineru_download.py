"""
MinerU 解析结果下载脚本 (mineru_download.py)
=============================================
通过 curl.exe 下载 CDN 上的 zip 结果，解决 Python requests SSL 问题。
用法: python mineru_download.py
"""

import json
import os
import sys
import zipfile
import io
import requests
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MINERU_API_KEY = os.getenv("MINERU_API_KEY")
OUTPUT_DIR = Path("parsed_papers")

def get_batch_info(batch_id: str) -> dict:
    """获取批次解析结果的URL列表"""
    url = f"https://mineru.net/api/v4/extract-results/batch/{batch_id}"
    headers = {"Authorization": f"Bearer {MINERU_API_KEY}"}
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"  API error: {resp.status_code}")
        return {"extract_result": []}
    return resp.json().get("data", {})

def download_with_curl(zip_url: str, out_path: str) -> bool:
    """使用 curl.exe 下载文件"""
    try:
        result = subprocess.run(
            ["curl", "-L", "-o", out_path, "--connect-timeout", "30", "--max-time", "600", zip_url],
            capture_output=True, text=True, timeout=620
        )
        if result.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
            return True
        print(f"    curl failed: {result.stderr[:100]}")
        return False
    except Exception as e:
        print(f"    curl error: {e}")
        return False

def extract_zip(zip_path: Path, citation_key: str, out_dir: Path):
    """解压 zip 并重命名 md 文件"""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                content = zf.read(name)
                fname = Path(name).name
                if fname.lower().endswith(".md"):
                    target = out_dir / f"{citation_key}.md"
                elif fname.lower()[-4:] in [".png", ".jpg", "jpeg", ".svg", ".gif"]:
                    img_dir = out_dir / "images"
                    img_dir.mkdir(exist_ok=True)
                    target = img_dir / fname
                else:
                    target = out_dir / fname
                target.write_bytes(content)
        print(f"    OK ({len(zipfile.ZipFile(zip_path).namelist())} files)")
    except Exception as e:
        print(f"    EXTRACT ERROR: {e}")

def main():
    print("=" * 60)
    print("  MinerU CDN 下载脚本 (curl.exe)")
    print("=" * 60)

    if len(sys.argv) < 2:
        print("\n请输入 batch_id（可多个，空格分隔）：")
        print("  已知 batch IDs:")
        print("    1. b33838c2-fce4-4182-a3b6-99f0051ca12b")
        print("    2. 3828ff3a-da5b-43be-b364-e7d78310c669")
        print("    3. 619bdcad-27e3-4e50-a0e8-01fb012dded8")
        print("    4. 9dc10114-a55a-428b-be29-6042bef40939")
        batch_ids_str = input("\nbatch_id(s): ").strip()
        batch_ids = batch_ids_str.split()
    else:
        batch_ids = sys.argv[1:]

    if not batch_ids:
        print("没有提供 batch_id，退出。")
        return

    # 先读取 JSON 获取 citationKey 映射
    print(f"\n[0] 加载文献映射...")
    json_file = "260528阶段所有文献导出的条目部分含html.json"
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data if isinstance(data, list) else data.get("items", [])
    ck_map = {}
    for item in items:
        ck = item.get("citationKey") or item.get("citation-key")
        for att in item.get("attachments", []):
            p = att.get("path", "")
            if p.lower().endswith(".pdf"):
                ck_map[os.path.basename(p)] = ck
    # Also build reverse: citation_key -> path basename
    ck_to_bn = {v: k for k, v in ck_map.items()}
    print(f"  加载 {len(ck_map)} 个映射")

    total_downloaded = 0
    temp_dir = OUTPUT_DIR / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    for bid in batch_ids:
        print(f"\n{'─' * 50}")
        print(f"  批次: {bid}")
        print(f"{'─' * 50}")

        data = get_batch_info(bid)
        results = data.get("extract_result", [])
        if not results:
            print(f"  无解析结果或API错误")
            continue

        print(f"  共 {len(results)} 个文件")

        for i, res in enumerate(results):
            fname = res.get("file_name", f"unknown_{i}")
            zip_url = res.get("full_zip_url", "")
            state = res.get("state", "unknown")

            if state != "done":
                print(f"  [{i+1}] {fname[:50]}... state={state}, 跳过")
                continue

            if not zip_url:
                print(f"  [{i+1}] {fname[:50]}... 无下载链接")
                continue

            # 查找 citationKey
            basename = os.path.basename(fname)
            ck = None
            for pdf_bn, pdf_ck in ck_map.items():
                # 模糊匹配
                if pdf_bn.lower() in basename.lower() or basename.lower() in pdf_bn.lower():
                    ck = pdf_ck
                    break
            if not ck:
                # Try the reverse
                short = basename[:60].lower()
                for pdf_bn, pdf_ck in ck_map.items():
                    if pdf_ck in short:
                        ck = pdf_ck
                        break
            if not ck:
                ck = f"batch_{bid[:8]}_{i}"  # fallback

            out_dir = OUTPUT_DIR / ck
            if (out_dir / f"{ck}.md").exists():
                print(f"  [{i+1}] {ck}: 已下载，跳过")
                total_downloaded += 1
                continue

            print(f"  [{i+1}] {ck}: 下载...", end=" ", flush=True)
            zip_path = temp_dir / f"{bid[:8]}_{i}.zip"

            if download_with_curl(zip_url, str(zip_path)):
                extract_zip(zip_path, ck, out_dir)
                total_downloaded += 1
            else:
                print("FAILED")

            # 清理临时文件
            if zip_path.exists():
                zip_path.unlink()

    print(f"\n{'=' * 60}")
    print(f"  下载完成! 成功: {total_downloaded}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
