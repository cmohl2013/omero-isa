# omero-isa

Bidirectional transfer of research data between OMERO and the ISA (Investigation, Study, Assay) model format.

**Features:**
- 📤 Export OMERO Projects to ISA format (ARC - Annotated Research Context)
- 📥 Import ISA data back into OMERO as Projects
- 🔗 Preserve metadata, images, and ROI data
- 🧬 Support for complex research data structures

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Data Mapping](#data-mapping)
- [CLI Reference](#cli-reference)
- [Development](#development)
- [Documentation](#documentation)

## Quick Start

### Export: OMERO → ISA Format

```bash
# Login to OMERO
omero login

# Export a project to ISA format
omero transfer pack --plugin isa Project:414 /path/to/output/isa-project
```

### Import: ISA Format → OMERO

```bash
# Import an ISA project into OMERO
omero-isa -u username -w password -s localhost "My Project" /path/to/i_investigation.json
```

## Installation

### Requirements

- Python 3.8
- OMERO.py 5.13+

### From Repository

```bash
# Clone the repository
git clone https://github.com/cmohl2013/omero-isa.git
cd omero-isa

# Install in development mode with optional dependencies
pip install -e .[dev]
```

## Usage

### Import ISA Data into OMERO

```bash
omero-isa [OPTIONS] PROJECT_NAME INVESTIGATION_FILE
```

**Options:**
- `-u, --username`: OMERO username (required)
- `-w, --password`: OMERO password (required)
- `-s, --server`: OMERO server hostname (required)
- `-p, --port`: OMERO server port (default: 4064)

**Example:**

```bash
omero-isa -u admin -w password -s localhost "My Project" /path/to/i_investigation.json
```

### Export OMERO Data to ISA Format

```bash
omero login
omero transfer pack --plugin isa Project:414 /path/to/export
```

## Data Mapping

### Directory Structure

```
my-isa-project/
├── i_investigation.json          # ISA investigation metadata
├── s_study.json                  # ISA study metadata
└── assays/
    ├── assay-1/
    │   ├── a_assay.json          # ISA assay metadata
    │   └── dataset/
    │       ├── image1.tiff
    │       ├── image2.czi
    │       └── image2_roidata.json  # ROI data (if present)
    └── assay-2/
        ├── a_assay.json
        └── dataset/
            └── ...
```

### Mapping Rules

| OMERO | ISA |
|-------|-----|
| Project | Investigation + Study |
| Dataset | Assay |
| Image | Dataset File |
| ROI | ROI Data (JSON) |
| Annotations | Metadata |

**Details:**
- Each OMERO Project represents one ISA Investigation containing one Study
- OMERO Datasets are mapped to ISA Assays
- OMERO Images are stored as Dataset files within the Assay folder
- Region of Interest (ROI) data is exported as separate JSON files
- All metadata and annotations are preserved in the ISA JSON files

## CLI Reference

### omero-isa Import Command

```bash
usage: omero-isa [-h] [-u USERNAME] [-w PASSWORD] [-s SERVER] [-p PORT]
                 PROJECT_NAME INVESTIGATION_FILE

Import ARC repositories into OMERO using ISA format

positional arguments:
  PROJECT_NAME              Name of the project to create in OMERO
  INVESTIGATION_FILE        Path to the i_investigation.json file

optional arguments:
  -h, --help               show this help message and exit
  -u, --username USERNAME  OMERO username (required)
  -w, --password PASSWORD  OMERO password (required)
  -s, --server SERVER      OMERO server hostname (required)
  -p, --port PORT          OMERO server port (default: 4064)
```

## Development

### Setup Development Environment

```bash
# Create conda environment
conda create -n omero-isa -c conda-forge python=3.8 zeroc-ice=3.6.5
conda activate omero-isa

# Clone and install
git clone https://github.com/cmohl2013/omero-isa.git
cd omero-isa
pip install -e .[dev]
conda install pytest
```

### Run OMERO Test Database

```bash
# Make compose script executable
sudo chmod a+x .omero/compose

# Start test database
sudo .omero/compose up

# Full rebuild (updates OMERO version)
sudo .omero/compose up --build
```

### Run Tests

```bash
# All tests
OMERODIR="." ICE_CONFIG="test/ice.config" pytest -v

# Specific test file
OMERODIR="." ICE_CONFIG="test/ice.config" pytest test/test_cli.py -v

# With coverage report
OMERODIR="." ICE_CONFIG="test/ice.config" pytest --cov=src/omero_isa test/
```

### Test Database Access

- **URL**: http://localhost:4080/
- **Username**: Available via test framework (`self.user.getOmeName()._val`)
- **Password**: Same as username

Get test credentials:

```bash
OMERODIR="." ICE_CONFIG="test/ice.config" pytest -s -k print_test_user_credentials
```

## Documentation

Additional documentation is available in the `docs/` folder:

- [**ARCHITECTURE.md**](docs/ARCHITECTURE.md) - System design and components
- [**API_REFERENCE.md**](docs/API_REFERENCE.md) - Python API documentation
- [**EXAMPLES.md**](docs/EXAMPLES.md) - Detailed usage examples
- [**CLI_TESTS_GUIDE.md**](CLI_TESTS_GUIDE.md) - Testing guide

## License

This project is licensed under the BSD License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/cmohl2013/omero-isa/issues)
- **Documentation**: See `docs/` folder
