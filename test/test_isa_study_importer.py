from abstract_isa_test import AbstractIsaTest
from omero_isa.isa_investigation_importer import IsaInvestigationImporter, MappedAnnotationFactory


class TestIsaStudyImporter(AbstractIsaTest):

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
