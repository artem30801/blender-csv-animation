import os
import csv
import json

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty


from . general_functions import *


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
        default="drone"
    )

    show_warnings: bpy.props.BoolProperty(
        name="Show detailed animation warnings",
        default=False,
    )

    speed_warning_limit: bpy.props.FloatProperty(
        name="Speed limit",
        description="Limit of drone movement speed (m/s)",
        unit='VELOCITY',
        default=3,
        min=0,
    )

    drone_distance_limit: bpy.props.FloatProperty(
        name="Distance limit",
        description="Closest possible distance between drones (m)",
        unit='LENGTH',
        default=1.5,
        min=0,
    )

    filepath: StringProperty(
        name="File Path",
        description="File path used for exporting CSV files",
        maxlen=1024,
        subtype='DIR_PATH',
        default=""
    )

    def get_drone_objects(self, context):
        objects = context.visible_objects

        if self.use_namefilter:
            return filter(lambda x: self.drones_name.lower() in x.name.lower(), objects)
        else:
            return objects

    def execute(self, context):
        create_missing_dir(self.filepath)

        drone_objects = self.get_drone_objects(context)

        frame_start = context.scene.frame_start
        frame_end = context.scene.frame_end

        for drone_obj in drone_objects:

            speed_exeeded = False
            distance_exeeded = False

            context.scene.frame_set(frame_start)
            prev_point = get_position(drone_obj)

            anim_frames = []

            for frame_num in range(frame_start, frame_end + 1):
                context.scene.frame_set(frame_num)

                rgb = get_rgb(drone_obj)
                point = drone_obj.matrix_world.to_translation()
                rot_z = drone_obj.matrix_world.to_euler('XYZ')[2]
                props = get_drone_properties(drone_obj)

                speed = calc_speed(point, prev_point)
                speed_exeeded += self.check_speed(drone_obj, speed, frame_num)
                distance_exeeded += self.check_distances(drone_obj, drone_objects, frame_num)

                row = (
                    int(frame_num),
                    round(point[0], 5), round(point[1], 5), round(point[2], 5),
                    round(rot_z, 5),
                    rgb[0], rgb[1], rgb[2],
                    form_props(props),
                )
                anim_frames.append(row)

                prev_point = point

            if speed_exeeded:
                self.report({'WARNING'}, "Drone '{}' speed limits exceeded".format(drone_obj.name))
            if distance_exeeded:
                self.report({'WARNING'}, "Drone '%s' distance limits exceeded".format(drone_obj.name))

            header = form_header({"name": drone_obj.name.lower(),
                                  "file": os.path.splitext(bpy.path.basename(bpy.data.filepath))[0],
                                  "fps": context.scene.render.fps,
                                  })

            self.write_csv(anim_frames, header, drone_obj.name.lower())

            self.report({'WARNING'}, "Animation file exported for drone '{}'".format(drone_obj.name))

        return {'FINISHED'}

    def check_speed(self, drone_obj, speed, frame="Not specified"):
        if speed > self.speed_warning_limit:
            if self.show_warnings:
                self.report({'WARNING'},
                            "Speed of drone '{}' is greater than limit of {.3f} m/s ({.3f} m/s) on frame {}".format(
                                drone_obj.name,
                                round(self.speed_warning_limit, 5), round(speed, 5),
                                frame,
                            ))
            return True
        return False

    def check_distances(self, drone, drone_objects: list, frame=0):
        _drone_objects = drone_objects.copy()
        if drone in _drone_objects:
            _drone_objects.remove(drone)

        close_drones = filter(lambda drone2:
                              get_distance(drone, drone2) < self.drone_distance_limit,
                              _drone_objects)

        if close_drones:
            if self.show_warnings:
                for err_drone in close_drones:
                    distance = calc_distance(get_position(drone), get_position(err_drone))
                    self.report({'WARNING'},
                                "Distance between drones '{}' and '{}'"
                                " is less than {.3f} m ({.3f} m) on frame {.3f}".format(
                                    drone.name, err_drone.name,
                                    self.drone_distance_limit, distance,
                                    frame
                                ))
            return True
        return False

    def write_csv(self, contents, header, name):
        with open(os.path.join(self.filepath, '{}.csv'.format(name)), 'w') as csv_file:
            anim_writer = csv.writer(
                csv_file,
                delimiter=',',
                quotechar='|',
                quoting=csv.QUOTE_MINIMAL
            )
            anim_writer.writerow([header])
            anim_writer.writerows(contents)


def create_missing_dir(folder_path):
    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)


def form_header(d: dict):
    header = json.dumps(d)
    return header


def form_props(d: dict):
    props = json.dumps(d)
    return props


def get_rgb(drone):
    rgb = [0, 0, 0]
    try:
        slot = next(filter(lambda x: "led_color" in x.name.lower(),
                           drone.material_slots))
    except StopIteration:
        print("No matching slots")
        pass
    else:
        try:
            material = slot.material
            if material.use_nodes:
                print('Node led color')
                value = get_node_color(material)

            else:
                print('Material led color')
                value = material.diffuse_color

            alpha = value[3]
            rgb = [int(value[component] * alpha * 255) for component in range(3)]
        except AttributeError:
            print("Missing attributes")
            pass

    finally:
        return rgb


def get_node_color(material):
    try:
        node = next(filter(lambda x: x.type in ('EMISSION', 'BSDF_DIFFUSE', "Principled BSDF"),
                           material.node_tree.nodes))
    except StopIteration:
        print("No matching nodes")
        raise AttributeError("No matching nodes")
    else:
        return node.inputs[0].default_value












