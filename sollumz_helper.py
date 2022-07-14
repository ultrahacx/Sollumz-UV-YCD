import bpy
import traceback
import os
import time
from abc import abstractmethod
from .tools.blenderhelper import get_children_recursive
from .sollumz_properties import BOUND_TYPES
from .ydr.ydrexport import get_used_materials


class SOLLUMZ_OT_base:
    bl_options = {"UNDO"}
    bl_action = "do"
    bl_showtime = False
    bl_update_view = False

    def __init__(self):
        self.messages = []

    @abstractmethod
    def run(self, context):
        pass

    def execute(self, context):
        start = time.time()
        try:
            result = self.run(context)
            if self.bl_update_view:
                reset_sollumz_view(context.scene)
        except:
            result = False
            self.error(
                f"Error occured running operator : {self.bl_idname} \n {traceback.format_exc()}")
        end = time.time()

        if self.bl_showtime and result == True:
            self.message(
                f"{self.bl_label} took {round(end - start, 3)} seconds to {self.bl_action}.")

        if len(self.messages) > 0:
            self.message("\n".join(self.messages))

        if result:
            return {"FINISHED"}
        else:
            return {"CANCELLED"}

    def message(self, msg):
        self.report({"INFO"}, msg)

    def warning(self, msg):
        self.report({"WARNING"}, msg)

    def error(self, msg):
        self.report({"ERROR"}, msg)


def reset_sollumz_view(scene):
    scene.hide_collision = not scene.hide_collision
    scene.hide_high_lods = not scene.hide_high_lods
    scene.hide_medium_lods = not scene.hide_medium_lods
    scene.hide_low_lods = not scene.hide_low_lods
    scene.hide_very_low_lods = not scene.hide_very_low_lods

    scene.hide_collision = not scene.hide_collision
    scene.hide_high_lods = not scene.hide_high_lods
    scene.hide_medium_lods = not scene.hide_medium_lods
    scene.hide_low_lods = not scene.hide_low_lods
    scene.hide_very_low_lods = not scene.hide_very_low_lods


def get_sollumz_objects_from_objects(objs, sollum_type):
    robjs = []
    for obj in objs:
        if obj.sollum_type in sollum_type:
            robjs.append(obj)
        for child in obj.children:
            if child.sollum_type in sollum_type:
                robjs.append(child)
    return robjs


def find_fragment_file(filepath):
    directory = os.path.dirname(filepath)
    for file in os.listdir(directory):
        if file.endswith(".yft.xml"):
            return os.path.join(directory, file)
    return None


def has_embedded_textures(obj):
    for mat in get_used_materials(obj):
        nodes = mat.node_tree.nodes
        for node in nodes:
            if isinstance(node, bpy.types.ShaderNodeTexImage):
                if node.texture_properties.embedded == True:
                    return True
    return False


def has_collision(obj):
    for child in get_children_recursive(obj):
        if child.sollum_type in BOUND_TYPES:
            return True
    return False
