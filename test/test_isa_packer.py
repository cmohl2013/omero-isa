from abstract_isa_test import AbstractIsaTest
from omero_isa.isa_packer import IsaPacker

class TestIsaPacker(AbstractIsaTest):

    def test_isa_packer_with_assay_annotation(self,
                                              project_with_arc_assay_annotation,
                                              tmp_path,
                                              path_omero_data_with_arc_assay_annotation,
                                              omero_data_with_arc_assay_annotation_image_filenames_mapping):

        path_to_arc_repo = tmp_path / "my_arc"
        ap = IsaPacker(
            ome_object=project_with_arc_assay_annotation,
            destination_path=path_to_arc_repo,
            tmp_path=path_omero_data_with_arc_assay_annotation,
            image_filenames_mapping=omero_data_with_arc_assay_annotation_image_filenames_mapping,
            conn=self.gw,
        )

        ap.pack()


    def test_isa_packer_project_1(self,
                                  project_1,
                                  tmp_path,
                                  omero_data_1_filenames_mapping,
                                  path_omero_data_1):

        path_to_arc_repo = tmp_path / "my_arc"
        ap = IsaPacker(
            ome_object=project_1,
            destination_path=path_to_arc_repo,
            tmp_path=path_omero_data_1,
            image_filenames_mapping=omero_data_1_filenames_mapping,
            conn=self.gw,
        )

        ap.pack()
