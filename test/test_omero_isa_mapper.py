from abstract_isa_test import AbstractIsaTest

from omero_isa.isa_mapping import OmeroIsaMapper


class TestOmeroIsaMapper(AbstractIsaTest):

    def test_omero_isa_mapper_attributes(self, project_1, tmp_path):

        p = project_1

        mapper = OmeroIsaMapper(project_1)


        assert mapper.investigation.studies[0].title == "My First Study"
        assert mapper.investigation.studies[0].identifier == "my-first-study"
        assert len(mapper.investigation.studies[0].assays) == 0

        mapper.save_as_tab(tmp_path)
        assert (tmp_path / "i_investigation.txt").exists()
