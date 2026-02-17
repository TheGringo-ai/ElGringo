# ChatterFix Intelligence - Native macOS App

A professional native macOS application for CMMS data analysis and maintenance intelligence.

## Features

- **Native macOS UI** - SwiftUI-based interface with drag & drop support
- **Multi-File Upload** - Import work orders, assets, inventory, and parts data
- **Python/MLX Integration** - Calls your existing Python analysis scripts
- **Menu Bar Access** - Quick access from the menu bar
- **Client Management** - Track clients and projects
- **Report Generation** - Generate all reports with one click
- **PDF Export** - Professional PDF reports for clients

## Building & Running

### From Xcode
1. Open `ChatterFix.xcodeproj` in Xcode
2. Select your development team (or leave blank for local testing)
3. Click Run (⌘R)

### From Command Line
```bash
cd ChatterFixApp
xcodebuild -project ChatterFix.xcodeproj -scheme ChatterFix -configuration Debug build
open ~/Library/Developer/Xcode/DerivedData/ChatterFix-*/Build/Products/Debug/ChatterFix.app
```

## Architecture

```
ChatterFix.app
├── SwiftUI Frontend
│   ├── Dashboard - Revenue metrics, service cards
│   ├── Clients - Client management
│   ├── Audit - Multi-file upload, report generation
│   ├── Reports - Report library
│   └── Settings - Python config, preferences
│
└── Python Backend (via subprocess)
    ├── scripts/generate_deliverables.py
    ├── scripts/data_cleaner.py
    ├── scripts/pdf_generator.py
    └── MLX model inference
```

## Data Storage

Company data is stored at:
```
~/.chatterfix/
├── clients/           # Client JSON files
├── company_data/      # CSV files per company
├── reports/           # Generated reports
└── settings.json      # App settings
```

## Integration with Python

The app automatically finds your AITeamPlatform project at:
- `~/Development/Projects/AITeamPlatform`
- `~/Projects/AITeamPlatform`
- `~/AITeamPlatform`

All your existing Python scripts work as-is. The Swift app simply calls them via subprocess.

## Security

- Runs only on YOUR Mac (code-signed to your Apple ID)
- No server required - all data stays local
- Python scripts are bundled (in production) or referenced (in development)

## Requirements

- macOS 14.0 (Sonoma) or later
- Apple Silicon (M1/M2/M3)
- Python 3.11+ with required packages
- Xcode 15+ (for building)

## License

Copyright 2024 ChatterFix AI. All rights reserved.
