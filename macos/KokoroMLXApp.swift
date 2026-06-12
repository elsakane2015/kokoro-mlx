import AppKit
import Darwin
import Foundation
import UniformTypeIdentifiers
import WebKit

private let appName = "Kokoro MLX"
private let bundleIdentifier = "com.litotime.kokoromlx"
private let backendName = "kokoro-mlx-backend"
private let defaultPort: UInt16 = 8000

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKDownloadDelegate, WKScriptMessageHandler {
    private var window: NSWindow!
    private var webView: WKWebView!
    private var backend: Process?
    private var logHandle: FileHandle?
    private var serverURL: URL?

    func applicationDidFinishLaunching(_ notification: Notification) {
        configureMenu()
        createWindow()
        showLoading(message: "正在加载本地语音模型，请稍候…")
        startBackend()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        stopBackend()
    }

    private func configureMenu() {
        let mainMenu = NSMenu()
        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)

        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "关于 \(appName)", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "退出 \(appName)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appMenuItem.submenu = appMenu

        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)
        let editMenu = NSMenu(title: "编辑")
        editMenu.addItem(withTitle: "撤销", action: Selector(("undo:")), keyEquivalent: "z")
        editMenu.addItem(withTitle: "重做", action: Selector(("redo:")), keyEquivalent: "Z")
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(withTitle: "剪切", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "复制", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "粘贴", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "全选", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editMenuItem.submenu = editMenu
        NSApp.mainMenu = mainMenu
    }

    private func createWindow() {
        let configuration = WKWebViewConfiguration()
        let userContentController = WKUserContentController()
        userContentController.add(self, name: "downloadAudio")
        configuration.userContentController = userContentController
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self

        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1180, height: 820),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = appName
        window.minSize = NSSize(width: 860, height: 620)
        window.contentView = webView
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func startBackend() {
        guard let backendURL = Bundle.main.url(forResource: backendName, withExtension: nil, subdirectory: "Backend"),
              let modelURL = Bundle.main.resourceURL?.appendingPathComponent("model") else {
            showFailure("应用资源不完整，请重新安装。")
            return
        }

        guard let port = findAvailablePort(startingAt: defaultPort) else {
            showFailure("无法找到可用的本地端口。")
            return
        }
        let url = URL(string: "http://127.0.0.1:\(port)")!
        serverURL = url

        do {
            let log = try openLog()
            let process = Process()
            process.executableURL = backendURL
            process.arguments = ["--port", String(port), "--model", modelURL.path]
            var environment = ProcessInfo.processInfo.environment
            environment["HF_HUB_OFFLINE"] = "1"
            environment["TRANSFORMERS_OFFLINE"] = "1"
            process.environment = environment
            process.standardOutput = log
            process.standardError = log
            process.terminationHandler = { [weak self] task in
                guard task.terminationStatus != 0 else { return }
                DispatchQueue.main.async {
                    self?.showFailure("本地语音服务意外退出。请重新打开应用。")
                }
            }
            backend = process
            try process.run()
            waitUntilReady(url: url, attemptsRemaining: 240)
        } catch {
            showFailure("无法启动本地语音服务：\(error.localizedDescription)")
        }
    }

    private func findAvailablePort(startingAt port: UInt16) -> UInt16? {
        for candidate in port...min(port + 99, UInt16.max) {
            let descriptor = socket(AF_INET, SOCK_STREAM, 0)
            guard descriptor >= 0 else { continue }
            defer { close(descriptor) }

            var address = sockaddr_in()
            address.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
            address.sin_family = sa_family_t(AF_INET)
            address.sin_port = candidate.bigEndian
            address.sin_addr = in_addr(s_addr: inet_addr("127.0.0.1"))

            let result = withUnsafePointer(to: &address) {
                $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                    Darwin.bind(descriptor, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
                }
            }
            if result == 0 {
                return candidate
            }
        }
        return nil
    }

    private func waitUntilReady(url: URL, attemptsRemaining: Int) {
        guard attemptsRemaining > 0, backend?.isRunning == true else {
            showFailure("模型加载失败或等待超时。详情请查看日志。")
            return
        }
        let healthURL = url.appendingPathComponent("api/health")
        URLSession.shared.dataTask(with: healthURL) { [weak self] _, response, _ in
            if let status = (response as? HTTPURLResponse)?.statusCode, status == 200 {
                DispatchQueue.main.async {
                    self?.webView.load(URLRequest(url: url))
                }
                return
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                self?.waitUntilReady(url: url, attemptsRemaining: attemptsRemaining - 1)
            }
        }.resume()
    }

    private func openLog() throws -> FileHandle {
        let support = try FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        ).appendingPathComponent(appName, isDirectory: true)
        try FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
        let logURL = support.appendingPathComponent("backend.log")
        FileManager.default.createFile(atPath: logURL.path, contents: nil)
        let handle = try FileHandle(forWritingTo: logURL)
        logHandle = handle
        return handle
    }

    private func stopBackend() {
        if let process = backend, process.isRunning {
            process.terminate()
            process.waitUntilExit()
        }
        try? logHandle?.close()
        logHandle = nil
        backend = nil
    }

    private func presentDownloadPanel(filename: String) {
        guard serverURL != nil else {
            presentAlert(title: "无法下载音频", message: "本地服务尚未准备好。")
            return
        }

        let panel = NSSavePanel()
        panel.nameFieldStringValue = filename.isEmpty ? "speech.wav" : filename
        panel.allowedContentTypes = [.wav]
        panel.canCreateDirectories = true
        panel.beginSheetModal(for: window) { [weak self] result in
            guard let self else { return }
            guard result == .OK, let destination = panel.url else { return }
            self.fetchLatestAudio { downloadResult in
                switch downloadResult {
                case .success(let data):
                    do {
                        try data.write(to: destination, options: [.atomic])
                    } catch {
                        DispatchQueue.main.async {
                            self.presentAlert(
                                title: "保存失败",
                                message: "无法写入文件：\(error.localizedDescription)"
                            )
                        }
                    }
                case .failure(let error):
                    DispatchQueue.main.async {
                        self.presentAlert(
                            title: "下载失败",
                            message: error.localizedDescription
                        )
                    }
                }
            }
        }
    }

    private func fetchLatestAudio(completion: @escaping (Result<Data, Error>) -> Void) {
        guard let serverURL else {
            completion(.failure(NSError(domain: appName, code: 1, userInfo: [NSLocalizedDescriptionKey: "本地服务不可用。"])))
            return
        }

        let downloadURL = serverURL.appendingPathComponent("api/speech/download")
        URLSession.shared.dataTask(with: downloadURL) { data, response, error in
            if let error {
                completion(.failure(error))
                return
            }

            guard let http = response as? HTTPURLResponse else {
                completion(.failure(NSError(domain: appName, code: 2, userInfo: [NSLocalizedDescriptionKey: "下载响应无效。"])))
                return
            }

            guard http.statusCode == 200 else {
                completion(.failure(NSError(domain: appName, code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: "当前没有可下载的音频。"])))
                return
            }

            guard let data else {
                completion(.failure(NSError(domain: appName, code: 3, userInfo: [NSLocalizedDescriptionKey: "未收到音频数据。"])))
                return
            }

            completion(.success(data))
        }.resume()
    }

    private func presentAlert(title: String, message: String) {
        DispatchQueue.main.async {
            let alert = NSAlert()
            alert.alertStyle = .warning
            alert.messageText = title
            alert.informativeText = message
            alert.beginSheetModal(for: self.window)
        }
    }

    private func showLoading(message: String) {
        showStatus(title: "正在启动 \(appName)", message: message, isError: false)
    }

    private func showFailure(_ message: String) {
        showStatus(title: "无法启动 \(appName)", message: message, isError: true)
    }

    private func showStatus(title: String, message: String, isError: Bool) {
        let color = isError ? "#dc2626" : "#6d5dfc"
        let html = """
        <!doctype html><meta charset="utf-8">
        <style>
          body{margin:0;display:grid;place-items:center;height:100vh;background:linear-gradient(135deg,#f4f7ff,#f7f2ff);font-family:-apple-system,BlinkMacSystemFont,sans-serif;color:#172033}
          main{width:min(520px,80vw);padding:48px;text-align:center;background:#fff;border-radius:28px;box-shadow:0 24px 70px rgba(58,43,120,.14)}
          .mark{width:56px;height:56px;margin:0 auto 24px;border-radius:18px;background:\(color);box-shadow:0 10px 30px \(color)55}
          h1{font-size:25px;margin:0 0 12px}p{font-size:15px;line-height:1.7;color:#657087;margin:0}
        </style>
        <main><div class="mark"></div><h1>\(title)</h1><p>\(message)</p></main>
        """
        webView.loadHTMLString(html, baseURL: nil)
    }

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
    ) {
        decisionHandler(navigationAction.shouldPerformDownload ? .download : .allow)
    }

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationResponse: WKNavigationResponse,
        decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void
    ) {
        if navigationResponse.response.mimeType == "audio/wav" {
            decisionHandler(.download)
        } else {
            decisionHandler(.allow)
        }
    }

    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) {
        download.delegate = self
    }

    func download(
        _ download: WKDownload,
        decideDestinationUsing response: URLResponse,
        suggestedFilename: String,
        completionHandler: @escaping (URL?) -> Void
    ) {
        let panel = NSSavePanel()
        panel.nameFieldStringValue = suggestedFilename.isEmpty ? "speech.wav" : suggestedFilename
        panel.allowedContentTypes = [.wav]
        panel.beginSheetModal(for: window) { result in
            completionHandler(result == .OK ? panel.url : nil)
        }
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "downloadAudio" else { return }
        let filename = (message.body as? [String: Any])?["filename"] as? String ?? "speech.wav"
        presentDownloadPanel(filename: filename)
    }
}

@main
enum KokoroMLXApplication {
    static func main() {
        let currentPID = ProcessInfo.processInfo.processIdentifier
        if let existing = NSRunningApplication.runningApplications(withBundleIdentifier: bundleIdentifier)
            .first(where: { $0.processIdentifier != currentPID }) {
            existing.activate()
            return
        }

        let application = NSApplication.shared
        let delegate = AppDelegate()
        application.delegate = delegate
        application.setActivationPolicy(.regular)
        application.run()
    }
}
