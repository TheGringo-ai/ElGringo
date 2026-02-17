// Client.swift
// Client data model

import Foundation

struct Client: Identifiable, Hashable {
    var id: UUID = UUID()
    var name: String
    var contact: String = ""
    var email: String = ""
    var phone: String = ""
    var industry: String = ""
    var notes: String = ""
    var address: String = ""
    var status: ClientStatus = .prospect
    var createdAt: Date = Date()
    var totalRevenue: Double = 0
    var projectCount: Int = 0

    // Data tracking
    var lastDataUpload: Date?
    var auditCount: Int = 0
    var lastAuditDate: Date?

    var initials: String {
        let words = name.split(separator: " ")
        if words.count >= 2 {
            return String(words[0].prefix(1) + words[1].prefix(1)).uppercased()
        } else if let first = words.first {
            return String(first.prefix(2)).uppercased()
        }
        return "??"
    }

    init(name: String, contact: String = "", email: String = "", phone: String = "", industry: String = "", notes: String = "", address: String = "") {
        self.name = name
        self.contact = contact
        self.email = email
        self.phone = phone
        self.industry = industry
        self.notes = notes
        self.address = address
    }
}

// Custom Codable to handle missing fields from old data
extension Client: Codable {
    enum CodingKeys: String, CodingKey {
        case id, name, contact, email, phone, industry, notes, address
        case status, createdAt, totalRevenue, projectCount
        case lastDataUpload, auditCount, lastAuditDate
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)

        id = try container.decode(UUID.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        contact = try container.decodeIfPresent(String.self, forKey: .contact) ?? ""
        email = try container.decodeIfPresent(String.self, forKey: .email) ?? ""
        phone = try container.decodeIfPresent(String.self, forKey: .phone) ?? ""
        industry = try container.decodeIfPresent(String.self, forKey: .industry) ?? ""
        notes = try container.decodeIfPresent(String.self, forKey: .notes) ?? ""
        address = try container.decodeIfPresent(String.self, forKey: .address) ?? ""
        status = try container.decodeIfPresent(ClientStatus.self, forKey: .status) ?? .prospect
        createdAt = try container.decodeIfPresent(Date.self, forKey: .createdAt) ?? Date()
        totalRevenue = try container.decodeIfPresent(Double.self, forKey: .totalRevenue) ?? 0
        projectCount = try container.decodeIfPresent(Int.self, forKey: .projectCount) ?? 0
        lastDataUpload = try container.decodeIfPresent(Date.self, forKey: .lastDataUpload)
        auditCount = try container.decodeIfPresent(Int.self, forKey: .auditCount) ?? 0
        lastAuditDate = try container.decodeIfPresent(Date.self, forKey: .lastAuditDate)
    }

    // Get statistics from CompanyDataManager
    func getDataStatistics() -> CompanyStatistics {
        return CompanyDataManager.shared.getStatistics(for: id)
    }

    // Check if client has any uploaded data
    var hasData: Bool {
        return getDataStatistics().hasData
    }
}

enum ClientStatus: String, Codable, CaseIterable {
    case prospect = "Prospect"
    case active = "Active"
    case churned = "Churned"

    var color: String {
        switch self {
        case .prospect: return "orange"
        case .active: return "green"
        case .churned: return "gray"
        }
    }
}
