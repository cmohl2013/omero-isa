from isatools.model import Study, Investigation, Publication, OntologyAnnotation
from isatools import isatab

from pathlib import Path

from functools import lru_cache


class OmeroIsaMapper():

    def __init__(self, ome_project):

        self.obj = ome_project
        owner = ome_project.getOwner


        study = Study(filename="s_study.txt")

        ome_project_name = ome_project.getName()
        study.identifier = ome_project_name.lower().replace(" ", "-")
        study.title = ome_project_name
        study.description = ome_project.getDescription()

        self.investigation = Investigation(filename="i_investigation.txt")

        self.investigation.studies.append(study)


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
            "investigation_publications": {
                "namespace": ("ISA:INVESTIGATION:INVESTIGATION PUBLICATIONS"),
                "default_values": {
                    "doi": None,
                    "pubmed_id": None,
                    "author_list": None,
                    "title": None,
                    "status": None,
                },
        }}



    def save_as_tab(self, root_path: Path):
        isatab.dump(self.investigation, root_path)


    def _create_investigation(self):
        self._create_isa_attributes()

        investigation_params = self.isa_attributes["investigation"]["values"][0]
        self.investigation = Investigation(**investigation_params)

        for publication_params in self.isa_attributes["investigation_publications"]["values"]:

            status = publication_params.get("status", None)
            if status is not None:
                publication_params["status"] = OntologyAnnotation(term=status)

            pub = Publication(**publication_params)
            self.investigation.publications.append(pub)
        pass


    def _create_isa_attributes(self):

        isa_attributes = {}

        for annotation_type in self.isa_attribute_config:
            annotation_data = self._annotation_data(annotation_type)
            config = self.isa_attribute_config[annotation_type]

            isa_attributes[annotation_type] = {}
            isa_attributes[annotation_type]["values"] = []

            values_to_set = {}
            if len(annotation_data) == 0:
                # set defaults if no annotations available
                for key in config["default_values"]:
                    value = config["default_values"][key]
                    if value is not None:
                        values_to_set[key] = value
                if len(values_to_set) > 0:
                    isa_attributes[annotation_type]["values"].append(values_to_set)
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
