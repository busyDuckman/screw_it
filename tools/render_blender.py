"""Ray-traced (Cycles) product shot of an STL.

Usage:
  blender -b -P tools/render_blender.py -- in.stl out.png [--color R,G,B]
          [--elev DEG] [--azim DEG] [--samples N] [--size W,H]
          [--outline] [--glass] [--flat]
          [--labels a,b,c --label-spacing MM]
"""
import argparse
import math
import sys

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("stl")
    p.add_argument("out")
    p.add_argument("--color", default="0.95,0.42,0.08")
    p.add_argument("--elev", type=float, default=38)
    p.add_argument("--azim", type=float, default=-28)
    p.add_argument("--samples", type=int, default=256)
    p.add_argument("--size", default="1600,1000")
    p.add_argument("--lens", type=float, default=85)
    p.add_argument("--outline", action="store_true", help="draw silhouette + crease lines")
    p.add_argument("--glass", action="store_true", help="coloured glass instead of plastic")
    p.add_argument("--flat", action="store_true", help="flat shading: show the mesh facets")
    p.add_argument("--labels", help="comma separated names, one per part along X")
    p.add_argument("--label-spacing", type=float, default=16, help="X pitch of the parts (mm)")
    return p.parse_args(argv)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def import_stl(path, smooth=True):
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = obj
    if smooth:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
    # Sit the part on z=0, centred on the origin.
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    obj.location = (0, 0, 0)
    bpy.context.view_layer.update()
    zmin = min((obj.matrix_world @ Vector(c)).z for c in obj.bound_box)
    obj.location.z -= zmin - 0.05  # hair above the floor: avoids edge flicker
    return obj


def plastic_material(rgb):
    mat = bpy.data.materials.new("PLA")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = 0.5
    bsdf.inputs["Subsurface Weight"].default_value = 0.08
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.4, 0.2)
    bsdf.inputs["Subsurface Scale"].default_value = 0.6
    bsdf.inputs["Coat Weight"].default_value = 0.0
    return mat


def glass_material(rgb):
    mat = bpy.data.materials.new("Glass")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = 0.02
    bsdf.inputs["Transmission Weight"].default_value = 1.0
    bsdf.inputs["IOR"].default_value = 1.45
    return mat


def outlines(scene, width_px):
    """Freestyle ink lines on silhouettes and sharp creases."""
    scene.render.use_freestyle = True
    scene.render.line_thickness_mode = "ABSOLUTE"
    scene.render.line_thickness = width_px
    settings = scene.view_layers[0].freestyle_settings
    settings.crease_angle = math.radians(120)
    lineset = settings.linesets[0] if settings.linesets else settings.linesets.new("Lines")
    lineset.select_by_visibility = True
    lineset.select_silhouette = True
    lineset.select_border = True
    lineset.select_crease = True
    if lineset.linestyle is None:
        lineset.linestyle = bpy.data.linestyles.new("Ink")
    lineset.linestyle.color = (0.02, 0.05, 0.12)


def floor_labels(names, spacing, obj):
    """Flat text on the floor in front of evenly spaced parts."""
    mat = bpy.data.materials.new("Ink")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.08, 0.09, 0.11, 1)
    bsdf.inputs["Roughness"].default_value = 0.8
    y = -obj.dimensions.y / 2 - 3.5
    for i, name in enumerate(names):
        curve = bpy.data.curves.new(f"label_{i}", "FONT")
        curve.body = name
        curve.align_x = "CENTER"
        curve.align_y = "TOP"
        curve.size = 3.5
        curve.extrude = 0.05
        text = bpy.data.objects.new(f"label_{i}", curve)
        bpy.context.collection.objects.link(text)
        text.location = ((i - (len(names) - 1) / 2) * spacing, y, 0.06)
        text.data.materials.append(mat)


def backdrop(size):
    """Seamless studio sweep: a floor that curves up into a back wall."""
    bpy.ops.mesh.primitive_plane_add(size=size * 6, location=(0, size * 0.5, 0))
    floor = bpy.context.object
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.subdivide(number_cuts=40)
    bpy.ops.object.mode_set(mode="OBJECT")
    bend_y, radius = size * 1.2, size * 1.5
    for v in floor.data.vertices:
        d = v.co.y + size * 0.5 - bend_y
        if d > 0:
            ang = min(d / radius, math.pi / 2)
            v.co.z = radius * (1 - math.cos(ang))
            v.co.y = bend_y - size * 0.5 + radius * math.sin(ang)
    mod = floor.modifiers.new("smooth", "SUBSURF")
    mod.levels = mod.render_levels = 2
    bpy.ops.object.shade_smooth()
    mat = bpy.data.materials.new("Backdrop")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.82, 0.83, 0.85, 1)
    b.inputs["Roughness"].default_value = 0.9
    floor.data.materials.append(mat)


def area_light(name, loc, target, energy, size, color=(1, 1, 1)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    direction = Vector(target) - Vector(loc)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_camera(obj, elev, azim, lens, aspect):
    dims = obj.dimensions
    centre = Vector((0, 0, dims.z / 2))
    radius = 0.5 * dims.length
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = lens
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    sensor = cam_data.sensor_width
    fov = 2 * math.atan(sensor / (2 * lens))
    if aspect < 1:
        fov *= aspect
    dist = radius / math.sin(fov / 2) * 1.15
    e, a = math.radians(elev), math.radians(azim)
    cam.location = centre + Vector((math.sin(a) * math.cos(e),
                                    -math.cos(a) * math.cos(e),
                                    math.sin(e))) * dist
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = (centre - cam.location).length
    cam_data.dof.aperture_fstop = 11
    cam_data.clip_end = dist * 20
    bpy.context.scene.camera = cam
    return dist, centre


def configure_render(scene, out, samples, w, h):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.filepath = out
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.92, 0.95, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25
    scene.world = world
    # Use the GPU when there is one; Cycles falls back to CPU otherwise.
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            if any(d.type == backend for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == backend
                scene.cycles.device = "GPU"
                print(f"Cycles device: {backend}")
                break
        except TypeError:
            continue


def main():
    args = parse_args()
    scene = reset_scene()
    w, h = (int(v) for v in args.size.split(","))
    obj = import_stl(args.stl, smooth=not args.flat)
    rgb = [float(c) for c in args.color.split(",")]
    obj.data.materials.append(glass_material(rgb) if args.glass else plastic_material(rgb))
    size = max(obj.dimensions.x, obj.dimensions.y)
    if args.labels:
        floor_labels(args.labels.split(","), args.label_spacing, obj)
    backdrop(size)
    dist, centre = setup_camera(obj, args.elev, args.azim, args.lens, w / h)
    s = size
    area_light("Key", (-s * 0.9, -s * 1.0, s * 1.3), centre, 9e4 * (s / 100) ** 2, s * 0.8, (1, 0.96, 0.9))
    area_light("Fill", (s * 1.2, -s * 0.6, s * 0.5), centre, 1.2e4 * (s / 100) ** 2, s * 1.2, (0.9, 0.95, 1))
    area_light("Rim", (s * 0.3, s * 1.1, s * 0.9), centre, 5e4 * (s / 100) ** 2, s * 0.5)
    configure_render(scene, args.out, args.samples, w, h)
    if args.outline:
        outlines(scene, max(1.0, w / 900))
    bpy.ops.render.render(write_still=True)


main()
