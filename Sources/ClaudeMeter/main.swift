import SwiftUI
import AppKit

struct Usage: Codable {
    let total: Double
    let budget: Double
    let expected: Double
    let status: String
    let source: String?
    let by_model: [String: Double]
}

final class UsageModel: ObservableObject {
    @Published var usage: Usage?
    @Published var expanded = false
    // Resolved at compile time to this checkout's root, so the binary can run
    // from anywhere (e.g. ~/.local/bin) regardless of who built it or where.
    private let scriptPath = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("usage_calc.py")
        .path

    func refresh() {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        task.arguments = ["-I", scriptPath]
        let pipe = Pipe()
        task.standardOutput = pipe
        do {
            try task.run()
        } catch {
            return
        }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        task.waitUntilExit()
        if let decoded = try? JSONDecoder().decode(Usage.self, from: data) {
            DispatchQueue.main.async { self.usage = decoded }
        }
    }
}

struct MeterView: View {
    @ObservedObject var model: UsageModel

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Claude Code Usage").font(.headline)
            if let u = model.usage {
                HStack {
                    Text("$\(u.total, specifier: "%.2f") / $\(u.budget, specifier: "%.0f")")
                        .font(.system(.body, design: .monospaced))
                    Spacer()
                    Text(u.status == "over" ? "▲ over" : "▼ under")
                        .foregroundColor(u.status == "over" ? .red : .green)
                        .font(.caption.bold())
                }
                ProgressView(value: min(u.total / max(u.budget, 0.01), 1.0))
                    .tint(u.status == "over" ? .red : .green)
                Text("expected by today: $\(u.expected, specifier: "%.2f")")
                    .font(.caption)
                    .foregroundColor(.secondary)
                if u.source != "account" {
                    Text("estimated (no account spend data found)")
                        .font(.caption2)
                        .foregroundColor(.orange)
                }
                Button(model.expanded ? "Hide breakdown" : "By model") {
                    model.expanded.toggle()
                }
                .font(.caption)
                .buttonStyle(.plain)
                .foregroundColor(.accentColor)
                if model.expanded {
                    ForEach(u.by_model.sorted(by: { $0.value > $1.value }), id: \.key) { name, cost in
                        HStack {
                            Text(name).font(.caption2)
                            Spacer()
                            Text("$\(cost, specifier: "%.2f")").font(.caption2.monospacedDigit())
                        }
                    }
                }
            } else {
                Text("Loading…").foregroundColor(.secondary)
            }
        }
        .padding(12)
        .frame(width: 220)
        .background(.ultraThinMaterial)
        .cornerRadius(10)
        .onAppear {
            model.refresh()
            Timer.scheduledTimer(withTimeInterval: 300, repeats: true) { _ in model.refresh() }
        }
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)

let model = UsageModel()
let hosting = NSHostingView(rootView: MeterView(model: model))
hosting.frame = NSRect(x: 0, y: 0, width: 220, height: 160)

let window = NSWindow(
    contentRect: hosting.frame,
    styleMask: [.borderless],
    backing: .buffered,
    defer: false
)
window.contentView = hosting
window.isOpaque = false
window.backgroundColor = .clear
window.level = .floating
window.collectionBehavior = [.canJoinAllSpaces, .stationary]
window.hasShadow = true
window.isMovableByWindowBackground = true

let autosaveName = "ClaudeMeterWidget"
let restored = window.setFrameAutosaveName(autosaveName)
let onScreen = NSScreen.screens.contains { $0.frame.intersects(window.frame) }

if !restored || !onScreen, let screen = NSScreen.main {
    let origin = NSPoint(
        x: screen.visibleFrame.maxX - hosting.frame.width - 20,
        y: screen.visibleFrame.maxY - hosting.frame.height - 20
    )
    window.setFrameOrigin(origin)
}

NotificationCenter.default.addObserver(forName: NSWindow.didMoveNotification, object: window, queue: .main) { _ in
    window.saveFrame(usingName: autosaveName)
}

window.makeKeyAndOrderFront(nil)
app.run()
