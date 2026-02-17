// AuditView.swift
// New audit workflow with multi-file support

import SwiftUI
import UniformTypeIdentifiers

struct AuditView: View {
    @EnvironmentObject var appState: AppState
    @State private var selectedClient: String = ""
    @State private var newClientName: String = ""
    @State private var newClientEmail: String = ""
    @State private var newClientPhone: String = ""
    @State private var isNewClient: Bool = true

    @State private var auditSelected: Bool = true
    @State private var auditFee: Double = 7500
    @State private var roadmapSelected: Bool = false
    @State private var roadmapFee: Double = 15000
    @State private var subscriptionSelected: Bool = false
    @State private var subscriptionFee: Double = 25000

    @State private var selectedTab: DataFileType = .workOrders

    var totalFee: Double {
        var total: Double = 0
        if auditSelected { total += auditFee }
        if roadmapSelected { total += roadmapFee }
        if subscriptionSelected { total += subscriptionFee }
        return total
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // Header
                Text("New Intelligence Project")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                // Step 1: Client Selection
                clientSection

                Divider()

                // Step 2: Service Selection
                serviceSection

                Divider()

                // Step 3: Data Upload
                dataUploadSection

                Divider()

                // Step 4: Generate Reports
                generateSection
            }
            .padding(24)
        }
        .background(Color(NSColor.textBackgroundColor))
    }

    // MARK: - Client Section
    private var clientSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            SectionHeader(number: 1, title: "Select Client")

            Picker("Client", selection: $isNewClient) {
                Text("New Client").tag(true)
                Text("Existing Client").tag(false)
            }
            .pickerStyle(.segmented)
            .frame(width: 300)

            if isNewClient {
                HStack(spacing: 16) {
                    VStack(alignment: .leading, spacing: 8) {
                        TextField("Company Name *", text: $newClientName)
                            .textFieldStyle(.roundedBorder)

                        TextField("Contact Email", text: $newClientEmail)
                            .textFieldStyle(.roundedBorder)
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        TextField("Contact Phone", text: $newClientPhone)
                            .textFieldStyle(.roundedBorder)

                        // Spacer for alignment
                        Text("")
                            .frame(height: 22)
                    }
                }
                .frame(maxWidth: 600)
            } else {
                Picker("Select Client", selection: $selectedClient) {
                    Text("Choose...").tag("")
                    ForEach(DataManager.shared.getSavedCompanies(), id: \.self) { company in
                        Text(company).tag(company)
                    }
                }
                .frame(width: 300)

                if !selectedClient.isEmpty {
                    Label("Data found for \(selectedClient)", systemImage: "checkmark.circle.fill")
                        .foregroundColor(.green)
                }
            }
        }
    }

    // MARK: - Service Section
    private var serviceSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            SectionHeader(number: 2, title: "Select Services")

            HStack(spacing: 16) {
                ServiceSelector(
                    title: "Initial Audit & Clean",
                    icon: "magnifyingglass",
                    isSelected: $auditSelected,
                    fee: $auditFee,
                    minFee: 5000,
                    maxFee: 10000,
                    color: .blue
                )

                ServiceSelector(
                    title: "Strategy Roadmap",
                    icon: "map.fill",
                    isSelected: $roadmapSelected,
                    fee: $roadmapFee,
                    minFee: 15000,
                    maxFee: 15000,
                    color: .purple
                )

                ServiceSelector(
                    title: "Annual Subscription",
                    icon: "chart.bar.fill",
                    isSelected: $subscriptionSelected,
                    fee: $subscriptionFee,
                    minFee: 25000,
                    maxFee: 25000,
                    color: .green
                )
            }

            HStack {
                Spacer()
                VStack(alignment: .trailing) {
                    Text("Total")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Text("$\(totalFee, specifier: "%.0f")")
                        .font(.title)
                        .fontWeight(.bold)
                        .foregroundColor(.green)
                }
            }
        }
    }

    // MARK: - Data Upload Section
    private var dataUploadSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            SectionHeader(number: 3, title: "Upload Company Data")

            Text("Upload one or more data files from the client's CMMS system.")
                .font(.subheadline)
                .foregroundColor(.secondary)

            // Tab Selection
            HStack(spacing: 0) {
                ForEach(DataFileType.allCases) { type in
                    DataTabButton(
                        type: type,
                        isSelected: selectedTab == type,
                        hasData: hasData(for: type)
                    ) {
                        selectedTab = type
                    }
                }
            }
            .background(Color(NSColor.controlBackgroundColor))
            .cornerRadius(8)

            // File Drop Zone
            FileDropZone(
                title: "Drop \(selectedTab.displayName) CSV here",
                subtitle: selectedTab.description,
                allowedTypes: ["csv"],
                currentFile: getFilePath(for: selectedTab)
            ) { urls in
                if let url = urls.first {
                    setFilePath(url, for: selectedTab)
                }
            }
            .frame(height: 180)

            // Data Summary
            dataSummary
        }
    }

    // MARK: - Data Summary
    private var dataSummary: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Data Summary")
                .font(.headline)

            HStack(spacing: 16) {
                DataSummaryCard(
                    title: "Work Orders",
                    count: appState.companyData.workOrderCount,
                    icon: "doc.text.fill"
                )

                DataSummaryCard(
                    title: "Assets",
                    count: appState.companyData.assetCount,
                    icon: "gearshape.fill"
                )

                DataSummaryCard(
                    title: "Inventory",
                    count: appState.companyData.inventoryCount,
                    icon: "shippingbox.fill"
                )

                DataSummaryCard(
                    title: "Parts",
                    count: appState.companyData.partsCount,
                    icon: "wrench.fill"
                )
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(12)
    }

    // MARK: - Generate Section
    private var generateSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            SectionHeader(number: 4, title: "Generate Reports")

            if appState.companyData.hasAnyData {
                HStack(spacing: 16) {
                    ActionButton(
                        title: "Generate All Reports",
                        icon: "bolt.fill",
                        color: .blue,
                        isPrimary: true
                    ) {
                        generateAllReports()
                    }

                    ActionButton(
                        title: "Quick Data Audit",
                        icon: "doc.text.magnifyingglass",
                        color: .purple
                    ) {
                        generateQuickAudit()
                    }

                    ActionButton(
                        title: "Complete Package",
                        icon: "shippingbox.fill",
                        color: .green
                    ) {
                        generateCompletePackage()
                    }

                    ActionButton(
                        title: "PDF Only",
                        icon: "doc.richtext.fill",
                        color: .orange
                    ) {
                        generatePDFOnly()
                    }
                }
            } else {
                Label("Upload at least a Work Orders file to generate reports.", systemImage: "info.circle")
                    .foregroundColor(.secondary)
            }
        }
    }

    // MARK: - Helper Methods
    private func hasData(for type: DataFileType) -> Bool {
        switch type {
        case .workOrders: return appState.companyData.workOrdersPath != nil
        case .assets: return appState.companyData.assetsPath != nil
        case .inventory: return appState.companyData.inventoryPath != nil
        case .parts: return appState.companyData.partsPath != nil
        }
    }

    private func getFilePath(for type: DataFileType) -> URL? {
        switch type {
        case .workOrders: return appState.companyData.workOrdersPath
        case .assets: return appState.companyData.assetsPath
        case .inventory: return appState.companyData.inventoryPath
        case .parts: return appState.companyData.partsPath
        }
    }

    private func setFilePath(_ url: URL, for type: DataFileType) {
        switch type {
        case .workOrders: appState.companyData.workOrdersPath = url
        case .assets: appState.companyData.assetsPath = url
        case .inventory: appState.companyData.inventoryPath = url
        case .parts: appState.companyData.partsPath = url
        }

        // Load the data
        appState.companyData.loadData(from: url, type: type)
    }

    private var clientName: String {
        isNewClient ? newClientName : selectedClient
    }

    private func generateAllReports() {
        guard !clientName.isEmpty else { return }
        appState.selectedClient = Client(name: clientName, email: newClientEmail, phone: newClientPhone)
        appState.generateAllReports()
    }

    private func generateQuickAudit() {
        guard !clientName.isEmpty else { return }
        appState.isProcessing = true
        appState.processingStatus = "Running quick data audit..."

        Task {
            do {
                try await PythonBridge.shared.runQuickAudit(
                    for: clientName,
                    data: appState.companyData
                )
                await MainActor.run {
                    appState.isProcessing = false
                }
            } catch {
                await MainActor.run {
                    appState.isProcessing = false
                }
            }
        }
    }

    private func generateCompletePackage() {
        guard !clientName.isEmpty else { return }
        appState.isProcessing = true
        appState.processingStatus = "Generating complete deliverables package..."

        Task {
            do {
                let result = try await PythonBridge.shared.generateDeliverables(
                    for: clientName,
                    data: appState.companyData
                )

                await MainActor.run {
                    appState.isProcessing = false

                    // Show in Finder
                    if let outputDir = result.outputDirectory {
                        NSWorkspace.shared.selectFile(nil, inFileViewerRootedAtPath: outputDir)
                    }
                }
            } catch {
                await MainActor.run {
                    appState.isProcessing = false
                }
            }
        }
    }

    private func generatePDFOnly() {
        guard !clientName.isEmpty else { return }

        let savePanel = NSSavePanel()
        savePanel.allowedContentTypes = [.pdf]
        savePanel.nameFieldStringValue = "\(clientName.replacingOccurrences(of: " ", with: "_"))_Intelligence_Report.pdf"

        savePanel.begin { response in
            if response == .OK, let url = savePanel.url {
                appState.isProcessing = true
                appState.processingStatus = "Generating PDF report..."

                Task {
                    do {
                        try await PythonBridge.shared.generatePDF(
                            for: clientName,
                            data: appState.companyData,
                            outputPath: url
                        )

                        await MainActor.run {
                            appState.isProcessing = false
                            NSWorkspace.shared.open(url)
                        }
                    } catch {
                        await MainActor.run {
                            appState.isProcessing = false
                        }
                    }
                }
            }
        }
    }
}

// MARK: - Section Header
struct SectionHeader: View {
    let number: Int
    let title: String

    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(Color.accentColor)
                    .frame(width: 28, height: 28)

                Text("\(number)")
                    .font(.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
            }

            Text(title)
                .font(.title2)
                .fontWeight(.semibold)
        }
    }
}

// MARK: - Service Selector
struct ServiceSelector: View {
    let title: String
    let icon: String
    @Binding var isSelected: Bool
    @Binding var fee: Double
    let minFee: Double
    let maxFee: Double
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(color)

                Toggle("", isOn: $isSelected)
                    .toggleStyle(.checkbox)
            }

            Text(title)
                .font(.headline)

            if isSelected {
                if minFee != maxFee {
                    Slider(value: $fee, in: minFee...maxFee, step: 500)

                    Text("$\(fee, specifier: "%.0f")")
                        .font(.title3)
                        .fontWeight(.bold)
                        .foregroundColor(.green)
                } else {
                    Text("$\(fee, specifier: "%.0f")")
                        .font(.title3)
                        .fontWeight(.bold)
                        .foregroundColor(.green)
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(NSColor.controlBackgroundColor))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(isSelected ? color : Color.clear, lineWidth: 2)
                )
        )
        .opacity(isSelected ? 1.0 : 0.6)
    }
}

// MARK: - Data Tab Button
struct DataTabButton: View {
    let type: DataFileType
    let isSelected: Bool
    let hasData: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: type.icon)
                Text(type.displayName)

                if hasData {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                        .font(.caption)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(isSelected ? Color.accentColor : Color.clear)
            .foregroundColor(isSelected ? .white : .primary)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Data Summary Card
struct DataSummaryCard: View {
    let title: String
    let count: Int?
    let icon: String

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(count != nil ? .accentColor : .secondary)

            Text(count != nil ? "\(count!)" : "—")
                .font(.title2)
                .fontWeight(.bold)

            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(NSColor.textBackgroundColor))
        .cornerRadius(8)
    }
}

// MARK: - Action Button
struct ActionButton: View {
    let title: String
    let icon: String
    let color: Color
    var isPrimary: Bool = false
    let action: () -> Void

    var body: some View {
        if isPrimary {
            Button(action: action) {
                HStack {
                    Image(systemName: icon)
                    Text(title)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
            }
            .buttonStyle(.borderedProminent)
            .tint(color)
        } else {
            Button(action: action) {
                HStack {
                    Image(systemName: icon)
                    Text(title)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
            }
            .buttonStyle(.bordered)
            .tint(color)
        }
    }
}

// DataFileType is defined in CompanyData.swift

#Preview {
    AuditView()
        .environmentObject(AppState())
        .frame(width: 1000, height: 900)
}
