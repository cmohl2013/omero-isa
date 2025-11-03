from abstract_isa_test import AbstractIsaTest
from omero_isa.isa_packer import IsaPacker
import json

class TestIsaPacker(AbstractIsaTest):

    def test_print_test_user_credentials(self, project_with_arc_assay_annotation, project_1):
        print(f"test user: {self.user.getOmeName()._val}")


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
        assert (path_to_arc_repo / "i_investigation.json").exists()

        with open(path_to_arc_repo / "i_investigation.json") as f:
            d = json.load(f)

        assert d["identifier"] == "my-custom-investigation-id"

        assert d["ontologySourceReferences"][0]["comments"][0]["name"] == "omero_annotation_namespace"
        assert d["ontologySourceReferences"][0]["comments"][0]["value"] == "ISA:INVESTIGATION:ONTOLOGY SOURCE REFERENCE"

        assert d["studies"][0]["comments"][0]["name"] == "omero_annotation_namespace"
        assert d["studies"][0]["comments"][0]["value"] == "ISA:STUDY:STUDY"

        assert d["studies"][0]["identifier"] == "my-custom-study-id"
        assert len(d["studies"][0]["assays"]) == 2
        assert len(d["studies"][0]["publications"]) == 2
        assert len(d["publications"]) == 2

        assert d["ontologySourceReferences"][0]["description"] == "Experimental Factor Ontology"

        dataset_path = tmp_path / "my_arc/assays/my-assay-with-annotations/dataset"
        assert (dataset_path / "sted-confocal.lif").exists()


        roi_filenames = list(dataset_path.glob("*_roidata.json"))

        assert len(roi_filenames) == 1





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

        assert (path_to_arc_repo / "i_investigation.json").exists()
