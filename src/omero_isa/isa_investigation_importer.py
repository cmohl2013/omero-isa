from omero import rtypes, model
from omero.model import ProjectI, MapAnnotationI, DatasetI, NamedValue, Annotation, ImageI
import subprocess
from omero_isa.roi import import_rois_from_json

def import_and_tag_image(conn, file_path, dataset_id, name, description):
    # 1. Daten aus der bestehenden Verbindung extrahieren
    host = conn.host
    port = conn.port
    session_id = conn.c.getSessionId()

    # 2. Den CLI-Befehl zusammenbauen
    # -k nutzt den Session-Key (kein Passwort nötig!)
    cmd = [
        "omero", "import", file_path,
        "-s", str(host),
        "-p", str(port),
        "-k", str(session_id),
        "-d", str(dataset_id),
        "--name", name,
        "--description", description
    ]

    # 3. Ausführen
    print(f"Start importing: {name}...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Success: File was imported as '{name}'.")
        # Extrahiere die Bild-ID aus dem CLI-Output (z. B. "Image:123")
        for line in result.stdout.splitlines():
            if line.startswith("Image:"):
                image_id = int(line.split(":")[1].split(",")[0])
                # Hole das Bildobjekt aus der OMERO-Datenbank
                return conn.getObject("Image", image_id)
    else:
        print("Import error:")
        print(result.stderr)
        return None


class IsaInvestigationImporter:


    def __init__(self, data, path_to_arc):


        # one isa investigation must contain exactly one study
        # the study relates to the omero project
        assert "studies" in data.keys()
        assert len(data["studies"]) == 1

        # isa investigations to be imnported as omero projects
        # must contain annotation_namespace metadata



        self.data = data
        self.study_data = data["studies"][0]
        self.assay_data = self.study_data.get("assays", None)

        self.path_to_arc = path_to_arc

    def _add_datasets(self, parent_object, conn):

        if self.assay_data is not None:
            for assay_item in self.assay_data:
                dataset = DatasetFactory(assay_item, self.path_to_arc)
                dataset.save(conn, parent_object)

    def _add_mapped_annotations(self, parent_object, conn):

        try:
            maf = MappedAnnotationFactory(self.data)
            maf.save(conn, parent_object=parent_object)
        except AssertionError:
            pass

        # try:
        #     maf = MappedAnnotationFactory(self.study_data)
        #     maf.save(conn, parent_object=parent_object)
        # except AssertionError:
        #     pass


        for k in self.data.keys():
            d = self.data[k]
            if isinstance(d, list):
                for e in d:
                    try:
                        maf = MappedAnnotationFactory(e)
                        maf.save(conn, parent_object=parent_object)
                    except AssertionError:
                        pass
            else:
                try:
                    maf = MappedAnnotationFactory(self.data[k])
                    maf.save(conn, parent_object=parent_object)
                except AssertionError:
                    pass




        for k in self.study_data.keys():
            if k == "assays":
                continue
            study_data_item = self.study_data[k]
            if isinstance(study_data_item, dict):
                try:
                    maf = MappedAnnotationFactory(self.study_data[k])
                    maf.save(conn, parent_object=parent_object)
                except AssertionError:
                    pass
            elif isinstance(study_data_item, list):
                for item in study_data_item:
                    try:
                        maf = MappedAnnotationFactory(item)
                        maf.save(conn, parent_object=parent_object)
                    except AssertionError:
                        pass





    def save(self, conn):

        project_name = self.study_data.get("title", "no_study_title")
        project_description = self.study_data.get("description", "")
        project = ProjectI()
        project.setName(rtypes.rstring(project_name))
        project.setDescription(rtypes.rstring(project_description))

        # Save the project to the server
        project = conn.getUpdateService().saveAndReturnObject(project)
        self._add_mapped_annotations(project, conn)
        self._add_datasets(project, conn)
        return project



class ImageFactory:

    def __init__(self, data, path_to_arc):

        assert isinstance(data, dict)
        self.data = data
        self.path_to_arc = path_to_arc

    def save(self, conn, parent_object=None):
        """
        Save an image to OMERO by uploading the file specified in self.data['name'].
        :return: The created OMERO Image object
        """

        img_name = ""
        img_description = ""
        roidata_filename = None
        for comment in self.data["comments"]:
            if comment["name"] == "name":
                img_name = comment["value"]
            elif comment["name"] == "description":
                img_description = comment["value"]
            elif comment["name"] == "roidata_filename":
                roidata_filename = comment["value"]





        # Ensure the file path exists in the data
        file_path = self.data.get("name")
        if not file_path:
            raise ValueError("The 'name' key must be present in the data and point to a valid file path.")

        image_filepath = self.path_to_arc.parent / file_path
        assert image_filepath.exists(), image_filepath


        # Upload the image file to OMERO


        image = import_and_tag_image(
            conn,
            image_filepath,
            parent_object.getId()._val,
            img_name,
            img_description,
            )

        if roidata_filename is not None:
            roidata_filepath = image_filepath.parent / roidata_filename
            assert roidata_filepath.exists(), f"roi nicht gedunden {roidata_filepath}"

            roi = import_rois_from_json(
                roidata_filepath,
                image,
                conn)




class DatasetFactory:

    def __init__(self, data, path_to_arc):

        assert isinstance(data, dict)

        self.data = data
        self.path_to_arc = path_to_arc


    def _add_mapped_annotations(self, parent_object, conn):

        try:
            maf = MappedAnnotationFactory(self.data)
            maf.save(conn, parent_object=parent_object)
        except AssertionError:
            pass

        for k in self.data.keys():
            d = self.data[k]
            if isinstance(d, list):
                for e in d:
                    try:
                        maf = MappedAnnotationFactory(e)
                        maf.save(conn, parent_object=parent_object)
                    except AssertionError:
                        pass
            else:
                try:
                    maf = MappedAnnotationFactory(self.data[k])
                    maf.save(conn, parent_object=parent_object)
                except AssertionError:
                    pass

    def _add_images(self, parent_object, conn):

        images_data = self.data.get("dataFiles", None)

        if images_data is None:
            return


        for image_data in images_data:
            if image_data.get("type", None) == "Raw Image Data File":
                img = ImageFactory(image_data, self.path_to_arc)
                img.save(conn, parent_object)



    def save(self, conn, parent_object=None):

        comments = self.data.get("comments", None)
        assert comments is not None
        for comment in comments:
            assert isinstance(comment, dict)
            if comment.get("name", None) == "identifier":
                dataset_name = comment.get("value")
                break

        dataset = DatasetI()
        dataset.setName(rtypes.rstring(dataset_name))


        # Save the project to the server
        dataset = conn.getUpdateService().saveAndReturnObject(dataset)
        self._add_mapped_annotations(dataset, conn)
        self._add_images(dataset, conn)

        if parent_object is not None:
            link(parent_object, dataset, conn)

        return dataset




class MappedAnnotationFactory:


    def __init__(self, data):


        assert isinstance(data, dict)
        assert "comments" in data.keys()
        assert len(data["comments"]) >= 1
        assert data["comments"][0].get("name", None) is not None
        assert data["comments"][0].get("value", None) is not None

        assert data["comments"][0]["name"] == "omero_annotation_namespace"
        self.namespace = data["comments"][0]["value"]
        self.data = data

        mapping = {}


        ontology_annotation_keys = ["termAccession", "termSource", "annotationValue"]

        for k,v in data.items():

            if not isinstance(v, (list, dict)):
                mapping[k] = v

            # ontology annotation keys are prefixed with the parent key
            if isinstance(v, dict):

                if  set(ontology_annotation_keys).issubset(set(v.keys())):
                    mapping[f"{k}_term"] = v["annotationValue"]
                    mapping[f"{k}_term_accession"] = v["termAccession"]
                    mapping[f"{k}_term_source"] = v["termSource"]


        self.mapping = mapping

        self._create_mapped_annotation()


    def _create_mapped_annotation(self):

        map_annotation = MapAnnotationI()
        map_value_ls = [
            NamedValue(str(key), str(self.mapping[key])) for key in self.mapping
        ]
        map_annotation.setMapValue(map_value_ls)

        map_annotation.setNs(rtypes.rstring(self.namespace))

        self.map_annotation = map_annotation

    def save(self, conn, parent_object=None):

        map_ann = conn.getUpdateService().saveAndReturnObject(self.map_annotation)

        if parent_object is not None:
            link(parent_object, self.map_annotation, conn)




def link(obj1, obj2, conn):
        """
        Links two linkable model entities together by creating an instance of
        the correct link entity (e.g. ProjectDatasetLinkI,
        ScreenAnnotationLinkI etc) and persisting it
        in the DB. Accepts client instance to allow calls to happen in correct
        user contexts.

        :param obj1: parent object
        :param obj2: child object
        :param client: The client to use to create the link
        """


        otype1 = obj1.ice_staticId().split("::")[-1]
        if isinstance(obj2, Annotation):
            otype2 = "Annotation"
        else:
            otype2 = obj2.ice_staticId().split("::")[-1]
        try:
            linktype = getattr(model, "%s%sLinkI" % (otype1, otype2))
        except AttributeError:
            assert False, "Object type not supported."

        link = linktype()

        """check if object exist or not"""
        if obj1.id is None:
            link.setParent(obj1)
        else:
            link.setParent(obj1.proxy())
        if obj2.id is None:
            link.setChild(obj2)
        else:
            link.setChild(obj2.proxy())
        return conn.getUpdateService().saveAndReturnObject(link)