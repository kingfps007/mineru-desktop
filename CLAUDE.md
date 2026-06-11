# CLAUDE.md

MinerU CLI v4.0.0 — Windows 命令行 PDF 批量解析工具，替代 Electron GUI。

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
4. 输入：Zotero BBT JSON 或 PDF 文件夹
5. 范围选择：支持 11-108、1,3,5-10 等打印机风格
6. 批量处理：所有 PDF 放一个文件夹，mineru 只调一次（模型加载一次）

## 版本记录

| 版本 | 日期 | 变更 |
|:---|:---|:---|
| 4.0.0 | 2026-06-11 | CLI替代Electron；全功能安装向导；中英双语；批量处理不再重复加载模型 |
| 3.4.0 | 2026-06-11 | 移除Word生成；禁用暂停；BATCH_SIZE=200；关窗口杀进程 |
| 3.3.9 | 2026-06-07 | 代理开关、API区域限制绕过 |

## 架构（Electron已废弃，保留参考）

```
scripts/
├── mineru_cli.py         ← 主程序（当前产品）
├── mineru_parser.py      ← 批量解析库
├── mineru_download.py    ← 模型下载
├── mineru_app.py         ← MinerU 核心封装
├── mineru_html_parser.py ← HTML→MD
└── _remap_citations.py   ← 引用重映射

backend/server.py          ← Electron后端（已废弃）
electron-app/              ← Electron前端（已废弃）
```

## 关键约束

- 不得删除 `~/mineru_desktop_config.json`、`~/mineru.json`、`.env`
- conda 环境 `~/.conda/envs/MinerU/` (11GB) 禁止误删
- 模型缓存 `~/.cache/modelscope/hub/models/OpenDataLab/` (4.6GB)
- NVIDIA 检测通过 nvidia-smi，AMD/Intel 显卡自动跳过 VLM

## 踩坑记录

- **CLI 用 subprocess 调 mineru，不要调 server.py**：直接调用更稳定，没有进程通信开销
- **所有 PDF 放临时文件夹→mineru 一次调用**：避免每次重新加载模型
- **不要用 `magic_pdf` 检测 MinerU 包**：正确包名是 `mineru`
- **框线用 ASCII 不用双字节字符**：避免终端中文对齐错位
- **修改 Electron UI 用 CSS 隐藏而非删除 DOM**：删除可能致 JS 初始化崩溃
- **每次提交前更新全部文档和版本号**：用户已多次提醒
- **增量修改，不改无关代码**：不要顺手重构或简化工作代码
