# macOS App 完整打包 TODO

目标：为没有终端使用经验的用户提供开箱即用的 `Kokoro MLX.app` 和已签名、公证的 DMG 安装包。

## 完成规则

- 每个任务完成实现后，必须执行其下方的 Review 检查。
- 只有 Review 检查通过后，才能将任务和 Review 同时勾选为 `[x]`。
- Review 失败时保持 `[ ]`，修复并重新检查。
- 不将 Apple 账号、密码、App 专用密码或私钥写入项目。

## 1. 分发范围与前置条件

- [x] 确认目标平台为 Apple Silicon Mac
  - [x] Review：确认项目依赖 MLX，不能分发给 Intel Mac
- [x] 确认最低系统版本暂定为 macOS 15
  - [x] Review：检查当前 MLX 二进制最低系统版本标记为 macOS 15
- [x] 确认使用 Developer ID 进行站外分发
  - [x] Review：确认存在有效证书 `Developer ID Application: Xuefeng Huang (HCDD4TQBT8)`
- [x] 确认 App 名称、Bundle ID 和版本号
  - [x] Review：检查 `Kokoro MLX`、`com.litotime.kokoromlx`、`0.1.2` 在构建配置和 App 信息中一致
- [ ] 配置 `notarytool` 钥匙串 profile
  - [ ] Review：使用 profile 查询公证历史成功，且项目中不包含公证凭据

## 2. App 启动器与生命周期

- [x] 实现 macOS App 图形化启动器
  - [x] Review：双击 App 可以启动，且不会显示终端窗口
- [x] 在 App 内启动并管理本地 FastAPI 服务
  - [x] Review：服务仅监听 `127.0.0.1`，外部设备无法访问
- [x] 实现端口占用处理
  - [x] Review：默认端口被占用时，App 能自动选择可用端口并正常打开界面
- [x] 实现单实例控制
  - [x] Review：重复双击 App 不会启动多个模型和多个服务
- [x] 实现退出清理
  - [x] Review：退出 App 后 HTTP 服务停止，端口被释放
- [ ] 实现模型加载和启动失败提示
  - [ ] Review：资源缺失、端口失败和模型加载失败时均显示可理解的图形化错误

## 3. 原生窗口与用户体验

- [ ] 在原生 WebView 中显示现有网页界面
  - [ ] Review：App 内可完成文本输入、音色选择、生成和播放
- [ ] 实现原生 WAV 保存流程
  - [ ] Review：无需浏览器下载栏即可选择位置并保存有效 WAV 文件
- [x] 增加模型加载状态界面
  - [x] Review：首次打开时不会出现空白窗口，用户能看到加载进度或状态
- [ ] 处理 App 重新打开行为
  - [ ] Review：点击 Dock 图标或重新打开 App 时，已有窗口能够恢复到前台
- [ ] 检查离线状态下的错误文案
  - [ ] Review：断网使用时不会出现要求用户打开终端的提示

## 4. 完整离线资源

- [x] 将 Kokoro 模型主体打包进 App
  - [x] Review：清空 Hugging Face 缓存并断网后，App 仍能加载模型
- [x] 将全部 54 个音色的 safetensors 文件打包进 App
  - [x] Review：界面能列出并加载全部 54 个音色
- [x] 排除重复 `.pt` 音色和模型示例音频
  - [x] Review：检查 App 资源中不存在重复 `.pt` 音色和非必要 samples
- [x] 打包中文语言资源
  - [x] Review：断网后中文女声和男声均能生成有效语音
- [x] 打包英文语言资源和 spaCy 模型
  - [x] Review：断网且无本机 spaCy 缓存时，美式和英式英语均能生成有效语音
- [x] 打包日语语言资源
  - [x] Review：断网后日语音色能生成有效语音
- [x] 打包 eSpeak 及其他语言资源
  - [x] Review：断网后西班牙语、法语、印地语、意大利语和葡萄牙语可生成语音
- [x] 禁止运行时隐式下载
  - [x] Review：在无网络环境遍历语言功能时，不触发任何下载请求

## 5. 图标与 App 元数据

- [ ] 使用根目录 `logo.png` 生成 macOS `.icns`
  - [ ] Review：检查 Finder、Dock 和 App 信息窗口中的图标显示正常
- [x] 配置 `Info.plist`
  - [x] Review：检查 Bundle ID、版本号、最低系统版本、版权和高分屏配置
- [x] 配置 App 菜单和名称
  - [x] Review：菜单栏和系统窗口中不出现 Python、PyInstaller 或脚本名称

## 6. PyInstaller 构建

- [x] 创建隔离的 macOS App 构建环境
  - [x] Review：构建环境不包含项目开发环境中的无关依赖
- [x] 创建 PyInstaller spec 和必要 hooks
  - [x] Review：静态网页、语言数据、动态库和模型资源均被正确收集
- [x] 使用 `--windowed --onedir` 构建 arm64 App
  - [x] Review：App 架构为 arm64，双击启动正常
- [x] 排除 torch、测试工具和无关依赖
  - [x] Review：检查 App 中不存在 torch、pytest、ruff、build 和 hatchling
- [x] 检查动态库路径和架构
  - [x] Review：所有非系统 Mach-O 文件均为 arm64，且不存在失效动态库引用
- [x] 检查 App 体积
  - [x] Review：记录 App 解压后大小，并确认没有明显重复资源

## 7. 自动化测试与离线验收

- [x] 为 App 启动器和资源路径增加自动化测试
  - [x] Review：新增测试通过，原有测试无回归
- [x] 在构建产物上执行 HTTP API 冒烟测试
  - [x] Review：健康检查、音色列表和语音生成接口均通过
- [ ] 在构建产物上执行图形界面端到端测试
  - [ ] Review：可在 App 内生成、播放并保存 WAV
- [ ] 执行无终端用户流程测试
  - [ ] Review：仅通过 Finder 和 App 图形界面即可完成安装和使用
- [ ] 执行全离线测试
  - [ ] Review：断网并隔离本机缓存后，App 可正常完成语音生成
- [ ] 在另一台干净 Apple Silicon Mac 上测试
  - [ ] Review：未安装 Python、Homebrew 和开发工具的机器可直接安装使用

## 8. 签名、公证与 DMG

- [x] 配置 Hardened Runtime 和必要 entitlements
  - [x] Review：签名后 App 能正常启动，且 entitlements 为最小必要集合
- [x] 使用 Developer ID 对 App 和嵌套二进制签名
  - [x] Review：`codesign --verify --deep --strict` 检查通过
- [ ] 执行 Gatekeeper 检查
  - [ ] Review：`spctl --assess` 对 App 返回通过
- [x] 创建带应用程序快捷方式的 DMG
  - [x] Review：用户可将 App 拖入“应用程序”，DMG 布局和图标正常
- [x] 使用 Developer ID 对 DMG 签名
  - [x] Review：DMG 签名验证通过
- [ ] 提交 Apple 公证
  - [ ] Review：`notarytool` 返回 Accepted
- [ ] 将公证票据附加到 App 和 DMG
  - [ ] Review：`stapler validate` 对 App 和 DMG 均通过
- [ ] 对最终 DMG 执行 Gatekeeper 检查
  - [ ] Review：在另一台 Mac 上下载后可直接打开，不需要绕过安全警告

## 9. 发布材料

- [x] 生成最终 arm64 DMG
  - [x] Review：文件名包含 App 名称、版本号和 arm64 标识
- [x] 生成 SHA-256 校验文件
  - [x] Review：使用校验文件验证最终 DMG 成功
- [x] 收集第三方依赖和模型许可证
  - [x] Review：App 或 DMG 中包含必要的许可证和版权说明
- [x] 编写面向普通用户的安装说明
  - [x] Review：说明不要求用户执行任何终端命令
- [x] 编写构建、签名和公证维护文档
  - [x] Review：不泄露凭据的情况下，可重复完成正式构建
- [x] 记录最终兼容性、体积和已知限制
  - [x] Review：发布说明与实际测试结果一致

## 最终完成条件

- [ ] 最终 Review：朋友在干净的 Apple Silicon Mac 上，从 DMG 安装后可以离线生成、播放和保存语音，全程不使用终端
