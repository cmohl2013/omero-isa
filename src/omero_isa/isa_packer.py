"""
ISA Packer for exporting OMERO projects to ISA format.

This module provides functionality to export OMERO projects and their associated
data (datasets, images, metadata) back into ISA (Investigation, Study, Assay) format.
The export creates a complete ARC (Annotated Research Context) structure with:
- Investigation JSON file (i_investigation.json)
- ISA-Tab files (i_*.txt, s_*.txt, a_*.txt)
- Complete file hierarchy with images and ROI data

Classes:
    IsaPacker: Main packer class for exporting OMERO projects to ISA format

Functions:
    pack_isa: Convenience function to create and run IsaPacker

Author:
    Christoph Möhl

Version:
    0.0.0
"""
from pathlib import Path
from omero_isa.isa_mapping import OmeroProjectMapper, OmeroDatasetMapper


def pack_isa(ome_object, destination_path, tmp_path, image_filenames_mapping, conn):
    """Pack an OMERO project into ISA format.

    Convenience function that creates an IsaPacker instance and executes the
    packing workflow. This is the main entry point for exporting OMERO data
    to ISA format.

    Args:
        ome_object (omero.model.ProjectI): The OMERO Project object to export.
        destination_path (Path): Directory where the ISA files will be saved.
        tmp_path (Path): Temporary directory containing extracted image files.
        image_filenames_mapping (dict): Mapping of image IDs to filenames
            (e.g., {"Image:123": Path("image.tif")}).
        conn (omero.gateway.BlitzGateway): Active OMERO connection.

    Returns:
        None

    Raises:
        AssertionError: If ome_object is not a Project.
        RuntimeError: If packing fails during export.

    Examples:
        >>> pack_isa(
        ...     project,
        ...     Path('/path/to/export'),
        ...     Path('/tmp/images'),
        ...     image_mapping,
        ...     conn
        ... )

    Note:
        - Creates i_investigation.json and ISA-Tab files
        - Requires all image files to be present in tmp_path
        - All OMERO datasets are converted to ISA assays
    """
    packer = IsaPacker(
        ome_object, destination_path, tmp_path, image_filenames_mapping, conn
    )
    packer.pack()


class IsaPacker(object):
    """Pack an OMERO project into ISA format.

    Converts an OMERO project and its associated datasets, images, and metadata
    into ISA (Investigation, Study, Assay) format. The packing process:
    1. Maps OMERO Project → ISA Investigation
    2. Maps OMERO Datasets → ISA Assays
    3. Maps OMERO Images → ISA DataFiles
    4. Exports all metadata to JSON and ISA-Tab formats
    5. Organizes files in ARC directory structure

    Attributes:
        obj (omero.model.ProjectI): The OMERO Project to pack.
        destination_path (Path): Output directory for ISA files.
        conn (omero.gateway.BlitzGateway): Active OMERO connection.
        image_filenames_mapping (dict): Maps image IDs to filenames.
        path_to_image_files (Path): Path to extracted image files.
        isa_assay_mappers (list): List of OmeroDatasetMapper instances.
        ome_dataset_for_isa_assay (dict): Maps datasets to assays.

    Examples:
        >>> packer = IsaPacker(
        ...     project,
        ...     Path('/export/path'),
        ...     Path('/tmp/images'),
        ...     image_mapping,
        ...     conn
        ... )
        >>> packer.pack()
        >>> # Creates i_investigation.json and related files

    Raises:
        AssertionError: If ome_object is not a Project (OMERO_CLASS != "Project").

    Note:
        - The project must have valid metadata annotations
        - All datasets will become ISA assays
        - Image files must be available in path_to_image_files
    """

    def __init__(
        self,
        ome_object,
        destination_path: Path,
        tmp_path,
        image_filenames_mapping,
        conn,
    ):
        """Initialize the IsaPacker.

        Args:
            ome_object (omero.model.ProjectI): The OMERO Project to export.
                Must have OMERO_CLASS == "Project".
            destination_path (Path): Directory where ISA files will be saved.
            tmp_path (Path): Temporary directory with extracted image files.
            image_filenames_mapping (dict): Maps image IDs to filename paths.
                Format: {"Image:123": Path("image.tif")}
            conn (omero.gateway.BlitzGateway): Active OMERO connection.

        Raises:
            AssertionError: If ome_object is not a Project.
        """
        assert ome_object.OMERO_CLASS == "Project"
        self.obj = ome_object  # must be a project
        self.destination_path = destination_path
        self.conn = conn
        self.image_filenames_mapping = image_filenames_mapping
        self.path_to_image_files = tmp_path

        self.isa_assay_mappers = []
        self.ome_dataset_for_isa_assay = {}

    def pack(self):
        """Execute the packing workflow to export OMERO project to ISA format.

        Orchestrates the complete export process:
        1. Creates OmeroProjectMapper from OMERO Project
        2. Retrieves all datasets from the project
        3. Maps each dataset to ISA assay using OmeroDatasetMapper
        4. Saves investigation as JSON and ISA-Tab formats

        The process preserves all metadata annotations and creates a complete
        ARC directory structure with proper file organization.

        Returns:
            None

        Raises:
            AssertionError: If investigation doesn't contain exactly one study.
            RuntimeError: If save operation fails.

        Examples:
            >>> packer = IsaPacker(project, dest_path, tmp_path, mapping, conn)
            >>> packer.pack()
            >>> # Files are now available in destination_path

        Note:
            - All datasets are converted to assays in the single study
            - Images are organized by dataset/assay
            - ROI data is included as JSON files
            - Creates both JSON and ISA-Tab format files
        """
        project_mapper = OmeroProjectMapper(self.obj)
        project_mapper._create_investigation()

        ome_project = self.obj
        project_id = ome_project.getId()

        ome_datasets = self.conn.getObjects("Dataset", opts={"project": project_id})

        def _filename_for_image(image_id):
            """Get the filename for an image by ID.

            Args:
                image_id (int): The OMERO image ID.

            Returns:
                str: The filename associated with the image.
            """
            return self.image_filenames_mapping[f"Image:{image_id}"].name

        investigation = project_mapper.investigation

        assert len(investigation.studies) == 1
        study = investigation.studies[0]

        for dataset in ome_datasets:
            dataset_mapper = OmeroDatasetMapper(
                dataset,
                self.conn,
                self.path_to_image_files,
                self.image_filenames_mapping,
                self.destination_path,
                image_filename_getter=_filename_for_image,
            )
            self.isa_assay_mappers.append(dataset_mapper)
            study.assays.append(dataset_mapper.assay)

        project_mapper.save_as_tab(self.destination_path)
        project_mapper.save_as_json(self.destination_path)
