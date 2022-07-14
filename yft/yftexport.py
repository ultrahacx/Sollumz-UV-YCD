import os
from mathutils import Matrix
from ..yft.yftimport import get_fragment_drawable
from ..sollumz_properties import BOUND_TYPES, SollumType
from ..ydr.ydrexport import drawable_from_object, get_used_materials, lights_from_object
from ..ybn.ybnexport import composite_from_objects
from ..cwxml.fragment import BoneTransformItem, ChildrenItem, Fragment, GroupItem, LODProperty, TransformItem, WindowItem
from ..sollumz_helper import get_sollumz_objects_from_objects
from ..tools.fragmenthelper import image_to_shattermap
from ..tools.meshhelper import get_bound_center, get_sphere_radius
from ..tools.utils import divide_vector_inv, prop_array_to_vector


def get_group_objects(fragment, index=0):
    groups = []
    for child in fragment.children:
        if child.sollum_type == SollumType.FRAGGROUP:
            groups.append(child)
            index += 1
    for g in groups:
        cgroups = get_group_objects(g, index)
        for cg in cgroups:
            if cg not in groups:
                groups.append(cg)

    return groups


def get_obj_parent_group_index(gobjs, obj):
    parent = obj.parent
    if parent.sollum_type == SollumType.FRAGGROUP:
        return gobjs.index(parent)
    else:
        return 255


def get_shattermap_image(obj):
    mat = obj.data.materials[0]
    return mat.node_tree.nodes["ShatterMap"].image


def obj_to_vehicle_window(obj, materials):
    mesh = obj.data

    v1 = None
    v2 = None
    v3 = None

    for loop in mesh.loops:
        vert_idx = loop.vertex_index
        uv = mesh.uv_layers[0].data[loop.index].uv
        if uv.x == 0 and uv.y == 1:
            v1 = mesh.vertices[vert_idx].co
        elif uv.x == 1 and uv.y == 1:
            v2 = mesh.vertices[vert_idx].co
        elif uv.x == 0 and uv.y == 0:
            v3 = mesh.vertices[vert_idx].co

    shattermap = get_shattermap_image(obj)
    resx = shattermap.size[0]
    resy = shattermap.size[1]
    thickness = 0.01

    edge1 = (v2 - v1) / resx
    edge2 = (v3 - v1) / resy
    edge3 = edge1.normalized().cross(edge2.normalized()) * thickness

    mat = Matrix()
    mat[0] = edge1.x, edge2.x, edge3.x, v1.x
    mat[1] = edge1.y, edge2.y, edge3.y, v1.y
    mat[2] = edge1.z, edge2.z, edge3.z, v1.z
    mat.invert()

    window = WindowItem()
    window.projection_matrix = mat
    window.shattermap = image_to_shattermap(shattermap)
    window.unk_ushort_1 = materials.index(obj.data.materials[1])
    window.unk_float_17 = obj.vehicle_window_properties.unk_float_17
    window.unk_float_18 = obj.vehicle_window_properties.unk_float_18
    window.cracks_texture_tiling = obj.vehicle_window_properties.cracks_texture_tiling
    return window


def fragment_from_object(exportop, fobj, exportpath, export_settings=None):
    fragment = Fragment()

    dobj = None
    for child in fobj.children:
        if child.sollum_type == SollumType.DRAWABLE:
            dobj = child
    if dobj is None:
        raise Exception("NO DRAWABLE TO EXPORT.")

    materials = None
    materials = get_used_materials(fobj)

    fragment.drawable = drawable_from_object(
        exportop, dobj, exportpath, None, materials, export_settings, True)

    lights_from_object(fobj, fragment.lights,
                       export_settings, armature_obj=dobj)

    fragment.name = fobj.name.split(".")[0]
    fragment.bounding_sphere_center = get_bound_center(
        fobj, world=export_settings.use_transforms)
    fragment.bounding_sphere_radius = get_sphere_radius(
        fragment.drawable.bounding_box_max, fragment.drawable.bounding_sphere_center)

    fragment.unknown_b0 = fobj.fragment_properties.unk_b0
    fragment.unknown_b8 = fobj.fragment_properties.unk_b8
    fragment.unknown_bc = fobj.fragment_properties.unk_bc
    fragment.unknown_c0 = fobj.fragment_properties.unk_c0
    fragment.unknown_c4 = fobj.fragment_properties.unk_c4
    fragment.unknown_cc = fobj.fragment_properties.unk_cc
    fragment.gravity_factor = fobj.fragment_properties.gravity_factor
    fragment.buoyancy_factor = fobj.fragment_properties.buoyancy_factor

    for idx in range(len(dobj.data.bones)):
        m = Matrix()
        for model in dobj.children:
            bone_index = 0
            if model.parent_type == "BONE":
                parent_bone = model.parent_bone
                if parent_bone is not None and parent_bone != "":
                    bone_index = model.parent.data.bones[parent_bone].bone_properties.tag

            if bone_index == idx:
                m = model.matrix_basis
        fragment.bones_transforms.append(
            BoneTransformItem("Item", m))

    lods = []
    for child in fobj.children:
        if child.sollum_type == SollumType.FRAGLOD:
            lods.append(child)

    lod1 = None
    lod2 = None
    lod3 = None

    for idx, lod in enumerate(lods):
        gobjs = get_group_objects(lod)
        bobjs = get_sollumz_objects_from_objects(gobjs, BOUND_TYPES)
        cobjs = get_sollumz_objects_from_objects(gobjs, SollumType.FRAGCHILD)
        vwobjs = get_sollumz_objects_from_objects(
            gobjs, SollumType.FRAGVEHICLEWINDOW)

        flod = LODProperty()
        flod.tag_name = f"LOD{idx+1}"
        flod.unknown_14 = lod.lod_properties.unknown_14
        flod.unknown_18 = lod.lod_properties.unknown_18
        flod.unknown_1c = lod.lod_properties.unknown_1c
        pos_offset = prop_array_to_vector(lod.lod_properties.position_offset)
        flod.position_offset = pos_offset
        flod.unknown_40 = prop_array_to_vector(lod.lod_properties.unknown_40)
        flod.unknown_50 = prop_array_to_vector(lod.lod_properties.unknown_50)
        flod.damping_linear_c = prop_array_to_vector(
            lod.lod_properties.damping_linear_c)
        flod.damping_linear_v = prop_array_to_vector(
            lod.lod_properties.damping_linear_v)
        flod.damping_linear_v2 = prop_array_to_vector(
            lod.lod_properties.damping_linear_v2)
        flod.damping_angular_c = prop_array_to_vector(
            lod.lod_properties.damping_angular_c)
        flod.damping_angular_v = prop_array_to_vector(
            lod.lod_properties.damping_angular_v)
        flod.damping_angular_v2 = prop_array_to_vector(
            lod.lod_properties.damping_angular_v2)

        flod.archetype.name = lod.lod_properties.archetype_name
        flod.archetype.mass = lod.lod_properties.archetype_mass
        flod.archetype.mass_inv = 1 / lod.lod_properties.archetype_mass
        flod.archetype.unknown_48 = lod.lod_properties.archetype_unknown_48
        flod.archetype.unknown_4c = lod.lod_properties.archetype_unknown_4c
        flod.archetype.unknown_50 = lod.lod_properties.archetype_unknown_50
        flod.archetype.unknown_54 = lod.lod_properties.archetype_unknown_54
        arch_it = prop_array_to_vector(
            lod.lod_properties.archetype_inertia_tensor)
        flod.archetype.inertia_tensor = arch_it
        flod.archetype.inertia_tensor_inv = divide_vector_inv(arch_it)
        flod.archetype.bounds = composite_from_objects(
            bobjs, export_settings, True)

        gidx = 0
        for gobj in gobjs:
            group = GroupItem()
            group.name = gobj.name if "group" not in gobj.name else gobj.name.replace(
                "_group", "").split(".")[0]
            group.parent_index = get_obj_parent_group_index(gobjs, gobj)
            group.glass_window_index = gobj.group_properties.glass_window_index
            group.glass_flags = gobj.group_properties.glass_flags
            group.strength = gobj.group_properties.strength
            group.force_transmission_scale_up = gobj.group_properties.force_transmission_scale_up
            group.force_transmission_scale_down = gobj.group_properties.force_transmission_scale_down
            group.joint_stiffness = gobj.group_properties.joint_stiffness
            group.min_soft_angle_1 = gobj.group_properties.min_soft_angle_1
            group.max_soft_angle_1 = gobj.group_properties.max_soft_angle_1
            group.max_soft_angle_2 = gobj.group_properties.max_soft_angle_2
            group.max_soft_angle_3 = gobj.group_properties.max_soft_angle_3
            group.rotation_speed = gobj.group_properties.rotation_speed
            group.rotation_strength = gobj.group_properties.rotation_strength
            group.restoring_max_torque = gobj.group_properties.restoring_max_torque
            group.latch_strength = gobj.group_properties.latch_strength
            group.mass = gobj.group_properties.mass
            group.min_damage_force = gobj.group_properties.min_damage_force
            group.damage_health = gobj.group_properties.damage_health
            group.unk_float_5c = gobj.group_properties.unk_float_5c
            group.unk_float_60 = gobj.group_properties.unk_float_60
            group.unk_float_64 = gobj.group_properties.unk_float_64
            group.unk_float_68 = gobj.group_properties.unk_float_68
            group.unk_float_6c = gobj.group_properties.unk_float_6c
            group.unk_float_70 = gobj.group_properties.unk_float_70
            group.unk_float_74 = gobj.group_properties.unk_float_74
            group.unk_float_78 = gobj.group_properties.unk_float_78
            group.unk_float_a8 = gobj.group_properties.unk_float_a8
            flod.groups.append(group)
            gidx += 1

        for cobj in cobjs:
            child = ChildrenItem()
            gobj = cobj.parent
            child.group_index = gobjs.index(gobj)
            child.bone_tag = cobj.child_properties.bone_tag
            child.pristine_mass = cobj.child_properties.pristine_mass
            child.damaged_mass = cobj.child_properties.damaged_mass
            child.unk_vec = prop_array_to_vector(
                cobj.child_properties.unk_vec)
            child.inertia_tensor = prop_array_to_vector(
                cobj.child_properties.inertia_tensor, 4)

            dobj = get_fragment_drawable(cobj)

            if dobj:
                child.drawable = drawable_from_object(
                    exportop, dobj, exportpath, None, materials, export_settings, True, False)
            else:
                child.drawable.matrix = Matrix()
                child.drawable.shader_group = None
                child.drawable.skeleton = None
                child.drawable.joints = None

            transform = cobj.matrix_basis.transposed()
            a = transform[3][0] - pos_offset.x
            b = transform[3][1] - pos_offset.y
            c = transform[3][2] - pos_offset.z
            transform[3][0] = a
            transform[3][1] = b
            transform[3][2] = c
            flod.transforms.append(TransformItem("Item", transform))
            flod.children.append(child)

        for wobj in vwobjs:
            vehwindow = obj_to_vehicle_window(wobj, materials)
            vehwindow.item_id = get_obj_parent_group_index(gobjs, wobj)
            fragment.vehicle_glass_windows.append(vehwindow)

        if lod.lod_properties.type == 1:
            lod1 = flod
        elif lod.lod_properties.type == 2:
            lod2 = flod
        elif lod.lod_properties.type == 3:
            lod3 = flod

    fragment.physics.lod1 = lod1
    fragment.physics.lod2 = lod2
    fragment.physics.lod3 = lod3

    return fragment


def export_yft(exportop, obj, filepath, export_settings):
    fragment = fragment_from_object(exportop, obj, filepath, export_settings)
    fragment.write_xml(filepath)

    if export_settings.export_with_hi:
        fragment.drawable.drawable_models_med = None
        fragment.drawable.drawable_models_low = None
        fragment.drawable.drawable_models_vlow = None
        for child in fragment.physics.lod1.children:
            child.drawable.drawable_models_med = None
            child.drawable.drawable_models_low = None
            child.drawable.drawable_models_vlow = None
        filepath = os.path.join(os.path.dirname(filepath),
                                os.path.basename(filepath).replace(".yft.xml", "_hi.yft.xml"))
        fragment.write_xml(filepath)
