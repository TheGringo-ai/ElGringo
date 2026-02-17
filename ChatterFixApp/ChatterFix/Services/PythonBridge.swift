// PythonBridge.swift
// Bridge to Python/MLX backend

import Foundation

class PythonBridge {
    static let shared = PythonBridge()

    private var pythonPath: String = "/usr/bin/python3"
    private var projectRoot: URL?

    private init() {}

    func initialize() {
        // Find Python
        if let brewPython = findExecutable("python3", in: "/opt/homebrew/bin") {
            pythonPath = brewPython
        } else if let systemPython = findExecutable("python3", in: "/usr/local/bin") {
            pythonPath = systemPython
        }

        // Find project root (where Python scripts live)
        // In development, this is the AITeamPlatform directory
        // In production, scripts would be bundled with the app

        if let devPath = findProjectRoot() {
            projectRoot = devPath
            print("Python Bridge: Found project at \(devPath.path)")
        }

        print("Python Bridge: Using Python at \(pythonPath)")
    }

    func shutdown() {
        // Cleanup if needed
    }

    // MARK: - Generate Deliverables

    struct DeliverableResult {
        var outputDirectory: String?
        var cleanedCSVPath: String?
        var pdfPath: String?
        var reports: [Report]
        var stats: [String: Any]
    }

    func generateDeliverables(for clientName: String, data: CompanyData) async throws -> DeliverableResult {
        guard let projectRoot = projectRoot else {
            throw PythonError.projectNotFound
        }

        guard let workOrdersPath = data.workOrdersPath else {
            throw PythonError.noDataProvided
        }

        let scriptPath = projectRoot.appendingPathComponent("scripts/generate_deliverables.py")

        // Run Python script
        let result = try await runPythonScript(
            scriptPath.path,
            arguments: [workOrdersPath.path, clientName]
        )

        // Parse output to find paths
        var deliverableResult = DeliverableResult(reports: [], stats: [:])

        // The script outputs the package location
        if let outputDir = extractPath(from: result, pattern: "Package Location: (.+)") {
            deliverableResult.outputDirectory = outputDir

            // Find the generated files
            let safeName = clientName.replacingOccurrences(of: " ", with: "_")
            deliverableResult.cleanedCSVPath = "\(outputDir)/1_CLEANED_DATA/\(safeName)_Cleaned_Data.csv"
            deliverableResult.pdfPath = "\(outputDir)/3_EXECUTIVE_REPORT/\(safeName)_Intelligence_Report.pdf"

            // Load reports
            let auditPath = "\(outputDir)/2_AUDIT_REPORTS/Data_Quality_Audit.md"
            let roiPath = "\(outputDir)/2_AUDIT_REPORTS/ROI_Analysis.md"
            let mtbfPath = "\(outputDir)/2_AUDIT_REPORTS/MTBF_Predictions.md"
            let execPath = "\(outputDir)/2_AUDIT_REPORTS/Executive_Summary.md"

            if let content = try? String(contentsOfFile: auditPath) {
                deliverableResult.reports.append(Report(
                    clientName: clientName,
                    type: .dataAudit,
                    content: content,
                    filePath: URL(fileURLWithPath: auditPath)
                ))
            }

            if let content = try? String(contentsOfFile: roiPath) {
                deliverableResult.reports.append(Report(
                    clientName: clientName,
                    type: .roiAnalysis,
                    content: content,
                    filePath: URL(fileURLWithPath: roiPath)
                ))
            }

            if let content = try? String(contentsOfFile: mtbfPath) {
                deliverableResult.reports.append(Report(
                    clientName: clientName,
                    type: .mtbfPrediction,
                    content: content,
                    filePath: URL(fileURLWithPath: mtbfPath)
                ))
            }

            if let content = try? String(contentsOfFile: execPath) {
                deliverableResult.reports.append(Report(
                    clientName: clientName,
                    type: .executiveSummary,
                    content: content,
                    filePath: URL(fileURLWithPath: execPath)
                ))
            }
        }

        return deliverableResult
    }

    // MARK: - Quick Audit

    func runQuickAudit(for clientName: String, data: CompanyData) async throws -> Report {
        guard let projectRoot = projectRoot else {
            throw PythonError.projectNotFound
        }

        guard let workOrdersPath = data.workOrdersPath else {
            throw PythonError.noDataProvided
        }

        // Run data audit script
        let scriptPath = projectRoot.appendingPathComponent("scripts/data_audit.py")

        let result = try await runPythonScript(
            scriptPath.path,
            arguments: [workOrdersPath.path, clientName]
        )

        return Report(
            clientName: clientName,
            type: .dataAudit,
            content: result
        )
    }

    // MARK: - Generate PDF

    func generatePDF(for clientName: String, data: CompanyData, outputPath: URL) async throws {
        guard let projectRoot = projectRoot else {
            throw PythonError.projectNotFound
        }

        guard let workOrdersPath = data.workOrdersPath else {
            throw PythonError.noDataProvided
        }

        // Use the pdf_generator script
        let script = """
        import sys
        sys.path.insert(0, '\(projectRoot.path)')
        from scripts.pdf_generator import PitchGenerator
        gen = PitchGenerator()
        gen.load_data('\(workOrdersPath.path)')
        gen.generate_pdf('\(clientName)', '\(outputPath.path)')
        print('PDF generated successfully')
        """

        let tempScript = FileManager.default.temporaryDirectory.appendingPathComponent("gen_pdf.py")
        try script.write(to: tempScript, atomically: true, encoding: .utf8)

        _ = try await runPythonScript(tempScript.path, arguments: [])

        try? FileManager.default.removeItem(at: tempScript)
    }

    // MARK: - Export PDF

    func exportPDF(to url: URL, client: String) async throws {
        // Copy existing PDF or generate new one
        guard let projectRoot = projectRoot else {
            throw PythonError.projectNotFound
        }

        let safeName = client.replacingOccurrences(of: " ", with: "_")
        let desktopPath = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Desktop/\(safeName)_Deliverables/3_EXECUTIVE_REPORT/\(safeName)_Intelligence_Report.pdf")

        if FileManager.default.fileExists(atPath: desktopPath.path) {
            try FileManager.default.copyItem(at: desktopPath, to: url)
        }
    }

    // MARK: - Helpers

    private func runPythonScript(_ scriptPath: String, arguments: [String]) async throws -> String {
        return try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: self.pythonPath)
                process.arguments = [scriptPath] + arguments

                // Set environment
                var env = ProcessInfo.processInfo.environment
                env["PYTHONPATH"] = self.projectRoot?.path ?? ""
                process.environment = env

                // Set working directory
                if let projectRoot = self.projectRoot {
                    process.currentDirectoryURL = projectRoot
                }

                let pipe = Pipe()
                let errorPipe = Pipe()
                process.standardOutput = pipe
                process.standardError = errorPipe

                do {
                    try process.run()
                    process.waitUntilExit()

                    let outputData = pipe.fileHandleForReading.readDataToEndOfFile()
                    let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()

                    let output = String(data: outputData, encoding: .utf8) ?? ""
                    let error = String(data: errorData, encoding: .utf8) ?? ""

                    if process.terminationStatus != 0 {
                        continuation.resume(throwing: PythonError.scriptFailed(error))
                    } else {
                        continuation.resume(returning: output + error)
                    }
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    private func findExecutable(_ name: String, in directory: String) -> String? {
        let path = "\(directory)/\(name)"
        if FileManager.default.fileExists(atPath: path) {
            return path
        }
        return nil
    }

    private func findProjectRoot() -> URL? {
        // Try to find AITeamPlatform directory
        let home = FileManager.default.homeDirectoryForCurrentUser

        let possiblePaths = [
            home.appendingPathComponent("Development/Projects/AITeamPlatform"),
            home.appendingPathComponent("Projects/AITeamPlatform"),
            home.appendingPathComponent("AITeamPlatform")
        ]

        for path in possiblePaths {
            if FileManager.default.fileExists(atPath: path.appendingPathComponent("scripts/generate_deliverables.py").path) {
                return path
            }
        }

        // Try bundle resources (for production app)
        if let bundlePath = Bundle.main.resourcePath {
            let bundleURL = URL(fileURLWithPath: bundlePath)
            if FileManager.default.fileExists(atPath: bundleURL.appendingPathComponent("scripts/generate_deliverables.py").path) {
                return bundleURL
            }
        }

        return nil
    }

    private func extractPath(from text: String, pattern: String) -> String? {
        if let regex = try? NSRegularExpression(pattern: pattern),
           let match = regex.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)),
           let range = Range(match.range(at: 1), in: text) {
            return String(text[range]).trimmingCharacters(in: .whitespacesAndNewlines)
        }
        return nil
    }
}

// MARK: - Errors

enum PythonError: LocalizedError {
    case projectNotFound
    case noDataProvided
    case scriptFailed(String)

    var errorDescription: String? {
        switch self {
        case .projectNotFound:
            return "Could not find AITeamPlatform project directory"
        case .noDataProvided:
            return "No work order data provided"
        case .scriptFailed(let error):
            return "Python script failed: \(error)"
        }
    }
}
