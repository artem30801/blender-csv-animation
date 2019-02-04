import os
import csv
import math

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty

bl_info = {
    "name": "Export > CSV Drone Swarm Animation Exporter (.csv)",
    "author": "Artem Vasiunik",
    "version": (0, 2, 1),
    "blender": (2, 80, 0),
    #"api": 36079,
    "location": "File > Export > CSV Drone Swarm Animation Exporter (.csv)",
    "description": "Export > CSV Drone Swarm Animation Exporter (.csv)",
    "warning": "",
    "wiki_url": "https://github.com/artem30801/blender-csv-animation/blob/master/README.md",
    "tracker_url": "https://github.com/artem30801/blender-csv-animation/issues",
    "category": "Import-Export"
}


class ExportCsv(Operator, ExportHelper):
    bl_idname = "export_swarm_anim.folder"
    bl_label = "Export Drone Swarm animation"
    filename_ext = ''
    use_filter_folder = True

    use_namefilter: bpy.props.BoolProperty(
        name="Use name filter for objects",
        default=True,    
    )

    drones_name: bpy.props.StringProperty(
        name="Name identifier",
        description="Name identifier for all drone objects",
        default="copter"
    )

    speed_warning_limit: bpy.props.FloatProperty(
        name="Speed limit",
        description="Limit of drone movement speed (m/s)",
        default=3
    )
    drone_distance_limit: bpy.props.FloatProperty(
        name="Distance limit",
        description="Closest possible distance between drones (m)",
        default=1.5
    )


    filepath: StringProperty(
        name="File Path",
        description="File path used for exporting CSV files",
        maxlen=1024,
        subtype='DIR_PATH',
        default=""
    )

    def execute(self, context):
        return export_animation(context, self.filepath, self.drones_name, self.use_namefilter,
                                self.speed_warning_limit, self.drone_distance_limit
                                )


def export_animation(context, folder_path, drones_name, use_namefilter,
                     speed_warning_limit, drone_distance_limit
                     ):
    create_folder_if_does_not_exist(folder_path)
    scene = context.scene
    objects = context.visible_objects

    drone_objects = []
    if use_namefilter:
        for obj in objects:
            if drones_name.lower() in obj.name.lower():
                drone_objects.append(obj)
    else:
        drone_objects = objects
        
    frame_start = scene.frame_start
    frame_end = scene.frame_end

    for obj in drone_objects:
        with open(os.path.join(folder_path, '{}.csv'.format(obj.name.lower())), 'w') as csv_file:
            animation_file_writer = csv.writer(
                csv_file,
                delimiter=',',
                quotechar='|',
                quoting=csv.QUOTE_MINIMAL
            )
            prev_x, prev_y, prev_z = 0, 0, 0
            for frame_number in range(frame_start, frame_end + 1):
                scene.frame_set(frame_number)
                rgb = get_rgb_from_object(obj)
                x, y, z = obj.matrix_world.to_translation()
                rot_z = obj.matrix_world.to_euler('XYZ')[2]
                
                speed = calc_speed(
                    (x, y, z),
                    (prev_x, prev_y, prev_z)
                ) if frame_number != frame_start else 1

                if speed > speed_warning_limit:
                    bpy.context.window_manager.popup_menu(
                        popup_speed_error_menu,
                        title="Error",
                        icon='ERROR'
                    )
                        
                prev_x, prev_y, prev_z = x, y, z
                animation_file_writer.writerow([
                    str(frame_number),
                    round(x, 5), round(y, 5), round(z, 5),
                    round(rot_z, 5),
                    *rgb,
                ])
    return {'FINISHED'}


def create_folder_if_does_not_exist(folder_path):
    if os.path.isdir(folder_path):
        return
    os.mkdir(folder_path)


def get_rgb_from_object(obj):
    rgb = [0, 0, 0]
    try:
        if len(obj.data.materials) >= 1:
            material = obj.data.materials[0]
            for component in range(3):
                rgb[component] = int(material.diffuse_color[component] * 255)
    except AttributeError:
        pass
    finally:
        return rgb


def calc_speed(start_point, end_point):
    time_delta = 0.1
    distance = calc_distance(start_point, end_point)
    return distance / time_delta


def calc_distance(start_point, end_point):
    distance = math.sqrt(
        (start_point[0] - end_point[0]) ** 2 +
        (start_point[1] - end_point[1]) ** 2 +
        (start_point[2] - end_point[2]) ** 2
    )
    return distance


def popup_speed_error_menu(self, context, limit):
    self.layout.label("Speed of drone is greater than 3 m/s")  #TODO param


def popup_dronedistance_error_menu(self, context, limit):
    self.layout.label("Distance detween some drones is greater than 1 m")



def menu_func(self, context):
    self.layout.operator(
        ExportCsv.bl_idname,
        text="CSV Drone Swarm Animation Exporter (.csv)"
    )


def register():
    bpy.utils.register_class(ExportCsv)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)


def unregister():
    bpy.utils.unregister_class(ExportCsv)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()
