// FileDropZone.swift
// Drag and drop file zone component

import SwiftUI
import UniformTypeIdentifiers

struct FileDropZone: View {
    let title: String
    let subtitle: String
    let allowedTypes: [String]
    var currentFile: URL? = nil
    let onDrop: ([URL]) -> Void

    @State private var isTargeted: Bool = false
    @State private var showFilePicker: Bool = false

    var body: some View {
        ZStack {
            // Background
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(NSColor.controlBackgroundColor))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .strokeBorder(
                            isTargeted ? Color.accentColor : Color.secondary.opacity(0.3),
                            style: StrokeStyle(lineWidth: 2, dash: [8])
                        )
                )

            // Content
            VStack(spacing: 12) {
                if let file = currentFile {
                    // File loaded state
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 40))
                        .foregroundColor(.green)

                    Text(file.lastPathComponent)
                        .font(.headline)

                    Button("Change File") {
                        showFilePicker = true
                    }
                    .buttonStyle(.bordered)
                } else {
                    // Empty state
                    Image(systemName: "arrow.down.doc.fill")
                        .font(.system(size: 40))
                        .foregroundColor(isTargeted ? .accentColor : .secondary)

                    Text(title)
                        .font(.headline)
                        .foregroundColor(isTargeted ? .accentColor : .primary)

                    Text(subtitle)
                        .font(.caption)
                        .foregroundColor(.secondary)

                    Button("Browse Files") {
                        showFilePicker = true
                    }
                    .buttonStyle(.bordered)
                }
            }
            .padding()
        }
        .onDrop(of: [.fileURL], isTargeted: $isTargeted) { providers in
            handleDrop(providers)
        }
        .fileImporter(
            isPresented: $showFilePicker,
            allowedContentTypes: allowedTypes.map { UTType(filenameExtension: $0) ?? .data },
            allowsMultipleSelection: true
        ) { result in
            switch result {
            case .success(let urls):
                onDrop(urls)
            case .failure:
                break
            }
        }
        .animation(.easeInOut(duration: 0.2), value: isTargeted)
    }

    private func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        var urls: [URL] = []

        let group = DispatchGroup()

        for provider in providers {
            group.enter()
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, error in
                defer { group.leave() }

                if let data = item as? Data,
                   let url = URL(dataRepresentation: data, relativeTo: nil) {
                    // Check if allowed type
                    let ext = url.pathExtension.lowercased()
                    if allowedTypes.contains(ext) {
                        urls.append(url)
                    }
                }
            }
        }

        group.notify(queue: .main) {
            if !urls.isEmpty {
                onDrop(urls)
            }
        }

        return true
    }
}

// MARK: - Preview
#Preview {
    VStack(spacing: 20) {
        FileDropZone(
            title: "Drop CSV files here",
            subtitle: "Work orders, assets, inventory",
            allowedTypes: ["csv"]
        ) { urls in
            print("Dropped: \(urls)")
        }
        .frame(height: 200)

        FileDropZone(
            title: "Drop CSV files here",
            subtitle: "Work orders, assets, inventory",
            allowedTypes: ["csv"],
            currentFile: URL(fileURLWithPath: "/Users/test/work_orders.csv")
        ) { urls in
            print("Dropped: \(urls)")
        }
        .frame(height: 200)
    }
    .padding()
    .frame(width: 400)
}
