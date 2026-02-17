// ChatterFixApp.swift
// ChatterFix Intelligence - Native macOS App
// Copyright 2024 ChatterFix AI

import SwiftUI

@main
struct ChatterFixApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            MainView()
                .environmentObject(appState)
                .frame(minWidth: 1200, minHeight: 800)
        }
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("New Audit") {
                    appState.selectedTab = .audit
                }
                .keyboardShortcut("n", modifiers: .command)

                Button("Import Data...") {
                    appState.showImportPanel = true
                }
                .keyboardShortcut("i", modifiers: .command)
            }

            CommandMenu("Reports") {
                Button("Generate All Reports") {
                    appState.generateAllReports()
                }
                .keyboardShortcut("r", modifiers: [.command, .shift])

                Button("Export PDF") {
                    appState.exportPDF()
                }
                .keyboardShortcut("e", modifiers: .command)
            }
        }

        // Menu Bar Extra
        MenuBarExtra("ChatterFix", systemImage: "wrench.and.screwdriver.fill") {
            MenuBarView()
                .environmentObject(appState)
        }
        .menuBarExtraStyle(.window)

        // Settings Window
        Settings {
            SettingsView()
                .environmentObject(appState)
        }
    }
}

// MARK: - App Delegate
class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Setup Python environment
        PythonBridge.shared.initialize()

        // Register for notifications
        NSApp.registerForRemoteNotifications()
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Cleanup
        PythonBridge.shared.shutdown()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return false // Keep running in menu bar
    }
}

// MARK: - App State
class AppState: ObservableObject {
    @Published var selectedTab: NavigationTab = .dashboard
    @Published var selectedClient: Client? {
        didSet {
            // When client changes, load their data from CompanyDataManager
            if let client = selectedClient {
                loadClientData(for: client)
            }
        }
    }
    @Published var companyData: CompanyData = CompanyData()
    @Published var reports: [Report] = []
    @Published var isProcessing: Bool = false
    @Published var processingStatus: String = ""
    @Published var showImportPanel: Bool = false
    @Published var clients: [Client] = []

    private let dataManager = DataManager.shared
    private let companyDataManager = CompanyDataManager.shared
    private let pythonBridge = PythonBridge.shared

    init() {
        loadSavedData()
    }

    func loadSavedData() {
        // Load clients from disk
        if let loadedClients = dataManager.loadClients() {
            self.clients = loadedClients
        }
    }

    /// Load data from CompanyDataManager for a specific client
    func loadClientData(for client: Client) {
        // Get merged work orders file if available
        if let upload = companyDataManager.getLatestUpload(for: client.id, type: .workOrders) {
            companyData.workOrdersPath = upload.storedPath
        } else {
            // Try to get merged file
            if let mergedPath = try? companyDataManager.getMergedData(for: client.id, type: .workOrders) {
                companyData.workOrdersPath = mergedPath
            }
        }

        // Load other data types
        if let upload = companyDataManager.getLatestUpload(for: client.id, type: .assets) {
            companyData.assetsPath = upload.storedPath
        }
        if let upload = companyDataManager.getLatestUpload(for: client.id, type: .inventory) {
            companyData.inventoryPath = upload.storedPath
        }
        if let upload = companyDataManager.getLatestUpload(for: client.id, type: .parts) {
            companyData.partsPath = upload.storedPath
        }

        print("Loaded client data for \(client.name): workOrders=\(companyData.workOrdersPath?.path ?? "nil")")
    }

    /// Refresh data for current client (call after uploading new files)
    func refreshClientData() {
        if let client = selectedClient {
            loadClientData(for: client)
        }
    }

    func generateAllReports() {
        guard let client = selectedClient else { return }
        isProcessing = true
        processingStatus = "Generating reports..."

        Task {
            do {
                let result = try await pythonBridge.generateDeliverables(
                    for: client.name,
                    data: companyData
                )

                await MainActor.run {
                    self.reports = result.reports
                    self.isProcessing = false
                    self.showNotification(title: "Reports Ready", body: "All reports for \(client.name) have been generated.")
                }
            } catch {
                await MainActor.run {
                    self.isProcessing = false
                    self.processingStatus = "Error: \(error.localizedDescription)"
                }
            }
        }
    }

    func exportPDF() {
        guard let client = selectedClient else { return }

        let savePanel = NSSavePanel()
        savePanel.allowedContentTypes = [.pdf]
        savePanel.nameFieldStringValue = "\(client.name)_Intelligence_Report.pdf"

        savePanel.begin { response in
            if response == .OK, let url = savePanel.url {
                Task {
                    try? await self.pythonBridge.exportPDF(to: url, client: client.name)
                }
            }
        }
    }

    func showNotification(title: String, body: String) {
        let notification = NSUserNotification()
        notification.title = title
        notification.informativeText = body
        notification.soundName = NSUserNotificationDefaultSoundName
        NSUserNotificationCenter.default.deliver(notification)
    }
}

// MARK: - Navigation
enum NavigationTab: String, CaseIterable, Identifiable {
    case dashboard = "Dashboard"
    case clients = "Clients"
    case audit = "New Audit"
    case analysis = "Analysis Tools"
    case reports = "Reports"
    case assistant = "AI Assistant"
    case settings = "Settings"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .dashboard: return "chart.bar.fill"
        case .clients: return "person.2.fill"
        case .audit: return "doc.text.magnifyingglass"
        case .analysis: return "waveform.path.ecg"
        case .reports: return "chart.pie.fill"
        case .assistant: return "cpu"
        case .settings: return "gear"
        }
    }
}
