// CompanyData.swift
// Company data management model

import Foundation
import SwiftUI

class CompanyData: ObservableObject {
    @Published var workOrdersPath: URL?
    @Published var assetsPath: URL?
    @Published var inventoryPath: URL?
    @Published var partsPath: URL?
    @Published var mergedPath: URL?

    @Published var workOrderCount: Int?
    @Published var assetCount: Int?
    @Published var inventoryCount: Int?
    @Published var partsCount: Int?

    @Published var workOrdersData: [[String: String]]?
    @Published var assetsData: [[String: String]]?
    @Published var inventoryData: [[String: String]]?
    @Published var partsData: [[String: String]]?

    var hasAnyData: Bool {
        workOrdersPath != nil || assetsPath != nil || inventoryPath != nil || partsPath != nil
    }

    var hasWorkOrders: Bool {
        workOrdersPath != nil
    }

    @MainActor
    func loadData(from url: URL, type: DataFileType) {
        do {
            let content = try String(contentsOf: url, encoding: .utf8)
            let rows = parseCSV(content)
            let count = rows.count

            switch type {
            case .workOrders:
                self.workOrdersData = rows
                self.workOrderCount = count
            case .assets:
                self.assetsData = rows
                self.assetCount = count
            case .inventory:
                self.inventoryData = rows
                self.inventoryCount = count
            case .parts:
                self.partsData = rows
                self.partsCount = count
            }
        } catch {
            print("Error loading data: \(error)")
        }
    }

    func clear() {
        workOrdersPath = nil
        assetsPath = nil
        inventoryPath = nil
        partsPath = nil
        mergedPath = nil

        workOrderCount = nil
        assetCount = nil
        inventoryCount = nil
        partsCount = nil

        workOrdersData = nil
        assetsData = nil
        inventoryData = nil
        partsData = nil
    }

    private func parseCSV(_ content: String) -> [[String: String]] {
        var result: [[String: String]] = []
        let lines = content.components(separatedBy: .newlines).filter { !$0.isEmpty }

        guard lines.count > 1 else { return result }

        let headers = parseCSVLine(lines[0])

        for i in 1..<lines.count {
            let values = parseCSVLine(lines[i])
            var row: [String: String] = [:]

            for (index, header) in headers.enumerated() {
                if index < values.count {
                    row[header] = values[index]
                }
            }

            result.append(row)
        }

        return result
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
}

// DataFileType enum (shared with AuditView)
enum DataFileType: String, CaseIterable, Identifiable, Codable {
    case workOrders
    case assets
    case inventory
    case parts

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .workOrders: return "Work Orders"
        case .assets: return "Assets"
        case .inventory: return "Inventory"
        case .parts: return "Parts"
        }
    }

    var icon: String {
        switch self {
        case .workOrders: return "doc.text.fill"
        case .assets: return "gearshape.fill"
        case .inventory: return "shippingbox.fill"
        case .parts: return "wrench.fill"
        }
    }

    var description: String {
        switch self {
        case .workOrders: return "Maintenance history, work orders, service records"
        case .assets: return "Equipment registry, asset master list"
        case .inventory: return "Spare parts stock, inventory levels"
        case .parts: return "Parts usage per work order, BOMs"
        }
    }
}
