// DataManager.swift
// Persistent data storage manager

import Foundation

class DataManager {
    static let shared = DataManager()

    private let fileManager = FileManager.default
    private var dataDirectory: URL

    private init() {
        // Store data in ~/.chatterfix/
        let home = fileManager.homeDirectoryForCurrentUser
        dataDirectory = home.appendingPathComponent(".chatterfix")

        // Create directories if needed
        try? fileManager.createDirectory(at: dataDirectory, withIntermediateDirectories: true)
        try? fileManager.createDirectory(at: clientsDirectory, withIntermediateDirectories: true)
        try? fileManager.createDirectory(at: companyDataDirectory, withIntermediateDirectories: true)
    }

    // MARK: - Directories

    private var clientsDirectory: URL {
        dataDirectory.appendingPathComponent("clients")
    }

    private var companyDataDirectory: URL {
        dataDirectory.appendingPathComponent("company_data")
    }

    // MARK: - Clients

    func saveClient(_ client: Client) {
        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted

        if let data = try? encoder.encode(client) {
            let path = clientsDirectory.appendingPathComponent("\(client.id.uuidString).json")
            try? data.write(to: path)
        }
    }

    func loadClients() -> [Client]? {
        var clients: [Client] = []

        guard let files = try? fileManager.contentsOfDirectory(at: clientsDirectory, includingPropertiesForKeys: nil) else {
            return nil
        }

        let decoder = JSONDecoder()

        for file in files where file.pathExtension == "json" {
            if let data = try? Data(contentsOf: file),
               let client = try? decoder.decode(Client.self, from: data) {
                clients.append(client)
            }
        }

        return clients.isEmpty ? nil : clients
    }

    func deleteClient(_ client: Client) {
        let path = clientsDirectory.appendingPathComponent("\(client.id.uuidString).json")
        try? fileManager.removeItem(at: path)
    }

    // MARK: - Company Data

    func getCompanyDataPath(_ companyName: String) -> URL {
        let safeName = companyName.replacingOccurrences(of: " ", with: "_")
            .replacingOccurrences(of: "/", with: "-")
        let path = companyDataDirectory.appendingPathComponent(safeName)
        try? fileManager.createDirectory(at: path, withIntermediateDirectories: true)
        return path
    }

    func getSavedCompanies() -> [String] {
        guard let dirs = try? fileManager.contentsOfDirectory(at: companyDataDirectory, includingPropertiesForKeys: nil) else {
            return []
        }

        return dirs
            .filter { $0.hasDirectoryPath }
            .map { $0.lastPathComponent.replacingOccurrences(of: "_", with: " ") }
    }

    func saveCompanyData(_ data: Data, companyName: String, fileType: String) {
        let companyDir = getCompanyDataPath(companyName)
        let filePath = companyDir.appendingPathComponent("\(fileType).csv")
        try? data.write(to: filePath)
    }

    func loadCompanyData(companyName: String, fileType: String) -> URL? {
        let companyDir = getCompanyDataPath(companyName)
        let filePath = companyDir.appendingPathComponent("\(fileType).csv")

        if fileManager.fileExists(atPath: filePath.path) {
            return filePath
        }

        return nil
    }

    // MARK: - Reports

    private var reportsDirectory: URL {
        dataDirectory.appendingPathComponent("reports")
    }

    func saveReport(_ report: Report) {
        try? fileManager.createDirectory(at: reportsDirectory, withIntermediateDirectories: true)

        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted

        if let data = try? encoder.encode(report) {
            let path = reportsDirectory.appendingPathComponent("\(report.id.uuidString).json")
            try? data.write(to: path)
        }
    }

    func loadReports() -> [Report] {
        var reports: [Report] = []

        guard let files = try? fileManager.contentsOfDirectory(at: reportsDirectory, includingPropertiesForKeys: nil) else {
            return reports
        }

        let decoder = JSONDecoder()

        for file in files where file.pathExtension == "json" {
            if let data = try? Data(contentsOf: file),
               let report = try? decoder.decode(Report.self, from: data) {
                reports.append(report)
            }
        }

        return reports
    }

    // MARK: - Settings

    func saveSetting<T: Codable>(_ value: T, forKey key: String) {
        let path = dataDirectory.appendingPathComponent("settings.json")

        var settings: [String: Data] = [:]

        if let data = try? Data(contentsOf: path),
           let existing = try? JSONDecoder().decode([String: Data].self, from: data) {
            settings = existing
        }

        if let valueData = try? JSONEncoder().encode(value) {
            settings[key] = valueData
        }

        if let data = try? JSONEncoder().encode(settings) {
            try? data.write(to: path)
        }
    }

    func loadSetting<T: Codable>(forKey key: String) -> T? {
        let path = dataDirectory.appendingPathComponent("settings.json")

        guard let data = try? Data(contentsOf: path),
              let settings = try? JSONDecoder().decode([String: Data].self, from: data),
              let valueData = settings[key],
              let value = try? JSONDecoder().decode(T.self, from: valueData) else {
            return nil
        }

        return value
    }
}
