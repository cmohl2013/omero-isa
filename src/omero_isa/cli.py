import argparse
import sys
import json
from pathlib import Path
from omero.gateway import BlitzGateway
from omero_isa.isa_investigation_importer import IsaInvestigationImporter


def create_argument_parser():
    """Create and return the argument parser for the omero-isa CLI."""
    parser = argparse.ArgumentParser(
        prog="omero-isa",
        description="Import ARC repositories into OMERO using ISA format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  omero-isa -u admin -w password -s localhost "My Project" /path/to/i_investigation.json
  omero-isa -u admin -w password -s omero.company.com -p 4064 "My Project" /path/to/i_investigation.json
        """
    )

    parser.add_argument(
        "project_name",
        type=str,
        help="Name of the project to create in OMERO"
    )

    parser.add_argument(
        "investigation_file",
        type=str,
        help="Path to the i_investigation.json file"
    )

    parser.add_argument(
        "-u", "--username",
        required=True,
        help="OMERO username"
    )

    parser.add_argument(
        "-w", "--password",
        required=True,
        help="OMERO password"
    )

    parser.add_argument(
        "-s", "--server",
        required=True,
        help="OMERO server hostname"
    )

    parser.add_argument(
        "-p", "--port",
        type=int,
        default=4064,
        help="OMERO server port (default: 4064)"
    )

    return parser


def validate_investigation_file(file_path):
    """Validate that the investigation file exists and is valid JSON."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Investigation file not found: {file_path}")

    if not path.suffix.lower() == ".json":
        raise ValueError(f"File must be a JSON file, got: {path.suffix}")

    try:
        with open(path, "r") as f:
            data = json.load(f)
        return path, data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {file_path}: {e}")


def connect_to_omero(username, password, server, port):
    """Establish connection to OMERO server using BlitzGateway."""
    try:
        conn = BlitzGateway(
            username,
            password,
            host=server,
            port=port
        )

        if conn.connect():
            print(f"✓ Successfully connected to OMERO at {server}:{port}")
            return conn
        else:
            raise ConnectionError(f"Failed to connect to OMERO at {server}:{port}")
    except Exception as e:
        raise ConnectionError(f"Connection error: {e}")


def import_arc_repository(conn, investigation_path, investigation_data, project_name):
    """Import the ARC repository into OMERO."""
    try:
        print(f"✓ Loading investigation file: {investigation_path}")

        # Create importer instance
        importer = IsaInvestigationImporter(
            data=investigation_data,
            path_to_arc=investigation_path,
            project_name=project_name
        )

        # Import the investigation
        print("▸ Importing ARC repository...")
        project = importer.save(conn)

        print(f"✓ Successfully imported ARC repository")
        print(f"  Project ID: {project.id}")
        print(f"  Project name: {project.name}")

        return project
    except Exception as e:
        raise RuntimeError(f"Failed to import ARC repository: {e}")


def main():
    """Main entry point for the omero-isa CLI."""
    parser = create_argument_parser()
    args = parser.parse_args()

    try:
        # Validate investigation file
        print("▸ Validating investigation file...")
        investigation_path, investigation_data = validate_investigation_file(
            args.investigation_file
        )

        # Connect to OMERO
        print(f"▸ Connecting to OMERO at {args.server}:{args.port}...")
        conn = connect_to_omero(
            username=args.username,
            password=args.password,
            server=args.server,
            port=args.port
        )

        # Import ARC repository
        project = import_arc_repository(
            conn,
            investigation_path,
            investigation_data,
            args.project_name
        )

        # Close connection
        conn.close()
        print("✓ Connection closed")
        print("\n✓ Import completed successfully!")
        return 0

    except FileNotFoundError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"✗ Validation Error: {e}", file=sys.stderr)
        return 1
    except ConnectionError as e:
        print(f"✗ Connection Error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"✗ Import Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n✗ Import cancelled by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())