from abc import ABC as AbstractClass, abstractmethod
from mathutils import Vector
from xml.etree import ElementTree as ET
from .element import (
    AttributeProperty,
    ElementTree,
    ElementProperty,
    FlagsProperty,
    ListProperty,
    MatrixProperty,
    ValueProperty,
    VectorProperty
)


class YBN:

    file_extension = ".ybn.xml"

    @staticmethod
    def from_xml_file(filepath):
        return BoundFile.from_xml_file(filepath)

    @staticmethod
    def write_xml(bound_file, filepath):
        return bound_file.write_xml(filepath)


class BoundFile(ElementTree):
    tag_name = "BoundsFile"

    def __init__(self):
        super().__init__()
        self.composite = BoundComposite()


class Bound(ElementTree, AbstractClass):
    tag_name = "Bounds"

    def __init__(self):
        super().__init__()
        self.box_min = VectorProperty("BoxMin")
        self.box_max = VectorProperty("BoxMax")
        self.box_center = VectorProperty("BoxCenter")
        self.sphere_center = VectorProperty("SphereCenter")
        self.sphere_radius = ValueProperty("SphereRadius", 0.0)
        self.margin = ValueProperty("Margin", 0)
        self.volume = ValueProperty("Volume", 0)
        self.inertia = VectorProperty("Inertia")
        self.material_index = ValueProperty("MaterialIndex", 0)
        self.material_color_index = ValueProperty("MaterialColourIndex", 0)
        self.procedural_id = ValueProperty("ProceduralID", 0)
        self.room_id = ValueProperty("RoomID", 0)
        self.ped_density = ValueProperty("PedDensity", 0)
        self.unk_flags = ValueProperty("UnkFlags", 0)
        self.poly_flags = ValueProperty("PolyFlags", 0)
        self.unk_type = ValueProperty("UnkType", 0)


class BoundComposite(Bound):
    def __init__(self):
        super().__init__()
        self.type = AttributeProperty("type", "Composite")
        self.children = BoundListProperty()


class BoundItem(Bound, AbstractClass):
    tag_name = "Item"

    @property
    @abstractmethod
    def type(self) -> str:
        raise NotImplementedError

    def __init__(self):
        super().__init__()
        self.type = AttributeProperty("type", self.type)
        self.composite_transform = MatrixProperty("CompositeTransform")
        self.composite_flags1 = FlagsProperty("CompositeFlags1")
        self.composite_flags2 = FlagsProperty("CompositeFlags2")


class BoundBox(BoundItem):
    type = "Box"


class BoundSphere(BoundItem):
    type = "Sphere"


class BoundCapsule(BoundItem):
    type = "Capsule"


class BoundCylinder(BoundItem):
    type = "Cylinder"


class BoundDisc(BoundItem):
    type = "Disc"


class BoundCloth(BoundItem):
    type = "Cloth"


class VerticesProperty(ElementProperty):
    value_types = (list)

    def __init__(self, tag_name: str = "Vertices", value=None):
        super().__init__(tag_name, value or [])

    @staticmethod
    def from_xml(element: ET.Element):
        new = VerticesProperty(element.tag, [])
        text = element.text.strip().split("\n")
        if len(text) > 0:
            for line in text:
                coords = line.strip().split(",")
                if not len(coords) == 3:
                    return VerticesProperty.read_value_error(element)

                new.value.append(
                    Vector((float(coords[0]), float(coords[1]), float(coords[2]))))

        return new

    def to_xml(self):
        element = ET.Element(self.tag_name)
        text = ["\n"]

        for vertex in self.value:
            if not isinstance(vertex, Vector):
                raise TypeError(
                    f"VerticesProperty can only contain Vector objects, not '{type(self.value)}'!")
            for index, component in enumerate(vertex):
                text.append(str(component))
                if index < len(vertex) - 1:
                    text.append(", ")
            text.append("\n")

        element.text = "".join(text)

        return element


class OctantsProperty(ElementProperty):
    value_types = (list)

    def __init__(self, tag_name: str = "Octants", value=None):
        super().__init__(tag_name, value or [])

    @staticmethod
    def from_xml(element: ET.Element):
        new = OctantsProperty(element.tag, [])
        if not element.text:
            return new
        allinds = []
        ind_s = element.text.strip().replace(" ", "").replace("\n", ",").split(",")
        ind = []
        for idx, i in enumerate(ind_s):
            if idx % 3 == 0 and idx != 0:
                allinds.append(ind)
                ind = []
            if i:
                ind.append(int(i))

        new.value = allinds
        return new

    def to_xml(self):
        element = ET.Element(self.tag_name)
        return element


class BoundGeometryBVH(BoundItem):
    type = "GeometryBVH"

    def __init__(self):
        super().__init__()
        self.geometry_center = VectorProperty("GeometryCenter")
        self.materials = MaterialsListProperty()
        self.vertices = VerticesProperty("Vertices")
        self.vertex_colors = VertexColorProperty("VertexColours")
        self.polygons = PolygonsProperty()


class BoundGeometry(BoundGeometryBVH):
    type = "Geometry"

    def __init__(self):
        super().__init__()
        self.unk_float_1 = ValueProperty("UnkFloat1")
        self.unk_float_2 = ValueProperty("UnkFloat2")
        # Placeholder: Currently not implemented by CodeWalker
        self.vertices_2 = VerticesProperty("Vertices2")
        self.octants = OctantsProperty("Octants")


class BoundListProperty(ListProperty):
    list_type = BoundItem
    tag_name = "Children"

    @staticmethod
    def from_xml(element: ET.Element):
        new = BoundListProperty()

        for child in element.iter():
            if "type" in child.attrib:
                bound_type = child.get("type")
                if bound_type == "Box":
                    new.value.append(BoundBox.from_xml(child))
                elif bound_type == "Sphere":
                    new.value.append(BoundSphere.from_xml(child))
                elif bound_type == "Capsule":
                    new.value.append(BoundCapsule.from_xml(child))
                elif bound_type == "Cylinder":
                    new.value.append(BoundCylinder.from_xml(child))
                elif bound_type == "Disc":
                    new.value.append(BoundDisc.from_xml(child))
                elif bound_type == "Cloth":
                    new.value.append(BoundCloth.from_xml(child))
                elif bound_type == "Geometry":
                    new.value.append(BoundGeometry.from_xml(child))
                elif bound_type == "GeometryBVH":
                    new.value.append(BoundGeometryBVH.from_xml(child))

        return new


class MaterialItem(ElementTree):
    tag_name = "Item"

    def __init__(self):
        super().__init__()
        self.type = ValueProperty("Type", 0)
        self.procedural_id = ValueProperty("ProceduralID", 0)
        self.room_id = ValueProperty("RoomID", 0)
        self.ped_density = ValueProperty("PedDensity", 0)
        self.flags = FlagsProperty()
        self.material_color_index = ValueProperty("MaterialColourIndex", 0)
        self.unk = ValueProperty("Unk", 0)


class MaterialsListProperty(ListProperty):
    list_type = MaterialItem
    tag_name = "Materials"


class VertexColorProperty(ElementProperty):
    value_types = (list)

    def __init__(self, tag_name: str = "VertexColours", value=None):
        super().__init__(tag_name, value or [])

    @staticmethod
    def from_xml(element: ET.Element):
        new = VertexColorProperty(element.tag, [])
        text = element.text.strip().split("\n")
        if len(text) > 0:
            for line in text:
                colors = line.strip().split(",")
                if not len(colors) == 4:
                    return VertexColorProperty.read_value_error(element)

                new.value.append([int(colors[0]), int(
                    colors[1]), int(colors[2]), int(colors[3])])

        return new

    def to_xml(self):
        element = ET.Element(self.tag_name)
        element.text = "\n"

        if len(self.value) == 0:
            return None

        for color in self.value:
            for index, component in enumerate(color):
                element.text += str(int(component * 255))
                if index < len(color) - 1:
                    element.text += ", "
            element.text += "\n"

        return element


class Polygon(ElementTree, AbstractClass):
    def __init__(self):
        super().__init__()
        self.material_index = AttributeProperty("m", 0)


class PolygonsProperty(ListProperty):
    list_type = Polygon
    tag_name = "Polygons"

    @staticmethod
    def from_xml(element: ET.Element):
        new = PolygonsProperty()

        for child in element.iter():
            if child.tag == "Box":
                new.value.append(Box.from_xml(child))
            elif child.tag == "Sphere":
                new.value.append(Sphere.from_xml(child))
            elif child.tag == "Capsule":
                new.value.append(Capsule.from_xml(child))
            elif child.tag == "Cylinder":
                new.value.append(Cylinder.from_xml(child))
            elif child.tag == "Triangle":
                new.value.append(Triangle.from_xml(child))

        return new


class Triangle(Polygon):
    tag_name = "Triangle"

    def __init__(self):
        super().__init__()
        self.v1 = AttributeProperty("v1", 0)
        self.v2 = AttributeProperty("v2", 0)
        self.v3 = AttributeProperty("v3", 0)
        self.f1 = AttributeProperty("f1", 0)
        self.f2 = AttributeProperty("f2", 0)
        self.f3 = AttributeProperty("f3", 0)


class Sphere(Polygon):
    tag_name = "Sphere"

    def __init__(self):
        super().__init__()
        self.v = AttributeProperty("v", 0)
        self.radius = AttributeProperty("radius", 0)


class Capsule(Polygon):
    tag_name = "Capsule"

    def __init__(self):
        super().__init__()
        self.v1 = AttributeProperty("v1", 0)
        self.v2 = AttributeProperty("v2", 1)
        self.radius = AttributeProperty("radius", 0)


class Box(Polygon):
    tag_name = "Box"

    def __init__(self):
        super().__init__()
        self.v1 = AttributeProperty("v1", 0)
        self.v2 = AttributeProperty("v2", 1)
        self.v3 = AttributeProperty("v3", 2)
        self.v4 = AttributeProperty("v4", 3)


class Cylinder(Polygon):
    tag_name = "Cylinder"

    def __init__(self):
        super().__init__()
        self.v1 = AttributeProperty("v1", 0)
        self.v2 = AttributeProperty("v2", 1)
        self.radius = AttributeProperty("radius", 0)
