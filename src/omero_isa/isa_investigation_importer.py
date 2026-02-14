"""
ISA Investigation Importer for OMERO.

This module provides functionality to import ISA (Investigation, Study, Assay) format
data into OMERO database. It handles the creation of projects, datasets, images, and
associated metadata from ISA JSON files.

The import workflow follows this structure:
- Investigation → OMERO Project
- Study → OMERO Project
- Assay → OMERO Dataset
- DataFile → OMERO Image

Classes:
    IsaInvestigationImporter: Main importer class for ISA investigations
    ImageFactory: Factory for creating and importing images
    DatasetFactory: Factory for creating and importing datasets
    MappedAnnotationFactory: Factory for creating mapped annotations

Functions:
    import_and_tag_image: Import image file using OMERO CLI
    link: Link two OMERO objects together

Author:
    Christoph Möhl

Version:
    0.0.0
"""
from omero import rtypes, model
from omero.model import ProjectI, MapAnnotationI, DatasetI, NamedValue, Annotation, ImageI
import subprocess
from omero_isa.roi import import_rois_from_json


def import_and_tag_image(conn, file_path, dataset_id, name, description):
    """Import and tag an image file into OMERO using the OMERO CLI.

    Uses the OMERO command-line interface to import an image file into a specified
    dataset. The import leverages the existing OMERO session to avoid re-authentication.

    Args:
        conn (omero.gateway.BlitzGateway): Active OMERO connection.
        file_path (str or Path): Full path to the image file to import.
        dataset_id (int): ID of the OMERO Dataset to import the image into.
        name (str): Display name for the imported image in OMERO.
        description (str): Description text for the imported image.

    Returns:
        omero.model.ImageI or None: The created Image object if successful,
            None if the import failed.

    Raises:
        subprocess.CalledProcessError: If the OMERO CLI command fails to execute.

    Examples:
        >>> conn = connect_to_omero('admin', 'password', 'localhost', 4064)
        >>> dataset_id = 123
        >>> image = import_and_tag_image(
        ...     conn,
        ...     '/path/to/image.tif',
        ...     dataset_id,
        ...     'My Image',
        ...     'Image description'
        ... )
        >>> print(image.getId()._val)
        456

    Note:
        - Uses session key (-k flag) for authentication, no password needed
        - Extracts image ID from CLI output (format: "Image:123")
        - Prints progress and error messages to stdout/stderr
    """
    # 1. Extract connection details from existing connection
    host = conn.host
    port = conn.port
    session_id = conn.c.getSessionId()

    # 2. Build CLI command using session key (no password needed!)
    cmd = [
        "omero", "import", file_path,
        "-s", str(host),
        "-p", str(port),
        "-k", str(session_id),
        "-d", str(dataset_id),
        "--name", name,
        "--description", description
    ]

    # 3. Execute import command
    print(f"Start importing: {name}...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Success: File was imported as '{name}'.")
        # Extract image ID from CLI output (e.g., "Image:123")
        for line in result.stdout.splitlines():
            if line.startswith("Image:"):
                image_id = int(line.split(":")[1].split(",")[0])
                return conn.getObject("Image", image_id)
    else:
        print("Import error:")
        print(result.stderr)
        return None



class IsaInvestigationImporter:
    """Main importer class for ISA investigations into OMERO.

    Handles the import of an entire ISA investigation (which contains exactly one study)
    into an OMERO project. This class coordinates the creation of the project, datasets
    (from assays), and images, along with all associated metadata and annotations.

    The class expects ISA JSON data in a specific format with assertions on the structure:
    - Must contain exactly one study
    - Study data must include necessary metadata for annotation

    Attributes:
        project_name (str): Name for the created OMERO project. Defaults to study title.
        data (dict): The full ISA investigation JSON data.
        study_data (dict): The first (and only) study in the investigation.
        assay_data (list or None): List of assays within the study, or None if empty.
        path_to_arc (Path): Path to the ARC (Annotated Research Context) directory.

    Examples:
        >>> from pathlib import Path
        >>> import json
        >>> investigation_path = Path('/path/to/i_investigation.json')
        >>> with open(investigation_path) as f:
        ...     data = json.load(f)
        >>> importer = IsaInvestigationImporter(
        ...     data=data,
        ...     path_to_arc=investigation_path.parent,
        ...     project_name="My ISA Project"
        ... )
        >>> project = importer.save(conn)
        >>> print(f"Created project: {project.getName()._val}")
        Created project: My ISA Project

    Note:
        - Asserts that exactly one study exists in the investigation
        - Asserts that investigation data contains proper annotation structure
        - All image file paths are relative to the ARC root directory
    """

    def __init__(self, data, path_to_arc, project_name=None):
        """Initialize the ISA investigation importer.

        Args:
            data (dict): Parsed ISA investigation JSON data containing studies.
            path_to_arc (Path): Path to the ARC root directory containing image files.
            project_name (str, optional): Custom name for the OMERO project.
                If None, defaults to the study title. Defaults to None.

        Raises:
            AssertionError: If investigation doesn't contain exactly one study or
                if required annotation metadata is missing.
        """
        # one isa investigation must contain exactly one study
        # the study relates to the omero project
        assert "studies" in data.keys()
        assert len(data["studies"]) == 1

        self.project_name = project_name
        self.data = data
        self.study_data = data["studies"][0]
        self.assay_data = self.study_data.get("assays", None)
        self.path_to_arc = path_to_arc

    def _add_datasets(self, parent_object, conn):
        """Add OMERO datasets (created from ISA assays) to the project.

        Creates a Dataset for each assay in the study and links them to the parent
        project object. Each dataset will include all associated images and metadata.

        Args:
            parent_object (omero.model.ProjectI): The parent OMERO project object.
            conn (omero.gateway.BlitzGateway): Active OMERO connection.

        Returns:
            None

        Note:
            - Skips processing if no assays are present (assay_data is None)
            - Each assay creates one dataset via DatasetFactory
        """
        if self.assay_data is not None:
            for assay_item in self.assay_data:
                dataset = DatasetFactory(assay_item, self.path_to_arc)
                dataset.save(conn, parent_object)

    def _add_mapped_annotations(self, parent_object, conn):
        """Add all mapped annotations from investigation and study data.

        Extracts and creates mapped annotations from various levels of the ISA
        investigation hierarchy:
        - Investigation-level annotations
        - Study-level annotations
        - Nested list and dict annotations

        Args:
            parent_object (omero.model.ProjectI): The parent OMERO project object.
            conn (omero.gateway.BlitzGateway): Active OMERO connection.

        Returns:
            None

        Note:
            - Silently skips data that doesn't contain annotation metadata
            - Processes both dict and list type data structures
            - Handles AssertionErrors gracefully during annotation creation
        """
        try:
            maf = MappedAnnotationFactory(self.data)
            maf.save(conn, parent_object=parent_object)
        except AssertionError:
            pass

        for k in self.data.keys():
            d = self.data[k]
            if isinstance(d, list):
                for e in d:
                    try:
                        maf = MappedAnnotationFactory(e)
                        maf.save(conn, parent_object=parent_object)
                    except AssertionError:
                        pass
            else:
                try:
                    maf = MappedAnnotationFactory(self.data[k])
                    maf.save(conn, parent_object=parent_object)
                except AssertionError:
                    pass

        for k in self.study_data.keys():
            if k == "assays":
                continue
            study_data_item = self.study_data[k]
            if isinstance(study_data_item, dict):
                try:
                    maf = MappedAnnotationFactory(self.study_data[k])
                    maf.save(conn, parent_object=parent_object)
                except AssertionError:
                    pass
            elif isinstance(study_data_item, list):
                for item in study_data_item:
                    try:
                        maf = MappedAnnotationFactory(item)
                        maf.save(conn, parent_object=parent_object)
                    except AssertionError:
                        pass



    def save(self, conn):
        """Save the ISA investigation as a new OMERO project.

        Creates the OMERO project from the ISA investigation data, adds all
        metadata annotations, and creates associated datasets from assays.

        Args:
            conn (omero.gateway.BlitzGateway): Active OMERO connection.

        Returns:
            omero.model.ProjectI: The created OMERO project object with all
                imported data including datasets, images, and annotations.

        Raises:
            RuntimeError: If the project creation or save operation fails.

        Examples:
            >>> project = importer.save(conn)
            >>> print(project.getName()._val)
            'My ISA Project'
        """
        if self.project_name is None:
            self.project_name = self.study_data.get("title", "no_study_title")
        project_description = self.study_data.get("description", "")
        project = ProjectI()
        project.setName(rtypes.rstring(self.project_name))
        project.setDescription(rtypes.rstring(project_description))

        # Save the project to the server
        project = conn.getUpdateService().saveAndReturnObject(project)
        self._add_mapped_annotations(project, conn)
        self._add_datasets(project, conn)
        return project




class ImageFactory:
    """Factory class for creating and importing images into OMERO.

    Handles the creation and import of image files into OMERO datasets. Extracts
    metadata from ISA data structures and manages image file imports using the
    OMERO CLI. Also handles associated ROI (Region of Interest) data if present.

    Attributes:
        data (dict): The ISA data structure containing image metadata and file info.
        path_to_arc (Path): Path to the ARC root directory.

    Examples:
        >>> image_data = {
        ...     'name': 'assays/my-assay/dataset/image.tif',
        ...     'comments': [
        ...         {'name': 'name', 'value': 'My Image'},
        ...         {'name': 'description', 'value': 'Image description'}
        ...     ]
        ... }
        >>> factory = ImageFactory(image_data, Path('/path/to/arc'))
        >>> image = factory.save(conn, parent_dataset)

    Raises:
        AssertionError: If data is not a dict or required fields are missing.
        ValueError: If image file path is invalid or file doesn't exist.
    """

    def __init__(self, data, path_to_arc):
        """Initialize the ImageFactory.

        Args:
            data (dict): ISA data structure containing image metadata and filename.
            path_to_arc (Path): Path to the ARC root directory.

        Raises:
            AssertionError: If data is not a dictionary.
        """
        assert isinstance(data, dict)
        self.data = data
        self.path_to_arc = path_to_arc

    def save(self, conn, parent_object=None):
        """Save and import an image file into OMERO.

        Extracts image metadata from ISA data, uploads the image file using OMERO CLI,
        and imports any associated ROI data if present.

        Args:
            conn (omero.gateway.BlitzGateway): Active OMERO connection.
            parent_object (omero.model.DatasetI, optional): Parent dataset object
                to import the image into. Defaults to None.

        Returns:
            omero.model.ImageI: The imported OMERO Image object.

        Raises:
            ValueError: If 'name' key is missing from data.
            AssertionError: If image file or ROI file doesn't exist.

        Note:
            - Image metadata is extracted from 'comments' field
            - Supported metadata: name, description, roidata_filename
            - ROI data is optional but will be imported if present
        """
        img_name = ""
        img_description = ""
        roidata_filename = None
        for comment in self.data["comments"]:
            if comment["name"] == "name":
                img_name = comment["value"]
            elif comment["name"] == "description":
                img_description = comment["value"]
            elif comment["name"] == "roidata_filename":
                roidata_filename = comment["value"]

        # Ensure the file path exists in the data
        file_path = self.data.get("name")
        if not file_path:
            raise ValueError("The 'name' key must be present in the data and point to a valid file path.")

        image_filepath = self.path_to_arc.parent / file_path
        assert image_filepath.exists(), image_filepath

        # Upload the image file to OMERO
        image = import_and_tag_image(
            conn,
            image_filepath,
            parent_object.getId()._val,
            img_name,
            img_description,
        )

        if roidata_filename is not None:
            roidata_filepath = image_filepath.parent / roidata_filename
            assert roidata_filepath.exists(), f"ROI file not found: {roidata_filepath}"

            roi = import_rois_from_json(
                roidata_filepath,
                image,
                conn
            )





class DatasetFactory:
    """Factory class for creating and importing OMERO datasets from ISA assays.

    Converts ISA assay data into OMERO datasets, managing the creation of datasets,
    importing associated images, and adding metadata annotations.

    Attributes:
        data (dict): The ISA assay data structure.
        path_to_arc (Path): Path to the ARC root directory.

    Examples:
        >>> assay_data = {
        ...     'identifier': 'my-assay',
        ...     'comments': [
        ...         {'name': 'identifier', 'value': 'my-assay-id'}
        ...     ],
        ...     'dataFiles': [...]
        ... }
        >>> factory = DatasetFactory(assay_data, Path('/path/to/arc'))
        >>> dataset = factory.save(conn, parent_project)

    Raises:
        AssertionError: If data is not a dict or missing required fields.
    """

    def __init__(self, data, path_to_arc):
        """Initialize the DatasetFactory.

        Args:
            data (dict): ISA assay data structure.
            path_to_arc (Path): Path to the ARC root directory.

        Raises:
            AssertionError: If data is not a dictionary.
        """
        assert isinstance(data, dict)
        self.data = data
        self.path_to_arc = path_to_arc

    def _add_mapped_annotations(self, parent_object, conn):
        """Add mapped annotations from assay data to the dataset.

        Args:
            parent_object (omero.model.DatasetI): The parent dataset object.
            conn (omero.gateway.BlitzGateway): Active OMERO connection.

        Returns:
            None
        """
        try:
            maf = MappedAnnotationFactory(self.data)
            maf.save(conn, parent_object=parent_object)
        except AssertionError:
            pass

        for k in self.data.keys():
            d = self.data[k]
            if isinstance(d, list):
                for e in d:
                    try:
                        maf = MappedAnnotationFactory(e)
                        maf.save(conn, parent_object=parent_object)
                    except AssertionError:
                        pass
            else:
                try:
                    maf = MappedAnnotationFactory(self.data[k])
                    maf.save(conn, parent_object=parent_object)
                except AssertionError:
                    pass

    def _add_images(self, parent_object, conn):
        """Add images from ISA data files to the dataset.

        Filters dataFiles to find images marked as 'Raw Image Data File' and
        imports them into the dataset.

        Args:
            parent_object (omero.model.DatasetI): The parent dataset object.
            conn (omero.gateway.BlitzGateway): Active OMERO connection.

        Returns:
            None
        """
        images_data = self.data.get("dataFiles", None)

        if images_data is None:
            return

        for image_data in images_data:
            if image_data.get("type", None) == "Raw Image Data File":
                img = ImageFactory(image_data, self.path_to_arc)
                img.save(conn, parent_object)

    def save(self, conn, parent_object=None):
        """Save and create an OMERO dataset from ISA assay data.

        Creates the dataset, adds metadata annotations, imports associated images,
        and links to parent project.

        Args:
            conn (omero.gateway.BlitzGateway): Active OMERO connection.
            parent_object (omero.model.ProjectI, optional): Parent project object
                to link the dataset to. Defaults to None.

        Returns:
            omero.model.DatasetI: The created OMERO dataset object.

        Raises:
            AssertionError: If 'comments' field is missing or has no identifier.
        """
        comments = self.data.get("comments", None)
        assert comments is not None
        for comment in comments:
            assert isinstance(comment, dict)
            if comment.get("name", None) == "identifier":
                dataset_name = comment.get("value")
                break

        dataset = DatasetI()
        dataset.setName(rtypes.rstring(dataset_name))

        # Save the dataset to the server
        dataset = conn.getUpdateService().saveAndReturnObject(dataset)
        self._add_mapped_annotations(dataset, conn)
        self._add_images(dataset, conn)

        if parent_object is not None:
            link(parent_object, dataset, conn)

        return dataset





class MappedAnnotationFactory:
    """Factory class for creating mapped annotations from ISA data structures.

    Converts ISA metadata dictionaries into OMERO MapAnnotation objects. Extracts
    namespace information and handles ontology-annotated fields with term accessions
    and sources.

    Attributes:
        namespace (str): The annotation namespace from ISA comments.
        data (dict): The original ISA data structure.
        mapping (dict): Processed key-value pairs for the MapAnnotation.
        map_annotation (omero.model.MapAnnotationI): The created MapAnnotation object.

    Examples:
        >>> data = {
        ...     'identifier': 'my-assay-1',
        ...     'title': 'My Assay',
        ...     'comments': [
        ...         {'name': 'omero_annotation_namespace', 'value': 'ISA:ASSAY:ASSAY'},
        ...         {'name': 'identifier', 'value': 'my-assay-id'}
        ...     ]
        ... }
        >>> factory = MappedAnnotationFactory(data)
        >>> annotation = factory.save(conn, parent_project)

    Raises:
        AssertionError: If data doesn't contain required 'comments' field or
            if comments don't have proper namespace annotation.
    """

    def __init__(self, data):
        """Initialize the MappedAnnotationFactory.

        Args:
            data (dict): ISA data structure containing metadata and comments.

        Raises:
            AssertionError: If data is not a dict, doesn't contain 'comments',
                or comments don't have 'omero_annotation_namespace' as first entry.
        """
        assert isinstance(data, dict)
        assert "comments" in data.keys()
        assert len(data["comments"]) >= 1
        assert data["comments"][0].get("name", None) is not None
        assert data["comments"][0].get("value", None) is not None

        assert data["comments"][0]["name"] == "omero_annotation_namespace"
        self.namespace = data["comments"][0]["value"]
        self.data = data

        mapping = {}

        ontology_annotation_keys = ["termAccession", "termSource", "annotationValue"]

        for k, v in data.items():

            if not isinstance(v, (list, dict)):
                mapping[k] = v

            # ontology annotation keys are prefixed with the parent key
            if isinstance(v, dict):

                if set(ontology_annotation_keys).issubset(set(v.keys())):
                    mapping[f"{k}_term"] = v["annotationValue"]
                    mapping[f"{k}_term_accession"] = v["termAccession"]
                    mapping[f"{k}_term_source"] = v["termSource"]

        self.mapping = mapping

        self._create_mapped_annotation()

    def _create_mapped_annotation(self):
        """Create the MapAnnotation object from the processed mapping.

        Constructs an OMERO MapAnnotationI object with all key-value pairs
        and sets the namespace.

        Returns:
            None
        """
        map_annotation = MapAnnotationI()
        map_value_ls = [
            NamedValue(str(key), str(self.mapping[key])) for key in self.mapping
        ]
        map_annotation.setMapValue(map_value_ls)

        map_annotation.setNs(rtypes.rstring(self.namespace))

        self.map_annotation = map_annotation

    def save(self, conn, parent_object=None):
        """Save the mapped annotation to OMERO.

        Persists the MapAnnotation to the OMERO database and optionally links it
        to a parent object (Project, Dataset, or Image).

        Args:
            conn (omero.gateway.BlitzGateway): Active OMERO connection.
            parent_object (omero.model.ModelObject, optional): Parent OMERO object
                to link the annotation to. Defaults to None.

        Returns:
            omero.model.AnnotationLinkI: The annotation link object.

        Raises:
            RuntimeError: If the save operation fails.
        """
        map_ann = conn.getUpdateService().saveAndReturnObject(self.map_annotation)

        if parent_object is not None:
            link(parent_object, self.map_annotation, conn)





def link(obj1, obj2, conn):
    """Link two OMERO objects together.

    Creates a link between two OMERO model objects by instantiating the correct
    link class (e.g. ProjectDatasetLinkI, DatasetImageLinkI, etc) and persisting
    it to the database. Automatically handles parent-child relationships and
    properly proxies objects when necessary.

    Args:
        obj1 (omero.model.ModelObject): Parent object to link from.
        obj2 (omero.model.ModelObject or Annotation): Child object to link to.
        conn (omero.gateway.BlitzGateway): Active OMERO connection for saving.

    Returns:
        omero.model.LinkI: The created and persisted link object.

    Raises:
        AssertionError: If the object types are not linkable or not supported
            by the OMERO model.

    Examples:
        >>> project = conn.getObject("Project", project_id)
        >>> dataset = conn.getObject("Dataset", dataset_id)
        >>> link(project, dataset, conn)

    Note:
        - Automatically determines the correct link class based on object types
        - Handles both new (id=None) and existing (id set) objects
        - Annotations are always treated as child objects
        - Uses proxy() for objects with existing IDs to avoid conflicts
    """
    otype1 = obj1.ice_staticId().split("::")[-1]
    if isinstance(obj2, Annotation):
        otype2 = "Annotation"
    else:
        otype2 = obj2.ice_staticId().split("::")[-1]
    try:
        linktype = getattr(model, "%s%sLinkI" % (otype1, otype2))
    except AttributeError:
        assert False, "Object type not supported."

    link = linktype()

    # Check if object exist or not
    if obj1.id is None:
        link.setParent(obj1)
    else:
        link.setParent(obj1.proxy())
    if obj2.id is None:
        link.setChild(obj2)
    else:
        link.setChild(obj2.proxy())
    return conn.getUpdateService().saveAndReturnObject(link)