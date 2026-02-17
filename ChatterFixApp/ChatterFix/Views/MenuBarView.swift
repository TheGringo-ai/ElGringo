// MenuBarView.swift
// Menu bar quick access

import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack {
                Image(systemName: "wrench.and.screwdriver.fill")
                    .foregroundStyle(
                        LinearGradient(
                            colors: [.blue, .purple],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )

                Text("ChatterFix")
                    .fontWeight(.semibold)

                Spacer()

                if appState.isProcessing {
                    ProgressView()
                        .scaleEffect(0.7)
                }
            }
            .padding()

            Divider()

            // Quick Stats
            VStack(alignment: .leading, spacing: 8) {
                StatItem(label: "Active Clients", value: "12")
                StatItem(label: "This Month", value: "$47,500")
                StatItem(label: "Pending Reports", value: "3")
            }
            .padding()

            Divider()

            // Quick Actions
            VStack(spacing: 2) {
                MenuButton(title: "New Audit", icon: "plus.circle") {
                    openMainWindow()
                    appState.selectedTab = .audit
                }

                MenuButton(title: "View Reports", icon: "doc.text") {
                    openMainWindow()
                    appState.selectedTab = .reports
                }

                MenuButton(title: "Import Data", icon: "arrow.down.doc") {
                    appState.showImportPanel = true
                    openMainWindow()
                }
            }
            .padding(.vertical, 4)

            Divider()

            // Footer Actions
            VStack(spacing: 2) {
                MenuButton(title: "Open Dashboard", icon: "macwindow") {
                    openMainWindow()
                }

                MenuButton(title: "Preferences...", icon: "gear") {
                    openSettings()
                }

                MenuButton(title: "Quit ChatterFix", icon: "power") {
                    NSApplication.shared.terminate(nil)
                }
            }
            .padding(.vertical, 4)
        }
        .frame(width: 280)
    }

    private func openMainWindow() {
        NSApp.activate(ignoringOtherApps: true)

        if let window = NSApp.windows.first(where: { $0.title.contains("ChatterFix") || $0.isKeyWindow }) {
            window.makeKeyAndOrderFront(nil)
        } else {
            // Open new window if none exists
            if let window = NSApp.windows.first {
                window.makeKeyAndOrderFront(nil)
            }
        }
    }

    private func openSettings() {
        NSApp.activate(ignoringOtherApps: true)
        NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
    }
}

// MARK: - Stat Item
struct StatItem: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .font(.caption)
                .fontWeight(.semibold)
        }
    }
}

// MARK: - Menu Button
struct MenuButton: View {
    let title: String
    let icon: String
    let action: () -> Void

    @State private var isHovering: Bool = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .frame(width: 20)
                    .foregroundColor(.secondary)

                Text(title)

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(isHovering ? Color.accentColor.opacity(0.1) : Color.clear)
            .cornerRadius(6)
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovering = hovering
        }
    }
}

#Preview {
    MenuBarView()
        .environmentObject(AppState())
}
