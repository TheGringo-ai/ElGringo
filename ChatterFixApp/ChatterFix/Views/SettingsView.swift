// SettingsView.swift
// App settings

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @State private var pythonPath: String = "/usr/bin/python3"
    @State private var defaultOutputPath: String = ""
    @State private var autoSaveEnabled: Bool = true
    @State private var notificationsEnabled: Bool = true
    @State private var darkModeOverride: Bool = false

    var body: some View {
        TabView {
            generalSettings
                .tabItem {
                    Label("General", systemImage: "gear")
                }

            pythonSettings
                .tabItem {
                    Label("Python", systemImage: "terminal")
                }

            notificationSettings
                .tabItem {
                    Label("Notifications", systemImage: "bell")
                }

            aboutView
                .tabItem {
                    Label("About", systemImage: "info.circle")
                }
        }
        .padding(20)
        .frame(width: 500, height: 400)
    }

    // MARK: - General Settings
    private var generalSettings: some View {
        Form {
            Section("Output") {
                HStack {
                    TextField("Default Output Path", text: $defaultOutputPath)
                        .textFieldStyle(.roundedBorder)

                    Button("Browse") {
                        selectOutputDirectory()
                    }
                }

                Toggle("Auto-save company data", isOn: $autoSaveEnabled)
            }

            Section("Appearance") {
                Toggle("Override system dark mode", isOn: $darkModeOverride)
            }
        }
        .formStyle(.grouped)
    }

    // MARK: - Python Settings
    private var pythonSettings: some View {
        Form {
            Section("Python Configuration") {
                HStack {
                    TextField("Python Path", text: $pythonPath)
                        .textFieldStyle(.roundedBorder)

                    Button("Detect") {
                        detectPython()
                    }
                }

                Text("ChatterFix uses Python for data processing and ML inference.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Section("MLX Status") {
                HStack {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                    Text("MLX Framework: Available")
                }

                HStack {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                    Text("Apple Silicon: Detected")
                }
            }
        }
        .formStyle(.grouped)
    }

    // MARK: - Notification Settings
    private var notificationSettings: some View {
        Form {
            Section("Notifications") {
                Toggle("Enable notifications", isOn: $notificationsEnabled)

                if notificationsEnabled {
                    Toggle("Report generation complete", isOn: .constant(true))
                    Toggle("Failure alerts", isOn: .constant(true))
                    Toggle("Processing errors", isOn: .constant(true))
                }
            }
        }
        .formStyle(.grouped)
    }

    // MARK: - About View
    private var aboutView: some View {
        VStack(spacing: 20) {
            Image(systemName: "wrench.and.screwdriver.fill")
                .font(.system(size: 64))
                .foregroundStyle(
                    LinearGradient(
                        colors: [.blue, .purple],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )

            Text("ChatterFix Intelligence")
                .font(.title)
                .fontWeight(.bold)

            Text("Version 1.0.0")
                .foregroundColor(.secondary)

            Divider()
                .frame(width: 200)

            Text("Maintenance cost optimization powered by AI")
                .font(.subheadline)
                .foregroundColor(.secondary)

            Spacer()

            Text("© 2024 ChatterFix AI")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding()
    }

    // MARK: - Helpers
    private func selectOutputDirectory() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false

        if panel.runModal() == .OK, let url = panel.url {
            defaultOutputPath = url.path
        }
    }

    private func detectPython() {
        let paths = [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]

        for path in paths {
            if FileManager.default.fileExists(atPath: path) {
                pythonPath = path
                break
            }
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(AppState())
}
