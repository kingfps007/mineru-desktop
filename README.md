# MinerU Desktop

基于 [MinerU (OpenDataLab)](https://github.com/opendatalab/MinerU) 的 Windows 桌面端 PDF 批量解析工具，
集成 Zotero 文献管理生态，支持 Markdown 转 Word（含 Zotero 引用域代码）。

## 功能

- **批量解析**：导入 Zotero BetterBibTeX JSON 或直接多选文件，VLM/Pipeline 后端解析为 Markdown + 图片
- **Markdown → Word**：将 `[@citekey]` 格式引用转 Zotero 域代码，一键生成 .docx
- **安装向导**：逐步引导安装 Miniconda → MinerU → PyTorch → 模型 → Zotero 插件
- **实时监控**：GPU/模型状态仪表盘 + 解析进度 + 温度保护自动暂停
- **MinerU Cloud API**：支持官方精准解析 API Token 配置

## 技术栈

- 前端: Electron 33 + 原生 HTML/CSS/JS
- 后端: Python FastAPI + Uvicorn → REST API + WebSocket
- 引擎: MinerU 3.1.x（pipeline / vlm / hybrid 三大后端）
- 打包: electron-builder → 单文件 .exe

## 快速开始

```bash
# 后端依赖
pip install fastapi uvicorn websockets python-docx python-dotenv

# 前端
cd electron-app && npm install

# 开发模式
npm start     # 自动启动后端 + Electron
```

## 打包

```bash
cd electron-app && npm run build
# → dist/MinerU_Desktop_vX.X.X.exe
```

## 许可证

Apache 2.0 — 基于 [OpenDataLab/MinerU](https://github.com/opendatalab/MinerU)
