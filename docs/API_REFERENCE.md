# API Reference

## Module: omero_isa.cli

Command-line interface for importing ISA data into OMERO.

### Functions

#### create_argument_parser()

```python
def create_argument_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser for the omero-isa CLI.

    Returns:
        ArgumentParser configured for omero-isa CLI
    """
```

Creates an argument parser with the following arguments:
- `project_name` (str): Name of the OMERO project to create
- `investigation_file` (str): Path to i_investigation.json
- `-u, --username` (str): OMERO username (required)
- `-w, --password` (str): OMERO password (required)
- `-s, --server` (str): OMERO server hostname (required)
- `-p, --port` (int): OMERO server port (default: 4064)

**Example:**

```python
parser = create_argument_parser()
args = parser.parse_args([
    '-u', 'admin',
    '-w', 'password',
    '-s', 'localhost',
    'My Project',
    '/path/to/i_investigation.json'
])
```

#### validate_investigation_file(file_path: str)

```python
def validate_investigation_file(file_path: str) -> Path:
    """Validate that the investigation file exists and is valid JSON.

    Args:
        file_path: Path to the investigation JSON file

    Returns:
        Path object for the validated file

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file is not JSON or contains invalid JSON
    """
```

**Example:**

```python
try:
    path = validate_investigation_file('/path/to/i_investigation.json')
except FileNotFoundError:
    print("File not found")
except ValueError:
    print("Invalid JSON")
```

#### connect_to_omero(username: str, password: str, server: str, port: int)

```python
def connect_to_omero(username: str, password: str, server: str, port: int) -> BlitzGateway:
    """Establish connection to OMERO server using BlitzGateway.

    Args:
        username: OMERO username
        password: OMERO password
        server: OMERO server hostname
        port: OMERO server port

    Returns:
        Connected BlitzGateway object

    Raises:
        ConnectionError: If connection fails
    """
```

**Example:**

```python
try:
    conn = connect_to_omero('admin', 'password', 'localhost', 4064)
    print(f"Connected as: {conn.getUser().getName()}")
    conn.close()
except ConnectionError as e:
    print(f"Connection failed: {e}")
```

#### import_arc_repository(conn: BlitzGateway, investigation_path: Path, project_name: str)

```python
def import_arc_repository(
    conn: BlitzGateway,
    investigation_path: Path,
    project_name: str
) -> object:
    """Import the ARC repository into OMERO.

    Args:
        conn: Connected BlitzGateway object
        investigation_path: Path to i_investigation.json
        project_name: Name of the OMERO project to create

    Returns:
        Created OMERO Project object

    Raises:
        RuntimeError: If import fails
    """
```

**Example:**

```python
from pathlib import Path

conn = connect_to_omero('admin', 'password', 'localhost', 4064)
path = Path('/path/to/i_investigation.json')

project = import_arc_repository(conn, path, 'My Project')
print(f"Created project: {project.getName()}")

conn.close()
```

#### main(argv: list = None)

```python
def main(argv: list = None) -> int:
    """Main entry point for the omero-isa CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code: 0 for success, 1 for error
    """
```

**Example:**

```python
# Direct call
exit_code = main([
    '-u', 'admin',
    '-w', 'password',
    '-s', 'localhost',
    'My Project',
    '/path/to/i_investigation.json'
])

# Via command line
# $ omero-isa -u admin -w password -s localhost "My Project" /path/to/i_investigation.json
```

---

## Module: omero_isa.isa_investigation_importer

Import ISA Investigation data into OMERO.

### Class: IsaInvestigationImporter

```python
class IsaInvestigationImporter:
    """Import ISA Investigation data into OMERO."""

    def __init__(self, investigation_data: dict, path_to_arc: Path):
        """Initialize the importer.

        Args:
            investigation_data: Parsed ISA investigation JSON
            path_to_arc: Path to the ARC repository root
        """

    def save(self, conn: BlitzGateway) -> object:
        """Import the investigation into OMERO.

        Args:
            conn: Connected BlitzGateway object

        Returns:
            Created OMERO Project object

        Raises:
            AssertionError: If investigation structure is invalid
            RuntimeError: If import fails
        """
```

**Example:**

```python
import json
from pathlib import Path
from omero.gateway import BlitzGateway
from omero_isa.isa_investigation_importer import IsaInvestigationImporter

# Load investigation JSON
with open('/path/to/i_investigation.json') as f:
    investigation_data = json.load(f)

# Connect to OMERO
conn = BlitzGateway(username='admin', password='password', host='localhost')
conn.connect()

# Create importer
importer = IsaInvestigationImporter(
    investigation_data=investigation_data,
    path_to_arc=Path('/path/to/arc')
)

# Import into OMERO
project = importer.save(conn)

print(f"Created project: {project.getId()}")

conn.close()
```

---

## Module: omero_isa.isa_packer

Export OMERO Projects to ISA format.

### Class: IsaPacker

```python
class IsaPacker:
    """Export OMERO Project to ISA format."""

    def __init__(
        self,
        ome_object: object,
        destination_path: Path,
        tmp_path: Path = None,
        image_filenames_mapping: dict = None,
        conn: BlitzGateway = None
    ):
        """Initialize the packer.

        Args:
            ome_object: OMERO Project object
            destination_path: Directory for exported ISA files
            tmp_path: Temporary directory for processing
            image_filenames_mapping: Mapping of image IDs to filenames
            conn: Connected BlitzGateway object
        """

    def pack(self) -> None:
        """Export OMERO project to ISA format.

        Raises:
            RuntimeError: If export fails
        """
```

**Example:**

```python
from pathlib import Path
from omero.gateway import BlitzGateway
from omero_isa.isa_packer import IsaPacker

# Connect to OMERO
conn = BlitzGateway(username='admin', password='password', host='localhost')
conn.connect()

# Get project
project = conn.getObject('Project', 414)

# Create packer
packer = IsaPacker(
    ome_object=project,
    destination_path=Path('/path/to/export/my-project'),
    conn=conn
)

# Export to ISA
packer.pack()

print("Export complete")

conn.close()
```

---

## Module: omero_isa.isa_mapping

Mapping utilities between OMERO and ISA formats.

### Functions

#### extract_metadata(omero_object: object) -> dict

```python
def extract_metadata(omero_object: object) -> dict:
    """Extract metadata from OMERO object.

    Args:
        omero_object: OMERO Project/Dataset/Image

    Returns:
        Dictionary of metadata
    """
```

#### create_omero_object(isa_data: dict, parent: object) -> object

```python
def create_omero_object(isa_data: dict, parent: object) -> object:
    """Create OMERO object from ISA data.

    Args:
        isa_data: ISA data dictionary
        parent: Parent OMERO object

    Returns:
        Created OMERO object
    """
```

---

## Common Data Structures

### ISA Investigation JSON

```json
{
  "identifier": "my-investigation-id",
  "title": "My Investigation",
  "description": "Investigation description",
  "submissionDate": "2024-01-01",
  "publicReleaseDate": "2024-01-01",
  "studies": [
    {
      "identifier": "my-study-id",
      "title": "My Study",
      "assays": [
        {
          "identifier": "my-assay-id",
          "filename": "a_assay.json",
          "materialAttributes": [],
          "characteristicCategories": []
        }
      ]
    }
  ]
}
```

### OMERO Project Structure

```python
project = conn.getObject('Project', project_id)
project.getName()        # str: Project name
project.getDescription() # str: Project description
project.getId()          # int: Project ID
project.countChildren()  # int: Number of datasets
project.listChildren()   # list: Dataset objects
```

### OMERO Dataset Structure

```python
dataset = project.listChildren()[0]
dataset.getName()        # str: Dataset name
dataset.getDescription() # str: Dataset description
dataset.getId()          # int: Dataset ID
dataset.countChildren()  # int: Number of images
dataset.listChildren()   # list: Image objects
```

### OMERO Image Structure

```python
image = dataset.listChildren()[0]
image.getName()          # str: Image name
image.getId()            # int: Image ID
image.countPixels()      # int: Number of pixel arrays
image.listAnnotations()  # list: Annotation objects
```

---

## Error Codes

| Error | Exit Code | Description |
|-------|-----------|-------------|
| FileNotFoundError | 1 | Investigation file not found |
| ValueError | 1 | Invalid JSON or invalid arguments |
| ConnectionError | 1 | Cannot connect to OMERO server |
| RuntimeError | 1 | Error during import/export |
| KeyboardInterrupt | 130 | User interrupted (Ctrl+C) |

---

## Environment Variables (Testing)

| Variable | Description |
|----------|-------------|
| OMERODIR | OMERO installation directory (for tests) |
| ICE_CONFIG | Ice configuration file path (for tests) |
| OMERO_SERVER | OMERO server hostname (override) |
| OMERO_PORT | OMERO server port (override) |
