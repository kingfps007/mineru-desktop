# MinerU CLI v4.0.2

Windows 命令行 PDF 批量解析工具，为学术文献综述工作流设计。从 Zotero 文献库一键批量提取 Markdown + 图片 + 公式。

## 为什么有这个项目

写综述论文需要精读几十上百篇文献。手动复制粘贴 PDF 内容效率极低，且公式、表格、图片会丢失。现有 PDF 解析工具要么收费、要么不稳定、要么针对单篇设计无法批量处理。

MinerU CLI 用命令行替代了不稳定的 Electron 桌面应用——从一个 71MB 的 GUI（启动 10 秒、三层进程通信容易崩溃、每 10 篇就重新加载 AI 模型）精简为 580 行终端工具（即时启动、直接调用、RAM 自适应 BATCH + 失败自动重试）。

## 工作原理

```
Zotero 文献库 → BBT 导出 JSON（含 PDF 路径）→ MinerU CLI
    → 批量调用 MinerU 引擎（pipeline/VLM 后端）
    → 每篇论文输出：Markdown 正文 + 图片（~50-150张/篇） + 表格 + LaTeX 公式
    → AI 辅助分析 Markdown → 撰写综述 → 生成含 Zotero 引用的 DOCX
```

核心引擎是 [OpenDataLab/MinerU](https://github.com/opendatalab/MinerU)，支持两种后端：
- **Pipeline**：传统规则引擎（布局分析→表格识别→公式提取→OCR），CPU/GPU 均可
- **VLM**：视觉大模型端到端解析，精度更高，需 NVIDIA 8GB+ 显存

## 功能

| 模块 | 说明 |
|:---|:---|
| 📊 系统仪表盘 | CPU/RAM/GPU/环境/模型/CUDA 状态实时检测 |
| 🔧 安装向导 | 10 步自动化（Miniconda→Python环境→PyTorch→MinerU→模型→Zotero→CUDA），按完成状态显隐，硬件不兼容自动跳过 |
| 🚀 批量解析 | Pipeline/VLM/Hybrid 本地后端 + 云端 API |
| 📋 灵活输入 | Zotero BBT JSON（自动从附件提取 PDF 路径）/ 文件夹 |
| 🎯 范围选择 | 支持 `11-108`、`1,3,5-10` 等打印机风格 |
| 🌐 中英双语 | 全界面实时切换 |
| ⚡ 智能分批 | RAM 自适应 BATCH（3-10 篇/批），失败自动重试 1 次 |

## 使用方法

```bash
# 双击 MinerU_CLI.exe 或
python scripts/mineru_cli.py
```

典型流程：打开 → 选语言 → 仪表盘状态确认 → （首次）安装向导 → 选后端 → 导入 Zotero JSON → 选范围（如 11-108）→ 输出目录 → 开始解析

## 项目结构

```
├── MinerU_CLI.exe          ← 主程序（7.2MB 单文件，PyInstaller 打包）
├── MinerU_CLI.bat          ← 批处理快捷启动（需 conda 环境）
├── scripts/
│   ├── mineru_cli.py       ← 主程序源码
│   ├── mineru_parser.py    ← 批量解析库（PDF→MinerU API）
│   ├── mineru_download.py  ← 模型下载工具
│   ├── mineru_app.py       ← MinerU 核心调用封装
│   └── mineru_html_parser.py ← HTML→Markdown 解析
```

## 构建

```bash
conda activate MinerU
pip install pyinstaller
pyinstaller --onefile --name MinerU_CLI --distpath . scripts/mineru_cli.py
```

## 依赖

- MinerU 引擎（magic-pdf + 模型）
- Python 3.10+（conda MinerU 环境）
- PyTorch CUDA（可选，GPU 加速需 NVIDIA 显卡）

## 版本

**v4.0.2** (2026-06-11) — 修复稳定性：恢复conda env传递+RAM自适应BATCH+线程超时+重试+Ctrl+C清理；代码精简40%
**v4.0.1** (2026-06-11) — 自动RAM调BATCH；.bat启动替代PyInstaller
**v4.0.0** (2026-06-11) — CLI 替代 Electron；全功能安装向导；中英双语；单次模型加载；清理历史遗留。

## 许可证

Apache 2.0
