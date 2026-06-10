# CLAUDE.md

MinerU Desktop — Windows 桌面端 PDF 批量解析工具。Electron 33 + Python FastAPI 后端 + MinerU 引擎。

## 项目定位

只做 PDF→MD 批量解析。**不做 DOCX 生成**——该功能已移至 `~/Desktop/PCM-BTM综述论文/脚本/生成docx.py`。

## 构建与运行

```bash
cd electron-app && npm install && npm run build
# exe 输出到项目根目录: MinerU_Desktop.exe
```

## 架构

```
electron-app/src/main/index.js    # 主进程：启动/停止 Python 后端
electron-app/src/renderer/index.html  # 渲染进程：全部 UI
backend/server.py                  # FastAPI 后端（端口 18766）
scripts/                           # 辅助脚本（MinerU 解析器、下载器等）
```

## 版本记录

| 版本 | 日期 | 变更 |
|:---|:---|:---|
| 3.4.0 | 2026-06-11 | 移除Word生成；禁用全部暂停（GPU/CPU/RAM）；BATCH_SIZE=200；关窗口杀mineru残留；exe放根目录 |
| 3.3.9 | 2026-06-07 | 代理开关、API 区域限制绕过 |

## 关键约束

- **禁止删除或覆盖** `~/mineru_desktop_config.json` 和 `~/mineru.json`
- Python 路径：main/index.js 按固定候选列表查找 Python，打包后依赖用户环境
- BATCH_SIZE 默认 200（一次加载模型处理全部），RETRIES=5
- API Key 在 `.env` 和 `mineru_desktop_config.json`，禁止提交 Git

## 踩坑记录

- **修改 Electron UI 时用 CSS 隐藏而非删除 DOM 元素**：删除 DOM 节点可能导致 JS 初始化报错，整个应用无响应
- Electron 版本必须精确锁定（`33.4.11` 非 `^33.0.0`），否则 electron-builder 找不到二进制
- **所有暂停机制已禁用**：前端 CPU/RAM 紧急停止、后端 GPU 温度暂停——用户反馈高占用是正常的，不导致卡顿
- **每次提交前必须同步更新**：package.json 版本号、HTML 标题、CLAUDE.md 版本记录、README 版本号
- npm install 后 node_modules 约 290MB，旧构建版本每个 ~300-400MB，定期清理
