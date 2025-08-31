from isatools.model import Study, Investigation, Publication, OntologyAnnotation, OntologySource, Assay, DataFile, Person ,Comment
from isatools import isatab
import json
from isatools.isajson import ISAJSONEncoder

from pathlib import Path

from functools import lru_cache
import os
import shutil

from omero_isa.roi import export_rois_to_json



def get_image_metadata_omero(image):

    def _pixel_unit(image):
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
    def _create_isa_attributes(self):
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

            #isa_attributes[annotation_type]["ontology_values"] = ontology_annotation_attributes

            values_to_set = {}

            if len(annotation_data) == 0:
                # set defaults if no annotations available
                for key in config["default_values"]:
                    value = config["default_values"][key]
                    if value is not None:
                        values_to_set[key] = value
                if len(values_to_set) > 0:
                    isa_attributes[annotation_type]["values"].append(values_to_set)
                    isa_attributes[annotation_type]["ontology_values"].append({}) # no defaults for ontology_values


            else:
                # set annotation value if key is
                # registered in config["default_values"]

                def _expand_isa_attribute_key(key):
                    return f"Investigation {key.title()}"

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

            self.isa_attributes = isa_attributes

    @lru_cache
    def _all_annotatation_objects(self):
        return [a for a in self.obj.listAnnotations()]

    def _annotation_data(self, annotation_type):
        namespace = self.isa_attribute_config[annotation_type]["namespace"]
        annotation_data = []
        for annotation in self._all_annotatation_objects():
            if annotation.getNs() == namespace:
                annotation_data.append(dict(annotation.getValue()))
        return annotation_data



class OmeroDatasetMapper(AbstractIsaMapper):
    def __init__(self,
                 ome_dataset,
                 conn,
                 path_omero_data,
                 image_filenames_mapping,
                 destination_path,
                 image_filename_getter=None):
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
                    "filename": "", #f"a_{self.assay_identifier}.txt",
                    "measurement_type": None,
                    "technology_type": None,
                    "Technolology_platform": None,
                },
            },
        }

        self._create_assay()



    def _create_assay(self):

        self._create_isa_attributes()

        assay_params = self.isa_attributes["assay"]["values"][0]
        assay_params["comments"] = [Comment("identifier", self.assay_identifier)]
        self.assay = Assay(**assay_params)


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
        image_id_str = f"Image:{image_id}"

        rel_path = Path(self.image_filenames_mapping[image_id_str])

        if not abspath:
            return rel_path
        return self.path_omero_data / rel_path



class OmeroProjectMapper(AbstractIsaMapper):
    def __init__(self, ome_project):
        self.obj = ome_project
        owner = ome_project.getOwner()  # used to set default values below

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
                "ontology_annotations":["roles"]
            },
            "investigation_publications": {
                "namespace": ("ISA:INVESTIGATION:INVESTIGATION PUBLICATIONS"),
                "default_values": {
                    "doi": None,
                    "pubmed_id": None,
                    "author_list": None,
                    "title": None,
                },
                "ontology_annotations":["status"]
            },
            "study": {
                "namespace": "ISA:STUDY:STUDY",
                "default_values": {
                    "filename": "",#"s_study.txt",
                    "identifier": ome_project.getName().lower().replace(" ", "-"),
                    "title": ome_project.getName(),
                    "description": ome_project.getDescription(),
                    "submission_date": None,
                    "public_release_date": None,
                },
                "ontology_annotations":["design_descriptors"]
            },
            "study_publications": {
                "namespace":"ISA:STUDY:STUDY PUBLICATIONS",
                "default_values": {
                    "doi": None,
                    "pubmed_id": None,
                    "author_list": None,
                    "title": None,
                },
                "ontology_annotations":["status"]
            },
        }

    def save_as_tab(self, root_path: Path):
        isatab.dump(self.investigation, root_path)

    def save_as_json(self, root_path: Path):

        # Note that the extra parameters sort_keys, indent and separators are to make the output more human-readable.
        out = json.dumps(self.investigation, cls=ISAJSONEncoder, sort_keys=True, indent=4, separators=(',', ': '))

        with open(root_path / "i_investigation.json", "w") as f:
            f.write(out)


    def _create_investigation(self):
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
