import bpy
import math
import os.path as op
import mmvt_utils as mu

bpy.types.Scene.output_path = bpy.props.StringProperty(
    name="Output Path", default="", description="Define the path for the output files", subtype='DIR_PATH')


def load_camera(self=None):
    camera_fname = op.join(bpy.path.abspath(bpy.context.scene.output_path), 'camera.pkl')
    if op.isfile(camera_fname):
        X_rotation, Y_rotation, Z_rotation, X_location, Y_location, Z_location = mu.load(camera_fname)
        RenderFigure.update_camera = False
        bpy.context.scene.X_rotation = X_rotation
        bpy.context.scene.Y_rotation = Y_rotation
        bpy.context.scene.Z_rotation = Z_rotation
        bpy.context.scene.X_location = X_location
        bpy.context.scene.Y_location = Y_location
        bpy.context.scene.Z_location = Z_location
        RenderFigure.update_camera = True
        update_camera()
    else:
        mu.message(self, 'No camera file was found in {}!'.format(camera_fname))


def grab_camera(self=None, do_save=True):
    RenderFigure.update_camera = False
    bpy.context.scene.X_rotation = X_rotation = math.degrees(bpy.data.objects['Camera'].rotation_euler.x)
    bpy.context.scene.Y_rotation = Y_rotation = math.degrees(bpy.data.objects['Camera'].rotation_euler.y)
    bpy.context.scene.Z_rotation = Z_rotation = math.degrees(bpy.data.objects['Camera'].rotation_euler.z)
    bpy.context.scene.X_location = X_location = bpy.data.objects['Camera'].location.x
    bpy.context.scene.Y_location = Y_location = bpy.data.objects['Camera'].location.y
    bpy.context.scene.Z_location = Z_location = bpy.data.objects['Camera'].location.z
    if do_save:
        if op.isdir(bpy.path.abspath(bpy.context.scene.output_path)):
            camera_fname = op.join(bpy.path.abspath(bpy.context.scene.output_path), 'camera.pkl')
            mu.save((X_rotation, Y_rotation, Z_rotation, X_location, Y_location, Z_location), camera_fname)
            print('Camera location was saved to {}'.format(camera_fname))
        else:
            mu.message(self, "Can't find the folder {}".format(bpy.path.abspath(bpy.context.scene.output_path)))
    RenderFigure.update_camera = True


def render_draw(self, context):
    layout = self.layout
    col = layout.column(align=True)
    col.prop(context.scene, "X_rotation", text='X rotation')
    col.prop(context.scene, "Y_rotation", text='Y rotation')
    col.prop(context.scene, "Z_rotation", text='Z rotation')
    col = layout.column(align=True)
    col.prop(context.scene, "X_location", text='X location')
    col.prop(context.scene, "Y_location", text='Y location')
    col.prop(context.scene, "Z_location", text='Z location')
    layout.prop(context.scene, "quality", text='Quality')
    layout.prop(context.scene, 'output_path')
    layout.prop(context.scene, 'smooth_figure')
    layout.operator(GrabCamera.bl_idname, text="Grab Camera", icon='BORDER_RECT')
    layout.operator(LoadCamera.bl_idname, text="Load Camera", icon='RENDER_REGION')
    layout.operator(MirrorCamera.bl_idname, text="Mirror Camera", icon='RENDER_REGION')
    layout.operator(RenderFigure.bl_idname, text="Render", icon='SCENE')


def update_camera(self=None, context=None):
    if RenderFigure.update_camera:
        bpy.data.objects['Camera'].rotation_euler.x = math.radians(bpy.context.scene.X_rotation)
        bpy.data.objects['Camera'].rotation_euler.y = math.radians(bpy.context.scene.Y_rotation)
        bpy.data.objects['Camera'].rotation_euler.z = math.radians(bpy.context.scene.Z_rotation)
        bpy.data.objects['Camera'].location.x = bpy.context.scene.X_location
        bpy.data.objects['Camera'].location.y = bpy.context.scene.Y_location
        bpy.data.objects['Camera'].location.z = bpy.context.scene.Z_location


def mirror():
    camera_rotation_z = bpy.context.scene.Z_rotation
    # target_rotation_z = math.degrees(bpy.data.objects['Camera'].rotation_euler.z)
    bpy.data.objects['Target'].rotation_euler.z += math.radians(180 - camera_rotation_z)
    print(bpy.data.objects['Target'].rotation_euler.z)


bpy.types.Scene.X_rotation = bpy.props.FloatProperty(
    default=0, min=-360, max=360, description="Camera rotation around x axis", update=update_camera)
bpy.types.Scene.Y_rotation = bpy.props.FloatProperty(
    default=0, min=-360, max=360, description="Camera rotation around y axis", update=update_camera)
bpy.types.Scene.Z_rotation = bpy.props.FloatProperty(
    default=0, min=-360, max=360, description="Camera rotation around z axis", update=update_camera)
bpy.types.Scene.X_location = bpy.props.FloatProperty(description="Camera x location", update=update_camera)
bpy.types.Scene.Y_location = bpy.props.FloatProperty(description="Camera y lovation", update=update_camera)
bpy.types.Scene.Z_location = bpy.props.FloatProperty(description="Camera z locationo", update=update_camera)
bpy.types.Scene.quality = bpy.props.FloatProperty(
    default=20, min=1, max=100,description="quality of figure in parentage")
bpy.types.Scene.smooth_figure = bpy.props.BoolProperty(
    name='smooth image', description="This significantly affect rendering speed")


class MirrorCamera(bpy.types.Operator):
    bl_idname = "ohad.mirror_camera"
    bl_label = "Mirror Camera"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        mirror()
        return {"FINISHED"}


class GrabCamera(bpy.types.Operator):
    bl_idname = "ohad.grab_camera"
    bl_label = "Grab Camera"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        grab_camera(self)
        return {"FINISHED"}


class LoadCamera(bpy.types.Operator):
    bl_idname = "ohad.load_camera"
    bl_label = "Load Camera"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        load_camera(self)
        return {"FINISHED"}


class RenderFigure(bpy.types.Operator):
    bl_idname = "ohad.rendering"
    bl_label = "Render figure"
    bl_options = {"UNDO"}
    update_camera = True

    def invoke(self, context, event=None):
        render_image()
        return {"FINISHED"}


def render_image():
    quality = bpy.context.scene.quality
    use_square_samples = bpy.context.scene.smooth_figure

    bpy.context.scene.render.resolution_percentage = quality
    # print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
    print('use_square_samples: {}'.format(use_square_samples))
    # print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
    bpy.context.scene.cycles.use_square_samples = use_square_samples

    cur_frame = bpy.context.scene.frame_current
    file_name = op.join(bpy.path.abspath(bpy.context.scene.output_path), 'f{}'.format(cur_frame))
    print('file name: {}'.format(file_name))
    bpy.context.scene.render.filepath = file_name
    # Render and save the rendered scene to file. ------------------------------
    print('Image quality:')
    print(bpy.context.scene.render.resolution_percentage)
    print("Rendering...")
    bpy.ops.render.render(write_still=True)
    print("Finished")


class RenderingMakerPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Render"
    addon = None

    def draw(self, context):
        render_draw(self, context)


def init(addon):
    RenderingMakerPanel.addon = addon
    bpy.data.objects['Target'].rotation_euler.z = 0
    grab_camera(None, False)
    register()


def register():
    try:
        unregister()
        bpy.utils.register_class(RenderingMakerPanel)
        bpy.utils.register_class(GrabCamera)
        bpy.utils.register_class(LoadCamera)
        bpy.utils.register_class(MirrorCamera)
        bpy.utils.register_class(RenderFigure)
        # print('Render Panel was registered!')
    except:
        print("Can't register Render Panel!")


def unregister():
    try:
        bpy.utils.unregister_class(RenderingMakerPanel)
        bpy.utils.unregister_class(GrabCamera)
        bpy.utils.unregister_class(LoadCamera)
        bpy.utils.unregister_class(MirrorCamera)
        bpy.utils.unregister_class(RenderFigure)
    except:
        pass
        # print("Can't unregister Render Panel!")
