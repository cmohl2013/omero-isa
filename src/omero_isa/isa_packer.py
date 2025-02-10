from pathlib import Path
from omero_isa.isa_mapping import OmeroIsaMapper

def pack_isa(ome_object,
             destination_path,
             tmp_path,
             image_filenames_mapping,
             conn):

    packer = IsaPacker(ome_object,
                       destination_path,
                       tmp_path,
                       image_filenames_mapping,
                       conn)
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

        mapper = OmeroIsaMapper(self.obj)
        mapper.save_as_tab(self.destination_path)
        # TODO
        # i_*.txt for identifying the Investigation file, e.g. i_investigation.txt
        # s_*.txt for identifying Study file(s), e.g. s_gene_survey.txt
        # a_*.txt for identifying Assay file(s), e.g. a_transcription.txt
