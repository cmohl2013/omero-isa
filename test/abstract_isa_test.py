import os
import shutil
import tarfile
from pathlib import Path

import pytest
from generate_xml import list_file_ids
from ome_types import from_xml
from omero.cli import CLI
from omero.gateway import BlitzGateway
from omero.model import MapAnnotationI, NamedValue
from omero.plugins.sessions import SessionsControl
from omero.rtypes import rstring
from omero.testlib import ITest
from omero_cli_transfer import TransferControl



class AbstractCLITest(ITest):
    @classmethod
    def setup_class(cls):
        super(AbstractCLITest, cls).setup_class()
        cls.cli = CLI()
        cls.cli.register("sessions", SessionsControl, "TEST")

    def setup_mock(self):
        self.mox = mox.Mox()

    def teardown_mock(self):
        self.mox.UnsetStubs()
        self.mox.VerifyAll()


class AbstractIsaTest(AbstractCLITest):
    def setup_method(self, method):
        self.args = self.login_args()
        self.cli.register("transfer", TransferControl, "TEST")
        self.args += ["transfer"]
        self.gw = BlitzGateway(client_obj=self.client)
        self.session = self.client.getSessionId()

    def create_mapped_annotation(
        self, name=None, map_values=None, namespace=None, parent_object=None
    ):
        map_annotation = self.new_object(MapAnnotationI, name=name)
        if map_values is not None:
            map_value_ls = [
                NamedValue(str(key), str(map_values[key])) for key in map_values
            ]
            map_annotation.setMapValue(map_value_ls)
        if namespace is not None:
            map_annotation.setNs(rstring(namespace))

        map_annotation = self.client.sf.getUpdateService().saveAndReturnObject(
            map_annotation
        )
        if parent_object is not None:
            self.link(parent_object, map_annotation)

        return map_annotation

    @pytest.fixture(scope="function")
    def dataset_1(self):
        dataset_1 = self.make_dataset(name="My First Assay")

        for i in range(3):
            img_name = f"assay 2 image {i}"
            image = self.create_test_image(
                80, 40, 3, 4, 2, self.client.getSession(), name=img_name
            )
            self.link(dataset_1, image)

        return self.gw.getObject("Dataset", dataset_1.id._val)

    @pytest.fixture(scope="function")
    def dataset_1_obj(self):
        dataset_1 = self.make_dataset(name="My First Assay")

        for i in range(3):
            img_name = f"assay 2 image {i}"
            image = self.create_test_image(
                80, 40, 3, 4, 2, self.client.getSession(), name=img_name
            )
            self.link(dataset_1, image)

        return dataset_1

    @pytest.fixture(scope="function")
    def dataset_2(self):
        dataset_2 = self.make_dataset(name="My Second Assay")

        for i in range(3):
            img_name = f"assay 2 image {i}"
            image = self.create_test_image(
                100, 100, 1, 1, 1, self.client.getSession(), name=img_name
            )
            self.link(dataset_2, image)

        return dataset_2

    @pytest.fixture(scope="function")
    def project_1(self, dataset_1, dataset_2):
        project_1 = self.make_project(name="My First Study")

        self.link(project_1, dataset_1)
        self.link(project_1, dataset_2)

        return self.gw.getObject("Project", project_1.id._val)




    @pytest.fixture(scope="function")
    def dataset_with_arc_assay_annotation(self):
        dataset = self.make_dataset(name="My Assay with Annotations")

        annotation_namespace = "ISA:ASSAY:ASSAY"
        annotations = {
            "Assay Identifier": "my-custom-assay-id",
            "Measurement Type": ("High resolution transmission electron micrograph"),
            "Measurement Type Term Accession Number": (
                "http://purl.obolibrary.org/obo/CHMO_0002125"
            ),
            "Measurement Type Term Source REF": "CHMO",
            "Technology Type": "transmission electron microscopy",
            "Technology Type Term Accession Number": (
                "http://www.bioassayontology.org/bao#BAO_0000455"
            ),
            "Technology Type Term Source Ref": "BAO",
            "Technolology Platform": "JEOL JEM2100Plus",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=dataset,
        )

        annotation_namespace = "ISA:ASSAY:ASSAY PERFORMERS"
        annotations = {
            "Last Name": "Doe",
            "First Name": "John",
            "Email": "john.doe@email.com",
            "Phone": "+49 (0)221 12345",
            "Fax": "+49 (0)221 12347",
            "Address": "Cologne University, Cologne",
            "Affiliation": "Institute of Plant Science, Cologne University",
            "orcid": "789897890ß6",
            "Roles": "researcher",
            "Roles Term Accession Number": ("http://purl.org/spar/scoro/researcher"),
            "Roles Term Source REF": "SCoRO",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=dataset,
        )

        annotation_namespace = "ISA:ASSAY:ASSAY PERFORMERS"
        annotations = {
            "Last Name": "Laura",
            "First Name": "Langer",
            "Mid Initials": "L",
            "Email": "laura.l.langer@email.com",
            "Phone": "0211-12345",
            "Roles": "researcher",
            "Roles Term Accession Number": ("http://purl.org/spar/scoro/researcher"),
            "Roles Term Source REF": "SCoRO",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=dataset,
        )

        # image 1
        image_tif = self.create_test_image(
            100,
            100,
            1,
            1,
            1,
            self.client.getSession(),
            name="pixel image 1",
        )
        self.link(dataset, image_tif)



        def _add_local_image_file(path_to_img_file):
            assert path_to_img_file.exists()
            target_str = f"Dataset:{dataset.id._val}"
            pix_ids = self.import_image(
                path_to_img_file, extra_args=["--target", target_str]
            )
            return pix_ids

        path_to_img_file = (
            Path(__file__).parent / "data/img_files/CD_s_1_t_3_c_2_z_5.czi"
        )
        _add_local_image_file(path_to_img_file=path_to_img_file)


        path_to_img_file = Path(__file__).parent / "data/img_files/sted-confocal.lif"
        _add_local_image_file(path_to_img_file=path_to_img_file)

        return dataset


    @pytest.fixture(scope="function")
    def project_with_arc_assay_annotation(
        self, dataset_1, dataset_with_arc_assay_annotation
    ):
        project = self.make_project(name="My Study with Annotations")
        self.link(project, dataset_1)
        self.link(project, dataset_with_arc_assay_annotation)

        annotation_namespace = "These Values are not relevant for ARCs"
        annotations = {"color 1": "red", "color 2": "blue"}
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        annotation_namespace = "ISA:INVESTIGATION:ONTOLOGY SOURCE REFERENCE"
        annotations = {
            "Term Source Name": "EFO",
            "Term Source File": ("http://www.ebi.ac.uk/efo/releases/v3.14.0/efo.owl"),
            "Term Source Description": "Experimental Factor Ontology",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        annotation_namespace = "ISA:INVESTIGATION:INVESTIGATION"
        annotations = {
            "identifier": "my-custom-investigation-id",
            "title": "Mitochondria in HeLa Cells",
            "description": (
                "Observation of MDV formation in Mitochondria"
            ),
            "submission_date": "8/11/2022",
            "public_release_date": "1/12/2022",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        annotation_namespace = "ISA:INVESTIGATION:INVESTIGATION CONTACTS"
        annotations = {
            "Investigation Person Last Name": "Mueller",
            "Investigation Person First Name": "Arno",
            "Investigation Person Email": "arno.mueller@email.com",
            "Investigation Person Roles": "researcher",
            "Investigation Person Roles Term Accession Number": (
                "http://purl.org/spar/scoro/researcher"
            ),
            "Investigation Person Roles Term Source REF": "SCoRO",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        annotation_namespace = "ISA:INVESTIGATION:INVESTIGATION PUBLICATIONS"
        annotations = {
            "doi": "10.1038/s41467-022-34205-9",
            "pubmed_id": 678978,
            "author_list": "Mueller M, Langer L L",
            "title": (
                "HJKIH P9 orchestrates JKLKinase " "trafficking in mesenchymal cells."
            ),
            "status": "published",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        annotation_namespace = "ISA:INVESTIGATION:INVESTIGATION PUBLICATIONS"
        annotations = {
            "doi": "10.1038/s41467-022-34789-9",
            "pubmed_id": 678978,
            "author_list": "Meier M, Kluge L L",
            "title": (
                "Rho GTPase is downreglated upon JK0897 treatment"
            ),
            "status": "published",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )


        annotation_namespace = "ISA:STUDY:STUDY"
        annotations = {
            "Study Identifier": "my-custom-study-id",
            "Study Title": "My Custom Study Title",
            "Study Description": "My custom description.",
            "Study Submission Date": "8/11/2022",
            "Study Public Release Date": "3/3/2023",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        annotation_namespace = "ISA:STUDY:STUDY PUBLICATIONS"
        annotations = {
            "Study Publication DOI": "10.1038/s41467-022-34205-9",
            "Study Publication PubMed ID": 678978,
            "Study Publication Author List": "Mueller M, Langer L L",
            "Study Publication Title": (
                "HJKIH P9 orchestrates " "JKLKinase trafficking in mesenchymal cells."
            ),
            "Study Publication Status": "published",
            "Study Publication Status Term Accession Number": (
                "http://www.ebi.ac.uk/efo/EFO_0001796"
            ),
            "Study Publication Status Term Source REF": "EFO",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )
        annotation_namespace = "ISA:STUDY:STUDY PUBLICATIONS"
        annotations = {
            "Study Publication DOI": "10.567/s56878-890890-330-3",
            "Study Publication PubMed ID": 7898961,
            "Study Publication Author List": "Mueller M, Langer L L, Berg J",
            "Study Publication Title": ("HELk reformation in activated Hela Cells"),
            "Study Publication Status": "published",
            "Study Publication Status Term Accession Number": (
                "http://www.ebi.ac.uk/efo/EFO_0001796"
            ),
            "Study Publication Status Term Source REF": "EFO",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        annotation_namespace = "ISA:STUDY:STUDY DESIGN DESCRIPTORS"
        annotations = {
            "Study Design Type": "Transmission Electron Microscopy",
            "Study Design Type Term Accession Number": (
                "http://www.ebi.ac.uk/efo/EFO_0001796"
            ),
            "Study Design Type Term Source REF": "EFO",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        annotation_namespace = "ISA:STUDY:STUDY FACTORS"
        annotations = {
            "Study Factor Name": "My Factor",
            "Study Factor Type": "Factor for test reasons",
            "Study Design Type Term Accession Number": (
                "http://www.ebi.ac.uk/efo/EFO_0001796"
            ),
            "Study Design Type Term Source REF": "EFO",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        annotation_namespace = "ISA:STUDY:STUDY FACTORS"
        annotations = {
            "Study Factor Name": "My Second Factor",
            "Study Factor Type": "Factor Number 2 for test reasons",
            "Study Design Type Term Accession Number": (
                "http://www.ebi.ac.uk/efo/EFO_0001796"
            ),
            "Study Design Type Term Source REF": "EFO",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        annotation_namespace = "ISA:STUDY:STUDY PROTOCOLS"
        annotations = {
            "Study Protocol Name": "Cell embedding for electron microscopy",
            "Study Protocol Type": "Test Protocol Type",
            "Study Protocol Type Term Accession Number": (
                "http://www.ebi.ac.uk/efo/EFO_0001796"
            ),
            "Study Protocol Type Term Source REF": "EFO",
            "Study Protocol Description": "A protocol for test reasons.",
            "Study Protocol URI": (
                "urn:oasis:names:specification:docbook:dtd:xml:4.1.2"
            ),
            "Study Protocol Version": "0.0.1",
            "Study Protocol Parameters Name": ("temperature;" "glucose concentration"),
            "Study Protocol Parameters Term Accession Number": (
                "http://www.ebi.ac.uk/efo/EFO_0001796;"
                "http://www.ebi.ac.uk/efo/EFO_0001796"
            ),
            "Study Protocol Parameters Term Source REF": "EFO;EFO",
            "Study Protocol Components Name": (
                "SuperEmeddingMediumX;" "SuperEmeddingMediumY"
            ),
            "Study Protocol Components Type": "reagent;reagent",
            "Study Protocol Components Type Term Accession Number": (
                "http://www.ebi.ac.uk/efo/EFO_0001796;"
                "http://www.ebi.ac.uk/efo/EFO_0001796"
            ),
            "Study Protocol Components Type Term Source REF": "EFO;EFO",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        annotation_namespace = "ISA:STUDY:STUDY CONTACTS"
        annotations = {
            "Study Person Last Name": "Mueller",
            "Study Person First Name": "Arno",
            "Study Person Email": "arno.mueller@email.com",
            "Study Person Roles": "researcher",
            "Study Person Roles Term Accession Number": (
                "http://purl.org/spar/scoro/researcher"
            ),
            "Study Person Roles Term Source REF": "SCoRO",
        }
        self.create_mapped_annotation(
            name=annotation_namespace,
            map_values=annotations,
            namespace=annotation_namespace,
            parent_object=project,
        )

        return self.gw.getObject("Project", project.id._val)