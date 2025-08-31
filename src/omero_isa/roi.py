from omero.model import (
    RoiI, PolygonI, RectangleI, EllipseI, LineI, PointI, LabelI
)
from omero.rtypes import rstring, rint, rdouble
import json




def export_rois_to_json(json_path, image, conn):


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

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)




def import_rois_from_json(json_path, image, conn):
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

        update_service.saveAndReturnObject(roi)
