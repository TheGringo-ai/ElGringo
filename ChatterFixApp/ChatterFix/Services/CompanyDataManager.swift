// CompanyDataManager.swift
// Manages per-company data storage and historical tracking

import Foundation

class CompanyDataManager {
    static let shared = CompanyDataManager()

    private let baseDirectory: URL

    private init() {
        let home = FileManager.default.homeDirectoryForCurrentUser
        baseDirectory = home.appendingPathComponent(".chatterfix/companies")
        createBaseDirectoryIfNeeded()
    }

    private func createBaseDirectoryIfNeeded() {
        try? FileManager.default.createDirectory(at: baseDirectory, withIntermediateDirectories: true)
    }

    // MARK: - Company Directory Management

    func companyDirectory(for clientId: UUID) -> URL {
        let dir = baseDirectory.appendingPathComponent(clientId.uuidString)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    func dataDirectory(for clientId: UUID, type: DataFileType) -> URL {
        let dir = companyDirectory(for: clientId).appendingPathComponent(type.rawValue)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    // MARK: - File Import

    /// Import a CSV file for a specific client and data type
    /// Returns the stored file URL and upload record
    func importFile(_ sourceURL: URL, for clientId: UUID, type: DataFileType) throws -> DataUpload {
        let targetDir = dataDirectory(for: clientId, type: type)

        // Create timestamped filename
        let timestamp = ISO8601DateFormatter().string(from: Date())
            .replacingOccurrences(of: ":", with: "-")
        let originalName = sourceURL.deletingPathExtension().lastPathComponent
        let filename = "\(originalName)_\(timestamp).csv"
        let targetURL = targetDir.appendingPathComponent(filename)

        // Copy file to company directory
        try FileManager.default.copyItem(at: sourceURL, to: targetURL)

        // Create upload record
        let upload = DataUpload(
            id: UUID(),
            clientId: clientId,
            dataType: type,
            originalFilename: sourceURL.lastPathComponent,
            storedFilename: filename,
            storedPath: targetURL,
            uploadedAt: Date(),
            rowCount: countRows(in: targetURL)
        )

        // Save upload to history
        saveUploadRecord(upload, for: clientId)

        return upload
    }

    /// Import file from Data (used when file picker returns security-scoped URLs)
    func importFileData(_ data: Data, fileName: String, for clientId: UUID, type: DataFileType) throws -> DataUpload {
        let targetDir = dataDirectory(for: clientId, type: type)

        // Create timestamped filename
        let timestamp = ISO8601DateFormatter().string(from: Date())
            .replacingOccurrences(of: ":", with: "-")
        let baseName = (fileName as NSString).deletingPathExtension
        let storedFilename = "\(baseName)_\(timestamp).csv"
        let targetURL = targetDir.appendingPathComponent(storedFilename)

        // Write data to target location
        try data.write(to: targetURL)

        // Create upload record
        let upload = DataUpload(
            id: UUID(),
            clientId: clientId,
            dataType: type,
            originalFilename: fileName,
            storedFilename: storedFilename,
            storedPath: targetURL,
            uploadedAt: Date(),
            rowCount: countRows(in: targetURL)
        )

        // Save upload to history
        saveUploadRecord(upload, for: clientId)

        return upload
    }

    /// Import multiple CSV files at once
    func importFiles(_ urls: [URL], for clientId: UUID, type: DataFileType) throws -> [DataUpload] {
        var uploads: [DataUpload] = []
        for url in urls {
            let upload = try importFile(url, for: clientId, type: type)
            uploads.append(upload)
        }
        return uploads
    }

    // MARK: - Data Retrieval

    /// Get all uploaded files for a client and data type
    func getUploads(for clientId: UUID, type: DataFileType) -> [DataUpload] {
        let history = loadUploadHistory(for: clientId)
        return history.filter { $0.dataType == type }.sorted { $0.uploadedAt > $1.uploadedAt }
    }

    /// Get all uploads for a client across all types
    func getAllUploads(for clientId: UUID) -> [DataUpload] {
        return loadUploadHistory(for: clientId).sorted { $0.uploadedAt > $1.uploadedAt }
    }

    /// Get the most recent file for a data type
    func getLatestUpload(for clientId: UUID, type: DataFileType) -> DataUpload? {
        return getUploads(for: clientId, type: type).first
    }

    /// Merge all CSV files for a data type into a single compiled file
    func getMergedData(for clientId: UUID, type: DataFileType) throws -> URL {
        let uploads = getUploads(for: clientId, type: type)
        guard !uploads.isEmpty else {
            throw CompanyDataError.noDataAvailable
        }

        let mergedDir = companyDirectory(for: clientId).appendingPathComponent("merged")
        try? FileManager.default.createDirectory(at: mergedDir, withIntermediateDirectories: true)

        let mergedURL = mergedDir.appendingPathComponent("\(type.rawValue)_merged.csv")

        // Read and merge all files
        var allRows: [[String: String]] = []
        var headers: [String] = []

        for upload in uploads {
            let (fileHeaders, rows) = try parseCSV(at: upload.storedPath)
            if headers.isEmpty {
                headers = fileHeaders
            } else {
                // Merge headers if new columns found
                for header in fileHeaders where !headers.contains(header) {
                    headers.append(header)
                }
            }
            allRows.append(contentsOf: rows)
        }

        // Write merged file
        try writeCSV(headers: headers, rows: allRows, to: mergedURL)

        return mergedURL
    }

    // MARK: - Upload History

    private func uploadHistoryPath(for clientId: UUID) -> URL {
        return companyDirectory(for: clientId).appendingPathComponent("upload_history.json")
    }

    private func loadUploadHistory(for clientId: UUID) -> [DataUpload] {
        let path = uploadHistoryPath(for: clientId)
        guard FileManager.default.fileExists(atPath: path.path) else {
            return []
        }

        do {
            let data = try Data(contentsOf: path)
            return try JSONDecoder().decode([DataUpload].self, from: data)
        } catch {
            print("Error loading upload history: \(error)")
            return []
        }
    }

    private func saveUploadRecord(_ upload: DataUpload, for clientId: UUID) {
        var history = loadUploadHistory(for: clientId)
        history.append(upload)

        let path = uploadHistoryPath(for: clientId)
        do {
            let data = try JSONEncoder().encode(history)
            try data.write(to: path)
        } catch {
            print("Error saving upload history: \(error)")
        }
    }

    // MARK: - Statistics

    func getStatistics(for clientId: UUID) -> CompanyStatistics {
        let uploads = getAllUploads(for: clientId)

        var stats = CompanyStatistics()

        for type in DataFileType.allCases {
            let typeUploads = uploads.filter { $0.dataType == type }
            let totalRows = typeUploads.reduce(0) { $0 + $1.rowCount }

            switch type {
            case .workOrders:
                stats.workOrderFiles = typeUploads.count
                stats.totalWorkOrders = totalRows
            case .assets:
                stats.assetFiles = typeUploads.count
                stats.totalAssets = totalRows
            case .inventory:
                stats.inventoryFiles = typeUploads.count
                stats.totalInventoryItems = totalRows
            case .parts:
                stats.partsFiles = typeUploads.count
                stats.totalParts = totalRows
            }
        }

        stats.lastUpload = uploads.first?.uploadedAt
        stats.totalUploads = uploads.count

        return stats
    }

    // MARK: - Cleanup

    func deleteUpload(_ upload: DataUpload, for clientId: UUID) throws {
        // Remove file
        try FileManager.default.removeItem(at: upload.storedPath)

        // Update history
        var history = loadUploadHistory(for: clientId)
        history.removeAll { $0.id == upload.id }

        let path = uploadHistoryPath(for: clientId)
        let data = try JSONEncoder().encode(history)
        try data.write(to: path)
    }

    func deleteAllData(for clientId: UUID) throws {
        let dir = companyDirectory(for: clientId)
        try FileManager.default.removeItem(at: dir)
    }

    // MARK: - CSV Helpers

    private func countRows(in url: URL) -> Int {
        guard let content = try? String(contentsOf: url, encoding: .utf8) else {
            return 0
        }
        let lines = content.components(separatedBy: .newlines).filter { !$0.isEmpty }
        return max(0, lines.count - 1) // Subtract header row
    }

    private func parseCSV(at url: URL) throws -> (headers: [String], rows: [[String: String]]) {
        let content = try String(contentsOf: url, encoding: .utf8)
        let lines = content.components(separatedBy: .newlines).filter { !$0.isEmpty }

        guard lines.count > 0 else {
            return ([], [])
        }

        let headers = parseCSVLine(lines[0])
        var rows: [[String: String]] = []

        for i in 1..<lines.count {
            let values = parseCSVLine(lines[i])
            var row: [String: String] = [:]

            for (index, header) in headers.enumerated() {
                if index < values.count {
                    row[header] = values[index]
                }
            }

            rows.append(row)
        }

        return (headers, rows)
    }

    private func parseCSVLine(_ line: String) -> [String] {
        var result: [String] = []
        var current = ""
        var inQuotes = false

        for char in line {
            if char == "\"" {
                inQuotes.toggle()
            } else if char == "," && !inQuotes {
                result.append(current.trimmingCharacters(in: .whitespaces))
                current = ""
            } else {
                current.append(char)
            }
        }

        result.append(current.trimmingCharacters(in: .whitespaces))
        return result
    }

    private func writeCSV(headers: [String], rows: [[String: String]], to url: URL) throws {
        var lines: [String] = []

        // Header line
        lines.append(headers.map { escapeCSV($0) }.joined(separator: ","))

        // Data lines
        for row in rows {
            let values = headers.map { header in
                escapeCSV(row[header] ?? "")
            }
            lines.append(values.joined(separator: ","))
        }

        let content = lines.joined(separator: "\n")
        try content.write(to: url, atomically: true, encoding: .utf8)
    }

    private func escapeCSV(_ value: String) -> String {
        if value.contains(",") || value.contains("\"") || value.contains("\n") {
            return "\"\(value.replacingOccurrences(of: "\"", with: "\"\""))\""
        }
        return value
    }
}

// MARK: - Data Models

struct DataUpload: Identifiable, Codable {
    let id: UUID
    let clientId: UUID
    let dataType: DataFileType
    let originalFilename: String
    let storedFilename: String
    let storedPath: URL
    let uploadedAt: Date
    let rowCount: Int

    var formattedDate: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: uploadedAt)
    }
}

struct CompanyStatistics {
    var workOrderFiles: Int = 0
    var totalWorkOrders: Int = 0
    var assetFiles: Int = 0
    var totalAssets: Int = 0
    var inventoryFiles: Int = 0
    var totalInventoryItems: Int = 0
    var partsFiles: Int = 0
    var totalParts: Int = 0
    var lastUpload: Date?
    var totalUploads: Int = 0

    var hasData: Bool {
        totalUploads > 0
    }
}

enum CompanyDataError: Error, LocalizedError {
    case noDataAvailable
    case fileNotFound
    case invalidFormat

    var errorDescription: String? {
        switch self {
        case .noDataAvailable: return "No data has been uploaded for this company"
        case .fileNotFound: return "The requested file could not be found"
        case .invalidFormat: return "The file format is invalid"
        }
    }
}
