// ClientsView.swift
// Client management view

import SwiftUI

struct ClientsView: View {
    @EnvironmentObject var appState: AppState
    @State private var searchText: String = ""
    @State private var showAddClient: Bool = false
    @State private var selectedFilter: ClientFilter = .all
    @State private var selectedClientForData: Client?
    @State private var showDataManager: Bool = false

    var filteredClients: [Client] {
        var clients = DataManager.shared.loadClients() ?? []

        if !searchText.isEmpty {
            clients = clients.filter { $0.name.localizedCaseInsensitiveContains(searchText) }
        }

        switch selectedFilter {
        case .all:
            break
        case .active:
            clients = clients.filter { $0.status == .active }
        case .prospect:
            clients = clients.filter { $0.status == .prospect }
        }

        return clients
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            // Content
            if filteredClients.isEmpty {
                emptyState
            } else {
                clientList
            }
        }
        .background(Color(NSColor.textBackgroundColor))
        .sheet(isPresented: $showAddClient) {
            AddClientSheet()
        }
        .sheet(isPresented: $showDataManager) {
            if let client = selectedClientForData {
                ClientDataView(client: client)
                    .environmentObject(appState)
                    .frame(width: 1000, height: 700)
            }
        }
    }

    // MARK: - Header
    private var header: some View {
        HStack(spacing: 16) {
            Text("Clients")
                .font(.largeTitle)
                .fontWeight(.bold)

            Spacer()

            // Search
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)
                TextField("Search clients...", text: $searchText)
                    .textFieldStyle(.plain)
            }
            .padding(8)
            .background(Color(NSColor.controlBackgroundColor))
            .cornerRadius(8)
            .frame(width: 250)

            // Filter
            Picker("Filter", selection: $selectedFilter) {
                ForEach(ClientFilter.allCases) { filter in
                    Text(filter.rawValue).tag(filter)
                }
            }
            .pickerStyle(.segmented)
            .frame(width: 200)

            // Add Button
            Button(action: { showAddClient = true }) {
                Label("Add Client", systemImage: "plus")
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(24)
    }

    // MARK: - Client List
    private var clientList: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(filteredClients) { client in
                    ClientRow(
                        client: client,
                        onSelect: {
                            appState.selectedClient = client
                            appState.selectedTab = .audit
                        },
                        onManageData: {
                            selectedClientForData = client
                            showDataManager = true
                        },
                        onRunAnalysis: {
                            appState.selectedClient = client
                            appState.selectedTab = .analysis
                        }
                    )
                }
            }
            .padding(24)
        }
    }

    // MARK: - Empty State
    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "person.2.slash")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("No Clients Found")
                .font(.title2)
                .fontWeight(.semibold)

            Text(searchText.isEmpty ? "Add your first client to get started." : "No clients match your search.")
                .foregroundColor(.secondary)

            if searchText.isEmpty {
                Button(action: { showAddClient = true }) {
                    Label("Add Client", systemImage: "plus")
                }
                .buttonStyle(.borderedProminent)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Client Row
struct ClientRow: View {
    let client: Client
    let onSelect: () -> Void
    let onManageData: () -> Void
    let onRunAnalysis: () -> Void

    @State private var isHovering: Bool = false
    @State private var statistics: CompanyStatistics = CompanyStatistics()

    var body: some View {
        HStack(spacing: 16) {
            // Avatar
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [.blue, .purple],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 48, height: 48)

                Text(client.initials)
                    .font(.headline)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
            }

            // Info
            VStack(alignment: .leading, spacing: 4) {
                Text(client.name)
                    .font(.headline)

                HStack(spacing: 12) {
                    if !client.industry.isEmpty {
                        Label(client.industry, systemImage: "building.2")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    if !client.email.isEmpty {
                        Label(client.email, systemImage: "envelope")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()

            // Data Status
            VStack(alignment: .center, spacing: 4) {
                Text("Data Files")
                    .font(.caption)
                    .foregroundColor(.secondary)

                HStack(spacing: 4) {
                    if statistics.hasData {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                            .font(.caption)
                        Text("\(statistics.totalUploads)")
                            .font(.headline)
                            .fontWeight(.bold)
                    } else {
                        Image(systemName: "exclamationmark.circle")
                            .foregroundColor(.orange)
                            .font(.caption)
                        Text("None")
                            .font(.caption)
                            .foregroundColor(.orange)
                    }
                }
            }
            .frame(width: 70)

            // Records
            VStack(alignment: .center, spacing: 4) {
                Text("Records")
                    .font(.caption)
                    .foregroundColor(.secondary)

                Text("\(totalRecords)")
                    .font(.headline)
                    .fontWeight(.bold)
            }
            .frame(width: 70)

            // Revenue
            VStack(alignment: .trailing, spacing: 4) {
                Text("Revenue")
                    .font(.caption)
                    .foregroundColor(.secondary)

                Text("$\(client.totalRevenue, specifier: "%.0f")")
                    .font(.headline)
                    .fontWeight(.bold)
            }
            .frame(width: 80)

            // Status Badge
            StatusBadge(status: client.status)

            // Actions
            HStack(spacing: 8) {
                Button {
                    onManageData()
                } label: {
                    Label("Data", systemImage: "folder.fill")
                }
                .buttonStyle(.bordered)

                if statistics.hasData {
                    Button {
                        onRunAnalysis()
                    } label: {
                        Label("Analyze", systemImage: "chart.bar.fill")
                    }
                    .buttonStyle(.borderedProminent)
                }

                Button("Audit") {
                    onSelect()
                }
                .buttonStyle(.bordered)
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(NSColor.controlBackgroundColor))
                .shadow(color: isHovering ? .accentColor.opacity(0.2) : .clear, radius: 8)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isHovering ? Color.accentColor.opacity(0.3) : Color.clear, lineWidth: 1)
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.2)) {
                isHovering = hovering
            }
        }
        .onAppear {
            statistics = CompanyDataManager.shared.getStatistics(for: client.id)
        }
    }

    private var totalRecords: Int {
        statistics.totalWorkOrders + statistics.totalAssets +
        statistics.totalInventoryItems + statistics.totalParts
    }
}

// MARK: - Status Badge
struct StatusBadge: View {
    let status: ClientStatus

    var color: Color {
        switch status {
        case .active: return .green
        case .prospect: return .orange
        case .churned: return .red
        }
    }

    var body: some View {
        Text(status.rawValue)
            .font(.caption)
            .fontWeight(.medium)
            .foregroundColor(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(color.opacity(0.15))
            .cornerRadius(4)
    }
}

// MARK: - Add Client Sheet
struct AddClientSheet: View {
    @Environment(\.dismiss) var dismiss
    @State private var name: String = ""
    @State private var contact: String = ""
    @State private var email: String = ""
    @State private var phone: String = ""
    @State private var industry: String = "Manufacturing"
    @State private var notes: String = ""

    let industries = ["Manufacturing", "Food & Beverage", "Healthcare", "Energy", "Transportation", "Other"]

    var body: some View {
        VStack(spacing: 24) {
            Text("Add New Client")
                .font(.title2)
                .fontWeight(.bold)

            Form {
                Section("Company Information") {
                    TextField("Company Name *", text: $name)
                    Picker("Industry", selection: $industry) {
                        ForEach(industries, id: \.self) { Text($0) }
                    }
                }

                Section("Contact Information") {
                    TextField("Contact Name", text: $contact)
                    TextField("Email", text: $email)
                    TextField("Phone", text: $phone)
                }

                Section("Notes") {
                    TextEditor(text: $notes)
                        .frame(height: 80)
                }
            }
            .formStyle(.grouped)

            HStack {
                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)

                Spacer()

                Button("Add Client") {
                    saveClient()
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
                .buttonStyle(.borderedProminent)
                .disabled(name.isEmpty)
            }
        }
        .padding(24)
        .frame(width: 500)
    }

    private func saveClient() {
        let client = Client(
            name: name,
            contact: contact,
            email: email,
            phone: phone,
            industry: industry,
            notes: notes
        )
        DataManager.shared.saveClient(client)
    }
}

// MARK: - Client Filter
enum ClientFilter: String, CaseIterable, Identifiable {
    case all = "All"
    case active = "Active"
    case prospect = "Prospect"

    var id: String { rawValue }
}

#Preview {
    ClientsView()
        .environmentObject(AppState())
        .frame(width: 1000, height: 700)
}
