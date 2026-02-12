from abstract_isa_test import AbstractIsaTest
from omero_isa.isa_investigation_importer import IsaInvestigationImporter, MappedAnnotationFactory


class TestIsaStudyImporter(AbstractIsaTest):

    def test_isa_investigation_importer(self):

        conn = self.gw


        # valid data file with exactly one study and namespace information
        # for mapped annotations
        data = {
            "comments": [
                {
                    "name": "omero_annotation_namespace",
                    "value": "ISA:INVESTIGATION:INVESTIGATION",
                }
            ],
            "description": "Observation of MDV formation in Mitochondria",
            "identifier": "my-custom-investigation-id",
            "publications": [1, 2, 3],
            "studies": [
                {
                    "assays": [1, 2, 3],
                    "characteristicCategories": [],
                    "comments": [
                        {
                            "name": "omero_annotation_namespace",
                            "value": "ISA:STUDY:STUDY",
                        }
                    ],
                    "description": "My custom description.",
                    "title": "My annotated Study",
                }
            ],
        }

        imp = IsaInvestigationImporter(data)
        omero_project = imp.save(conn)

        assert omero_project is not None
        print(omero_project.getId().getValue())
        print(self.user.getOmeName()._val)


    def test_mapped_annotation_factory(self):

        data = {
            "comments": [
                {
                    "name": "omero_annotation_namespace",
                    "value": "ISA:INVESTIGATION:INVESTIGATION",
                }
            ],
            "description": "Observation of MDV formation in Mitochondria",
            "identifier": "my-custom-investigation-id",
            "publications": [1, 2, 3],
            "studies": [
                {
                    "assays": [1, 2, 3],
                    "characteristicCategories": [],
                    "comments": [
                        {
                            "name": "omero_annotation_namespace",
                            "value": "ISA:STUDY:STUDY",
                        }
                    ],
                    "description": "My custom description.",
                    "title": "My annotated Study",
                }
            ],
        }


        maf = MappedAnnotationFactory(data)

        maf_study = MappedAnnotationFactory(data["studies"][0])


        conn = self.gw
        imp = IsaInvestigationImporter(data)
        omero_project = imp.save(conn)



        print(self.user.getOmeName()._val)

    def test_create_full_omero_project(self, path_test_data):
        import json
        path_to_arc = path_test_data / "data_to_import_1/i_investigation.json"


        with open(path_to_arc, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        imp = IsaInvestigationImporter(data, path_to_arc)
        conn = self.gw
        omero_project = imp.save(conn)

        assert omero_project is not None
        print(omero_project.getId().getValue())
        print(self.user.getOmeName()._val)

        pass
