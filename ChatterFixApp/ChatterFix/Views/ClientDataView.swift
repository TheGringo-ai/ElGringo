// ClientDataView.swift
// View for managing company-specific data uploads and history

import SwiftUI
import UniformTypeIdentifiers

struct ClientDataView: View {
    let client: Client
    @EnvironmentObject var appState: AppState
    @State private var selectedDataType: DataFileType = .workOrders
    @State private var uploads: [DataUpload] = []
    @State private var statistics: CompanyStatistics = CompanyStatistics()
    @State private var isImporting = false
    @State private var showDeleteConfirm = false
    @State private var uploadToDelete: DataUpload?
    @State private var importError: String?
    @State private var successMessage: String?

    private let dataManager = CompanyDataManager.shared

    var body: some View {
        VStack(spacing: 0) {
            // Header
            headerSection

            Divider()

            // Main content
            HStack(spacing: 0) {
                // Left: Data type tabs
                dataTypeSidebar
                    .frame(width: 200)

                Divider()

                // Right: File list and upload area
                VStack(spacing: 0) {
                    // Upload zone
                    uploadSection

                    Divider()

                    // File history
                    fileHistorySection
                }
            }
        }
        .onAppear {
            loadData()
        }
        .fileImporter(
            isPresented: $isImporting,
            allowedContentTypes: [UTType.commaSeparatedText],
            allowsMultipleSelection: true
        ) { result in
            handleFileImport(result)
        }
        .alert("Delete Upload?", isPresented: $showDeleteConfirm) {
            Button("Cancel", role: .cancel) { }
            Button("Delete", role: .destructive) {
                if let upload = uploadToDelete {
                    deleteUpload(upload)
                }
            }
        } message: {
            Text("This will permanently delete this file from the company's data history.")
        }
    }

    // MARK: - Header Section

    private var headerSection: some View {
        HStack(spacing: 16) {
            // Company avatar
            ZStack {
                Circle()
                    .fill(LinearGradient(
                        colors: [.blue, .purple],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ))
                    .frame(width: 60, height: 60)

                Text(client.initials)
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(client.name)
                    .font(.title2)
                    .fontWeight(.bold)

                HStack(spacing: 16) {
                    Label("\(statistics.totalUploads) uploads", systemImage: "doc.fill")
                    if let lastUpload = statistics.lastUpload {
                        Label("Last: \(lastUpload.formatted(date: .abbreviated, time: .shortened))", systemImage: "clock")
                    }
                }
                .font(.caption)
                .foregroundColor(.secondary)
            }

            Spacer()

            // Quick stats
            HStack(spacing: 24) {
                StatBox(title: "Work Orders", value: "\(statistics.totalWorkOrders)", icon: "doc.text.fill")
                StatBox(title: "Assets", value: "\(statistics.totalAssets)", icon: "gearshape.fill")
                StatBox(title: "Inventory", value: "\(statistics.totalInventoryItems)", icon: "shippingbox.fill")
                StatBox(title: "Parts", value: "\(statistics.totalParts)", icon: "wrench.fill")
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
    }

    // MARK: - Data Type Sidebar

    private var dataTypeSidebar: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Data Categories")
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)
                .padding(.horizontal)
                .padding(.top, 16)
                .padding(.bottom, 8)

            ForEach(DataFileType.allCases) { type in
                DataTypeRow(
                    type: type,
                    isSelected: selectedDataType == type,
                    fileCount: fileCount(for: type),
                    rowCount: rowCount(for: type)
                ) {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        selectedDataType = type
                        loadUploads()
                    }
                }
            }

            Spacer()

            // Data summary
            VStack(alignment: .leading, spacing: 8) {
                Text("Total Data")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                HStack {
                    Text("Files")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text("\(statistics.totalUploads)")
                        .font(.caption)
                        .fontWeight(.semibold)
                }

                HStack {
                    Text("Records")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text("\(totalRecords)")
                        .font(.caption)
                        .fontWeight(.semibold)
                }
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))
            .cornerRadius(8)
            .padding()
        }
        .background(Color(NSColor.windowBackgroundColor))
    }

    // MARK: - Upload Section

    private var uploadSection: some View {
        VStack(spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Upload \(selectedDataType.displayName)")
                        .font(.headline)

                    Text(selectedDataType.description)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Button {
                    isImporting = true
                } label: {
                    Label("Choose Files", systemImage: "plus.circle.fill")
                }
                .buttonStyle(.borderedProminent)
            }

            // Drop zone
            MultiFileDropZone(dataType: selectedDataType) { urls in
                importFiles(urls)
            }
            .frame(height: 120)

            if let error = importError {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(.orange)
                    Text(error)
                        .font(.caption)
                        .foregroundColor(.orange)
                    Spacer()
                    Button("Dismiss") {
                        importError = nil
                    }
                    .buttonStyle(.plain)
                    .font(.caption)
                }
                .padding(8)
                .background(Color.orange.opacity(0.1))
                .cornerRadius(8)
            }

            if let success = successMessage {
                HStack {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                    Text(success)
                        .font(.caption)
                        .foregroundColor(.green)
                    Spacer()
                    Button("Dismiss") {
                        successMessage = nil
                    }
                    .buttonStyle(.plain)
                    .font(.caption)
                }
                .padding(8)
                .background(Color.green.opacity(0.1))
                .cornerRadius(8)
            }
        }
        .padding()
    }

    // MARK: - File History Section

    private var fileHistorySection: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Upload History - \(selectedDataType.displayName)")
                    .font(.headline)

                Spacer()

                if !uploads.isEmpty {
                    Text("\(uploads.count) file(s)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding()

            if uploads.isEmpty {
                emptyStateView
            } else {
                ScrollView {
                    LazyVStack(spacing: 8) {
                        ForEach(uploads) { upload in
                            UploadRow(upload: upload) {
                                uploadToDelete = upload
                                showDeleteConfirm = true
                            }
                        }
                    }
                    .padding(.horizontal)
                    .padding(.bottom)
                }
            }
        }
    }

    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: selectedDataType.icon)
                .font(.system(size: 48))
                .foregroundColor(.secondary.opacity(0.5))

            Text("No \(selectedDataType.displayName.lowercased()) uploaded yet")
                .font(.headline)
                .foregroundColor(.secondary)

            Text("Drop CSV files above or click 'Choose Files' to upload")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }

    // MARK: - Helper Methods

    private func loadData() {
        statistics = dataManager.getStatistics(for: client.id)
        loadUploads()
    }

    private func loadUploads() {
        uploads = dataManager.getUploads(for: client.id, type: selectedDataType)
    }

    private func handleFileImport(_ result: Result<[URL], Error>) {
        switch result {
        case .success(let urls):
            importFiles(urls)
        case .failure(let error):
            importError = error.localizedDescription
        }
    }

    private func importFiles(_ urls: [URL]) {
        importError = nil
        successMessage = nil
        var successCount = 0

        for url in urls {
            // Start accessing security-scoped resource
            let accessing = url.startAccessingSecurityScopedResource()

            do {
                // Read file contents while we have access
                let fileData = try Data(contentsOf: url)
                let fileName = url.lastPathComponent

                // Stop accessing before we do other work
                if accessing {
                    url.stopAccessingSecurityScopedResource()
                }

                // Now import using the data
                let upload = try dataManager.importFileData(fileData, fileName: fileName, for: client.id, type: selectedDataType)
                successCount += 1
                print("Successfully imported: \(fileName) -> \(upload.storedPath.path)")

            } catch {
                if accessing {
                    url.stopAccessingSecurityScopedResource()
                }
                importError = "Failed to import \(url.lastPathComponent): \(error.localizedDescription)"
                print("Import error: \(error)")
            }
        }

        if successCount > 0 {
            loadData()
            successMessage = "Successfully imported \(successCount) file(s)"

            // Update appState so analysis can find the data
            appState.selectedClient = client
            appState.refreshClientData()
        }
    }

    private func deleteUpload(_ upload: DataUpload) {
        do {
            try dataManager.deleteUpload(upload, for: client.id)
            loadData()
        } catch {
            importError = "Failed to delete: \(error.localizedDescription)"
        }
    }

    private func fileCount(for type: DataFileType) -> Int {
        switch type {
        case .workOrders: return statistics.workOrderFiles
        case .assets: return statistics.assetFiles
        case .inventory: return statistics.inventoryFiles
        case .parts: return statistics.partsFiles
        }
    }

    private func rowCount(for type: DataFileType) -> Int {
        switch type {
        case .workOrders: return statistics.totalWorkOrders
        case .assets: return statistics.totalAssets
        case .inventory: return statistics.totalInventoryItems
        case .parts: return statistics.totalParts
        }
    }

    private var totalRecords: Int {
        statistics.totalWorkOrders + statistics.totalAssets +
        statistics.totalInventoryItems + statistics.totalParts
    }
}

// MARK: - Supporting Views

struct StatBox: View {
    let title: String
    let value: String
    let icon: String

    var body: some View {
        VStack(spacing: 4) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(.accentColor)

            Text(value)
                .font(.headline)

            Text(title)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .frame(width: 80)
    }
}

struct DataTypeRow: View {
    let type: DataFileType
    let isSelected: Bool
    let fileCount: Int
    let rowCount: Int
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: type.icon)
                    .font(.system(size: 16, weight: .medium))
                    .frame(width: 24)

                VStack(alignment: .leading, spacing: 2) {
                    Text(type.displayName)
                        .fontWeight(isSelected ? .semibold : .regular)

                    if fileCount > 0 {
                        Text("\(fileCount) files, \(rowCount) rows")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                if fileCount > 0 {
                    Circle()
                        .fill(Color.green)
                        .frame(width: 8, height: 8)
                }
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
        .padding(.horizontal, 8)
    }
}

struct UploadRow: View {
    let upload: DataUpload
    let onDelete: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "doc.fill")
                .font(.title2)
                .foregroundColor(.accentColor)

            VStack(alignment: .leading, spacing: 4) {
                Text(upload.originalFilename)
                    .font(.headline)

                HStack(spacing: 12) {
                    Label("\(upload.rowCount) rows", systemImage: "list.bullet")
                    Label(upload.formattedDate, systemImage: "clock")
                }
                .font(.caption)
                .foregroundColor(.secondary)
            }

            Spacer()

            Button(action: onDelete) {
                Image(systemName: "trash")
                    .foregroundColor(.red.opacity(0.7))
            }
            .buttonStyle(.plain)
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(8)
    }
}

struct MultiFileDropZone: View {
    let dataType: DataFileType
    let onDrop: ([URL]) -> Void

    @State private var isTargeted = false

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(
                    isTargeted ? Color.accentColor : Color.secondary.opacity(0.3),
                    style: StrokeStyle(lineWidth: 2, dash: [8])
                )
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(isTargeted ? Color.accentColor.opacity(0.1) : Color.clear)
                )

            VStack(spacing: 8) {
                Image(systemName: isTargeted ? "arrow.down.circle.fill" : "arrow.down.doc.fill")
                    .font(.system(size: 32))
                    .foregroundColor(isTargeted ? .accentColor : .secondary)

                Text(isTargeted ? "Drop to upload" : "Drop CSV files here")
                    .font(.headline)
                    .foregroundColor(isTargeted ? .accentColor : .secondary)

                Text("You can drop multiple files at once")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .onDrop(of: [.fileURL], isTargeted: $isTargeted) { providers in
            handleDrop(providers)
            return true
        }
    }

    private func handleDrop(_ providers: [NSItemProvider]) {
        var urls: [URL] = []
        let group = DispatchGroup()

        for provider in providers {
            group.enter()
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, error in
                if let data = item as? Data,
                   let url = URL(dataRepresentation: data, relativeTo: nil),
                   url.pathExtension.lowercased() == "csv" {
                    urls.append(url)
                }
                group.leave()
            }
        }

        group.notify(queue: .main) {
            if !urls.isEmpty {
                onDrop(urls)
            }
        }
    }
}

#Preview {
    ClientDataView(client: Client(name: "ABC Manufacturing", industry: "Manufacturing"))
        .environmentObject(AppState())
        .frame(width: 1000, height: 700)
}
