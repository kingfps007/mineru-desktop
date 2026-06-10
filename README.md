# MinerU Desktop

基于 [MinerU (OpenDataLab)](https://github.com/opendatalab/MinerU) 的 Windows 桌面端 PDF 批量解析工具，集成 Zotero 文献管理生态。

## 功能

- **批量解析**：导入 Zotero BetterBibTeX JSON 或直接多选文件，VLM/Pipeline 后端解析为 Markdown + 图片
- **安装向导**：逐步引导安装 Miniconda → MinerU → PyTorch → 模型 → Zotero 插件
- **实时监控**：GPU/模型状态仪表盘 + 解析进度 + 温度保护自动暂停
- **MinerU Cloud API**：支持官方精准解析 API Token 配置
- **MD → Zotero DOCX**：已移至论文项目 `~/Desktop/PCM-BTM综述论文/脚本/生成docx.py`

## 技术栈

- 前端: Electron 33 + 原生 HTML/CSS/JS
- 后端: Python FastAPI + Uvicorn
- 引擎: MinerU 3.1.x（pipeline / vlm / hybrid）
- 打包: electron-builder → 单文件 .exe

## 快速开始

```bash
cd electron-app && npm install && npm start
```

## 打包

```bash
cd electron-app && npm run build
# → MinerU_Desktop.exe（项目根目录）
```

## 当前版本

**v3.3.9-mod** (2026-06-10) — 移除 Word 生成功能（移至论文项目），exe 放根目录。

## 许可证

Apache 2.0
