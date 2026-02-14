# Examples

## Command-Line Usage

### Basic Import

```bash
# Simple import to local OMERO server
omero-isa -u admin -w password -s localhost "My Project" /path/to/i_investigation.json
```

### Import with Custom Port

```bash
# Import to remote OMERO server with custom port
omero-isa -u myuser -w mypass -s omero.company.com -p 4064 "Research Project" /data/isa/i_investigation.json
```

### Help and Version

```bash
# Show help
omero-isa --help

# Show help for import
omero-isa -h
```

### Error Handling

```bash
# File not found
$ omero-isa -u admin -w password -s localhost "My Project" /nonexistent.json
✗ Error: Investigation file not found: /nonexistent.json

# Invalid JSON
$ omero-isa -u admin -w password -s localhost "My Project" /invalid.json
✗ Validation Error: Invalid JSON in file /invalid.json

# Connection error
$ omero-isa -u admin -w password -s unreachable.host "My Project" /path/to/i_investigation.json
✗ Connection Error: Failed to connect to OMERO at unreachable.host:4064
```

---

## Python API Usage

### Example 1: Import ISA Data

```python
import json
from pathlib import Path
from omero.gateway import BlitzGateway
from omero_isa.isa_investigation_importer import IsaInvestigationImporter

# 1. Load ISA investigation file
with open('/path/to/i_investigation.json') as f:
    investigation_data = json.load(f)

# 2. Connect to OMERO
conn = BlitzGateway(
    username='admin',
    password='password',
    host='localhost',
    port=4064
)

if not conn.connect():
    raise ConnectionError("Failed to connect to OMERO")

# 3. Create importer
importer = IsaInvestigationImporter(
    investigation_data=investigation_data,
    path_to_arc=Path('/path/to/arc')
)

# 4. Import data
project = importer.save(conn)

# 5. Print results
print(f"Successfully created project:")
print(f"  ID: {project.getId()}")
print(f"  Name: {project.getName()}")

# 6. Close connection
conn.close()
```

### Example 2: Export OMERO Project

```python
from pathlib import Path
from omero.gateway import BlitzGateway
from omero_isa.isa_packer import IsaPacker

# 1. Connect to OMERO
conn = BlitzGateway(
    username='admin',
    password='password',
    host='localhost'
)
conn.connect()

# 2. Get project to export
project = conn.getObject('Project', 123)

# 3. Create packer
packer = IsaPacker(
    ome_object=project,
    destination_path=Path('/export/my-project'),
    conn=conn
)

# 4. Export to ISA format
packer.pack()

# 5. Verify export
export_dir = Path('/export/my-project')
assert (export_dir / 'i_investigation.json').exists()
print(f"Exported to: {export_dir}")

# 6. Close connection
conn.close()
```

### Example 3: Using CLI Programmatically

```python
from omero_isa.cli import main

# Run CLI as function
exit_code = main([
    '-u', 'admin',
    '-w', 'password',
    '-s', 'localhost',
    'My Project',
    '/path/to/i_investigation.json'
])

if exit_code == 0:
    print("Import successful")
else:
    print("Import failed")
```

### Example 4: Batch Import Multiple Projects

```python
from pathlib import Path
from omero.gateway import BlitzGateway
from omero_isa.isa_investigation_importer import IsaInvestigationImporter
import json

# List of investigation files to import
files_to_import = [
    '/data/project1/i_investigation.json',
    '/data/project2/i_investigation.json',
    '/data/project3/i_investigation.json',
]

# Connect to OMERO once
conn = BlitzGateway(username='admin', password='password', host='localhost')
conn.connect()

# Import each project
projects = []
for file_path in files_to_import:
    try:
        print(f"Importing {file_path}...")

        # Load data
        with open(file_path) as f:
            data = json.load(f)

        # Create importer
        importer = IsaInvestigationImporter(
            investigation_data=data,
            path_to_arc=Path(file_path).parent
        )

        # Import
        project = importer.save(conn)
        projects.append(project)

        print(f"  ✓ Created project: {project.getName()}")

    except Exception as e:
        print(f"  ✗ Error: {e}")

# Close connection
conn.close()

print(f"\nImported {len(projects)} projects successfully")
```

### Example 5: Error Handling

```python
import json
from pathlib import Path
from omero.gateway import BlitzGateway
from omero_isa.isa_investigation_importer import IsaInvestigationImporter

def safe_import(username, password, host, port, project_name, file_path):
    """Safely import ISA data with error handling."""

    try:
        # Validate file
        path = Path(file_path)
        if not path.exists():
            return False, f"File not found: {file_path}"

        if not path.suffix == '.json':
            return False, f"File must be JSON: {file_path}"

        # Load JSON
        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"

        # Connect to OMERO
        try:
            conn = BlitzGateway(
                username=username,
                password=password,
                host=host,
                port=port
            )
            if not conn.connect():
                return False, "Failed to connect to OMERO"
        except Exception as e:
            return False, f"Connection error: {e}"

        # Import
        try:
            importer = IsaInvestigationImporter(
                investigation_data=data,
                path_to_arc=path.parent
            )
            project = importer.save(conn)
            conn.close()

            return True, f"Created project {project.getName()} (ID: {project.getId()})"

        except AssertionError as e:
            conn.close()
            return False, f"Invalid ISA structure: {e}"
        except Exception as e:
            conn.close()
            return False, f"Import error: {e}"

    except Exception as e:
        return False, f"Unexpected error: {e}"


# Usage
success, message = safe_import(
    username='admin',
    password='password',
    host='localhost',
    port=4064,
    project_name='My Project',
    file_path='/path/to/i_investigation.json'
)

if success:
    print(f"✓ {message}")
else:
    print(f"✗ {message}")
```

---

## Working with ISA Data

### Example 6: Parse ISA Investigation Structure

```python
import json
from pathlib import Path

def explore_investigation(file_path):
    """Explore ISA investigation structure."""

    with open(file_path) as f:
        investigation = json.load(f)

    print(f"Investigation: {investigation.get('title')}")
    print(f"Identifier: {investigation.get('identifier')}")
    print(f"Description: {investigation.get('description')}")

    # Explore studies
    for study in investigation.get('studies', []):
        print(f"\n  Study: {study.get('title')}")
        print(f"  Identifier: {study.get('identifier')}")

        # Explore assays
        for assay in study.get('assays', []):
            print(f"    Assay: {assay.get('filename')}")
            print(f"    Identifier: {assay.get('identifier')}")

# Usage
explore_investigation('/path/to/i_investigation.json')
```

### Example 7: Access OMERO Project Data

```python
from omero.gateway import BlitzGateway

# Connect
conn = BlitzGateway(username='admin', password='password', host='localhost')
conn.connect()

# Get project
project = conn.getObject('Project', 123)

print(f"Project: {project.getName()}")
print(f"Description: {project.getDescription()}")

# List datasets
for dataset in project.listChildren():
    print(f"\n  Dataset: {dataset.getName()}")
    print(f"  Images: {dataset.countChildren()}")

    # List images
    for image in dataset.listChildren():
        print(f"    Image: {image.getName()}")
        print(f"    Size: {image.getSizeX()}x{image.getSizeY()}")

conn.close()
```

---
