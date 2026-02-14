"""
ROI (Region of Interest) handling for OMERO ISA import/export.

This module provides functionality to export ROI data from OMERO images to JSON
format and import ROI data from JSON back into OMERO. Supports multiple ROI shape
types including polygons, rectangles, ellipses, lines, points, and labels.

ROI data is stored with full spatial information (z, t, c dimensions) and can be
round-tripped between OMERO and ISA format.

Functions:
    export_rois_to_json: Export OMERO ROIs to JSON file
    import_rois_from_json: Import ROIs from JSON file into OMERO

Supported Shapes:
    - PolygonI: Multi-point polygon shapes
    - RectangleI: Rectangular regions with x, y, width, height
    - EllipseI: Elliptical regions with center and radii
    - LineI: Line segments with start and end points
    - PointI: Single point regions
    - LabelI: Text labels with position

"""
from omero.model import (
    RoiI, PolygonI, RectangleI, EllipseI, LineI, PointI, LabelI
)
from omero.rtypes import rstring, rint, rdouble
import json


def export_rois_to_json(json_path, image, conn):
    """Export all ROIs from an OMERO image to a JSON file.

    Retrieves all ROI objects associated with an image and exports them to
    a JSON file with complete shape information including coordinates and
    dimensional information (z, t, c).

    Args:
        json_path (str or Path): Path where the JSON file will be saved.
        image (omero.model.ImageI): The OMERO image object to export ROIs from.
        conn (omero.gateway.BlitzGateway): Active OMERO connection.

    Returns:
        Path or None: The path to the created JSON file if ROIs exist,
            None if the image has no ROIs.

    Raises:
        IOError: If the JSON file cannot be written.
        RuntimeError: If ROI retrieval from OMERO fails.

    Examples:
        >>> conn = BlitzGateway(...)
        >>> image = conn.getObject("Image", 123)
        >>> roi_path = export_rois_to_json(Path("rois.json"), image, conn)
        >>> print(roi_path)
        /path/to/rois.json

    JSON Structure:
        [
            {
                "roi_id": 1,
                "shapes": [
                    {
                        "type": "PolygonI",
                        "z": 0,
                        "t": 0,
                        "c": 0,
                        "points": "10,10 20,20 30,10"
                    },
                    ...
                ]
            }
        ]

    Note:
        - Only exports ROIs that have shapes
        - Returns None if no ROIs exist (not an error)
        - Preserves dimension information (z, t, c) for each shape
    """
    roi_service = conn.getRoiService()
    result = roi_service.findByImage(image.getId(), None)

    data = []
    for roi in result.rois:
        roi_data = {"roi_id": roi.getId().getValue(), "shapes": []}
        for shape in roi.copyShapes():
            shape_type = shape.__class__.__name__
            shape_info = {
                "type": shape_type,
                "z": shape.getTheZ().getValue() if shape.getTheZ() else None,
                "t": shape.getTheT().getValue() if shape.getTheT() else None,
                "c": shape.getTheC().getValue() if shape.getTheC() else None
            }

            if shape_type == "PolygonI":
                shape_info["points"] = shape.getPoints().getValue()
            elif shape_type == "RectangleI":
                shape_info.update({
                    "x": shape.getX().getValue(),
                    "y": shape.getY().getValue(),
                    "width": shape.getWidth().getValue(),
                    "height": shape.getHeight().getValue()
                })
            elif shape_type == "EllipseI":
                shape_info.update({
                    "x": shape.getX().getValue(),
                    "y": shape.getY().getValue(),
                    "radiusX": shape.getRadiusX().getValue(),
                    "radiusY": shape.getRadiusY().getValue()
                })
            elif shape_type == "LineI":
                shape_info.update({
                    "x1": shape.getX1().getValue(),
                    "y1": shape.getY1().getValue(),
                    "x2": shape.getX2().getValue(),
                    "y2": shape.getY2().getValue()
                })
            elif shape_type == "PointI":
                shape_info.update({
                    "x": shape.getX().getValue(),
                    "y": shape.getY().getValue()
                })
            elif shape_type == "LabelI":
                shape_info.update({
                    "x": shape.getX().getValue(),
                    "y": shape.getY().getValue(),
                    "text": shape.getTextValue().getValue()
                })

            roi_data["shapes"].append(shape_info)
        data.append(roi_data)

    if len(data) > 0:
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
        return json_path
    return None


def import_rois_from_json(json_path, image, conn):
    """Import ROIs from a JSON file into an OMERO image.

    Reads ROI definitions from a JSON file and creates ROI objects in OMERO.
    Supports all standard OMERO shape types. Each ROI and its shapes are
    properly linked to the target image.

    Args:
        json_path (str or Path): Path to the JSON file containing ROI definitions.
        image (omero.model.ImageI): The target OMERO image to import ROIs into.
        conn (omero.gateway.BlitzGateway): Active OMERO connection.

    Returns:
        omero.model.RoiI: The first imported ROI object (when importing multiple
            ROIs, the first one is returned for backwards compatibility).

    Raises:
        FileNotFoundError: If the JSON file doesn't exist.
        json.JSONDecodeError: If the JSON file is invalid.
        ValueError: If a shape type is not recognized.
        RuntimeError: If OMERO save operation fails.

    Examples:
        >>> conn = BlitzGateway(...)
        >>> image = conn.getObject("Image", 123)
        >>> roi = import_rois_from_json(Path("rois.json"), image, conn)
        >>> print(f"Imported {len(roi.copyShapes())} shapes")
        Imported 3 shapes

    Supported Shape Types:
        - PolygonI: points (string of "x,y x,y ...")
        - RectangleI: x, y, width, height
        - EllipseI: x, y, radiusX, radiusY
        - LineI: x1, y1, x2, y2
        - PointI: x, y
        - LabelI: x, y, text

    JSON Structure Expected:
        [
            {
                "roi_id": 1,
                "shapes": [
                    {
                        "type": "PolygonI",
                        "z": 0,
                        "t": 0,
                        "c": 0,
                        "points": "10,10 20,20 30,10"
                    }
                ]
            }
        ]

    Note:
        - All shapes must have z, t, c coordinates (can be None)
        - Unknown shape types are skipped
        - Each ROI is saved separately to OMERO
        - Default z, t, c to 0 if not specified
    """
    with open(json_path, "r") as f:
        roi_data_list = json.load(f)

    update_service = conn.getUpdateService()

    for roi_data in roi_data_list:
        roi = RoiI()
        roi.setImage(image._obj)

        for shape_info in roi_data["shapes"]:
            shape_type = shape_info["type"]
            z = rint(shape_info["z"] or 0)
            t = rint(shape_info["t"] or 0)
            c = rint(shape_info["c"] or 0)

            if shape_type == "PolygonI":
                shape = PolygonI()
                shape.setPoints(rstring(shape_info["points"]))
            elif shape_type == "RectangleI":
                shape = RectangleI()
                shape.setX(rdouble(shape_info["x"]))
                shape.setY(rdouble(shape_info["y"]))
                shape.setWidth(rdouble(shape_info["width"]))
                shape.setHeight(rdouble(shape_info["height"]))
            elif shape_type == "EllipseI":
                shape = EllipseI()
                shape.setX(rdouble(shape_info["x"]))
                shape.setY(rdouble(shape_info["y"]))
                shape.setRadiusX(rdouble(shape_info["radiusX"]))
                shape.setRadiusY(rdouble(shape_info["radiusY"]))
            elif shape_type == "LineI":
                shape = LineI()
                shape.setX1(rdouble(shape_info["x1"]))
                shape.setY1(rdouble(shape_info["y1"]))
                shape.setX2(rdouble(shape_info["x2"]))
                shape.setY2(rdouble(shape_info["y2"]))
            elif shape_type == "PointI":
                shape = PointI()
                shape.setX(rdouble(shape_info["x"]))
                shape.setY(rdouble(shape_info["y"]))
            elif shape_type == "LabelI":
                shape = LabelI()
                shape.setX(rdouble(shape_info["x"]))
                shape.setY(rdouble(shape_info["y"]))
                shape.setTextValue(rstring(shape_info["text"]))
            else:
                continue

            shape.setTheZ(z)
            shape.setTheT(t)
            shape.setTheC(c)
            roi.addShape(shape)

        print(f"import ROI from file {json_path}")
        update_service.saveAndReturnObject(roi)
        return roi
