// AIAssistantView.swift
// On-device AI assistant powered by MLX

import SwiftUI

struct AIAssistantView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var mlxEngine = MLXEngine.shared
    @State private var messages: [ChatMessage] = []
    @State private var inputText: String = ""
    @State private var isAnalyzing: Bool = false
    @State private var selectedMode: AssistantMode = .chat

    var body: some View {
        HSplitView {
            // Main Chat Area
            VStack(spacing: 0) {
                // Header
                header

                Divider()

                // Messages
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 16) {
                            ForEach(messages) { message in
                                MessageBubble(message: message)
                                    .id(message.id)
                            }

                            if mlxEngine.isProcessing {
                                TypingIndicator()
                            }
                        }
                        .padding()
                    }
                    .onChange(of: messages.count) { _ in
                        if let last = messages.last {
                            withAnimation {
                                proxy.scrollTo(last.id, anchor: .bottom)
                            }
                        }
                    }
                }

                Divider()

                // Input Area
                inputArea
            }

            // Side Panel - Quick Actions & Analysis
            sidePanel
                .frame(minWidth: 280, maxWidth: 350)
        }
        .background(Color(NSColor.textBackgroundColor))
        .onAppear {
            initializeAssistant()
        }
    }

    // MARK: - Header
    private var header: some View {
        HStack(spacing: 16) {
            // MLX Status
            HStack(spacing: 8) {
                Circle()
                    .fill(mlxEngine.isModelLoaded ? Color.green : Color.orange)
                    .frame(width: 10, height: 10)

                VStack(alignment: .leading, spacing: 2) {
                    Text("MLX Intelligence")
                        .font(.headline)

                    Text(mlxEngine.isModelLoaded ? "On-Device AI Ready" : "Loading...")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            Spacer()

            // Mode Selector
            Picker("Mode", selection: $selectedMode) {
                ForEach(AssistantMode.allCases) { mode in
                    Label(mode.rawValue, systemImage: mode.icon)
                        .tag(mode)
                }
            }
            .pickerStyle(.segmented)
            .frame(width: 300)

            // Clear Button
            Button(action: clearChat) {
                Image(systemName: "trash")
            }
            .buttonStyle(.borderless)
            .help("Clear conversation")
        }
        .padding()
    }

    // MARK: - Input Area
    private var inputArea: some View {
        HStack(spacing: 12) {
            // Context indicator
            if appState.companyData.hasAnyData {
                HStack(spacing: 4) {
                    Image(systemName: "doc.fill")
                        .font(.caption)
                    Text("Data loaded")
                        .font(.caption)
                }
                .foregroundColor(.green)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.green.opacity(0.15))
                .cornerRadius(4)
            }

            // Text Input
            TextField("Ask about your maintenance data...", text: $inputText)
                .textFieldStyle(.roundedBorder)
                .onSubmit {
                    sendMessage()
                }

            // Send Button
            Button(action: sendMessage) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.title2)
            }
            .buttonStyle(.borderless)
            .disabled(inputText.isEmpty || mlxEngine.isProcessing)
            .keyboardShortcut(.return, modifiers: [])
        }
        .padding()
    }

    // MARK: - Side Panel
    private var sidePanel: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Quick Actions")
                .font(.headline)
                .padding(.horizontal)
                .padding(.top)

            VStack(spacing: 8) {
                QuickActionButton(
                    title: "Analyze Data Quality",
                    icon: "checkmark.seal",
                    color: .blue
                ) {
                    analyzeDataQuality()
                }

                QuickActionButton(
                    title: "Find Cost Drivers",
                    icon: "dollarsign.circle",
                    color: .green
                ) {
                    findCostDrivers()
                }

                QuickActionButton(
                    title: "Predict Failures",
                    icon: "exclamationmark.triangle",
                    color: .orange
                ) {
                    predictFailures()
                }

                QuickActionButton(
                    title: "Generate Report",
                    icon: "doc.richtext",
                    color: .purple
                ) {
                    generateReport()
                }

                QuickActionButton(
                    title: "Optimization Tips",
                    icon: "lightbulb",
                    color: .yellow
                ) {
                    getOptimizationTips()
                }
            }
            .padding(.horizontal)

            Divider()
                .padding(.vertical)

            // Analysis Results
            if !messages.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Recent Insights")
                        .font(.headline)
                        .padding(.horizontal)

                    ScrollView {
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(extractInsights(), id: \.self) { insight in
                                HStack(alignment: .top, spacing: 8) {
                                    Image(systemName: "lightbulb.fill")
                                        .foregroundColor(.yellow)
                                        .font(.caption)

                                    Text(insight)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                        .padding(.horizontal)
                    }
                }
            }

            Spacer()

            // MLX Info
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Image(systemName: "cpu")
                    Text("Apple Silicon MLX")
                        .font(.caption)
                }

                Text("All AI runs locally on your Mac")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))
            .cornerRadius(8)
            .padding()
        }
        .background(Color(NSColor.windowBackgroundColor))
    }

    // MARK: - Actions

    private func initializeAssistant() {
        // Add welcome message
        let welcome = ChatMessage(
            role: .assistant,
            content: """
            👋 Welcome to ChatterFix Intelligence!

            I'm powered by Apple MLX and run entirely on your Mac - no cloud needed.

            I can help you:
            • Analyze your maintenance data
            • Identify cost drivers and money pits
            • Predict equipment failures
            • Generate reports and insights
            • Write custom analysis code

            Upload your data or ask me anything about maintenance optimization!
            """
        )
        messages.append(welcome)

        // Initialize MLX engine
        Task {
            await mlxEngine.initialize()
        }
    }

    private func sendMessage() {
        guard !inputText.isEmpty else { return }

        let userMessage = ChatMessage(role: .user, content: inputText)
        messages.append(userMessage)

        let prompt = inputText
        inputText = ""

        Task {
            let response = await generateResponse(for: prompt)
            let assistantMessage = ChatMessage(role: .assistant, content: response)

            await MainActor.run {
                messages.append(assistantMessage)
            }
        }
    }

    private func generateResponse(for prompt: String) async -> String {
        // Build context from loaded data
        var context = ""

        if let workOrders = appState.companyData.workOrdersData {
            context += "The user has loaded \(workOrders.count) work orders. "
        }
        if let assets = appState.companyData.assetsData {
            context += "They have \(assets.count) assets. "
        }

        let fullPrompt = """
        You are a maintenance intelligence assistant. Help the user analyze their CMMS data.

        Context: \(context)

        User: \(prompt)

        Provide helpful, specific advice based on maintenance best practices.
        """

        return await mlxEngine.generate(prompt: fullPrompt, maxTokens: 800)
    }

    private func analyzeDataQuality() {
        let prompt = "Analyze the quality of my maintenance data. What fields are missing? What improvements would you recommend?"
        inputText = prompt
        sendMessage()
    }

    private func findCostDrivers() {
        let prompt = "What are the top cost drivers in my maintenance data? Which assets are costing the most?"
        inputText = prompt
        sendMessage()
    }

    private func predictFailures() {
        let prompt = "Based on the maintenance history, which equipment is most likely to fail in the next 30 days?"
        inputText = prompt
        sendMessage()
    }

    private func generateReport() {
        let prompt = "Generate an executive summary of my maintenance data including key metrics, findings, and recommendations."
        inputText = prompt
        sendMessage()
    }

    private func getOptimizationTips() {
        let prompt = "What are the top 5 ways I could optimize my maintenance operations based on the data?"
        inputText = prompt
        sendMessage()
    }

    private func clearChat() {
        messages.removeAll()
        initializeAssistant()
    }

    private func extractInsights() -> [String] {
        // Extract key insights from assistant messages
        let assistantMessages = messages.filter { $0.role == .assistant }
        var insights: [String] = []

        for message in assistantMessages.suffix(3) {
            let lines = message.content.components(separatedBy: .newlines)
            for line in lines {
                let trimmed = line.trimmingCharacters(in: .whitespaces)
                if (trimmed.hasPrefix("-") || trimmed.hasPrefix("•") || trimmed.hasPrefix("*")) &&
                   trimmed.count > 10 && trimmed.count < 100 {
                    let clean = trimmed
                        .replacingOccurrences(of: "^[-•*]\\s*", with: "", options: .regularExpression)
                    insights.append(clean)
                }
            }
        }

        return Array(insights.prefix(5))
    }
}

// MARK: - Supporting Views

struct MessageBubble: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            if message.role == .assistant {
                // AI Avatar
                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                colors: [.blue, .purple],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 36, height: 36)

                    Image(systemName: "cpu")
                        .foregroundColor(.white)
                        .font(.system(size: 16))
                }
            }

            VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 4) {
                Text(message.role == .user ? "You" : "MLX Assistant")
                    .font(.caption)
                    .foregroundColor(.secondary)

                Text(message.content)
                    .padding(12)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(message.role == .user ?
                                  Color.accentColor.opacity(0.15) :
                                  Color(NSColor.controlBackgroundColor))
                    )
            }
            .frame(maxWidth: 600, alignment: message.role == .user ? .trailing : .leading)

            if message.role == .user {
                // User Avatar
                ZStack {
                    Circle()
                        .fill(Color.accentColor)
                        .frame(width: 36, height: 36)

                    Image(systemName: "person.fill")
                        .foregroundColor(.white)
                        .font(.system(size: 16))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: message.role == .user ? .trailing : .leading)
    }
}

struct TypingIndicator: View {
    @State private var animating = false

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3) { index in
                Circle()
                    .fill(Color.secondary)
                    .frame(width: 8, height: 8)
                    .scaleEffect(animating ? 1.0 : 0.5)
                    .animation(
                        .easeInOut(duration: 0.6)
                        .repeatForever()
                        .delay(Double(index) * 0.2),
                        value: animating
                    )
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(12)
        .onAppear { animating = true }
    }
}

struct QuickActionButton: View {
    let title: String
    let icon: String
    let color: Color
    let action: () -> Void

    @State private var isHovering = false

    var body: some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(color)
                    .frame(width: 24)

                Text(title)
                    .font(.subheadline)

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isHovering ? color.opacity(0.1) : Color(NSColor.controlBackgroundColor))
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovering = hovering
            }
        }
    }
}

// MARK: - Models

struct ChatMessage: Identifiable {
    let id = UUID()
    let role: MessageRole
    let content: String
    let timestamp: Date = Date()
}

enum MessageRole {
    case user
    case assistant
}

enum AssistantMode: String, CaseIterable, Identifiable {
    case chat = "Chat"
    case analyze = "Analyze"
    case code = "Code"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .chat: return "bubble.left.and.bubble.right"
        case .analyze: return "chart.bar.xaxis"
        case .code: return "chevron.left.forwardslash.chevron.right"
        }
    }
}

#Preview {
    AIAssistantView()
        .environmentObject(AppState())
        .frame(width: 1000, height: 700)
}
