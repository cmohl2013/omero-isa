from omero import rtypes, model
from omero.model import ProjectI, MapAnnotationI, NamedValue, Annotation

class IsaInvestigationImporter:


    def __init__(self, data):


        # one isa investigation must contain exactly one study
        # the study relates to the omero project
        assert "studies" in data.keys()
        assert len(data["studies"]) == 1

        # isa investigations to be imnported as omero projects
        # must contain annotation_namespace metadata



        self.data = data
        self.study_data = data["studies"][0]

    def _add_mapped_annotations(self, parent_object, conn):

        try:
            maf = MappedAnnotationFactory(self.data)
            maf.save(conn, parent_object=parent_object)
        except AssertionError:
            pass

        try:
            maf = MappedAnnotationFactory(self.study_data)
            maf.save(conn, parent_object=parent_object)
        except AssertionError:
            pass


        for k in self.data.keys():
            try:
                maf = MappedAnnotationFactory(self.data[k])
                maf.save(conn, parent_object=parent_object)
            except AssertionError:
                pass


        #TODO es werden hier noch keine listen abgearbeitet (people, publications..)
        # better hardcode

        for k in self.study_data.keys():
            try:
                maf = MappedAnnotationFactory(self.study_data[k])
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
        return project


class MappedAnnotationFactory:


    def __init__(self, data):


        assert isinstance(data, dict)
        assert "comments" in data.keys()
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
                if  ontology_annotation_keys in v.keys():
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