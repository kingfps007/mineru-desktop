# MinerU CLI v4.0.0

Windows 命令行 PDF 批量解析工具，替代 Electron GUI 版本。

## 为什么用 CLI 替代 Electron

| | Electron v3.x | CLI v4.0.0 |
|:---|:---|:---|
| 大小 | 71MB exe + 290MB node_modules | 7.2MB 单文件 |
| 启动 | 3-10秒 | 即时 |
| 稳定性 | 三层进程通信，易中断 | 单进程直接调用 |
| 解析速度 | 每10篇重新加载模型 | 全部一篇加载一次 |

## 功能

- **仪表盘**：CPU/RAM/GPU/PyTorch/模型/CUDA 状态一目了然
- **安装向导**：10步自动化安装（Miniconda→环境→PyTorch→MinerU→模型→Zotero→CUDA）
- **批量解析**：Pipeline/VLM/Hybrid 后端 + 云端 API
- **范围选择**：支持 `11-108`, `1,3,5-10` 等打印机风格
- **中英双语**：全界面双语言切换

## 使用方法

```bash
# 双击 MinerU_CLI.exe 或运行
python scripts/mineru_cli.py
```

## 构建

```bash
conda activate MinerU
pip install pyinstaller
pyinstaller --onefile --name MinerU_CLI --distpath . scripts/mineru_cli.py
# → MinerU_CLI.exe (~7.2MB)
```

## 当前版本

**v4.0.0** (2026-06-11) — CLI 替代 Electron，全功能安装向导，中英双语，单次模型加载

## 许可证

Apache 2.0 — 基于 [OpenDataLab/MinerU](https://github.com/opendatalab/MinerU)
