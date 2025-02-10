from isatools.model import Study, Investigation
from isatools import isatab

from pathlib import Path



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



    def save_as_tab(self, root_path: Path):

        isatab.dump(self.investigation, root_path)
