// AnalysisEngine.swift
// Comprehensive data analysis engine integrating all Python tools

import Foundation
import Combine

/// Analysis Engine - Orchestrates all ChatterFix analysis tools
/// Integrates: data_audit, roi_calculator, mtbf_predictor, executive_report, data_cleaner
class AnalysisEngine: ObservableObject {
    static let shared = AnalysisEngine()

    // MARK: - Published Properties
    @Published var isAnalyzing: Bool = false
    @Published var analysisProgress: Double = 0
    @Published var currentStep: String = ""
    @Published var lastAnalysis: AnalysisResult?

    // MARK: - Configuration
    private var projectRoot: URL?
    private var pythonPath: String = "/usr/bin/python3"

    private init() {
        findProjectRoot()
        findPython()
    }

    // MARK: - Analysis Types

    /// Complete analysis package - runs all tools
    func runCompleteAnalysis(csvPath: URL, companyName: String) async throws -> AnalysisResult {
        await setProgress(0.05, "Starting analysis...")

        var result = AnalysisResult(companyName: companyName)

        // Step 1: Data Audit (Grade & Quality)
        await setProgress(0.1, "Running Data Quality Audit...")
        result.dataAudit = try await runDataAudit(csvPath: csvPath, companyName: companyName)

        // Step 2: Data Cleaning
        await setProgress(0.25, "Cleaning and merging records...")
        let cleanedPath = try await runDataCleaner(csvPath: csvPath, companyName: companyName)
        result.cleanedDataPath = cleanedPath

        // Step 3: ROI Analysis
        await setProgress(0.45, "Calculating ROI & identifying Money Pits...")
        result.roiAnalysis = try await runROICalculator(csvPath: cleanedPath, companyName: companyName)

        // Step 4: MTBF Predictions
        await setProgress(0.65, "Predicting equipment failures...")
        result.mtbfPrediction = try await runMTBFPredictor(csvPath: cleanedPath, companyName: companyName)

        // Step 5: Executive Summary
        await setProgress(0.85, "Generating Executive Summary...")
        result.executiveSummary = try await runExecutiveReport(csvPath: cleanedPath, companyName: companyName)

        // Step 6: PDF Generation
        await setProgress(0.95, "Creating PDF Report...")
        result.pdfPath = try await runPDFGenerator(csvPath: cleanedPath, companyName: companyName)

        await setProgress(1.0, "Analysis Complete!")

        await MainActor.run {
            self.lastAnalysis = result
            self.isAnalyzing = false
        }

        return result
    }

    // MARK: - Individual Analysis Tools

    /// Data Quality Audit - Returns GPA score and quality metrics
    func runDataAudit(csvPath: URL, companyName: String) async throws -> DataAuditResult {
        let script = projectRoot?.appendingPathComponent("scripts/data_audit.py")
        guard let scriptPath = script?.path else {
            throw AnalysisError.scriptNotFound("data_audit.py")
        }

        let output = try await runPythonScript(scriptPath, arguments: [csvPath.path, companyName])

        return parseDataAuditOutput(output)
    }

    /// Data Cleaner - Merges partial records, returns cleaned file path
    func runDataCleaner(csvPath: URL, companyName: String) async throws -> URL {
        let script = projectRoot?.appendingPathComponent("scripts/data_cleaner.py")
        guard let scriptPath = script?.path else {
            throw AnalysisError.scriptNotFound("data_cleaner.py")
        }

        let outputDir = getOutputDirectory(for: companyName)
        let cleanedPath = outputDir.appendingPathComponent("\(companyName.sanitized)_cleaned.csv")

        _ = try await runPythonScript(scriptPath, arguments: [csvPath.path, cleanedPath.path])

        return cleanedPath
    }

    /// ROI Calculator - Identifies Money Pits and savings potential
    func runROICalculator(csvPath: URL, companyName: String) async throws -> ROIAnalysisResult {
        let script = projectRoot?.appendingPathComponent("scripts/roi_calculator.py")
        guard let scriptPath = script?.path else {
            throw AnalysisError.scriptNotFound("roi_calculator.py")
        }

        let output = try await runPythonScript(scriptPath, arguments: [csvPath.path, "--company", companyName])

        return parseROIOutput(output)
    }

    /// MTBF Predictor - Failure predictions and risk assessment
    func runMTBFPredictor(csvPath: URL, companyName: String) async throws -> MTBFResult {
        let script = projectRoot?.appendingPathComponent("scripts/mtbf_predictor.py")
        guard let scriptPath = script?.path else {
            throw AnalysisError.scriptNotFound("mtbf_predictor.py")
        }

        let output = try await runPythonScript(scriptPath, arguments: [csvPath.path, "--company", companyName])

        return parseMTBFOutput(output)
    }

    /// Executive Report - Strategic summary with action plan
    func runExecutiveReport(csvPath: URL, companyName: String) async throws -> ExecutiveSummaryResult {
        let script = projectRoot?.appendingPathComponent("scripts/executive_report.py")
        guard let scriptPath = script?.path else {
            throw AnalysisError.scriptNotFound("executive_report.py")
        }

        let outputDir = getOutputDirectory(for: companyName)
        let reportPath = outputDir.appendingPathComponent("\(companyName.sanitized)_Executive_Report.md")

        _ = try await runPythonScript(scriptPath, arguments: [csvPath.path, companyName, "-m", reportPath.path])

        let content = try? String(contentsOf: reportPath, encoding: .utf8)

        return ExecutiveSummaryResult(
            content: content ?? "",
            filePath: reportPath
        )
    }

    /// PDF Generator - Professional pitch document
    func runPDFGenerator(csvPath: URL, companyName: String) async throws -> URL {
        let script = projectRoot?.appendingPathComponent("scripts/pdf_generator.py")
        guard let scriptPath = script?.path else {
            throw AnalysisError.scriptNotFound("pdf_generator.py")
        }

        let outputDir = getOutputDirectory(for: companyName)
        let pdfPath = outputDir.appendingPathComponent("\(companyName.sanitized)_Intelligence_Report.pdf")

        // Run as Python code to call the class
        let pythonCode = """
        import sys
        sys.path.insert(0, '\(projectRoot?.path ?? "")')
        from scripts.pdf_generator import PitchGenerator
        gen = PitchGenerator()
        gen.load_data('\(csvPath.path)')
        gen.generate_pdf('\(companyName)', '\(pdfPath.path)')
        print('PDF_GENERATED:\(pdfPath.path)')
        """

        let tempScript = FileManager.default.temporaryDirectory.appendingPathComponent("gen_pdf_\(UUID().uuidString).py")
        try pythonCode.write(to: tempScript, atomically: true, encoding: .utf8)

        _ = try await runPythonScript(tempScript.path, arguments: [])

        try? FileManager.default.removeItem(at: tempScript)

        return pdfPath
    }

    /// Generate Complete Deliverables Package
    func generateDeliverables(csvPath: URL, companyName: String) async throws -> DeliverablesResult {
        let script = projectRoot?.appendingPathComponent("scripts/generate_deliverables.py")
        guard let scriptPath = script?.path else {
            throw AnalysisError.scriptNotFound("generate_deliverables.py")
        }

        let output = try await runPythonScript(scriptPath, arguments: [csvPath.path, companyName])

        return parseDeliverablesOutput(output, companyName: companyName)
    }

    // MARK: - Grouping Analysis

    /// Group by Work Order - Efficiency View
    func analyzeByWorkOrder(csvPath: URL) async throws -> WorkOrderAnalysis {
        let pythonCode = """
        import pandas as pd
        import json

        df = pd.read_csv('\(csvPath.path)', encoding='utf-8-sig')

        # Find work order column
        wo_cols = [c for c in df.columns if 'work' in c.lower() and ('order' in c.lower() or 'num' in c.lower() or 'no' in c.lower())]
        wo_col = wo_cols[0] if wo_cols else df.columns[0]

        # Group by work order
        grouped = df.groupby(wo_col).agg({
            col: lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else '' for col in df.columns
        }).reset_index(drop=True)

        # Find cost columns
        cost_cols = [c for c in df.columns if 'cost' in c.lower() or 'price' in c.lower()]
        total_cost = 0
        if cost_cols:
            for col in cost_cols:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace('[$,]', '', regex=True), errors='coerce')
                total_cost += df[col].sum()

        result = {
            'total_rows': len(df),
            'unique_work_orders': len(grouped),
            'reduction_pct': round((1 - len(grouped)/len(df)) * 100, 1) if len(df) > 0 else 0,
            'total_cost': total_cost,
            'work_order_column': wo_col
        }

        print(json.dumps(result))
        """

        let tempScript = FileManager.default.temporaryDirectory.appendingPathComponent("wo_analysis.py")
        try pythonCode.write(to: tempScript, atomically: true, encoding: .utf8)

        let output = try await runPythonScript(tempScript.path, arguments: [])
        try? FileManager.default.removeItem(at: tempScript)

        if let data = output.data(using: .utf8),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            return WorkOrderAnalysis(
                totalRows: json["total_rows"] as? Int ?? 0,
                uniqueWorkOrders: json["unique_work_orders"] as? Int ?? 0,
                reductionPercent: json["reduction_pct"] as? Double ?? 0,
                totalCost: json["total_cost"] as? Double ?? 0
            )
        }

        throw AnalysisError.parseError("Work order analysis failed")
    }

    /// Group by Asset ID - Reliability View (Money Pits)
    func analyzeByAsset(csvPath: URL) async throws -> AssetAnalysis {
        let pythonCode = """
        import pandas as pd
        import json

        df = pd.read_csv('\(csvPath.path)', encoding='utf-8-sig')

        # Find asset column
        asset_cols = [c for c in df.columns if 'asset' in c.lower() or 'equip' in c.lower() or 'machine' in c.lower()]
        asset_col = asset_cols[0] if asset_cols else df.columns[0]

        # Find cost column
        cost_cols = [c for c in df.columns if 'cost' in c.lower()]
        cost_col = cost_cols[0] if cost_cols else None

        # Find description column
        desc_cols = [c for c in df.columns if 'desc' in c.lower() or 'name' in c.lower()]
        desc_col = desc_cols[0] if desc_cols else None

        # Prepare cost data
        if cost_col:
            df[cost_col] = pd.to_numeric(df[cost_col].astype(str).str.replace('[$,]', '', regex=True), errors='coerce')

        # Group by asset
        agg_dict = {asset_col: 'count'}
        if cost_col:
            agg_dict[cost_col] = 'sum'

        asset_summary = df.groupby(asset_col).agg(agg_dict).reset_index()
        asset_summary.columns = ['asset_id', 'work_order_count'] + (['total_cost'] if cost_col else [])

        if cost_col:
            asset_summary = asset_summary.sort_values('total_cost', ascending=False)
        else:
            asset_summary = asset_summary.sort_values('work_order_count', ascending=False)

        # Get top 10 money pits
        top_10 = asset_summary.head(10).to_dict('records')

        # Get descriptions for top assets
        if desc_col:
            for item in top_10:
                asset_rows = df[df[asset_col] == item['asset_id']]
                if len(asset_rows) > 0 and desc_col in asset_rows.columns:
                    desc = asset_rows[desc_col].dropna().iloc[0] if len(asset_rows[desc_col].dropna()) > 0 else ''
                    item['description'] = str(desc)[:100]

        total_cost = df[cost_col].sum() if cost_col else 0
        top_10_cost = sum(item.get('total_cost', 0) for item in top_10)

        result = {
            'total_assets': len(asset_summary),
            'total_cost': float(total_cost),
            'top_10_cost': float(top_10_cost),
            'top_10_pct': round(top_10_cost / total_cost * 100, 1) if total_cost > 0 else 0,
            'money_pits': top_10
        }

        print(json.dumps(result))
        """

        let tempScript = FileManager.default.temporaryDirectory.appendingPathComponent("asset_analysis.py")
        try pythonCode.write(to: tempScript, atomically: true, encoding: .utf8)

        let output = try await runPythonScript(tempScript.path, arguments: [])
        try? FileManager.default.removeItem(at: tempScript)

        if let data = output.data(using: .utf8),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {

            var moneyPits: [MoneyPitAsset] = []
            if let pits = json["money_pits"] as? [[String: Any]] {
                for pit in pits {
                    moneyPits.append(MoneyPitAsset(
                        assetId: pit["asset_id"] as? String ?? "",
                        description: pit["description"] as? String ?? "",
                        workOrderCount: pit["work_order_count"] as? Int ?? 0,
                        totalCost: pit["total_cost"] as? Double ?? 0
                    ))
                }
            }

            return AssetAnalysis(
                totalAssets: json["total_assets"] as? Int ?? 0,
                totalCost: json["total_cost"] as? Double ?? 0,
                top10Cost: json["top_10_cost"] as? Double ?? 0,
                top10Percent: json["top_10_pct"] as? Double ?? 0,
                moneyPits: moneyPits
            )
        }

        throw AnalysisError.parseError("Asset analysis failed")
    }

    // MARK: - Helper Methods

    @MainActor
    private func setProgress(_ progress: Double, _ step: String) {
        self.analysisProgress = progress
        self.currentStep = step
        self.isAnalyzing = true
    }

    private func runPythonScript(_ scriptPath: String, arguments: [String]) async throws -> String {
        return try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: self.pythonPath)
                process.arguments = [scriptPath] + arguments

                var env = ProcessInfo.processInfo.environment
                env["PYTHONPATH"] = self.projectRoot?.path ?? ""
                process.environment = env

                if let root = self.projectRoot {
                    process.currentDirectoryURL = root
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

                    if process.terminationStatus != 0 && output.isEmpty {
                        continuation.resume(throwing: AnalysisError.scriptFailed(error))
                    } else {
                        continuation.resume(returning: output + error)
                    }
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    private func findProjectRoot() {
        let home = FileManager.default.homeDirectoryForCurrentUser
        let paths = [
            home.appendingPathComponent("Development/Projects/AITeamPlatform"),
            home.appendingPathComponent("Projects/AITeamPlatform"),
            home.appendingPathComponent("AITeamPlatform")
        ]

        for path in paths {
            if FileManager.default.fileExists(atPath: path.appendingPathComponent("scripts/data_audit.py").path) {
                projectRoot = path
                return
            }
        }
    }

    private func findPython() {
        let paths = ["/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"]
        for path in paths {
            if FileManager.default.fileExists(atPath: path) {
                pythonPath = path
                return
            }
        }
    }

    private func getOutputDirectory(for companyName: String) -> URL {
        let home = FileManager.default.homeDirectoryForCurrentUser
        let dir = home.appendingPathComponent(".chatterfix/analysis/\(companyName.sanitized)")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    // MARK: - Output Parsers

    private func parseDataAuditOutput(_ output: String) -> DataAuditResult {
        var result = DataAuditResult()

        // Extract grade
        if let gradeMatch = output.range(of: "Grade:\\s*([A-F][+-]?)", options: .regularExpression) {
            let gradeStr = String(output[gradeMatch])
            result.grade = gradeStr.replacingOccurrences(of: "Grade:", with: "").trimmingCharacters(in: .whitespaces)
        }

        // Extract GPA
        if let gpaMatch = output.range(of: "GPA:\\s*([0-9.]+)", options: .regularExpression) {
            let gpaStr = String(output[gpaMatch])
            if let gpa = Double(gpaStr.replacingOccurrences(of: "GPA:", with: "").trimmingCharacters(in: .whitespaces)) {
                result.gpa = gpa
            }
        }

        // Extract redundancy
        if let redundancyMatch = output.range(of: "([0-9.]+)%\\s*redundan", options: .regularExpression) {
            let redStr = String(output[redundancyMatch])
            if let red = Double(redStr.replacingOccurrences(of: "%", with: "").trimmingCharacters(in: .whitespaces)) {
                result.redundancyPercent = red
            }
        }

        result.rawOutput = output
        return result
    }

    private func parseROIOutput(_ output: String) -> ROIAnalysisResult {
        var result = ROIAnalysisResult()

        // Extract total spend
        if let spendMatch = output.range(of: "Total.*Spend.*\\$([0-9,]+)", options: .regularExpression) {
            let str = String(output[spendMatch])
            if let amount = str.extractCurrency() {
                result.totalSpend = amount
            }
        }

        // Extract savings
        if let savingsMatch = output.range(of: "Savings.*\\$([0-9,]+)", options: .regularExpression) {
            let str = String(output[savingsMatch])
            if let amount = str.extractCurrency() {
                result.potentialSavings = amount
            }
        }

        // Extract ROI
        if let roiMatch = output.range(of: "ROI.*([0-9]+)%", options: .regularExpression) {
            let str = String(output[roiMatch])
            if let roi = str.extractNumber() {
                result.roi = roi
            }
        }

        result.rawOutput = output
        return result
    }

    private func parseMTBFOutput(_ output: String) -> MTBFResult {
        var result = MTBFResult()

        // Extract imminent failures count
        if let failMatch = output.range(of: "Imminent.*Failures.*([0-9]+)", options: .regularExpression) {
            let str = String(output[failMatch])
            if let count = Int(str.extractNumberString()) {
                result.imminentFailures = count
            }
        }

        // Extract average MTBF
        if let mtbfMatch = output.range(of: "MTBF.*([0-9]+)\\s*days", options: .regularExpression) {
            let str = String(output[mtbfMatch])
            if let days = Int(str.extractNumberString()) {
                result.averageMTBF = days
            }
        }

        result.rawOutput = output
        return result
    }

    private func parseDeliverablesOutput(_ output: String, companyName: String) -> DeliverablesResult {
        let home = FileManager.default.homeDirectoryForCurrentUser
        let safeName = companyName.sanitized
        let baseDir = home.appendingPathComponent("Desktop/\(safeName)_Deliverables")

        return DeliverablesResult(
            outputDirectory: baseDir,
            cleanedCSV: baseDir.appendingPathComponent("1_CLEANED_DATA/\(safeName)_Cleaned_Data.csv"),
            auditReport: baseDir.appendingPathComponent("2_AUDIT_REPORTS/Data_Quality_Audit.md"),
            roiReport: baseDir.appendingPathComponent("2_AUDIT_REPORTS/ROI_Analysis.md"),
            mtbfReport: baseDir.appendingPathComponent("2_AUDIT_REPORTS/MTBF_Predictions.md"),
            executivePDF: baseDir.appendingPathComponent("3_EXECUTIVE_REPORT/\(safeName)_Intelligence_Report.pdf"),
            rawOutput: output
        )
    }
}

// MARK: - Result Types

struct AnalysisResult {
    var companyName: String
    var dataAudit: DataAuditResult?
    var cleanedDataPath: URL?
    var roiAnalysis: ROIAnalysisResult?
    var mtbfPrediction: MTBFResult?
    var executiveSummary: ExecutiveSummaryResult?
    var pdfPath: URL?
}

struct DataAuditResult {
    var grade: String = "N/A"
    var gpa: Double = 0
    var redundancyPercent: Double = 0
    var totalRows: Int = 0
    var uniqueRows: Int = 0
    var rawOutput: String = ""
}

struct ROIAnalysisResult {
    var totalSpend: Double = 0
    var potentialSavings: Double = 0
    var roi: Double = 0
    var paybackMonths: Int = 0
    var rawOutput: String = ""
}

struct MTBFResult {
    var imminentFailures: Int = 0
    var averageMTBF: Int = 0
    var projectedCost30Days: Double = 0
    var rawOutput: String = ""
}

struct ExecutiveSummaryResult {
    var content: String
    var filePath: URL
}

struct DeliverablesResult {
    var outputDirectory: URL
    var cleanedCSV: URL
    var auditReport: URL
    var roiReport: URL
    var mtbfReport: URL
    var executivePDF: URL
    var rawOutput: String
}

struct WorkOrderAnalysis {
    var totalRows: Int
    var uniqueWorkOrders: Int
    var reductionPercent: Double
    var totalCost: Double
}

struct AssetAnalysis {
    var totalAssets: Int
    var totalCost: Double
    var top10Cost: Double
    var top10Percent: Double
    var moneyPits: [MoneyPitAsset]
}

struct MoneyPitAsset: Identifiable {
    var id: String { assetId }
    var assetId: String
    var description: String
    var workOrderCount: Int
    var totalCost: Double
}

// MARK: - Errors

enum AnalysisError: LocalizedError {
    case scriptNotFound(String)
    case scriptFailed(String)
    case parseError(String)

    var errorDescription: String? {
        switch self {
        case .scriptNotFound(let name):
            return "Script not found: \(name)"
        case .scriptFailed(let error):
            return "Script execution failed: \(error)"
        case .parseError(let msg):
            return "Parse error: \(msg)"
        }
    }
}

// MARK: - String Extensions

extension String {
    var sanitized: String {
        self.replacingOccurrences(of: " ", with: "_")
            .replacingOccurrences(of: "/", with: "-")
    }

    func extractCurrency() -> Double? {
        let cleaned = self.replacingOccurrences(of: "[$,]", with: "", options: .regularExpression)
        if let range = cleaned.range(of: "[0-9.]+", options: .regularExpression) {
            return Double(cleaned[range])
        }
        return nil
    }

    func extractNumber() -> Double? {
        if let range = self.range(of: "[0-9.]+", options: .regularExpression) {
            return Double(self[range])
        }
        return nil
    }

    func extractNumberString() -> String {
        if let range = self.range(of: "[0-9]+", options: .regularExpression) {
            return String(self[range])
        }
        return "0"
    }
}
