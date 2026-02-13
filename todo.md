## todo


## optional
* study factors export
* study design descriptors export

## in progress
* refine mapped annotation export
* refine mapped annotation import
* cli for import
* user documentation
* poish: refine docstrings






## done

* project class for import
* omero namespace export
* image export
* image metadata to isa
* implement term source metadata
* ontology source references export
* ROI export
* mapped annotation class for import
  * mapped annotations for lists (people, publications)
* omero project import
* omero dataset import
* omero image import
* roi import






### konzept roi export

roi files werden als textfiles mit namen des image files abgespeichert im selben ordner. in den comments enthalten sie eine referenz auf den
pixel datensatz.



### concept import

* following metadata is exported for each mapped annotation as comment
    ```json
    "comments": [
        {
            "name": "annotation_namespace",
            "value": "ISA:INVESTIGATION:ONTOLOGY SOURCE REFERENCE"
        },
    ```

* The project name is taken from the study title

* comments are not imported as mapped annotations

* Dataset Names are taken from the assay comment "title"

* Image names are taken form the dataFile comment "name"

#### logic flow import

1st json level (project):
* create a new project for each study (name from study title)
* for all studies add investigation metadata:
    * add all values of the keys from the highest level to a mapped annotation if they are plain strings or termAcceccions and not empty (implement logic to identify term accessions automatically)
    * add all "people" elements as mapped annotation
    * add all "publications" elements as mapped annotation
* create a new project for each study element
* for each study element add all values of the keys to a mapped annotation of the project if they are plain strings and not empty
* add all "people" elements as mapped annotation (study contacts)
* add all "publications" elements as mapped annotation

* detect automatically term_accessions and add them to the mapped annotation

## class mapped_annotation

* ma = MappedAnnotation(json_data)
* The json_data must contain one comment on the highest level with the annotation namespace
* ma.create() creates the annotation omero object

## class image

* im = Image(json_data)
* The json_data is one dataFile json element
* im.create()
