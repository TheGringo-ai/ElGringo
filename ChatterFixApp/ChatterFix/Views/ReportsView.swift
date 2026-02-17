// ReportsView.swift
// Reports library view

import SwiftUI

struct ReportsView: View {
    @EnvironmentObject var appState: AppState
    @State private var searchText: String = ""
    @State private var selectedType: ReportType? = nil

    var filteredReports: [Report] {
        var reports = appState.reports

        if !searchText.isEmpty {
            reports = reports.filter {
                $0.clientName.localizedCaseInsensitiveContains(searchText) ||
                $0.type.rawValue.localizedCaseInsensitiveContains(searchText)
            }
        }

        if let type = selectedType {
            reports = reports.filter { $0.type == type }
        }

        return reports.sorted { $0.date > $1.date }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            // Content
            if filteredReports.isEmpty {
                emptyState
            } else {
                reportList
            }
        }
        .background(Color(NSColor.textBackgroundColor))
    }

    // MARK: - Header
    private var header: some View {
        HStack(spacing: 16) {
            Text("Reports Library")
                .font(.largeTitle)
                .fontWeight(.bold)

            Spacer()

            // Search
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)
                TextField("Search reports...", text: $searchText)
                    .textFieldStyle(.plain)
            }
            .padding(8)
            .background(Color(NSColor.controlBackgroundColor))
            .cornerRadius(8)
            .frame(width: 250)

            // Type Filter
            Picker("Type", selection: $selectedType) {
                Text("All Types").tag(nil as ReportType?)
                ForEach(ReportType.allCases) { type in
                    Text(type.displayName).tag(type as ReportType?)
                }
            }
            .frame(width: 180)
        }
        .padding(24)
    }

    // MARK: - Report List
    private var reportList: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(filteredReports) { report in
                    ReportRow(report: report)
                }
            }
            .padding(24)
        }
    }

    // MARK: - Empty State
    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "doc.text.magnifyingglass")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("No Reports Found")
                .font(.title2)
                .fontWeight(.semibold)

            Text(searchText.isEmpty ? "Generate your first report from the New Audit page." : "No reports match your search.")
                .foregroundColor(.secondary)

            if searchText.isEmpty {
                Button(action: { appState.selectedTab = .audit }) {
                    Label("Create New Audit", systemImage: "plus")
                }
                .buttonStyle(.borderedProminent)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Report Row
struct ReportRow: View {
    let report: Report

    @State private var isHovering: Bool = false
    @State private var showPreview: Bool = false

    var body: some View {
        HStack(spacing: 16) {
            // Type Icon
            ZStack {
                RoundedRectangle(cornerRadius: 10)
                    .fill(report.type.color.opacity(0.15))
                    .frame(width: 48, height: 48)

                Image(systemName: report.type.icon)
                    .font(.title2)
                    .foregroundColor(report.type.color)
            }

            // Info
            VStack(alignment: .leading, spacing: 4) {
                Text(report.clientName)
                    .font(.headline)

                Text(report.type.displayName)
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                Text(report.date.formatted(date: .abbreviated, time: .shortened))
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            // Grade (if applicable)
            if let grade = report.grade {
                GradeIndicator(grade: grade)
            }

            // Value
            if let value = report.value {
                VStack(alignment: .trailing, spacing: 2) {
                    Text("Value")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("$\(value, specifier: "%.0f")")
                        .font(.headline)
                        .fontWeight(.bold)
                        .foregroundColor(.green)
                }
            }

            // Actions
            HStack(spacing: 8) {
                Button(action: { showPreview = true }) {
                    Image(systemName: "eye")
                }
                .buttonStyle(.borderless)
                .help("Preview")

                Button(action: { exportReport() }) {
                    Image(systemName: "square.and.arrow.up")
                }
                .buttonStyle(.borderless)
                .help("Export")

                Button(action: { openInFinder() }) {
                    Image(systemName: "folder")
                }
                .buttonStyle(.borderless)
                .help("Show in Finder")
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(NSColor.controlBackgroundColor))
                .shadow(color: isHovering ? .accentColor.opacity(0.2) : .clear, radius: 8)
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.2)) {
                isHovering = hovering
            }
        }
        .sheet(isPresented: $showPreview) {
            ReportPreviewSheet(report: report)
        }
    }

    private func exportReport() {
        let savePanel = NSSavePanel()
        savePanel.allowedContentTypes = [.pdf]
        savePanel.nameFieldStringValue = "\(report.clientName)_\(report.type.rawValue).pdf"

        savePanel.begin { response in
            if response == .OK, let url = savePanel.url {
                // Export logic
                if let pdfPath = report.pdfPath {
                    try? FileManager.default.copyItem(at: pdfPath, to: url)
                }
            }
        }
    }

    private func openInFinder() {
        if let path = report.filePath?.deletingLastPathComponent() {
            NSWorkspace.shared.selectFile(nil, inFileViewerRootedAtPath: path.path)
        }
    }
}

// MARK: - Grade Indicator
struct GradeIndicator: View {
    let grade: String

    var color: Color {
        switch grade.uppercased() {
        case "A", "A+", "A-": return .green
        case "B", "B+", "B-": return Color(red: 0.4, green: 0.7, blue: 0.2)
        case "C", "C+", "C-": return .yellow
        case "D", "D+", "D-": return .orange
        default: return .red
        }
    }

    var body: some View {
        ZStack {
            Circle()
                .fill(color.opacity(0.15))
                .frame(width: 48, height: 48)

            Text(grade)
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(color)
        }
    }
}

// MARK: - Report Preview Sheet
struct ReportPreviewSheet: View {
    let report: Report
    @Environment(\.dismiss) var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading) {
                    Text(report.clientName)
                        .font(.title2)
                        .fontWeight(.bold)

                    Text(report.type.displayName)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title2)
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding()

            Divider()

            // Content
            ScrollView {
                if let content = report.content {
                    Text(content)
                        .font(.system(.body, design: .monospaced))
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                } else {
                    Text("No content available")
                        .foregroundColor(.secondary)
                        .padding()
                }
            }

            Divider()

            // Footer
            HStack {
                Button("Close") {
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)

                Spacer()

                Button("Export PDF") {
                    // Export logic
                }
                .buttonStyle(.borderedProminent)
            }
            .padding()
        }
        .frame(width: 800, height: 600)
    }
}

#Preview {
    ReportsView()
        .environmentObject(AppState())
        .frame(width: 1000, height: 700)
}
