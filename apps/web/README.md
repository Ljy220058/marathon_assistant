# Astro 前端

这是马拉松助手当前唯一的产品前端入口。页面层使用 Astro，并通过 FastAPI 后端获取训练计划数据。

## 启动后端 API

```cmd
cd /d "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手"
set PYTHONPATH=.
C:\Users\26318\anaconda3\envs\torch2.5.1\python.exe -m uvicorn marathon_qa_assistant.apps.api_app:app --host 127.0.0.1 --port 8000 --reload
```

## 启动前端

当前仓库路径是中文 Junction，Astro/Vite/esbuild 在这个路径下可能出现依赖解析失败。优先使用下面的脚本，它会把前端同步到 `%TEMP%\marathon_assistant_frontend` 这个纯英文运行目录再启动：

```cmd
cd /d "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\apps\web"
start_ascii.cmd
```

`start_ascii.cmd` 会保留临时运行目录中的 `node_modules` 和 `.npm-cache`。只有首次启动、依赖目录缺失，或 `package.json` / `package-lock.json` 变化时才会重新执行 `npm install`；普通源码改动只同步 `src` 和配置文件。

如果项目以后移动到纯英文真实路径，也可以直接运行：

```cmd
cd /d "C:\Users\26318\Documents\trae_projects\ollama_pro\马拉松助手\apps\web"
npm.cmd install
npm.cmd run dev
```

默认连接 `http://127.0.0.1:8000`，可在页面左侧修改基础地址。

## 兼容说明

- 旧前端运行线已移除，当前产品前端仅为 Astro。
- `apps/backend/src/marathon_qa_assistant/ui/report_ui.py` 仅保留测试兼容 helper，不再承担产品渲染职责。
