from abstract_isa_test import AbstractIsaTest

from omero_isa.isa_mapping import OmeroProjectMapper, OmeroDatasetMapper
from omero.gateway import BlitzGateway

class TestOmeroProjectMapper(AbstractIsaTest):

    def test_omero_project_mapper_attributes(self, project_1, tmp_path):

        p = project_1

        mapper = OmeroProjectMapper(project_1)
        mapper._create_investigation()

        assert mapper.investigation.studies[0].title == "My First Study"
        assert mapper.investigation.studies[0].identifier == "my-first-study"
        assert len(mapper.investigation.studies[0].assays) == 0

        mapper.save_as_tab(tmp_path)
        assert (tmp_path / "i_investigation.txt").exists()


    def test_omero_project_mapper_with_annotation(self, project_with_arc_assay_annotation, tmp_path):
        p = project_with_arc_assay_annotation
        mapper = OmeroProjectMapper(p)
        mapper._create_investigation()
        mapper.save_as_tab(tmp_path)

        with open(tmp_path / "i_investigation.txt", "r") as f:
            tabdata = f.read()
        print(tabdata)

    def test_omero_project_mapper_with_czi_files(self, project_czi, tmp_path):

        p = project_czi
        mapper = OmeroProjectMapper(p)
        mapper._create_investigation()
        mapper.save_as_tab(tmp_path)

        with open(tmp_path / "i_investigation.txt", "r") as f:
            tabdata = f.read()
        print(tabdata)
        print(tmp_path)
        pass




class TestOmeroDatasetMapper(AbstractIsaTest):

    def test_omero_dataset_mapper_attributes(self,
                                             dataset_czi_1,
                                             project_czi,
                                             path_omero_data_czi,
                                             tmp_path,
                                             omero_data_czi_image_filenames_mapping):


        conn = BlitzGateway(client_obj=self.client)
        dataset_czi_1_obj = self.gw.getObject("Dataset", dataset_czi_1.id._val)

        mapper = OmeroDatasetMapper(dataset_czi_1_obj,
                                    conn=conn,
                                    path_omero_data=path_omero_data_czi,
                                    image_filenames_mapping=omero_data_czi_image_filenames_mapping,
                                    destination_path=tmp_path,
                                    image_filename_getter=None,
                                    )

        mapper._create_assay()

        pass
