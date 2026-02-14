# Architecture

## System Overview

omero-isa provides bidirectional data transfer between OMERO and the ISA (Investigation, Study, Assay) model format.

```
┌─────────────────────────────────────────────────────────────┐
│                        omero-isa                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐              ┌──────────────────┐   │
│  │  OMERO Server    │              │  ISA Format      │   │
│  │  ─────────────   │              │  (JSON Files)    │   │
│  │ • Project        │◄────────────►│ • Investigation  │   │
│  │ • Dataset        │  Export/     │ • Study          │   │
│  │ • Image          │  Import      │ • Assay          │   │
│  │ • ROI            │              │ • Dataset Files  │   │
│  │ • Annotations    │              │ • ROI Data       │   │
│  └──────────────────┘              └──────────────────┘   │
│         ▲                                    ▲             │
│         │                                    │             │
│    ┌────┴─────────────────────────────────┬─┴────┐        │
│    │                                      │      │        │
│  [Export]                            [Import]    │        │
│  omero transfer pack                omero-isa    │        │
│  --plugin isa                        CLI         │        │
│                                                  │        │
└──────────────────────────────────────────────────┼────────┘
                                                   │
                                              CLI Interface
                                              with argparse
```

## Components

### 1. CLI Module (`src/omero_isa/cli.py`)

**Responsibility:** Command-line interface for importing ISA data into OMERO

**Main Functions:**
- `create_argument_parser()` - Parse command-line arguments
- `validate_investigation_file()` - Validate JSON files
- `connect_to_omero()` - Establish OMERO connection via BlitzGateway
- `import_arc_repository()` - Import ISA data into OMERO
- `main()` - Main entry point

**Entry Point:** `omero-isa` command (defined in `pyproject.toml`)

### 2. ISA Investigation Importer (`src/omero_isa/isa_investigation_importer.py`)

**Responsibility:** Convert ISA JSON data into OMERO Projects with Datasets and Images

**Main Functions:**
- `__init__()` - Initialize with investigation data
- `save()` - Create OMERO objects and import data

**Process Flow:**
1. Parse ISA investigation JSON
2. Create OMERO Project from Investigation
3. Create OMERO Datasets from Assays
4. Upload Images to Datasets
5. Link ROI data if present
6. Save metadata annotations

### 3. ISA Packer (`src/omero_isa/isa_packer.py`)

**Responsibility:** Export OMERO Projects to ISA format

**Main Functions:**
- `__init__()` - Initialize with OMERO object
- `pack()` - Export to ISA JSON and files

**Process Flow:**
1. Read OMERO Project metadata
2. Generate ISA investigation JSON
3. Export Datasets as Assays
4. Download Images and ROI data
5. Package everything into ISA directory structure

### 4. ISA Mapping (`src/omero_isa/isa_mapping.py`)

**Responsibility:** Utilities for mapping between OMERO and ISA data

**Main Functions:**
- `omero_to_isa()` - Convert OMERO objects to ISA format
- `isa_to_omero()` - Convert ISA data to OMERO objects
- `extract_metadata()` - Extract annotations from OMERO objects

## Data Flow

### Import Flow (ISA → OMERO)

```
User input via CLI
       │
       ▼
Argument parser
       │
       ├─ Project name
       ├─ Investigation file path
       ├─ OMERO credentials
       └─ Server connection details
       │
       ▼
Validate investigation file
       │
       ├─ File exists?
       ├─ Valid JSON?
       └─ Parse JSON structure
       │
       ▼
Connect to OMERO
       │
       ├─ Create BlitzGateway
       ├─ Authenticate
       └─ Get connection object
       │
       ▼
IsaInvestigationImporter
       │
       ├─ Parse investigation JSON
       ├─ Create OMERO Project
       ├─ Create OMERO Datasets (from Assays)
       ├─ Upload Images
       ├─ Link ROI data
       └─ Save metadata
       │
       ▼
Return OMERO Project ID
       │
       ▼
Close connection
       │
       ▼
Success message
```

### Export Flow (OMERO → ISA)

```
omero transfer pack --plugin isa
       │
       ▼
Load OMERO Project
       │
       ├─ Get Project metadata
       ├─ Load Datasets
       ├─ Load Images
       └─ Load ROI data
       │
       ▼
IsaPacker
       │
       ├─ Create investigation.json
       ├─ Create study.json
       ├─ For each Dataset:
       │   ├─ Create assay.json
       │   └─ Export images to dataset/
       ├─ Package ROI as JSON
       └─ Create directory structure
       │
       ▼
Write to disk
       │
       ├─ JSON files
       ├─ Image files
       └─ ROI files
       │
       ▼
Create archive (optional)
       │
       ▼
Success message
```

## Technology Stack

- **OMERO.py**: OMERO client library (BlitzGateway)
- **isatools**: ISA format parsing and generation
- **omero-cli-transfer**: OMERO CLI plugin framework
- **argparse**: Command-line argument parsing
- **json**: ISA file format (JSON)
- **pathlib**: File system operations

## Database Interaction

```
┌─────────────────────────────────────────┐
│         OMERO Server (PostgreSQL)       │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │
│  │      Project (Investigation)    │   │
│  │  • name                         │   │
│  │  • description                  │   │
│  │  • ownerId                      │   │
│  └──────────┬──────────────────────┘   │
│             │ contains                 │
│  ┌──────────▼──────────────────────┐   │
│  │    Dataset (Assay)              │   │
│  │  • name                         │   │
│  │  • description                  │   │
│  │  • parentProject                │   │
│  └──────────┬──────────────────────┘   │
│             │ contains                 │
│  ┌──────────▼──────────────────────┐   │
│  │      Image (File)               │   │
│  │  • name                         │   │
│  │  • pixels (data)                │   │
│  │  • roiList (if present)         │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  MapAnnotation (Metadata)       │   │
│  │  • namespace                    │   │
│  │  • keyValueMap                  │   │
│  │  • linkedTo (Project/Dataset)   │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
         ▲              ▲
         │              │
    Connected by BlitzGateway Connection Object (conn)
```

## Error Handling

The system handles errors at multiple levels:

1. **Argument Parsing**: Invalid arguments → exit with help message
2. **File Validation**: Missing/invalid JSON → FileNotFoundError, ValueError
3. **Connection**: OMERO unreachable → ConnectionError
4. **Import**: Malformed ISA data → ValueError, AssertionError
5. **Upload**: I/O errors → IOError, RuntimeError

All errors are caught in `main()` and logged with descriptive messages.

## Configuration

Configuration is handled via:
- **Command-line arguments**: User provides at runtime
- **Environment variables**: OMERODIR, ICE_CONFIG (for testing)
- **pyproject.toml**: Package metadata and entry points
- **ice.config**: OMERO test framework configuration

## Testing

Tests are organized by component:

```
test/
├── test_cli.py                    # CLI argument parsing and main()
├── test_isa_study_importer.py    # ISA import logic
├── test_isa_packer.py            # OMERO export logic
├── test_omero_isa_mapper.py       # Data mapping
└── data/                          # Test fixtures and sample data
```

Each test uses:
- **AbstractIsaTest**: Base test class with OMERO connection
- **Fixtures**: OMERO test objects (projects, datasets, images)
- **Mocking**: BlitzGateway mock objects for unit tests
