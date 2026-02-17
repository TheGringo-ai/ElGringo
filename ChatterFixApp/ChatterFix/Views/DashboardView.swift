// DashboardView.swift
// Main dashboard with metrics and service cards

import SwiftUI
import Charts

struct DashboardView: View {
    @EnvironmentObject var appState: AppState
    @State private var revenueData: [RevenuePoint] = RevenuePoint.sampleData
    @State private var clients: [Client] = []
    @State private var reports: [Report] = []

    private var totalRevenue: Double {
        clients.reduce(0) { $0 + $1.totalRevenue }
    }

    private var activeClients: Int {
        clients.filter { $0.status == .active }.count
    }

    private var reportsCount: Int {
        reports.count
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // Header
                header

                // Metrics Row
                metricsRow

                Divider()

                // Service Offerings
                serviceOfferings

                Divider()

                // Bottom Row
                HStack(alignment: .top, spacing: 24) {
                    recentProjects
                    revenueTrend
                }
            }
            .padding(24)
        }
        .background(Color(NSColor.textBackgroundColor))
        .onAppear {
            loadData()
        }
    }

    private func loadData() {
        clients = DataManager.shared.loadClients() ?? []
        reports = DataManager.shared.loadReports()
    }

    // MARK: - Header
    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Business Intelligence Dashboard")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("Maintenance cost optimization powered by AI")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
    }

    // MARK: - Metrics Row
    private var metricsRow: some View {
        HStack(spacing: 16) {
            MetricCard(
                title: "Total Clients",
                value: "\(clients.count)",
                change: "\(activeClients) active",
                isPositive: true,
                icon: "person.2.fill"
            )

            MetricCard(
                title: "Total Revenue",
                value: "$\(formatNumber(totalRevenue))",
                change: clients.isEmpty ? "No clients yet" : "From \(clients.count) clients",
                isPositive: totalRevenue > 0,
                icon: "dollarsign.circle.fill"
            )

            MetricCard(
                title: "Reports Generated",
                value: "\(reportsCount)",
                change: reports.isEmpty ? "Run an audit" : "View in Reports tab",
                isPositive: reportsCount > 0,
                icon: "doc.text.fill"
            )

            MetricCard(
                title: "Data Files",
                value: "\(countDataFiles())",
                change: "Across all clients",
                isPositive: true,
                icon: "folder.fill"
            )
        }
    }

    private func formatNumber(_ value: Double) -> String {
        if value >= 1000000 {
            return String(format: "%.1fM", value / 1000000)
        } else if value >= 1000 {
            return String(format: "%.0fK", value / 1000)
        } else {
            return String(format: "%.0f", value)
        }
    }

    private func countDataFiles() -> Int {
        var total = 0
        for client in clients {
            let stats = CompanyDataManager.shared.getStatistics(for: client.id)
            total += stats.totalUploads
        }
        return total
    }

    // MARK: - Service Offerings
    private var serviceOfferings: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Service Offerings")
                .font(.title2)
                .fontWeight(.semibold)

            HStack(spacing: 16) {
                ServiceCard(
                    title: "Initial Audit & Clean",
                    price: "$5,000 - $10,000",
                    icon: "magnifyingglass",
                    color: .blue,
                    features: [
                        "Data quality assessment (GPA score)",
                        "Duplicate detection & cleanup",
                        "Asset health analysis",
                        "Quick wins identification"
                    ]
                ) {
                    withAnimation {
                        appState.selectedTab = .audit
                    }
                }

                ServiceCard(
                    title: "Strategy Roadmap",
                    price: "$15,000",
                    icon: "map.fill",
                    color: .purple,
                    features: [
                        "ROI analysis (Money Pit report)",
                        "MTBF failure predictions",
                        "90-day action plan",
                        "Executive presentation deck"
                    ]
                ) {
                    withAnimation {
                        appState.selectedTab = .audit
                    }
                }

                ServiceCard(
                    title: "Annual Subscription",
                    price: "$25,000/year",
                    icon: "chart.bar.fill",
                    color: .green,
                    features: [
                        "Monthly automated reports",
                        "Real-time failure alerts",
                        "Continuous optimization",
                        "Priority support"
                    ]
                ) {
                    withAnimation {
                        appState.selectedTab = .audit
                    }
                }
            }
        }
    }

    // MARK: - Recent Projects
    private var recentProjects: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Recent Clients")
                .font(.title3)
                .fontWeight(.semibold)

            if clients.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "person.2.slash")
                        .font(.title)
                        .foregroundColor(.secondary)
                    Text("No clients yet")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Button("Add Client") {
                        appState.selectedTab = .clients
                    }
                    .buttonStyle(.bordered)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
            } else {
                VStack(spacing: 8) {
                    ForEach(clients.prefix(5)) { client in
                        ProjectRow(
                            client: client.name,
                            type: client.industry.isEmpty ? "Client" : client.industry,
                            status: client.status.rawValue,
                            amount: "$\(formatNumber(client.totalRevenue))"
                        )
                    }
                }
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(12)
        .frame(maxWidth: .infinity)
    }

    // MARK: - Revenue Trend
    private var revenueTrend: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Revenue Trend")
                .font(.title3)
                .fontWeight(.semibold)

            Chart(revenueData) { point in
                LineMark(
                    x: .value("Month", point.month),
                    y: .value("Revenue", point.revenue)
                )
                .foregroundStyle(
                    LinearGradient(
                        colors: [.blue, .purple],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )

                AreaMark(
                    x: .value("Month", point.month),
                    y: .value("Revenue", point.revenue)
                )
                .foregroundStyle(
                    LinearGradient(
                        colors: [.blue.opacity(0.3), .purple.opacity(0.1)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )

                PointMark(
                    x: .value("Month", point.month),
                    y: .value("Revenue", point.revenue)
                )
                .foregroundStyle(.blue)
            }
            .chartYAxis {
                AxisMarks(position: .leading) { value in
                    AxisValueLabel {
                        if let revenue = value.as(Double.self) {
                            Text("$\(Int(revenue / 1000))k")
                        }
                    }
                }
            }
            .frame(height: 200)
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(12)
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Metric Card
struct MetricCard: View {
    let title: String
    let value: String
    let change: String
    let isPositive: Bool
    let icon: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundStyle(
                        LinearGradient(
                            colors: [.blue, .purple],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                Spacer()
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(value)
                    .font(.title)
                    .fontWeight(.bold)

                Text(title)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            HStack(spacing: 4) {
                Image(systemName: isPositive ? "arrow.up.right" : "arrow.down.right")
                    .font(.caption2)
                Text(change)
                    .font(.caption)
            }
            .foregroundColor(isPositive ? .green : .red)
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(12)
    }
}

// MARK: - Service Card
struct ServiceCard: View {
    let title: String
    let price: String
    let icon: String
    let color: Color
    let features: [String]
    let action: () -> Void

    @State private var isHovering = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: icon)
                    .font(.title)
                    .foregroundColor(color)

                Spacer()
            }

            Text(title)
                .font(.headline)

            Text(price)
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(.green)

            VStack(alignment: .leading, spacing: 6) {
                ForEach(features, id: \.self) { feature in
                    HStack(alignment: .top, spacing: 8) {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.caption)
                            .foregroundColor(color)
                        Text(feature)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()

            Button(action: action) {
                Text("Get Started")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
            }
            .buttonStyle(.borderedProminent)
            .tint(color)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(NSColor.controlBackgroundColor))
                .shadow(color: isHovering ? color.opacity(0.3) : .clear, radius: 8)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isHovering ? color.opacity(0.5) : Color.clear, lineWidth: 2)
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.2)) {
                isHovering = hovering
            }
        }
    }
}

// MARK: - Project Row
struct ProjectRow: View {
    let client: String
    let type: String
    let status: String
    let amount: String

    var statusColor: Color {
        switch status.lowercased() {
        case "completed": return .blue
        case "in progress": return .orange
        case "active": return .green
        default: return .secondary
        }
    }

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(client)
                    .fontWeight(.medium)
                Text(type)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            Text(status)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(statusColor)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(statusColor.opacity(0.15))
                .cornerRadius(4)

            Text(amount)
                .font(.subheadline)
                .fontWeight(.semibold)
                .frame(width: 80, alignment: .trailing)
        }
        .padding(.vertical, 8)
    }
}

// MARK: - Revenue Data Model
struct RevenuePoint: Identifiable {
    let id = UUID()
    let month: String
    let revenue: Double

    static let sampleData: [RevenuePoint] = [
        RevenuePoint(month: "Jan", revenue: 15000),
        RevenuePoint(month: "Feb", revenue: 22500),
        RevenuePoint(month: "Mar", revenue: 35000),
        RevenuePoint(month: "Apr", revenue: 42000),
        RevenuePoint(month: "May", revenue: 55000),
        RevenuePoint(month: "Jun", revenue: 67500)
    ]
}

#Preview {
    DashboardView()
        .environmentObject(AppState())
        .frame(width: 1000, height: 800)
}
