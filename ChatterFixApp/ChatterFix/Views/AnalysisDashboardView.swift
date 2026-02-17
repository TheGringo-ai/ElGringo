// AnalysisDashboardView.swift
// Comprehensive analysis dashboard with all tools

import SwiftUI
import Charts

struct AnalysisDashboardView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var analysisEngine = AnalysisEngine.shared
    @State private var selectedAnalysis: AnalysisType = .overview
    @State private var analysisResult: AnalysisResult?
    @State private var workOrderAnalysis: WorkOrderAnalysis?
    @State private var assetAnalysis: AssetAnalysis?
    @State private var isRunning = false
    @State private var errorMessage: String?

    var body: some View {
        HSplitView {
            // Left Panel - Analysis Selection
            analysisSelector
                .frame(minWidth: 250, maxWidth: 300)

            // Right Panel - Analysis Content
            analysisContent
        }
        .background(Color(NSColor.textBackgroundColor))
    }

    // MARK: - Analysis Selector
    private var analysisSelector: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            VStack(alignment: .leading, spacing: 8) {
                Text("Analysis Tools")
                    .font(.title2)
                    .fontWeight(.bold)

                Text("Maintenance Intelligence Suite")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding()

            Divider()

            // Tool List
            ScrollView {
                VStack(spacing: 4) {
                    ForEach(AnalysisType.allCases) { type in
                        AnalysisToolButton(
                            type: type,
                            isSelected: selectedAnalysis == type
                        ) {
                            selectedAnalysis = type
                        }
                    }
                }
                .padding()
            }

            Divider()

            // Quick Actions
            VStack(spacing: 8) {
                Button(action: runCompleteAnalysis) {
                    HStack {
                        Image(systemName: "bolt.fill")
                        Text("Run Complete Analysis")
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(!appState.companyData.hasWorkOrders || isRunning)

                Button(action: generateDeliverables) {
                    HStack {
                        Image(systemName: "shippingbox.fill")
                        Text("Generate Deliverables")
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .disabled(!appState.companyData.hasWorkOrders || isRunning)
            }
            .padding()

            // Progress
            if isRunning {
                VStack(spacing: 8) {
                    ProgressView(value: analysisEngine.analysisProgress)
                    Text(analysisEngine.currentStep)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding()
            }
        }
        .background(Color(NSColor.windowBackgroundColor))
    }

    // MARK: - Analysis Content
    @ViewBuilder
    private var analysisContent: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                switch selectedAnalysis {
                case .overview:
                    overviewContent
                case .dataQuality:
                    dataQualityContent
                case .workOrderEfficiency:
                    workOrderContent
                case .assetReliability:
                    assetReliabilityContent
                case .roiAnalysis:
                    roiContent
                case .mtbfPrediction:
                    mtbfContent
                case .executiveSummary:
                    executiveContent
                }
            }
            .padding(24)
        }
    }

    // MARK: - Overview Content
    private var overviewContent: some View {
        VStack(alignment: .leading, spacing: 24) {
            Text("Analysis Overview")
                .font(.largeTitle)
                .fontWeight(.bold)

            if let result = analysisResult {
                // Key Metrics
                LazyVGrid(columns: [
                    GridItem(.flexible()),
                    GridItem(.flexible()),
                    GridItem(.flexible()),
                    GridItem(.flexible())
                ], spacing: 16) {
                    KeyMetricCard(
                        title: "Data Grade",
                        value: result.dataAudit?.grade ?? "N/A",
                        subtitle: "GPA: \(String(format: "%.2f", result.dataAudit?.gpa ?? 0))",
                        color: gradeColor(result.dataAudit?.grade ?? "F")
                    )

                    KeyMetricCard(
                        title: "Total Spend",
                        value: "$\(formatLargeNumber(result.roiAnalysis?.totalSpend ?? 0))",
                        subtitle: "Maintenance costs",
                        color: .blue
                    )

                    KeyMetricCard(
                        title: "Savings Potential",
                        value: "$\(formatLargeNumber(result.roiAnalysis?.potentialSavings ?? 0))",
                        subtitle: "\(Int(result.roiAnalysis?.roi ?? 0))% ROI",
                        color: .green
                    )

                    KeyMetricCard(
                        title: "Failure Alerts",
                        value: "\(result.mtbfPrediction?.imminentFailures ?? 0)",
                        subtitle: "Within 7 days",
                        color: .red
                    )
                }
            } else {
                // Empty State
                VStack(spacing: 16) {
                    Image(systemName: "chart.bar.doc.horizontal")
                        .font(.system(size: 64))
                        .foregroundColor(.secondary)

                    Text("No Analysis Results")
                        .font(.title2)
                        .fontWeight(.semibold)

                    Text("Upload company data and run analysis to see insights")
                        .foregroundColor(.secondary)

                    if appState.companyData.hasWorkOrders {
                        Button("Run Complete Analysis") {
                            runCompleteAnalysis()
                        }
                        .buttonStyle(.borderedProminent)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(48)
            }

            // Quick Insights
            if let result = analysisResult {
                Divider()

                Text("Key Insights")
                    .font(.title2)
                    .fontWeight(.semibold)

                VStack(alignment: .leading, spacing: 12) {
                    InsightRow(
                        icon: "exclamationmark.triangle.fill",
                        color: .red,
                        title: "Critical Finding",
                        description: "Your data shows \(Int(result.dataAudit?.redundancyPercent ?? 0))% redundancy - records are being duplicated or split."
                    )

                    InsightRow(
                        icon: "dollarsign.circle.fill",
                        color: .green,
                        title: "Savings Opportunity",
                        description: "Implementing recommendations could save $\(formatLargeNumber(result.roiAnalysis?.potentialSavings ?? 0)) annually."
                    )

                    InsightRow(
                        icon: "clock.badge.exclamationmark.fill",
                        color: .orange,
                        title: "Failure Risk",
                        description: "\(result.mtbfPrediction?.imminentFailures ?? 0) assets are predicted to fail within the next 7 days."
                    )
                }
            }
        }
    }

    // MARK: - Data Quality Content
    private var dataQualityContent: some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Data Quality Audit")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text("GPA scoring and redundancy analysis")
                        .foregroundColor(.secondary)
                }

                Spacer()

                Button("Run Audit") {
                    runDataAudit()
                }
                .buttonStyle(.borderedProminent)
                .disabled(!appState.companyData.hasWorkOrders || isRunning)
            }

            if let audit = analysisResult?.dataAudit {
                // Grade Display
                HStack(spacing: 32) {
                    // Grade Circle
                    ZStack {
                        Circle()
                            .stroke(gradeColor(audit.grade).opacity(0.3), lineWidth: 20)
                            .frame(width: 150, height: 150)

                        Circle()
                            .trim(from: 0, to: audit.gpa / 4.0)
                            .stroke(gradeColor(audit.grade), style: StrokeStyle(lineWidth: 20, lineCap: .round))
                            .frame(width: 150, height: 150)
                            .rotationEffect(.degrees(-90))

                        VStack {
                            Text(audit.grade)
                                .font(.system(size: 48, weight: .bold))
                                .foregroundColor(gradeColor(audit.grade))

                            Text("GPA: \(String(format: "%.2f", audit.gpa))")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }

                    // Metrics
                    VStack(alignment: .leading, spacing: 16) {
                        QualityMetric(label: "Redundancy", value: "\(Int(audit.redundancyPercent))%", status: audit.redundancyPercent > 50 ? .bad : .good)
                        QualityMetric(label: "Total Rows", value: "\(audit.totalRows)", status: .neutral)
                        QualityMetric(label: "Unique Records", value: "\(audit.uniqueRows)", status: .neutral)
                    }
                }
                .padding()
                .background(Color(NSColor.controlBackgroundColor))
                .cornerRadius(12)

                // Explanation
                VStack(alignment: .leading, spacing: 8) {
                    Text("What This Means")
                        .font(.headline)

                    Text("""
                    A grade of **\(audit.grade)** indicates that your maintenance data has significant quality issues. \
                    With **\(Int(audit.redundancyPercent))%** redundancy, you have partial records that should be merged. \
                    This affects the accuracy of all downstream reports and cost calculations.
                    """)
                    .foregroundColor(.secondary)
                }
                .padding()
                .background(Color(NSColor.controlBackgroundColor))
                .cornerRadius(12)
            }
        }
    }

    // MARK: - Work Order Content
    private var workOrderContent: some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Work Order Efficiency")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text("Group by Work Order Number - The 'Efficiency' View")
                        .foregroundColor(.secondary)
                }

                Spacer()

                Button("Analyze") {
                    runWorkOrderAnalysis()
                }
                .buttonStyle(.borderedProminent)
                .disabled(!appState.companyData.hasWorkOrders || isRunning)
            }

            if let wo = workOrderAnalysis {
                HStack(spacing: 16) {
                    AnalysisMetricCard(
                        title: "Raw Rows",
                        value: "\(wo.totalRows.formatted())",
                        icon: "doc.text"
                    )

                    AnalysisMetricCard(
                        title: "Unique Work Orders",
                        value: "\(wo.uniqueWorkOrders.formatted())",
                        icon: "checkmark.seal"
                    )

                    AnalysisMetricCard(
                        title: "Reduction",
                        value: "\(Int(wo.reductionPercent))%",
                        icon: "arrow.down.right"
                    )

                    AnalysisMetricCard(
                        title: "Total Cost",
                        value: "$\(formatLargeNumber(wo.totalCost))",
                        icon: "dollarsign.circle"
                    )
                }

                // Explanation
                VStack(alignment: .leading, spacing: 12) {
                    Text("The Efficiency View")
                        .font(.headline)

                    Text("""
                    By collapsing \(wo.totalRows.formatted()) rows into \(wo.uniqueWorkOrders.formatted()) unique Work Orders, \
                    we see the actual workload. The **\(Int(wo.reductionPercent))% reduction** shows how much \
                    redundancy existed in your raw data.

                    **Why companies pay for this:** This view catches "fat-finger" data entry errors \
                    and extreme cost outliers before they hit the year-end budget report.
                    """)
                    .foregroundColor(.secondary)
                }
                .padding()
                .background(Color(NSColor.controlBackgroundColor))
                .cornerRadius(12)
            }
        }
    }

    // MARK: - Asset Reliability Content
    private var assetReliabilityContent: some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Asset Reliability")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text("Group by Asset ID - The 'Money Pit' View")
                        .foregroundColor(.secondary)
                }

                Spacer()

                Button("Find Money Pits") {
                    runAssetAnalysis()
                }
                .buttonStyle(.borderedProminent)
                .disabled(!appState.companyData.hasWorkOrders || isRunning)
            }

            if let assets = assetAnalysis {
                // Summary Stats
                HStack(spacing: 16) {
                    AnalysisMetricCard(
                        title: "Total Assets",
                        value: "\(assets.totalAssets)",
                        icon: "gearshape.2"
                    )

                    AnalysisMetricCard(
                        title: "Total Spend",
                        value: "$\(formatLargeNumber(assets.totalCost))",
                        icon: "dollarsign.circle"
                    )

                    AnalysisMetricCard(
                        title: "Top 10 Cost",
                        value: "$\(formatLargeNumber(assets.top10Cost))",
                        icon: "flame"
                    )

                    AnalysisMetricCard(
                        title: "Budget Share",
                        value: "\(Int(assets.top10Percent))%",
                        icon: "chart.pie"
                    )
                }

                // Money Pits Table
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("Top 10 Money Pits")
                            .font(.headline)

                        Spacer()

                        Text("These \(assets.moneyPits.count) assets consume \(Int(assets.top10Percent))% of your budget")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    // Table
                    VStack(spacing: 0) {
                        // Header
                        HStack {
                            Text("Asset ID")
                                .fontWeight(.semibold)
                                .frame(width: 120, alignment: .leading)
                            Text("Description")
                                .fontWeight(.semibold)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            Text("Work Orders")
                                .fontWeight(.semibold)
                                .frame(width: 100, alignment: .trailing)
                            Text("Total Cost")
                                .fontWeight(.semibold)
                                .frame(width: 120, alignment: .trailing)
                        }
                        .padding(.vertical, 8)
                        .padding(.horizontal, 12)
                        .background(Color(NSColor.controlBackgroundColor))

                        // Rows
                        ForEach(assets.moneyPits) { asset in
                            HStack {
                                Text(asset.assetId)
                                    .frame(width: 120, alignment: .leading)
                                    .lineLimit(1)
                                Text(asset.description)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .lineLimit(1)
                                    .foregroundColor(.secondary)
                                Text("\(asset.workOrderCount)")
                                    .frame(width: 100, alignment: .trailing)
                                Text("$\(formatLargeNumber(asset.totalCost))")
                                    .frame(width: 120, alignment: .trailing)
                                    .foregroundColor(.red)
                                    .fontWeight(.medium)
                            }
                            .padding(.vertical, 8)
                            .padding(.horizontal, 12)

                            Divider()
                        }
                    }
                    .background(Color(NSColor.textBackgroundColor))
                    .cornerRadius(8)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
                    )
                }
                .padding()
                .background(Color(NSColor.controlBackgroundColor))
                .cornerRadius(12)

                // Recommendation
                VStack(alignment: .leading, spacing: 8) {
                    Text("Replace vs. Repair Analysis")
                        .font(.headline)

                    if let topAsset = assets.moneyPits.first {
                        Text("""
                        **\(topAsset.assetId)** has cost **$\(formatLargeNumber(topAsset.totalCost))** across \
                        **\(topAsset.workOrderCount)** work orders. If the machine's initial value was less than \
                        this amount, you should consider replacement. Stop fixing this; buy a new one.
                        """)
                        .foregroundColor(.secondary)
                    }
                }
                .padding()
                .background(Color.red.opacity(0.1))
                .cornerRadius(12)
            }
        }
    }

    // MARK: - ROI Content
    private var roiContent: some View {
        VStack(alignment: .leading, spacing: 24) {
            Text("ROI Analysis")
                .font(.largeTitle)
                .fontWeight(.bold)

            if let roi = analysisResult?.roiAnalysis {
                // Key Metrics
                HStack(spacing: 16) {
                    ROIMetricCard(
                        title: "Total Maintenance Spend",
                        value: "$\(formatLargeNumber(roi.totalSpend))",
                        color: .blue
                    )

                    ROIMetricCard(
                        title: "Potential Savings",
                        value: "$\(formatLargeNumber(roi.potentialSavings))",
                        color: .green
                    )

                    ROIMetricCard(
                        title: "ROI",
                        value: "\(Int(roi.roi))%",
                        color: .purple
                    )

                    ROIMetricCard(
                        title: "Payback Period",
                        value: "\(roi.paybackMonths) months",
                        color: .orange
                    )
                }

                // The Hook
                VStack(alignment: .leading, spacing: 8) {
                    Text("The Sales Hook")
                        .font(.headline)

                    Text("""
                    "Invest $\(formatLargeNumber(roi.potentialSavings * 0.1)) to save $\(formatLargeNumber(roi.potentialSavings)) over 3 years. \
                    Payback period: \(roi.paybackMonths) months. ROI: \(Int(roi.roi))%."
                    """)
                    .font(.title3)
                    .italic()
                    .padding()
                    .background(Color.green.opacity(0.1))
                    .cornerRadius(8)
                }
                .padding()
                .background(Color(NSColor.controlBackgroundColor))
                .cornerRadius(12)
            } else {
                Text("Run complete analysis to see ROI calculations")
                    .foregroundColor(.secondary)
            }
        }
    }

    // MARK: - MTBF Content
    private var mtbfContent: some View {
        VStack(alignment: .leading, spacing: 24) {
            Text("MTBF Failure Predictions")
                .font(.largeTitle)
                .fontWeight(.bold)

            if let mtbf = analysisResult?.mtbfPrediction {
                HStack(spacing: 16) {
                    AnalysisMetricCard(
                        title: "Imminent Failures",
                        value: "\(mtbf.imminentFailures)",
                        icon: "exclamationmark.triangle.fill",
                        iconColor: .red
                    )

                    AnalysisMetricCard(
                        title: "Avg MTBF",
                        value: "\(mtbf.averageMTBF) days",
                        icon: "clock"
                    )

                    AnalysisMetricCard(
                        title: "30-Day Risk",
                        value: "$\(formatLargeNumber(mtbf.projectedCost30Days))",
                        icon: "dollarsign.circle"
                    )
                }

                // Alert Box
                if mtbf.imminentFailures > 0 {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundColor(.red)
                            Text("Critical Alert")
                                .font(.headline)
                                .foregroundColor(.red)
                        }

                        Text("""
                        **\(mtbf.imminentFailures) assets** are predicted to fail within the next 7 days. \
                        Unplanned downtime costs significantly more than preventive maintenance.
                        """)
                    }
                    .padding()
                    .background(Color.red.opacity(0.1))
                    .cornerRadius(12)
                }
            }
        }
    }

    // MARK: - Executive Content
    private var executiveContent: some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack {
                Text("Executive Summary")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Spacer()

                if let pdfPath = analysisResult?.pdfPath {
                    Button("Open PDF") {
                        NSWorkspace.shared.open(pdfPath)
                    }
                    .buttonStyle(.borderedProminent)
                }
            }

            if let exec = analysisResult?.executiveSummary {
                ScrollView {
                    Text(exec.content)
                        .font(.system(.body, design: .monospaced))
                        .padding()
                }
                .background(Color(NSColor.controlBackgroundColor))
                .cornerRadius(12)
            }
        }
    }

    // MARK: - Actions

    private func runCompleteAnalysis() {
        guard let path = appState.companyData.workOrdersPath else { return }

        isRunning = true
        errorMessage = nil

        Task {
            do {
                let result = try await analysisEngine.runCompleteAnalysis(
                    csvPath: path,
                    companyName: appState.selectedClient?.name ?? "Analysis"
                )

                await MainActor.run {
                    self.analysisResult = result
                    self.isRunning = false
                }
            } catch {
                await MainActor.run {
                    self.errorMessage = error.localizedDescription
                    self.isRunning = false
                }
            }
        }
    }

    private func generateDeliverables() {
        guard let path = appState.companyData.workOrdersPath else { return }

        isRunning = true

        Task {
            do {
                let result = try await analysisEngine.generateDeliverables(
                    csvPath: path,
                    companyName: appState.selectedClient?.name ?? "Analysis"
                )

                await MainActor.run {
                    self.isRunning = false
                    // Open folder in Finder
                    NSWorkspace.shared.selectFile(nil, inFileViewerRootedAtPath: result.outputDirectory.path)
                }
            } catch {
                await MainActor.run {
                    self.errorMessage = error.localizedDescription
                    self.isRunning = false
                }
            }
        }
    }

    private func runDataAudit() {
        guard let path = appState.companyData.workOrdersPath else {
            errorMessage = "No data loaded. Please upload a CSV file first."
            return
        }

        isRunning = true
        errorMessage = nil

        Task {
            do {
                let auditResult = try await analysisEngine.runDataAudit(
                    csvPath: path,
                    companyName: appState.selectedClient?.name ?? "Analysis"
                )

                await MainActor.run {
                    // Update the analysis result with the audit data
                    if self.analysisResult == nil {
                        var newResult = AnalysisResult(companyName: appState.selectedClient?.name ?? "Analysis")
                        newResult.dataAudit = auditResult
                        self.analysisResult = newResult
                    } else {
                        self.analysisResult?.dataAudit = auditResult
                    }
                    self.isRunning = false
                }
            } catch {
                await MainActor.run {
                    self.errorMessage = "Audit failed: \(error.localizedDescription)"
                    self.isRunning = false
                }
            }
        }
    }

    private func runWorkOrderAnalysis() {
        guard let path = appState.companyData.workOrdersPath else { return }

        isRunning = true

        Task {
            do {
                let result = try await analysisEngine.analyzeByWorkOrder(csvPath: path)
                await MainActor.run {
                    self.workOrderAnalysis = result
                    self.isRunning = false
                }
            } catch {
                await MainActor.run {
                    self.isRunning = false
                }
            }
        }
    }

    private func runAssetAnalysis() {
        guard let path = appState.companyData.workOrdersPath else { return }

        isRunning = true

        Task {
            do {
                let result = try await analysisEngine.analyzeByAsset(csvPath: path)
                await MainActor.run {
                    self.assetAnalysis = result
                    self.isRunning = false
                }
            } catch {
                await MainActor.run {
                    self.isRunning = false
                }
            }
        }
    }

    // MARK: - Helpers

    private func gradeColor(_ grade: String) -> Color {
        switch grade.uppercased().prefix(1) {
        case "A": return .green
        case "B": return Color(red: 0.4, green: 0.7, blue: 0.2)
        case "C": return .yellow
        case "D": return .orange
        default: return .red
        }
    }

    private func formatLargeNumber(_ number: Double) -> String {
        if number >= 1_000_000 {
            return String(format: "%.1fM", number / 1_000_000)
        } else if number >= 1_000 {
            return String(format: "%.0fK", number / 1_000)
        } else {
            return String(format: "%.0f", number)
        }
    }
}

// MARK: - Analysis Types

enum AnalysisType: String, CaseIterable, Identifiable {
    case overview = "Overview"
    case dataQuality = "Data Quality"
    case workOrderEfficiency = "Work Orders"
    case assetReliability = "Asset Reliability"
    case roiAnalysis = "ROI Analysis"
    case mtbfPrediction = "MTBF Predictions"
    case executiveSummary = "Executive Summary"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .overview: return "chart.bar.xaxis"
        case .dataQuality: return "checkmark.seal"
        case .workOrderEfficiency: return "doc.text.magnifyingglass"
        case .assetReliability: return "gearshape.2"
        case .roiAnalysis: return "dollarsign.circle"
        case .mtbfPrediction: return "exclamationmark.triangle"
        case .executiveSummary: return "doc.richtext"
        }
    }

    var description: String {
        switch self {
        case .overview: return "Complete analysis overview"
        case .dataQuality: return "GPA score & redundancy"
        case .workOrderEfficiency: return "Group by Work Order"
        case .assetReliability: return "Find Money Pits"
        case .roiAnalysis: return "Savings calculator"
        case .mtbfPrediction: return "Failure forecasts"
        case .executiveSummary: return "90-day action plan"
        }
    }
}

// MARK: - Supporting Views

struct AnalysisToolButton: View {
    let type: AnalysisType
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: type.icon)
                    .frame(width: 24)
                    .foregroundColor(isSelected ? .white : .accentColor)

                VStack(alignment: .leading, spacing: 2) {
                    Text(type.rawValue)
                        .fontWeight(isSelected ? .semibold : .regular)
                    Text(type.description)
                        .font(.caption2)
                        .foregroundColor(isSelected ? .white.opacity(0.8) : .secondary)
                }

                Spacer()
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.accentColor : Color.clear)
            )
            .foregroundColor(isSelected ? .white : .primary)
        }
        .buttonStyle(.plain)
    }
}

struct KeyMetricCard: View {
    let title: String
    let value: String
    let subtitle: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)

            Text(value)
                .font(.title)
                .fontWeight(.bold)
                .foregroundColor(color)

            Text(subtitle)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(12)
    }
}

struct AnalysisMetricCard: View {
    let title: String
    let value: String
    let icon: String
    var iconColor: Color = .accentColor

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(iconColor)

            Text(value)
                .font(.title2)
                .fontWeight(.bold)

            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(12)
    }
}

struct ROIMetricCard: View {
    let title: String
    let value: String
    let color: Color

    var body: some View {
        VStack(spacing: 8) {
            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)

            Text(value)
                .font(.title)
                .fontWeight(.bold)
                .foregroundColor(color)
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(12)
    }
}

struct QualityMetric: View {
    let label: String
    let value: String
    let status: MetricStatus

    enum MetricStatus {
        case good, bad, neutral

        var color: Color {
            switch self {
            case .good: return .green
            case .bad: return .red
            case .neutral: return .primary
            }
        }
    }

    var body: some View {
        HStack {
            Text(label)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .fontWeight(.semibold)
                .foregroundColor(status.color)
        }
    }
}

struct InsightRow: View {
    let icon: String
    let color: Color
    let title: String
    let description: String

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(color)
                .font(.title3)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .fontWeight(.semibold)
                Text(description)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        .background(color.opacity(0.1))
        .cornerRadius(8)
    }
}

#Preview {
    AnalysisDashboardView()
        .environmentObject(AppState())
        .frame(width: 1200, height: 800)
}
