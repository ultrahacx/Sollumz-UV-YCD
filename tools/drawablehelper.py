import bpy
from ..ydr.shader_materials import create_shader, try_get_node, ShaderManager
from ..sollumz_properties import SollumType, SOLLUMZ_UI_NAMES, MaterialType
from ..tools.blenderhelper import join_objects, get_children_recursive
from mathutils import Vector


def create_drawable(sollum_type=SollumType.DRAWABLE):
    empty = bpy.data.objects.new(SOLLUMZ_UI_NAMES[sollum_type], None)
    empty.empty_display_size = 0
    empty.sollum_type = sollum_type
    bpy.context.collection.objects.link(empty)
    bpy.context.view_layer.objects.active = bpy.data.objects[empty.name]

    return empty


def convert_selected_to_drawable(objs, use_names=False, multiple=False, do_center=True):
    parent = None

    center = Vector()
    dobjs = []

    if not multiple:
        dobj = create_drawable()
        dobjs.append(dobj)
        if do_center:
            for obj in objs:
                center += obj.location

            center /= len(objs)
            dobj.location = center
        dmobj = create_drawable(SollumType.DRAWABLE_MODEL)
        dmobj.parent = dobj

    for obj in objs:

        if obj.type != "MESH":
            raise Exception(
                f"{obj.name} cannot be converted because it has no mesh data.")

        if multiple:
            dobj = parent or create_drawable()
            dobjs.append(dobj)
            if do_center:
                dobj.location = obj.location
                obj.location = Vector()
            dmobj = create_drawable(SollumType.DRAWABLE_MODEL)
            dmobj.parent = dobj
        elif do_center:
            obj.location -= center

        obj.parent = dmobj

        name = obj.name

        if use_names:
            obj.name = name + "_old"
            dobj.name = name

        obj.sollum_type = SollumType.DRAWABLE_GEOMETRY

        new_obj = obj.copy()
        # add color layer
        if len(new_obj.data.vertex_colors) == 0:
            new_obj.data.vertex_colors.new()
        # add object to collection
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.context.collection.objects.link(new_obj)
        new_obj.name = name + "_geom"

    return dobjs


def join_drawable_geometries(drawable):
    join_objects(get_drawable_geometries(drawable))


def get_drawable_geometries(drawable):
    cobjs = []
    children = get_children_recursive(drawable)
    for obj in children:
        if obj.sollum_type == SollumType.DRAWABLE_GEOMETRY:
            cobjs.append(obj)
    return cobjs


def convert_material(material):

    if material.sollum_type != MaterialType.NONE:
        raise Exception("Error can not convert a sollumz material.")

    bsdf = material.node_tree.nodes["Principled BSDF"]

    diffuse_node = None
    diffuse_input = bsdf.inputs["Base Color"]
    if diffuse_input.is_linked:
        diffuse_node = diffuse_input.links[0].from_node

    if not isinstance(diffuse_node, bpy.types.ShaderNodeTexImage):
        raise Exception("Error linked base color node is not a image node.")

    specular_node = None
    specular_input = bsdf.inputs["Specular"]
    if specular_input.is_linked:
        specular_node = specular_input.links[0].from_node

    normal_node = None
    normal_input = bsdf.inputs["Normal"]
    if len(normal_input.links) > 0:
        normal_map_node = normal_input.links[0].from_node
        normal_map_input = normal_map_node.inputs["Color"]
        if len(normal_map_input.links) > 0:
            normal_node = normal_map_input.links[0].from_node

    shader_name = "default"
    if normal_node is not None and specular_node is not None:
        shader_name = "normal_spec"
    elif normal_node is not None:
        shader_name = "normal"
    elif normal_node is None and specular_node is not None:
        shader_name = "spec"

    new_material = create_shader(shader_name)

    bsdf = new_material.node_tree.nodes["Principled BSDF"]

    new_diffuse_node = try_get_node(new_material.node_tree, "DiffuseSampler")
    if diffuse_node and new_diffuse_node:
        new_diffuse_node.image = diffuse_node.image

    new_specular_node = try_get_node(new_material.node_tree, "SpecSampler")
    if specular_node and new_specular_node:
        new_specular_node.image = specular_node.image

    new_normal_node = try_get_node(new_material.node_tree, "BumpSampler")
    if normal_node and new_normal_node:
        new_normal_node.image = normal_node.image

    return new_material


def convert_material_to_selected(material, shader_name):

    if material.sollum_type == MaterialType.SHADER:
        return convert_shader_to_shader(material, shader_name)

    bsdf = material.node_tree.nodes["Principled BSDF"]

    diffuse_node = None
    diffuse_input = bsdf.inputs["Base Color"]
    if diffuse_input.is_linked:
        diffuse_node = diffuse_input.links[0].from_node

    if not isinstance(diffuse_node, bpy.types.ShaderNodeTexImage):
        raise Exception("Error linked base color node is not a image node.")

    specular_node = None
    specular_input = bsdf.inputs["Specular"]
    if specular_input.is_linked:
        specular_node = specular_input.links[0].from_node

    normal_node = None
    normal_input = bsdf.inputs["Normal"]
    if len(normal_input.links) > 0:
        normal_map_node = normal_input.links[0].from_node
        normal_map_input = normal_map_node.inputs["Color"]
        if len(normal_map_input.links) > 0:
            normal_node = normal_map_input.links[0].from_node

    new_material = create_shader(shader_name)

    bsdf = new_material.node_tree.nodes["Principled BSDF"]

    new_diffuse_node = try_get_node(new_material.node_tree, "DiffuseSampler")
    if diffuse_node and new_diffuse_node:
        new_diffuse_node.image = diffuse_node.image

    new_specular_node = try_get_node(new_material.node_tree, "SpecSampler")
    if specular_node and new_specular_node:
        new_specular_node.image = specular_node.image

    new_normal_node = try_get_node(new_material.node_tree, "BumpSampler")
    if normal_node and new_normal_node:
        new_normal_node.image = normal_node.image

    return new_material


def convert_shader_to_shader(material, shader_name):

    shader = ShaderManager.shaders[shader_name]
    new_material = create_shader(shader_name)

    # TODO: array nodes params
    for param in shader.parameters:
        if param.type == "Texture":
            node = try_get_node(material.node_tree, param.name)
            if not node:
                continue
            tonode = try_get_node(new_material.node_tree, param.name)
            tonode.image = node.image
        elif param.type == "Vector":
            node_x = try_get_node(material.node_tree, param.name + "_x")
            if not node_x:
                continue
            node_y = try_get_node(material.node_tree, param.name + "_y")
            node_z = try_get_node(material.node_tree, param.name + "_z")
            node_w = try_get_node(material.node_tree, param.name + "_w")
            tonode_x = try_get_node(new_material.node_tree, param.name + "_x")
            tonode_y = try_get_node(new_material.node_tree, param.name + "_y")
            tonode_z = try_get_node(new_material.node_tree, param.name + "_z")
            tonode_w = try_get_node(new_material.node_tree, param.name + "_w")
            tonode_x.outputs[0].default_value = node_x.outputs[0].default_value
            tonode_y.outputs[0].default_value = node_y.outputs[0].default_value
            tonode_z.outputs[0].default_value = node_z.outputs[0].default_value
            tonode_w.outputs[0].default_value = node_w.outputs[0].default_value

    return new_material
