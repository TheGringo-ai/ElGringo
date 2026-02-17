// MainView.swift
// Main container with sidebar navigation

import SwiftUI

struct MainView: View {
    @EnvironmentObject var appState: AppState
    @State private var columnVisibility: NavigationSplitViewVisibility = .all

    var body: some View {
        NavigationSplitView(columnVisibility: $columnVisibility) {
            SidebarView()
        } detail: {
            contentView
        }
        .navigationSplitViewStyle(.balanced)
        .sheet(isPresented: $appState.showImportPanel) {
            ImportDataSheet()
        }
        .overlay {
            if appState.isProcessing {
                ProcessingOverlay(status: appState.processingStatus)
            }
        }
    }

    @ViewBuilder
    private var contentView: some View {
        switch appState.selectedTab {
        case .dashboard:
            DashboardView()
        case .clients:
            ClientsView()
        case .audit:
            AuditView()
        case .analysis:
            AnalysisDashboardView()
        case .reports:
            ReportsView()
        case .assistant:
            AIAssistantView()
        case .settings:
            SettingsView()
        }
    }
}

// MARK: - Sidebar
struct SidebarView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(spacing: 0) {
            // Logo and Title
            VStack(spacing: 8) {
                Image(systemName: "wrench.and.screwdriver.fill")
                    .font(.system(size: 48))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [.blue, .purple],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )

                Text("ChatterFix")
                    .font(.title2)
                    .fontWeight(.bold)

                Text("Intelligence")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.vertical, 24)

            Divider()
                .padding(.horizontal)

            // Navigation Items
            VStack(spacing: 4) {
                ForEach(NavigationTab.allCases) { tab in
                    NavigationButton(
                        tab: tab,
                        isSelected: appState.selectedTab == tab
                    ) {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            appState.selectedTab = tab
                        }
                    }
                }
            }
            .padding(.horizontal, 12)
            .padding(.top, 16)

            Spacer()

            // Quick Stats
            VStack(alignment: .leading, spacing: 12) {
                Text("Quick Stats")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                StatRow(label: "Active Clients", value: "12")
                StatRow(label: "This Month", value: "$47,500")
                StatRow(label: "Pending", value: "3")
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))
            .cornerRadius(12)
            .padding()

            // Version
            Text("v1.0.0")
                .font(.caption2)
                .foregroundColor(.secondary)
                .padding(.bottom, 8)
        }
        .frame(minWidth: 220, maxWidth: 280)
        .background(Color(NSColor.windowBackgroundColor))
    }
}

// MARK: - Navigation Button
struct NavigationButton: View {
    let tab: NavigationTab
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: tab.icon)
                    .font(.system(size: 16, weight: .medium))
                    .frame(width: 24)

                Text(tab.rawValue)
                    .fontWeight(isSelected ? .semibold : .regular)

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.accentColor.opacity(0.15) : Color.clear)
            )
            .foregroundColor(isSelected ? .accentColor : .primary)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Stat Row
struct StatRow: View {
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

// MARK: - Processing Overlay
struct ProcessingOverlay: View {
    let status: String

    var body: some View {
        ZStack {
            Color.black.opacity(0.3)
                .ignoresSafeArea()

            VStack(spacing: 20) {
                ProgressView()
                    .scaleEffect(1.5)
                    .progressViewStyle(CircularProgressViewStyle(tint: .white))

                Text(status)
                    .font(.headline)
                    .foregroundColor(.white)
            }
            .padding(40)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color(NSColor.windowBackgroundColor).opacity(0.95))
                    .shadow(radius: 20)
            )
        }
    }
}

// MARK: - Import Data Sheet
struct ImportDataSheet: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss

    var body: some View {
        VStack(spacing: 24) {
            Text("Import Company Data")
                .font(.title2)
                .fontWeight(.bold)

            FileDropZone(
                title: "Drop CSV files here",
                subtitle: "Work orders, assets, inventory, or parts",
                allowedTypes: ["csv"]
            ) { urls in
                for url in urls {
                    importFile(url)
                }
            }
            .frame(height: 200)

            HStack {
                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)

                Spacer()

                Button("Done") {
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
                .buttonStyle(.borderedProminent)
            }
        }
        .padding(24)
        .frame(width: 500)
    }

    private func importFile(_ url: URL) {
        // Detect file type and import
        let filename = url.lastPathComponent.lowercased()

        if filename.contains("work") || filename.contains("order") || filename.contains("wo") {
            appState.companyData.workOrdersPath = url
        } else if filename.contains("asset") || filename.contains("equipment") {
            appState.companyData.assetsPath = url
        } else if filename.contains("inventory") || filename.contains("stock") {
            appState.companyData.inventoryPath = url
        } else if filename.contains("part") {
            appState.companyData.partsPath = url
        } else {
            // Default to work orders
            appState.companyData.workOrdersPath = url
        }
    }
}

#Preview {
    MainView()
        .environmentObject(AppState())
}
