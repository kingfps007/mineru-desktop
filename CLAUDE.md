# CLAUDE.md

MinerU CLI v4.1.0 — Windows 命令行 PDF 批量解析工具，替代 Electron GUI。

## 项目定位

命令行 PDF→MD 批量解析。**Electron GUI 已废弃**（稳定性和大小问题），由 `scripts/mineru_cli.py` 替代。

## 产品

| 文件 | 用途 |
|:---|:---|
| `MinerU_CLI.exe` | 单文件可执行程序（7.2MB，PyInstaller打包） |
| `scripts/mineru_cli.py` | 源码（需Python运行） |
| `MinerU_CLI.bat` | 批处理快捷启动 |

## 功能

1. 仪表盘：检测 CPU/RAM/GPU/MinerU环境/PyTorch/模型/CUDA
2. 安装向导：10步（0-10），按完成状态自动显隐，硬件不兼容自动跳过
3. 解析：本地 Pipeline/VLM/Hybrid 或云端 API
4. 输入：Zotero BBT JSON（推荐，同时含PDF路径+Zotero URI）/ BibTeX (.bib) / PDF 文件夹
5. 范围选择：支持 11-108、1,3,5-10 等打印机风格
6. 批量处理：RAM 自适应 BATCH（3-10篇/批），每批独立调用 mineru；失败自动重试1次

## 版本记录

| 版本 | 日期 | 变更 |
|:---|:---|:---|
| 4.1.0 | 2026-06-12 | 新增 BibTeX (.bib) 输入支持，保留JSON兼容；输入菜单调整（[1]JSON [2].bib [3]文件夹） |
| 4.0.2 | 2026-06-11 | 修复稳定性：恢复conda env传递+RAM自适应BATCH+线程超时+重试+Ctrl+C清理；删除三份重复代码(968→580行) |
| 4.0.1 | 2026-06-11 | 放弃PyInstaller(.bat启动)；自动根据RAM调BATCH；修复MemoryError |
| 4.0.0 | 2026-06-11 | CLI替代Electron；全功能安装向导；中英双语；批量处理 |
| 3.4.0 | 2026-06-11 | 移除Word生成；禁用暂停；BATCH_SIZE=200；关窗口杀进程 |
| 3.3.9 | 2026-06-07 | 代理开关、API区域限制绕过 |

## 架构

```
scripts/
├── mineru_cli.py         ← 主程序（当前产品）
├── mineru_parser.py      ← 批量解析库
├── mineru_download.py    ← 模型下载
├── mineru_app.py         ← MinerU 核心封装
├── mineru_html_parser.py ← HTML→MD
└── _remap_citations.py   ← 引用重映射
```

## 版本发布规则

**每次代码改动必须：**
1. 更新版本号（CLAUDE.md、README.md、CLI横幅一致）
2. 重新构建 EXE：
   ```bash
   conda activate MinerU
   pyinstaller --onefile --name MinerU_CLI --distpath . scripts/mineru_cli.py
   ```
3. 确认 `MinerU_CLI.exe` 生成成功（~7MB）
4. 创建 GitHub Release：
   ```bash
   git add scripts/mineru_cli.py README.md CLAUDE.md MinerU_CLI.exe
   git commit -m "vX.Y.Z: 变更摘要"
   git tag vX.Y.Z
   git push && git push origin vX.Y.Z
   gh release create vX.Y.Z MinerU_CLI.exe --title "MinerU CLI vX.Y.Z" --notes "变更说明"
   ```
5. push 前检查 `.env`、token、API key 未被误提交

## 关键约束

- 不得删除 `~/mineru_desktop_config.json`、`~/mineru.json`、`.env`
- conda 环境 `~/.conda/envs/MinerU/` (11GB) 禁止误删
- 模型缓存 `~/.cache/modelscope/hub/models/OpenDataLab/` (4.6GB)
- NVIDIA 检测通过 nvidia-smi，AMD/Intel 显卡自动跳过 VLM

## 踩坑记录

- **CLI 用 subprocess 调 mineru，不要调 server.py**：直接调用更稳定，没有进程通信开销
- **subprocess.Popen 必须传 env**：不传 conda 环境变量会导致 mineru.exe 找不到 CUDA DLL
- **用 threading 读 stdout + join(timeout) 实现真正超时**：`for line in proc.stdout` 在前会阻塞 `proc.wait(timeout)`，超时形同虚设
- **不要用 `magic_pdf` 检测 MinerU 包**：正确包名是 `mineru`
- **框线用 ASCII 不用双字节字符**：避免终端中文对齐错位
- **修改 Electron UI 用 CSS 隐藏而非删除 DOM**：删除可能致 JS 初始化崩溃
- **每次提交前更新全部文档和版本号**：用户已多次提醒
- **增量修改，不改无关代码**：不要顺手重构或简化工作代码
- **同一文件不要有多个函数定义副本**：Python 最后定义覆盖前面，前几版是死代码还会误导维护
