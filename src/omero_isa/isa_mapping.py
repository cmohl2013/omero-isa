"""
ISA data mapping for OMERO import/export operations.

This module provides mapping functionality to convert between OMERO data structures
and ISA (Investigation, Study, Assay) format. It handles:
- Extraction of metadata from OMERO objects via annotations
- Creation of ISA-compliant Investigation, Study, and Assay objects
- Export to ISA-Tab and JSON formats
- Management of ontology annotations and comments

The mapping preserves namespace information to facilitate round-trip import/export
of OMERO data in ISA format.

Classes:
    AbstractIsaMapper: Base class for ISA mapper implementations
    OmeroDatasetMapper: Maps OMERO datasets to ISA assays
    OmeroProjectMapper: Maps OMERO projects to ISA investigations

Functions:
    get_image_metadata_omero: Extract image metadata from OMERO image object

Author:
    Christoph Möhl

Version:
    0.0.0
"""
from isatools.model import Study, Investigation, Publication, OntologyAnnotation, OntologySource, Assay, DataFile, Person, Comment
from isatools import isatab
import json
from isatools.isajson import ISAJSONEncoder

from pathlib import Path

from functools import lru_cache
import os
import shutil

from omero_isa.roi import export_rois_to_json


def get_image_metadata_omero(image):
    """Extract metadata from an OMERO image object.

    Retrieves comprehensive image metadata including dimensions, pixel sizes,
    acquisition time, and ownership information. Creates Comment objects for
    each metadata field in ISA format.

    Args:
        image (omero.model.ImageI): The OMERO image object to extract metadata from.

    Returns:
        list: List of Comment objects containing image metadata with keys:
            - omero_image_id: OMERO image ID
            - name: Image name
            - description: Image description
            - acquisition_time: ISO format acquisition timestamp
            - omero_image_owner: Image owner username
            - image_size_x: Image width in pixels
            - image_size_y: Image height in pixels
            - image_size_z: Image depth in Z slices
            - pixel_size_x: X pixel size
            - pixel_size_y: Y pixel size
            - pixel_size_z: Z pixel size
            - pixel_size_unit: Unit for pixel sizes

    Examples:
        >>> image = conn.getObject("Image", 123)
        >>> metadata = get_image_metadata_omero(image)
        >>> for comment in metadata:
        ...     print(f"{comment.name}: {comment.value}")
        omero_image_id: 123
        name: My Image
        ...

    Note:
        - Pixel unit is extracted from image's pixel size metadata
        - Returns None for pixel_size_unit if no unit is defined
        - All metadata values are converted to strings
    """

    def _pixel_unit(image):
        """Get pixel size unit from image metadata.

        Args:
            image (omero.model.ImageI): OMERO image object.

        Returns:
            str or None: The unit string or None if not set.
        """
        pix = image.getPixelSizeX(units=True)
        if pix is None:
            return
        return pix.getUnit()

    isa_column_mapping = {
        "omero_image_id": image.getId(),
        "name": image.getName(),
        "description": image.getDescription(),
        "acquisition_time": image.getDate().isoformat(),
        "omero_image_owner": image.getAuthor(),
        "image_size_x": image.getSizeX(),
        "image_size_y": image.getSizeY(),
        "image_size_z": image.getSizeZ(),
        "pixel_size_x": image.getPixelSizeX(),
        "pixel_size_y": image.getPixelSizeY(),
        "pixel_size_z": image.getPixelSizeZ(),
        "pixel_size_unit": _pixel_unit(image),
    }

    return [Comment(k, str(isa_column_mapping[k])) for k in isa_column_mapping]


class AbstractIsaMapper:
    """Abstract base class for ISA mapping implementations.

    Provides common functionality for extracting metadata annotations from OMERO
    objects and creating ISA-compliant data structures. Handles namespace-based
    annotation filtering and ontology annotation processing.

    Attributes:
        obj (omero.model.ModelObject): The OMERO object being mapped.
        isa_attribute_config (dict): Configuration for ISA attribute mapping.
        isa_attributes (dict): Processed ISA attributes.

    Note:
        - Subclasses must define isa_attribute_config in __init__
        - Caches annotation objects for performance
        - Handles both flat and ontology-annotated values
    """

    def _create_isa_attributes(self):
        """Create ISA attributes from OMERO annotations.

        Processes OMERO map annotations based on namespace configuration and
        creates ISA-compliant attribute structures. Handles:
        - Namespace filtering
        - Ontology annotation extraction
        - Default value application
        - Comment namespace preservation

        Returns:
            None (sets self.isa_attributes)

        Note:
            - Ontology annotations are prefixed in the source data (e.g., "term_source")
            - Creates separate ontology_values for ontology-annotated fields
            - Applies default values when annotations are missing
            - Preserves namespace in comments for round-trip compatibility
        """
        isa_attributes = {}

        for annotation_type in self.isa_attribute_config:
            annotation_data = self._annotation_data(annotation_type)
            config = self.isa_attribute_config[annotation_type]

            ontology_config = config.get("ontology_annotations", None)
            ontology_annotation_attributes = []

            for i in range(len(annotation_data)):
                ontology_annotation_attribute = {}
                if ontology_config is not None:

                    for ont in ontology_config:

                        ontology_annotation = {}
                        ontology_annotation = {k.replace(f"{ont}_", ''): v for k, v in annotation_data[i].items() if ont in k}
                        annotation_data[i] = {k: v for k, v in annotation_data[i].items() if ont not in k}

                        source_annotation = ontology_annotation.get("term_source", None)
                        if source_annotation is not None:
                            ontology_annotation["term_source"] = OntologySource(ontology_annotation["term_source"])
                        ontology_annotation_attribute[ont] = OntologyAnnotation(**ontology_annotation)

                ontology_annotation_attributes.append(ontology_annotation_attribute)

            isa_attributes[annotation_type] = {}
            isa_attributes[annotation_type]["values"] = []
            isa_attributes[annotation_type]["ontology_values"] = ontology_annotation_attributes

            values_to_set = {}

            if len(annotation_data) == 0:
                # set defaults if no annotations available
                for key in config["default_values"]:
                    value = config["default_values"][key]
                    if value is not None:
                        values_to_set[key] = value
                if len(values_to_set) > 0:
                    isa_attributes[annotation_type]["values"].append(values_to_set)
                    isa_attributes[annotation_type]["ontology_values"].append({})

            else:
                # set annotation value if key is registered in config["default_values"]
                for annotation in annotation_data:
                    for key in config["default_values"]:
                        value = annotation.get(key, config["default_values"][key])
                        if value is not None:
                            values_to_set[key] = value
                    if len(values_to_set) > 0:
                        isa_attributes[annotation_type]["values"].append(
                            values_to_set.copy()
                        )

            if len(isa_attributes[annotation_type]["values"]) == 0:
                del isa_attributes[annotation_type]
            else:
                assert len(isa_attributes[annotation_type]["values"]) == len(isa_attributes[annotation_type]["ontology_values"])

            # OMERO metadata export: namespaces are saved in ISA comments
            # to facilitate ISA import back to OMERO
            self.isa_attributes = isa_attributes

            if annotation_type in isa_attributes.keys():
                for i in range(len(isa_attributes[annotation_type]["values"])):
                    isa_attributes[annotation_type]["values"][i]["comments"] = [Comment("omero_annotation_namespace", config["namespace"])]
                    self.isa_attributes = isa_attributes

    @lru_cache
    def _all_annotatation_objects(self):
        """Get all annotation objects from the OMERO object.

        Returns:
            list: List of all annotation objects.
        """
        return [a for a in self.obj.listAnnotations()]

    def _annotation_data(self, annotation_type):
        """Extract annotation data matching a specific namespace.

        Args:
            annotation_type (str): The annotation type (key in isa_attribute_config).

        Returns:
            list: List of dicts containing annotation key-value pairs.
        """
        namespace = self.isa_attribute_config[annotation_type]["namespace"]
        annotation_data = []
        for annotation in self._all_annotatation_objects():
            if annotation.getNs() == namespace:
                annotation_data.append(dict(annotation.getValue()))
        return annotation_data


class OmeroDatasetMapper(AbstractIsaMapper):
    """Maps an OMERO dataset to an ISA assay.

    Converts an OMERO dataset and its associated images into ISA assay format.
    Handles image file organization, metadata extraction, and ROI data export.

    Attributes:
        obj (omero.model.DatasetI): The OMERO dataset being mapped.
        conn (omero.gateway.BlitzGateway): Active OMERO connection.
        destination_path (Path): Path where assay files will be saved.
        path_omero_data (Path): Path to extracted OMERO image files.
        image_filenames_mapping (dict): Maps image IDs to filenames.
        assay_identifier (str): Unique identifier for the assay.
        assay (isatools.model.Assay): The created ISA Assay object.

    Examples:
        >>> mapper = OmeroDatasetMapper(
        ...     dataset,
        ...     conn,
        ...     Path('/tmp/images'),
        ...     image_mapping,
        ...     Path('/export/path')
        ... )
        >>> assay = mapper.assay
        >>> print(assay.filename)
        'a_my-assay.txt'

    Note:
        - Images are automatically copied to assay directory structure
        - ROI data is exported as JSON files alongside images
        - All image metadata is preserved in assay data files
    """

    def __init__(self,
                 ome_dataset,
                 conn,
                 path_omero_data,
                 image_filenames_mapping,
                 destination_path,
                 image_filename_getter=None):
        """Initialize the OmeroDatasetMapper.

        Args:
            ome_dataset (omero.model.DatasetI): The OMERO dataset to map.
            conn (omero.gateway.BlitzGateway): Active OMERO connection.
            path_omero_data (Path): Path containing extracted OMERO image files.
            image_filenames_mapping (dict): Maps image IDs to filenames.
            destination_path (Path): Output directory for assay files.
            image_filename_getter (callable, optional): Function to get image filename
                from image ID. Defaults to None.
        """
        self.obj = ome_dataset
        self.conn = conn
        self.destination_path = destination_path
        self.path_omero_data = path_omero_data
        self.image_filenames_mapping = image_filenames_mapping
        owner = ome_dataset.getOwner()

        self.assay_identifier = self.obj.getName().lower().replace(" ", "-")

        self.isa_attribute_config = {
            "assay": {
                "namespace": "ISA:ASSAY:ASSAY",
                "default_values": {
                    "filename": "",
                },
                "ontology_annotations": ["measurement_type", "technology_type"],
            },
        }

        self._create_assay()

    def _create_assay(self):
        """Create the ISA Assay object from OMERO dataset.

        Extracts metadata, copies image files, exports ROI data, and creates
        ISA DataFile objects for each image.

        Returns:
            None (sets self.assay)
        """
        self._create_isa_attributes()

        assay_params = self.isa_attributes["assay"]["values"][0]
        assay_params["comments"].append(Comment("identifier", self.assay_identifier))
        self.assay = Assay(**assay_params)

        for ontology_source in self.isa_attributes["assay"]["ontology_values"]:
            if "measurement_type" in ontology_source.keys():
                self.assay.measurement_type = ontology_source["measurement_type"]
            if "technology_type" in ontology_source.keys():
                self.assay.technology_type = ontology_source["technology_type"]

        dest_image_folder_rel = Path(f"assays/{self.assay_identifier}/dataset")
        dest_image_folder = (
            self.destination_path / dest_image_folder_rel
        )

        for image in self.conn.getObjects(
            "Image", opts={"dataset": self.obj.getId()}
        ):
            img_filepath_abs = self.image_filename(image.getId(), abspath=True)
            img_filepath_rel = self.image_filename(
                image.getId(), abspath=False
            )
            target_path = dest_image_folder / img_filepath_rel.name
            target_path_rel = dest_image_folder_rel / img_filepath_rel.name

            os.makedirs(target_path.parent, exist_ok=True)
            # save original image file
            shutil.copy2(img_filepath_abs, target_path)
            # save rois if exist
            roi_path = target_path.with_suffix("").with_name(target_path.stem + "_roidata").with_suffix(".json")
            roidata_path = export_rois_to_json(roi_path, image, self.conn)

            image_metadata = get_image_metadata_omero(image)

            if roidata_path is not None:
                image_metadata.append(Comment("roidata_filename", roidata_path.name))

            img_datafile = DataFile(filename=str(target_path_rel),
                                    label="Raw Image Data File",
                                    comments=image_metadata)
            self.assay.data_files.append(img_datafile)

    def image_filename(self, image_id, abspath=True):
        """Get the filename for an image.

        Args:
            image_id (int): The OMERO image ID.
            abspath (bool): If True, return absolute path; else relative.
                Defaults to True.

        Returns:
            Path: The image filename as Path object.
        """
        image_id_str = f"Image:{image_id}"

        rel_path = Path(self.image_filenames_mapping[image_id_str])

        if not abspath:
            return rel_path
        return self.path_omero_data / rel_path


class OmeroProjectMapper(AbstractIsaMapper):
    """Maps an OMERO project to an ISA investigation.

    Converts an OMERO project and its metadata into ISA Investigation format.
    Creates a single study within the investigation and provides methods to
    save the investigation in both JSON and ISA-Tab formats.

    Attributes:
        obj (omero.model.ProjectI): The OMERO project being mapped.
        investigation (isatools.model.Investigation): The created ISA Investigation.
        isa_attribute_config (dict): Configuration for ISA attribute mapping.
        isa_attributes (dict): Processed ISA attributes.

    Examples:
        >>> mapper = OmeroProjectMapper(project)
        >>> mapper._create_investigation()
        >>> mapper.save_as_json(Path('/export/path'))
        >>> # Creates i_investigation.json

    Note:
        - Creates exactly one study within the investigation
        - Project name becomes study title
        - Project owner becomes contact information
        - All ontology sources are preserved
    """

    def __init__(self, ome_project):
        """Initialize the OmeroProjectMapper.

        Args:
            ome_project (omero.model.ProjectI): The OMERO project to map.
        """
        self.obj = ome_project
        owner = ome_project.getOwner()

        self.isa_attribute_config = {
            "investigation": {
                "namespace": "ISA:INVESTIGATION:INVESTIGATION",
                "default_values": {
                    "filename": "i_investigation.txt",
                    "identifier": "default-investigation-id",
                    "title": None,
                    "description": None,
                    "submission_date": None,
                    "public_release_date": None,
                },
            },
            "investigation_ontology_source_reference": {
                "namespace": "ISA:INVESTIGATION:ONTOLOGY SOURCE REFERENCE",
                "default_values": {
                    "name": "",
                    "file": "",
                    "description": "",
                },
            },
            "investigation_contacts": {
                "namespace": "ISA:INVESTIGATION:INVESTIGATION CONTACTS",
                "default_values": {
                    "last_name": owner.getLastName(),
                    "first_name": owner.getFirstName(),
                    "email": owner.getEmail(),
                    "phone": None,
                    "fax": None,
                    "address": None,
                    "affiliation": None,
                },
                "ontology_annotations": ["roles"]
            },
            "investigation_publications": {
                "namespace": ("ISA:INVESTIGATION:INVESTIGATION PUBLICATIONS"),
                "default_values": {
                    "doi": None,
                    "pubmed_id": None,
                    "author_list": None,
                    "title": None,
                },
                "ontology_annotations": ["status"]
            },
            "study": {
                "namespace": "ISA:STUDY:STUDY",
                "default_values": {
                    "filename": "",
                    "identifier": ome_project.getName().lower().replace(" ", "-"),
                    "title": ome_project.getName(),
                    "description": ome_project.getDescription(),
                    "submission_date": None,
                    "public_release_date": None,
                },
                "ontology_annotations": ["design_descriptors"]
            },
            "study_publications": {
                "namespace": "ISA:STUDY:STUDY PUBLICATIONS",
                "default_values": {
                    "doi": None,
                    "pubmed_id": None,
                    "author_list": None,
                    "title": None,
                },
                "ontology_annotations": ["status"]
            },
        }

    def save_as_tab(self, root_path: Path):
        """Save the investigation in ISA-Tab format.

        Creates ISA-Tab files (i_*.txt, s_*.txt, a_*.txt) in the specified directory.

        Args:
            root_path (Path): Directory where ISA-Tab files will be saved.

        Returns:
            None

        Raises:
            IOError: If files cannot be written.
        """
        isatab.dump(self.investigation, root_path)

    def save_as_json(self, root_path: Path):
        """Save the investigation in ISA-JSON format.

        Creates i_investigation.json with formatted output for readability.

        Args:
            root_path (Path): Directory where i_investigation.json will be saved.

        Returns:
            None

        Raises:
            IOError: If file cannot be written.
        """
        out = json.dumps(
            self.investigation,
            cls=ISAJSONEncoder,
            sort_keys=True,
            indent=4,
            separators=(',', ': ')
        )

        with open(root_path / "i_investigation.json", "w") as f:
            f.write(out)

    def _create_investigation(self):
        """Create the ISA Investigation object from OMERO project.

        Extracts metadata, creates investigation and study objects, adds contacts
        and publications, and populates all required ISA attributes.

        Returns:
            None (sets self.investigation)
        """
        self._create_isa_attributes()

        investigation_params = self.isa_attributes["investigation"]["values"][0]

        contacts = []
        contact_params = self.isa_attributes.get("investigation_contacts", None)
        if contact_params is not None:
            for contact_params, con_ontology_params in zip(contact_params["values"], contact_params["ontology_values"]):
                con = Person(**contact_params)
                role = con_ontology_params.get("roles", None)
                if role is not None:
                    con.roles = [role]
                contacts.append(con)
        investigation_params["contacts"] = contacts

        self.investigation = Investigation(**investigation_params)

        ontology_source_params = self.isa_attributes["investigation_ontology_source_reference"]["values"][0]
        ontology_source = OntologySource(**ontology_source_params)
        self.investigation.ontology_source_references.append(ontology_source)

        def _create_publications(isa_obj, publication_params):
            """Helper function to add publications to ISA objects.

            Args:
                isa_obj: The ISA object (Investigation or Study)
                publication_params: Publication parameters dict
            """
            if publication_params is not None:
                for publication_params, pub_ontology_params in zip(publication_params["values"], publication_params["ontology_values"]):
                    pub = Publication(**publication_params)
                    pub.status = pub_ontology_params.get("status", None)
                    isa_obj.publications.append(pub)

        _create_publications(self.investigation, self.isa_attributes.get("investigation_publications", None))

        study_params = self.isa_attributes["study"]["values"][0]
        for k in self.isa_attributes["study"]["ontology_values"][0]:
            study_params[k] = [self.isa_attributes["study"]["ontology_values"][0][k]]
        study = Study(**study_params)
        _create_publications(study, self.isa_attributes.get("study_publications", None))

        self.investigation.studies.append(study)
