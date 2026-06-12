# Kokoro MLX for macOS 使用说明

适用版本：Kokoro MLX 0.1.2  
适用设备：Apple Silicon Mac  
最低系统：macOS 15

## 安装

1. 双击打开 `Kokoro-MLX-0.1.2-arm64.dmg`。
2. 将 `Kokoro MLX.app` 拖到 `Applications` 文件夹快捷方式。
3. 在“应用程序”中双击 `Kokoro MLX`。

正式发布的安装包经过 Developer ID 签名和 Apple 公证后，可直接打开，不需要使用终端。

## 使用

1. 等待应用完成模型加载。
2. 输入要转换为语音的文本。
3. 选择语言、音色和语速。
4. 点击生成并试听语音。
5. 使用保存功能选择 WAV 文件保存位置。

应用只在本机启动服务，不会向局域网或公网开放。默认地址为
`http://127.0.0.1:8000`；如果端口被占用，应用会自动选择其他本地端口。

## 离线使用

模型、54 个音色和语言资源均已包含在 App 中。安装完成后，生成语音不需要联网。

## 退出

使用菜单栏中的“退出 Kokoro MLX”或按 `Command-Q`。退出应用后，本地服务会同时停止。

## 已知限制

- 仅支持 Apple Silicon Mac，不支持 Intel Mac。
- 最低支持 macOS 15。
- App 解压后约 786 MB，DMG 约 511 MB。
- 第一次启动和第一次生成语音可能需要等待模型初始化。
