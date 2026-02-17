// Report.swift
// Report data model

import Foundation
import SwiftUI

struct Report: Identifiable, Codable {
    var id: UUID = UUID()
    var clientName: String
    var type: ReportType
    var date: Date = Date()
    var grade: String?
    var value: Double?
    var content: String?
    var filePath: URL?
    var pdfPath: URL?
}

enum ReportType: String, Codable, CaseIterable, Identifiable {
    case dataAudit = "data_audit"
    case roiAnalysis = "roi_analysis"
    case mtbfPrediction = "mtbf_prediction"
    case executiveSummary = "executive_summary"
    case cleaningReport = "cleaning_report"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .dataAudit: return "Data Quality Audit"
        case .roiAnalysis: return "ROI Analysis"
        case .mtbfPrediction: return "MTBF Prediction"
        case .executiveSummary: return "Executive Summary"
        case .cleaningReport: return "Data Cleaning Report"
        }
    }

    var icon: String {
        switch self {
        case .dataAudit: return "checkmark.seal.fill"
        case .roiAnalysis: return "dollarsign.circle.fill"
        case .mtbfPrediction: return "exclamationmark.triangle.fill"
        case .executiveSummary: return "doc.richtext.fill"
        case .cleaningReport: return "sparkles"
        }
    }

    var color: Color {
        switch self {
        case .dataAudit: return .blue
        case .roiAnalysis: return .green
        case .mtbfPrediction: return .orange
        case .executiveSummary: return .purple
        case .cleaningReport: return .teal
        }
    }
}
