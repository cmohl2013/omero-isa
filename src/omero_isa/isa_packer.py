from pathlib import Path
from omero_isa.isa_mapping import OmeroProjectMapper, OmeroDatasetMapper


def pack_isa(ome_object, destination_path, tmp_path, image_filenames_mapping, conn):
    packer = IsaPacker(
        ome_object, destination_path, tmp_path, image_filenames_mapping, conn
    )
    packer.pack()


class IsaPacker(object):
    def __init__(
        self,
        ome_object,
        destination_path: Path,
        tmp_path,
        image_filenames_mapping,
        conn,
    ):
        assert ome_object.OMERO_CLASS == "Project"
        self.obj = ome_object  # must be a project
        self.destination_path = destination_path
        self.conn = conn
        self.image_filenames_mapping = image_filenames_mapping
        self.path_to_image_files = tmp_path

        self.isa_assay_mappers = []
        self.ome_dataset_for_isa_assay = {}

    def pack(self):
        project_mapper = OmeroProjectMapper(self.obj)
        project_mapper._create_investigation()

        ome_project = self.obj
        project_id = ome_project.getId()

        ome_datasets = self.conn.getObjects("Dataset", opts={"project": project_id})

        def _filename_for_image(image_id):
            return self.image_filenames_mapping[f"Image:{image_id}"].name

        investigation = project_mapper.investigation

        assert len(investigation.studies) == 1
        study = investigation.studies[0]

        for dataset in ome_datasets:
            dataset_mapper = OmeroDatasetMapper(
                dataset,
                self.conn,
                self.path_to_image_files,
                self.image_filenames_mapping,
                self.destination_path,
                image_filename_getter=_filename_for_image,
            )
            self.isa_assay_mappers.append(dataset_mapper)
            study.assays.append(dataset_mapper.assay)


        project_mapper.save_as_tab(self.destination_path)

        # TODO
        # i_*.txt for identifying the Investigation file, e.g. i_investigation.txt
        # s_*.txt for identifying Study file(s), e.g. s_gene_survey.txt
        # a_*.txt for identifying Assay file(s), e.g. a_transcription.txt
