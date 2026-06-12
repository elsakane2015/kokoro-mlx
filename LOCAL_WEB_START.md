# 本地网页启动说明

本项目的网页服务仅监听 `127.0.0.1`，只能从当前电脑访问，不会暴露到公网。

## 首次安装

在项目根目录执行：

```bash
cd /Users/xue/Documents/vscode/kokoro-mlx
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[web,zh]"
```

## 启动服务

```bash
cd /Users/xue/Documents/vscode/kokoro-mlx
source .venv/bin/activate
kokoro-mlx-server
```

启动后访问：

```text
http://127.0.0.1:8000
```

首次生成语音时，程序可能需要下载模型文件。

## 修改端口

通过命令行参数修改端口：

```bash
kokoro-mlx-server --port 9000
```

然后访问：

```text
http://127.0.0.1:9000
```

也可以使用环境变量：

```bash
KOKORO_MLX_PORT=9000 kokoro-mlx-server
```

命令行参数 `--port` 的优先级高于环境变量 `KOKORO_MLX_PORT`。

## 停止服务

在运行服务的终端中按 `Control+C`。

## HTTP API

- 健康检查：`GET /api/health`
- 音色列表：`GET /api/voices`
- 生成语音：`POST /api/speech`

示例：

```bash
curl -X POST http://127.0.0.1:8000/api/speech \
  -H "Content-Type: application/json" \
  -d '{"text":"你好，这是本地语音生成测试。","voice":"zf_xiaobei","language":"zh","speed":1,"sample_rate":24000}' \
  --output speech.wav
```
