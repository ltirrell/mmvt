bl_info = {
    "name": "Multi-modal visualization tool",
    "author": "Ohad Felsenstein & Noam Peled",
    "version": (1, 2),
    "blender": (2, 7, 2),
    "api": 33333,
    "location": "View3D > Add > Mesh > Say3D",
    "description": "Multi-modal visualization tool",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Add Mesh"}


import bpy
import mathutils
import numpy as np
import os
import sys
import time
import glob
import math
import importlib
import numbers
import traceback

import mmvt_utils
importlib.reload(mmvt_utils)

import connections_panel
importlib.reload(connections_panel)
import play_panel
importlib.reload(play_panel)


print("Neuroscience add on started!")
# todo: should change that in the code!!!
T = 2500

# LAYERS
(CONNECTIONS_LAYER, ELECTRODES_LAYER, ROIS_LAYER, ACTIVITY_LAYER, LIGHTS_LAYER,
    BRAIN_EMPTY_LAYER, EMPTY_LAYER) = 3, 1, 10, 11, 12, 5, 14
STAT_AVG, STAT_DIFF = range(2)
HEMIS = ['rh', 'lh']
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ data Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
bpy.types.Scene.conf_path = bpy.props.StringProperty(name="Root Path", default="",
                                                     description="Define the root path of the project",
                                                     subtype='DIR_PATH')

# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv Import Brain - START vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
bpy.types.Scene.brain_imported = False


def import_brain(base_path):
    brain_layer = BRAIN_EMPTY_LAYER
    bpy.context.scene.layers = [ind == brain_layer for ind in range(len(bpy.context.scene.layers))]
    layers_array = bpy.context.scene.layers
    emptys_names = ['Functional maps', 'Subcortical_meg_activity_map', 'Subcortical_fmri_activity_map']
    for name in emptys_names:
        create_empty_if_doesnt_exists(name, brain_layer, layers_array, 'Functional maps')

    brain_layer = ACTIVITY_LAYER
    bpy.context.scene.layers = [ind == brain_layer for ind in range(len(bpy.context.scene.layers))]
    # for ii in range(len(bpy.context.scene.layers)):
    #     bpy.context.scene.layers[ii] = (ii == brain_layer)

    print("importing Hemispheres")
    # # for cur_val in bpy.context.scene.layers:
    # #     print(cur_val)
    # print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    for ply_fname in glob.glob(os.path.join(base_path, '*.ply')):
        bpy.ops.object.select_all(action='DESELECT')
        print(ply_fname)
        bpy.ops.import_mesh.ply(filepath=os.path.join(base_path, ply_fname))
        cur_obj = bpy.context.selected_objects[0]
        cur_obj.select = True
        bpy.ops.object.shade_smooth()
        cur_obj.scale = [0.1] * 3
        cur_obj.hide = False
        cur_obj.name = cur_obj.name.split(sep='.')[0]
        cur_obj.active_material = bpy.data.materials['Activity_map_mat']
        cur_obj.parent = bpy.data.objects["Functional maps"]
        cur_obj.hide_select = True
        cur_obj.data.vertex_colors.new()
        print('did hide_select')

    bpy.ops.object.select_all(action='DESELECT')


def create_subcortical_activity_mat(name):
    cur_mat = bpy.data.materials['subcortical_activity_mat'].copy()
    cur_mat.name = name + '_Mat'


def import_subcorticals(base_path):
    empty_layer = BRAIN_EMPTY_LAYER
    brain_layer = ACTIVITY_LAYER

    bpy.context.scene.layers = [ind == empty_layer for ind in range(len(bpy.context.scene.layers))]
    layers_array = bpy.context.scene.layers
    emptys_names = ['Functional maps', 'Subcortical_meg_activity_map', 'Subcortical_fmri_activity_map']
    for name in emptys_names:
        create_empty_if_doesnt_exists(name, empty_layer, layers_array, 'Functional maps')
    bpy.context.scene.layers = [ind == brain_layer for ind in range(len(bpy.context.scene.layers))]

    print("importing Subcortical structures")
    # for cur_val in bpy.context.scene.layers:
    #     print(cur_val)
    #  print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    base_paths = [base_path] * 2 # Read the bast_path twice, for meg and fmri
    PATH_TYPE_SUB_MEG, PATH_TYPE_SUB_FMRI = range(2)
    for path_type, base_path in enumerate(base_paths):
        for ply_fname in glob.glob(os.path.join(base_path, '*.ply')):
            name = mmvt_utils.namebase(ply_fname)
            bpy.ops.object.select_all(action='DESELECT')
            print(ply_fname)
            bpy.ops.import_mesh.ply(filepath=os.path.join(base_path, ply_fname))
            cur_obj = bpy.context.selected_objects[0]
            cur_obj.select = True
            bpy.ops.object.shade_smooth()
            cur_obj.scale = [0.1] * 3
            cur_obj.hide = False
            cur_obj.name = mmvt_utils.namebase(ply_fname)

            if path_type == PATH_TYPE_SUB_MEG:
                cur_obj.name = '{}_meg_activity'.format(name)
                curMat = bpy.data.materials.get('{}_mat'.format(cur_obj.name))
                if curMat is None:
                    # todo: Fix the succortical_activity_Mat to succortical_activity_mat
                    curMat = bpy.data.materials['succortical_activity_Mat'].copy()
                    curMat.name = '{}_mat'.format(cur_obj.name)
                cur_obj.active_material = bpy.data.materials[curMat.name]
                cur_obj.parent = bpy.data.objects['Subcortical_meg_activity_map']
            elif path_type == PATH_TYPE_SUB_FMRI:
                cur_obj.name = '{}_fmri_activity'.format(name)
                if 'cerebellum' in cur_obj.name.lower():
                    cur_obj.active_material = bpy.data.materials['Activity_map_mat']
                else:
                    cur_obj.active_material = bpy.data.materials['subcortical_activity_mat']
                cur_obj.parent = bpy.data.objects['Subcortical_fmri_activity_map']
            else:
                print('import_subcorticals: Wrong path_type! Nothing to do...')
            cur_obj.hide_select = True
    bpy.ops.object.select_all(action='DESELECT')


class ImportBrain(bpy.types.Operator):
    bl_idname = "ohad.brain_importing"
    bl_label = "import2 brain"
    bl_options = {"UNDO"}
    current_root_path = ''
    brain_layer = BRAIN_EMPTY_LAYER

    def invoke(self, context, event=None):
        self.current_root_path = mmvt_utils.get_user_fol() #bpy.path.abspath(bpy.context.scene.conf_path)
        print("importing ROIs")
        # import_rois(self.current_root_path)
        # import_brain(self.current_root_path)
        import_subcorticals(os.path.join(self.current_root_path, 'subcortical'))
        last_obj = context.active_object.name
        print('last obj is -' + last_obj)

        if bpy.data.objects.get(' '):
            bpy.data.objects[' '].select = True
            context.scene.objects.active = bpy.data.objects[' ']
        bpy.data.objects[last_obj].select = False
        set_appearance_show_rois_layer(bpy.context.scene, True)
        bpy.types.Scene.brain_imported = True
        print('cleaning up')
        for obj in bpy.data.objects['Subcortical_structures'].children:
            # print(obj.name)
            if obj.name[-1] == '1':
                obj.name = obj.name[0:-4]
        print('Brain importing is Finished ')

        return {"FINISHED"}


def create_empty_if_doesnt_exists(name, brain_layer, layers_array, parent_obj_name='Brain'):
    if bpy.data.objects.get(name) is None:
        layers_array[brain_layer] = True
        bpy.ops.object.empty_add(type='PLAIN_AXES', radius=1, view_align=False, location=(0, 0, 0), layers=layers_array)
        bpy.data.objects['Empty'].name = name
        if name != parent_obj_name:
            bpy.data.objects[name].parent = bpy.data.objects[parent_obj_name]


def import_rois(base_path):
    #todo: add an atlas's label
    atlas = 'laus250'
    anatomy_inputs = {'Cortex-rh': os.path.join(base_path, '{}.pial.rh'.format(atlas)),
                      'Cortex-lh': os.path.join(base_path, '{}.pial.lh'.format(atlas)),
                      'Subcortical_structures': os.path.join(base_path, 'subcortical')}
    brain_layer = BRAIN_EMPTY_LAYER

    bpy.context.scene.layers = [ind == brain_layer for ind in range(len(bpy.context.scene.layers))]
    layers_array = bpy.context.scene.layers
    emptys_names = ["Brain", "Subcortical_structures", "Cortex-lh", "Cortex-rh"]
    for name in emptys_names:
        create_empty_if_doesnt_exists(name, brain_layer, layers_array)
    bpy.context.scene.layers = [ind == ROIS_LAYER for ind in range(len(bpy.context.scene.layers))]

    for anatomy_name, base_path in anatomy_inputs.items():
        current_mat = bpy.data.materials['unselected_label_Mat_cortex']
        if anatomy_name == 'Subcortical_structures':
            current_mat = bpy.data.materials['unselected_label_Mat_subcortical']
        for ply_fname in glob.glob(os.path.join(base_path, '*.ply')):
            bpy.ops.object.select_all(action='DESELECT')
            print(ply_fname)
            bpy.ops.import_mesh.ply(filepath=os.path.join(base_path, ply_fname))
            cur_obj = bpy.context.selected_objects[0]
            cur_obj.select = True
            bpy.ops.object.shade_smooth()
            cur_obj.parent = bpy.data.objects[anatomy_name]
            cur_obj.scale = [0.1] * 3
            cur_obj.active_material = current_mat
            cur_obj.hide = False
            cur_obj.name = mmvt_utils.namebase(ply_fname)
            # time.sleep(0.3)
    bpy.ops.object.select_all(action='DESELECT')


class ImportRoisClass(bpy.types.Operator):
    bl_idname = "ohad.roi_importing"
    bl_label = "import2 ROIs"
    bl_options = {"UNDO"}
    current_root_path = ''

    def invoke(self, context, event=None):
        self.current_root_path = bpy.path.abspath(bpy.context.scene.conf_path)
        import_brain(self.current_root_path)
        return {"FINISHED"}


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Import Brain - END^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv Import Electrodes - START vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
bpy.types.Scene.electrodes_imported = False


def create_sphere(loc, rad, my_layers, name):
    bpy.ops.mesh.primitive_uv_sphere_add(ring_count=30, size=rad, view_align=False, enter_editmode=False, location=loc,
                                         layers=my_layers)
    bpy.ops.object.shade_smooth()

    # Rename the object
    bpy.context.active_object.name = name


def create_and_set_material(obj):
    # curMat = bpy.data.materials['OrigPatchesMat'].copy()
    if obj.active_material.name != obj.name + '_Mat':
        if obj.name + '_Mat' in bpy.data.materials:
            cur_mat = bpy.data.materials[obj.name + '_Mat']
        else:
            cur_mat = bpy.data.materials['Deep_electrode_mat'].copy()
            cur_mat.name = obj.name + '_Mat'
        # Wasn't it originally (0, 0, 1, 1)?
        cur_mat.node_tree.nodes["RGB"].outputs[0].default_value = (0, 0, 1, 1) # (0, 1, 0, 1)
        obj.active_material = cur_mat


def import_electrodes(base_path):
    # input_file = os.path.join(base_path, "electrodes.npz")
    # todo: add a bipolar label gui
    bipolar = False
    input_file = os.path.join(base_path, 'electrodes_{}positions.npz'.format('bipolar_' if bipolar else ''))

    print('Adding deep electrodes')
    f = np.load(input_file)
    print('loaded')

    deep_electrodes_layer = 1
    electrode_size = 0.25

    layers_array = [False] * 20

    if bpy.data.objects.get("Deep_electrodes") is None:
        layers_array[BRAIN_EMPTY_LAYER] = True
        bpy.ops.object.empty_add(type='PLAIN_AXES', radius=1, view_align=False, location=(0, 0, 0), layers=layers_array)
        bpy.data.objects['Empty'].name = 'Deep_electrodes'

    layers_array = [False] * 20
    layers_array[deep_electrodes_layer] = True

    for (x, y, z), name in zip(f['pos'], f['names']):
        print('creating ' + str(name)[2:-1])
        # instead of the ugly str(name)[2:-1]...
        elc_name = name.astype(str)
        create_sphere((x * 0.1, y * 0.1, z * 0.1), electrode_size, layers_array, elc_name)
        cur_obj = bpy.data.objects[elc_name]
        cur_obj.select = True
        cur_obj.parent = bpy.data.objects['Deep_electrodes']
        # cur_obj.active_material = bpy.data.materials['Deep_electrode_mat']
        create_and_set_material(cur_obj)


class ImportElectrodes(bpy.types.Operator):
    bl_idname = "ohad.electrodes_importing"
    bl_label = "import2 electrodes"
    bl_options = {"UNDO"}
    current_root_path = ''

    def invoke(self, context, event=None):
        self.current_root_path = bpy.path.abspath(bpy.context.scene.conf_path)
        import_electrodes(self.current_root_path)
        bpy.types.Scene.electrodes_imported = True
        print('Electrodes importing is Finished ')
        return {"FINISHED"}


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Import Electrodes - END^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv Add data to brain - START vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
bpy.types.Scene.brain_data_exist = False


def insert_keyframe_to_custom_prop(obj, prop_name, value, keyframe):
    bpy.context.scene.objects.active = obj
    obj.select = True
    obj[prop_name] = value
    obj.keyframe_insert(data_path='[' + '"' + prop_name + '"' + ']', frame=keyframe)


def add_data_to_brain():
    base_path = mmvt_utils.get_user_fol()
    source_files = [os.path.join(base_path, 'labels_data_lh.npz'), os.path.join(base_path, 'labels_data_rh.npz'),
                    os.path.join(base_path, 'sub_cortical_activity.npz')]
    print('Adding data to Brain')
    number_of_maximal_time_steps = -1
    obj_counter = 0
    for input_file in source_files:
        if not os.path.isfile(input_file):
            mmvt_utils.message(None, '{} does not exist!'.format(input_file))
            continue
        f = np.load(input_file)
        print('{} loaded'.format(input_file))
        number_of_maximal_time_steps = max(number_of_maximal_time_steps, len(f['data'][0]))
        for obj_name, data in zip(f['names'], f['data']):
            # print('in label loop')
            obj_name = obj_name.astype(str)
            print(obj_name)
            cur_obj = bpy.data.objects[obj_name]
            # print('cur_obj name = '+cur_obj.name)

            for cond_ind, cond_str in enumerate(f['conditions']):
                # cond_str = str(cond_str)
                # if cond_str[1] == "'":
                #     cond_str = cond_str[2:-1]
                cond_str = cond_str.astype(str)
                # Set the values to zeros in the first and last frame for current object(current label)
                insert_keyframe_to_custom_prop(cur_obj, obj_name + '_' + cond_str, 0, 1)
                insert_keyframe_to_custom_prop(cur_obj, obj_name + '_' + cond_str, 0, len(f['data'][0]) + 2)

                print('keyframing ' + obj_name + ' object')
                # For every time point insert keyframe to current object
                for ind, timepoint in enumerate(data[:, cond_ind]):
                    # print('keyframing '+obj_name+' object')
                    insert_keyframe_to_custom_prop(cur_obj, obj_name + '_' + cond_str, timepoint, ind + 2)

                # remove the orange keyframe sign in the fcurves window
                fcurves = bpy.data.objects[obj_name].animation_data.action.fcurves[cond_ind]
                mod = fcurves.modifiers.new(type='LIMITS')
    try:
        bpy.ops.graph.previewrange_set()
    except:
        pass

    bpy.types.Scene.maximal_time_steps = number_of_maximal_time_steps
    print(bpy.types.Scene.maximal_time_steps)

    # for obj in bpy.data.objects:
    #     try:
    #         if (obj.parent is 'Cortex-lh') or ((obj.parent is 'Cortex-rh') or (obj.parent is 'Subcortical_structures')):
    #             obj.select = True
    #         else:
    #             obj.select = False
    #     except:
    #         obj.select = False
    for obj in bpy.data.objects:
        obj.select = False
    if bpy.data.objects.get(' '):
        bpy.context.scene.objects.active = bpy.data.objects[' ']
    print('Finished keyframing!!')


def add_data_to_parent_brain_obj(self, stat=STAT_DIFF):
    base_path = mmvt_utils.get_user_fol()
    brain_obj = bpy.data.objects['Brain']
    labels_data_file = 'labels_data_{hemi}.npz' if stat else 'labels_data_no_conds_{hemi}.npz'
    brain_sources = [os.path.join(base_path, labels_data_file.format(hemi=hemi)) for hemi in HEMIS]
    subcorticals_obj = bpy.data.objects['Subcortical_structures']
    subcorticals_sources = [os.path.join(base_path, 'subcortical_meg_activity.npz')]
    add_data_to_parent_obj(self, brain_obj, brain_sources, stat)
    add_data_to_parent_obj(self, subcorticals_obj, subcorticals_sources, stat)


def add_data_to_parent_obj(self, parent_obj, source_files, stat):
    sources = {}
    parent_obj.animation_data_clear()
    for input_file in source_files:
        if not os.path.isfile(input_file):
            mmvt_utils.message(self, "Can't load file {}!".format(input_file))
            continue
        print('loading {}'.format(input_file))
        f = np.load(input_file)
        for obj_name, data in zip(f['names'], f['data']):
            obj_name = obj_name.astype(str)
            if bpy.data.objects.get(obj_name) is None:
                continue
            if stat == STAT_AVG:
                data_stat = np.squeeze(np.mean(data, axis=1))
            elif stat == STAT_DIFF:
                data_stat = np.squeeze(np.diff(data, axis=1))
            else:
                data_stat = data
            sources[obj_name] = data_stat
    if len(sources) == 0:
        print('No sources in {}'.format(source_files))
    sources_names = sorted(list(sources.keys()))
    N = len(sources_names)
    T = len(sources[sources_names[0]]) + 2
    now = time.time()
    for obj_counter, source_name in enumerate(sources_names):
        mmvt_utils.time_to_go(now, obj_counter, N, runs_num_to_print=10)
        data = sources[source_name]
        # Set the values to zeros in the first and last frame for Brain object
        insert_keyframe_to_custom_prop(parent_obj, source_name, 0, 1)
        insert_keyframe_to_custom_prop(parent_obj, source_name, 0, T)

        # For every time point insert keyframe to the main Brain object
        # If you want to delete prints make sure no sleep is needed
        # print('keyframing Brain object {}'.format(obj_name))
        for ind in range(data.shape[0]):
            # if len(data[ind]) == 2:
            # print('keyframing Brain object')
            insert_keyframe_to_custom_prop(parent_obj, source_name, data[ind], ind + 2)
            # print('keyframed')

        # remove the orange keyframe sign in the fcurves window
        fcurves = parent_obj.animation_data.action.fcurves[obj_counter]
        mod = fcurves.modifiers.new(type='LIMITS')

    if bpy.data.objects.get(' '):
        bpy.context.scene.objects.active = bpy.data.objects[' ']
    print('Finished keyframing the brain parent obj!!')


class AddDataToBrain(bpy.types.Operator):
    bl_idname = "ohad.brain_add_data"
    bl_label = "add_data2 brain"
    bl_options = {"UNDO"}
    current_root_path = ''

    def invoke(self, context, event=None):
        # self.current_root_path = bpy.path.abspath(bpy.context.scene.conf_path)
        add_data_to_brain()
        add_data_to_parent_brain_obj(self)
        bpy.types.Scene.brain_data_exist = True
        return {"FINISHED"}


class AddDataNoCondsToBrain(bpy.types.Operator):
    bl_idname = "ohad.brain_add_data_no_conds"
    bl_label = "add_data no conds brain"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        add_data_to_parent_brain_obj(self, None)
        bpy.types.Scene.brain_data_exist = True
        return {"FINISHED"}


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Add data to brain - END^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv Add data to Electrodes - START vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
bpy.types.Scene.electrodes_data_exist = False


def insert_keyframe_to_custom_prop(obj, prop_name, value, keyframe):
    bpy.context.scene.objects.active = obj
    obj.select = True
    obj[prop_name] = value
    obj.keyframe_insert(data_path='[' + '"' + prop_name + '"' + ']', frame=keyframe)


def add_data_to_electrodes(self, source_files):
    print('Adding data to Electrodes')
    for input_file in source_files:
        # todo: we don't need to load this twice (also in add_data_to_electrodes_obj
        f = np.load(input_file)
        print('{} loaded'.format(input_file))
        now = time.time()
        N = len(f['names'])
        for obj_counter, (obj_name, data) in enumerate(zip(f['names'], f['data'])):
            mmvt_utils.time_to_go(now, obj_counter, N, runs_num_to_print=10)
            obj_name = obj_name.astype(str)
            # print(obj_name)
            cur_obj = bpy.data.objects[obj_name]
            for cond_ind, cond_str in enumerate(f['conditions']):
                cond_str = cond_str.astype(str)
                # Set the values to zeros in the first and last frame for current object(current label)
                insert_keyframe_to_custom_prop(cur_obj, obj_name + '_' + cond_str, 0, 1)
                insert_keyframe_to_custom_prop(cur_obj, obj_name + '_' + cond_str, 0, len(f['data'][0]) + 2)

                print('keyframing ' + obj_name + ' object in condition ' + cond_str)
                # For every time point insert keyframe to current object
                for ind, timepoint in enumerate(data[:, cond_ind]):
                    insert_keyframe_to_custom_prop(cur_obj, obj_name + '_' + str(cond_str), timepoint, ind + 2)
                # remove the orange keyframe sign in the fcurves window
                fcurves = bpy.data.objects[obj_name].animation_data.action.fcurves[cond_ind]
                mod = fcurves.modifiers.new(type='LIMITS')
    print('Finished keyframing!!')


def add_data_to_electrodes_parent_obj(self, parent_obj, source_files, stat):
    # todo: merge with add_data_to_brain_parent_obj, same code
    parent_obj.animation_data_clear()
    sources = {}
    for input_file in source_files:
        if not os.path.isfile(input_file):
            self.report({'ERROR'}, "Can't load file {}!".format(input_file))
            continue
        print('loading {}'.format(input_file))
        f = np.load(input_file)
        # for obj_name, data in zip(f['names'], f['data']):
        for obj_name, data_stat in zip(f['names'], f['stat']):
            obj_name = obj_name.astype(str)
            # if stat == STAT_AVG:
            #     data_stat = np.squeeze(np.mean(data, axis=1))
            # elif stat == STAT_DIFF:
            #     data_stat = np.squeeze(np.diff(data, axis=1))
            sources[obj_name] = data_stat

    sources_names = sorted(list(sources.keys()))
    N = len(sources_names)
    T = get_max_time_steps() # len(sources[sources_names[0]]) + 2
    now = time.time()
    for obj_counter, source_name in enumerate(sources_names):
        mmvt_utils.time_to_go(now, obj_counter, N, runs_num_to_print=10)
        data = sources[source_name]
        insert_keyframe_to_custom_prop(parent_obj, source_name, 0, 1)
        insert_keyframe_to_custom_prop(parent_obj, source_name, 0, T + 2)

        for ind in range(data.shape[0]):
            insert_keyframe_to_custom_prop(parent_obj, source_name, data[ind], ind + 2)

        fcurves = parent_obj.animation_data.action.fcurves[obj_counter]
        mod = fcurves.modifiers.new(type='LIMITS')

    print('Finished keyframing {}!!'.format(parent_obj.name))


class AddDataToElectrodes(bpy.types.Operator):
    bl_idname = "ohad.electrodes_add_data"
    bl_label = "add_data2 electrodes"
    bl_options = {"UNDO"}
    current_root_path = ''

    def invoke(self, context, event=None):
        # self.current_root_path = bpy.path.abspath(bpy.context.scene.conf_path)
        parent_obj = bpy.data.objects['Deep_electrodes']
        base_path = mmvt_utils.get_user_fol()
        source_files = [os.path.join(base_path, 'electrodes_data_{}.npz'.format(
            'avg' if bpy.context.scene.selection_type == 'conds' else 'diff'))]

        # add_data_to_electrodes(self, source_files)
        add_data_to_electrodes_parent_obj(self, parent_obj, source_files, STAT_DIFF)
        bpy.types.Scene.electrodes_data_exist = True
        if bpy.data.objects.get(' '):
            bpy.context.scene.objects.active = bpy.data.objects[' ']

        return {"FINISHED"}


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Add data to Electrodes - END^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


class DataMakerPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Data Panel"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, 'conf_path')
        col1 = self.layout.column(align=True)
        col2 = self.layout.column(align=True)
        if not bpy.types.Scene.brain_imported:
            col1.operator("ohad.brain_importing", text="Import Brain", icon='MATERIAL_DATA')
        if not bpy.types.Scene.electrodes_imported:
            col1.operator("ohad.electrodes_importing", text="Import Electrodes", icon='COLOR_GREEN')

        # if bpy.types.Scene.brain_imported and (not bpy.types.Scene.brain_data_exist):
        col2.operator(AddDataToBrain.bl_idname, text="Add data to Brain", icon='FCURVE')
        col2.operator(AddDataNoCondsToBrain.bl_idname, text="Add no conds data to Brain", icon='FCURVE')
        # if bpy.types.Scene.electrodes_imported and (not bpy.types.Scene.electrodes_data_exist):
        col2.operator("ohad.electrodes_add_data", text="Add data to Electrodes", icon='FCURVE')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ data Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Selection Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# select all ROIs
# Select all Electrodes
# select brain
# select Deep_electrodes
# clear selections

bpy.types.Scene.selection_type = bpy.props.EnumProperty(
    items=[("diff", "Conditions difference", "", 1), ("conds", "Both conditions", "", 2)],
    description="Selection type")


def deselect_all():
    for obj in bpy.data.objects:
        obj.select = False
    if bpy.data.objects.get(' '):
        bpy.data.objects[' '].select = True
        bpy.context.scene.objects.active = bpy.data.objects[' ']


def select_all_rois():
    select_brain_objects('Brain', bpy.data.objects['Cortex-lh'].children + bpy.data.objects['Cortex-rh'].children)


def select_only_subcorticals():
    select_brain_objects('Subcortical_structures', bpy.data.objects['Subcortical_structures'].children)


def select_all_electrodes():
    select_brain_objects('Deep_electrodes', bpy.data.objects['Deep_electrodes'].children)


def select_all_connections():
    select_brain_objects('connections', bpy.data.objects['connections'].children)


def select_brain_objects(parent_obj_name, children):
    parent_obj = bpy.data.objects[parent_obj_name]
    if parent_obj.animation_data and bpy.context.scene.selection_type == 'diff':
        mmvt_utils.show_hide_obj_and_fcurves(children, False)
        parent_obj.select = True
        for fcurve in parent_obj.animation_data.action.fcurves:
            fcurve.hide = False
            fcurve.select = True
    else:
        mmvt_utils.show_hide_obj_and_fcurves(children, True)
        parent_obj.select = False


class SelectionMakerPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Selection Panel"

    @staticmethod
    def draw(self, context):
        layout = self.layout
        # col = self.layout.column(align=True)
        # col1.operator("select.ROIs", text="ROIs")
        layout.prop(context.scene, "selection_type", text="")
        layout.operator("ohad.roi_selection", text="Select all cortical ROIs", icon='BORDER_RECT')
        layout.operator("ohad.subcorticals_selection", text="Select all subcorticals", icon = 'BORDER_RECT' )
        layout.operator("ohad.electrodes_selection", text="Select all Electrodes", icon='BORDER_RECT')
        layout.operator("ohad.connections_selection", text="Select all Connections", icon='BORDER_RECT')
        layout.operator("ohad.clear_selection", text="Deselect all", icon='PANEL_CLOSE')
        layout.operator("ohad.fit_selection", text="Fit graph window", icon='MOD_ARMATURE')


class SelectAllRois(bpy.types.Operator):
    bl_idname = "ohad.roi_selection"
    bl_label = "select2 ROIs"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        select_all_rois()
        mmvt_utils.view_all_in_graph_editor(context)
        return {"FINISHED"}


class SelectAllSubcorticals(bpy.types.Operator):
    bl_idname = "ohad.subcorticals_selection"
    bl_label = "select only subcorticals"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        select_only_subcorticals()
        mmvt_utils.view_all_in_graph_editor(context)
        return {"FINISHED"}


class SelectAllElectrodes(bpy.types.Operator):
    bl_idname = "ohad.electrodes_selection"
    bl_label = "select2 Electrodes"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        select_all_electrodes()
        mmvt_utils.view_all_in_graph_editor(context)
        return {"FINISHED"}


class SelectAllConnections(bpy.types.Operator):
    bl_idname = "ohad.connections_selection"
    bl_label = "select connections"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        select_all_connections()
        mmvt_utils.view_all_in_graph_editor(context)
        return {"FINISHED"}


class ClearSelection(bpy.types.Operator):
    bl_idname = "ohad.clear_selection"
    bl_label = "deselect all"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        for obj in bpy.data.objects:
            obj.select = False
        if bpy.data.objects.get(' '):
            bpy.data.objects[' '].select = True
            bpy.context.scene.objects.active = bpy.data.objects[' ']

        return {"FINISHED"}


class FitSelection(bpy.types.Operator):
    bl_idname = "ohad.fit_selection"
    bl_label = "Fit selection"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        mmvt_utils.view_all_in_graph_editor(context)
        return {"FINISHED"}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Selection Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Filter Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
bpy.types.Scene.closest_curve_str = ''
bpy.types.Scene.filter_is_on = False


def find_obj_with_val():
    cur_objects = []
    for obj in bpy.data.objects:
        if obj.select is True:
            cur_objects.append(obj)

    for ii in range(len(bpy.data.screens['Neuro'].areas)):
        if bpy.data.screens['Neuro'].areas[ii].type == 'GRAPH_EDITOR':
            for jj in range(len(bpy.data.screens['Neuro'].areas[ii].spaces)):
                if bpy.data.screens['Neuro'].areas[ii].spaces[jj].type == 'GRAPH_EDITOR':
                    # print(dir(bpy.data.screens['Neuro'].areas[ii].spaces[jj]))
                    target = bpy.data.screens['Neuro'].areas[ii].spaces[jj].cursor_position_y

    values, names, obj_names = [], [], []
    for cur_obj in cur_objects:
        # if cur_obj.animation_data is None:
        #     continue
        # for fcurve in cur_obj.animation_data.action.fcurves:
        #     val = fcurve.evaluate(bpy.context.scene.frame_current)
        #     name = mmvt_utils.fcurve_name(fcurve)
        for name, val in cur_obj.items():
            if isinstance(val, numbers.Number):
                values.append(val)
                names.append(name)
                obj_names.append(cur_obj.name)
            # print(name)
    np_values = np.array(values) - target
    try:
        index = np.argmin(np.abs(np_values))
        closest_curve_name = names[index]
        closet_object_name = obj_names[index]
    except ValueError:
        closest_curve_name = ''
        closet_object_name = ''
        print('ERROR - Make sure you select all objects in interest')
    # print(closest_curve_name, closet_object_name)
    bpy.types.Scene.closest_curve_str = closest_curve_name
    # object_name = closest_curve_str
    # if bpy.data.objects.get(object_name) is None:
    #     object_name = object_name[:object_name.rfind('_')]
    print('object name: {}, curve name: {}'.format(closet_object_name, closest_curve_name))
    parent_obj = bpy.data.objects[closet_object_name].parent
    # print('parent: {}'.format(bpy.data.objects[object_name].parent))
    # try:
    if parent_obj.name == 'Deep_electrodes':
        print('filtering electrodes')
        filter_electrode_func(closet_object_name, closest_curve_name)
    elif parent_obj.name == connections_panel.PARENT_OBJ:
        connections_panel.find_connections_closest_to_target_value(closet_object_name, closest_curve_name, target)
    else:
        filter_roi_func(closet_object_name, closest_curve_name)
    # except KeyError:
    #     filter_roi_func(object_name)


class FindCurveClosestToCursor(bpy.types.Operator):
    bl_idname = "ohad.curve_close_to_cursor"
    bl_label = "curve close to cursor"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        find_obj_with_val()
        return {"FINISHED"}


def filter_draw(self, context):
    layout = self.layout
    layout.prop(context.scene, "filter_topK", text="Top K")
    row = layout.row(align=0)
    row.prop(context.scene, "filter_from", text="From")
    # row.label(str(GrabFromFiltering.value))
    row.operator(GrabFromFiltering.bl_idname, text="", icon='BORDERMOVE')
    # row.operator("ohad.grab_from", text="", icon = 'BORDERMOVE')
    row.prop(context.scene, "filter_to", text="To")
    row.operator(GrabToFiltering.bl_idname, text="", icon='BORDERMOVE')
    layout.prop(context.scene, "filter_curves_type", text="")
    layout.prop(context.scene, "filter_curves_func", text="")
    layout.operator("ohad.filter", text="Filter " + bpy.context.scene.filter_curves_type, icon='BORDERMOVE')
    if bpy.types.Scene.filter_is_on:
        layout.operator("ohad.filter_clear", text="Clear Filtering", icon='PANEL_CLOSE')
    col = layout.column(align=0)
    col.operator("ohad.curve_close_to_cursor", text="closest curve to cursor", icon='SNAP_SURFACE')
    col.label(text=bpy.types.Scene.closest_curve_str)

    # bpy.context.area.type = 'GRAPH_EDITOR'
    # filter_to = bpy.context.scence.frame_preview_end


files_names = {'MEG': 'labels_data_{hemi}.npz', 'Electrodes': 'electrodes_data_{stat}.npz'}

bpy.types.Scene.closest_curve = bpy.props.StringProperty(description="Find closest curve to cursor", update=filter_draw)
#bpy.types.Scene.filter_topK = bpy.props.IntProperty(default=1, min=0, description="The top K elements to be shown")
bpy.types.Scene.filter_topK = bpy.props.IntProperty(default=1, min=0, description="The top K elements to be shown")
bpy.types.Scene.filter_from = bpy.props.IntProperty(default=0, min=0, description="When to filter from")
# bpy.types.Scene.filter_to = bpy.props.IntProperty(default=bpy.data.scenes['Scene'].frame_preview_end, min=0, description="When to filter to")
bpy.types.Scene.filter_to = bpy.props.IntProperty(default=bpy.context.scene.frame_end, min=0,
                                                  description="When to filter to")
bpy.types.Scene.filter_curves_type = bpy.props.EnumProperty(
    items=[("MEG", "MEG time course", "", 1), ("Electrodes", " Electrodes time course", "", 2)],
    description="Type of curve to be filtered", update=filter_draw)
bpy.types.Scene.filter_curves_func = bpy.props.EnumProperty(
    items=[("RMS", "RMS", "RMS between the two conditions", 1), ("SumAbs", "SumAbs", "Sum of the abs values", 2),
           ("threshold", "Above threshold", "", 3)],
    description="Filtering function", update=filter_draw)


class FilteringMakerPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Filter number of curves"

    def draw(self, context):
        filter_draw(self, context)


class GrabFromFiltering(bpy.types.Operator):
    bl_idname = "ohad.grab_from"
    bl_label = "grab from"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        # print(bpy.context.scene.frame_current)
        context.scene.filter_from = bpy.context.scene.frame_current
        # print(bpy.context.scene.filter_from)
        bpy.data.scenes['Scene'].frame_preview_start = context.scene.frame_current
        return {"FINISHED"}


class GrabToFiltering(bpy.types.Operator):
    bl_idname = "ohad.grab_to"
    bl_label = "grab to"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        # print(bpy.context.scene.frame_current)
        context.scene.filter_to = bpy.context.scene.frame_current
        # print(bpy.context.scene.filter_to)
        bpy.data.scenes['Scene'].frame_preview_end = context.scene.frame_current
        return {"FINISHED"}


class ClearFiltering(bpy.types.Operator):
    bl_idname = "ohad.filter_clear"
    bl_label = "filter clear"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        for subhierarchy in bpy.data.objects['Brain'].children:
            new_mat = bpy.data.materials['unselected_label_Mat_cortex']
            if subhierarchy.name == 'Subcortical_structures':
                new_mat = bpy.data.materials['unselected_label_Mat_subcortical']
            for obj in subhierarchy.children:
                obj.active_material = new_mat

        if bpy.data.objects.get('Deep_electrodes'):
            for obj in bpy.data.objects['Deep_electrodes'].children:
                obj.active_material.node_tree.nodes["Layer Weight"].inputs[0].default_value = 1
                # safety check, if something happened to the electrode's material
                create_and_set_material(obj)
                # Sholdn't change to color here. If user plot the electrodes, we don't want to change it back to white.
                # obj.active_material.node_tree.nodes["RGB"].outputs[0].default_value = (1, 1, 1, 1)

        type_of_filter = bpy.context.scene.filter_curves_type
        if type_of_filter == 'MEG':
            select_all_rois()
        elif type_of_filter == 'Electrodes':
            select_all_electrodes()
        bpy.data.scenes['Scene'].frame_preview_end = get_max_time_steps()
        bpy.data.scenes['Scene'].frame_preview_start = 1
        bpy.types.Scene.closest_curve_str = ''
        bpy.types.Scene.filter_is_on = False
        return {"FINISHED"}


def get_max_time_steps():
    # Check if maximal_time_steps is in bpy.types.Scene
    try:
        return bpy.types.Scene.maximal_time_steps
    except:
        print('No preperty maximal_time_steps in bpy.types.Scene')

    # Check if there is animation data in MEG
    try:
        hemi = bpy.data.objects['Cortex-lh']
        # Takes the first child first condition fcurve
        fcurves = hemi.children[0].animation_data.action.fcurves[0]
        return len(fcurves.keyframe_points) - 3
    except:
        print('No MEG data')

    try:
        elec = bpy.data.objects['Deep_electrodes'].children[0]
        fcurves = elec.animation_data.action.fcurves[0]
        return len(fcurves.keyframe_points) - 2
    except:
        print('No deep electrodes data')

    # Bad fallback...
    return T


def filter_roi_func(closet_object_name, closest_curve_name=None):
    if bpy.context.scene.selection_type == 'conds':
        bpy.data.objects[closet_object_name].select = True

    bpy.context.scene.objects.active = bpy.data.objects[closet_object_name]
    if bpy.data.objects[closet_object_name].active_material == bpy.data.materials['unselected_label_Mat_subcortical']:
        bpy.data.objects[closet_object_name].active_material = bpy.data.materials['selected_label_Mat_subcortical']
    else:
        bpy.data.objects[closet_object_name].active_material = bpy.data.materials['selected_label_Mat']
    bpy.types.Scene.filter_is_on = True


def filter_electrode_func(closet_object_name, closest_curve_name=None):
    bpy.data.objects[closet_object_name].active_material.node_tree.nodes["Layer Weight"].inputs[0].default_value = 0.3
    if bpy.context.scene.selection_type == 'conds':
        bpy.data.objects[closet_object_name].select = True
    bpy.context.scene.objects.active = bpy.data.objects[closet_object_name]
    bpy.types.Scene.filter_is_on = True


class Filtering(bpy.types.Operator):
    bl_idname = "ohad.filter"
    bl_label = "Filter deep elctrodes"
    bl_options = {"UNDO"}
    topK = -1
    filter_from = 100000
    filter_to = -100000
    current_activity_path = ''
    type_of_filter = None
    type_of_func = None
    current_file_to_upload = ''
    current_root_path = bpy.context.scene.conf_path

    def get_object_to_filter(self, source_files):
        data, names = [], []
        for input_file in source_files:
            try:
                f = np.load(input_file)
                data.append(f['data'])
                names.extend([name.astype(str) for name in f['names']])
            except:
                mmvt_utils.message(self, "Can't load {}!".format(input_file))

        print('filtering {}-{}'.format(self.filter_from, self.filter_to))

        t_range = range(self.filter_from, self.filter_to + 1)

        print(self.type_of_func)
        d = np.vstack((d for d in data))
        print('%%%%%%%%%%%%%%%%%%%' + str(len(d[0, :, 0])))
        t_range = range(max(self.filter_from, 1), min(self.filter_to, len(d[0, :, 0])) - 1)
        if self.type_of_func == 'RMS':
            dd = np.squeeze(np.diff(d[:, t_range, :], axis=2)) # d[:, t_range, 0] - d[:, t_range, 1]
            dd = np.sqrt(np.sum(np.power(dd, 2), 1))
        elif self.type_of_func == 'SumAbs':
            dd = np.sum(abs(d[:, t_range, :]), (1, 2))
        elif self.type_of_func == 'threshold':
            dd = np.max(np.abs(np.squeeze(np.diff(d[:, t_range, :], axis=2))), axis=1)

        if self.topK > 0:
            self.topK = min(self.topK, len(names))
        else:
            self.topK = sum(dd > 0)

        if self.type_of_func == 'threshold':
            indices = np.where(dd > bpy.context.scene.coloring_threshold)[0]
            objects_to_filtter_in = sorted(indices, key=lambda i:dd[i])[::-1][:self.topK]
            # objects_to_filtter_in = np.argsort(dd[indices])[::-1][:self.topK]
        else:
            objects_to_filtter_in = np.argsort(dd)[::-1][:self.topK]
        print(dd[objects_to_filtter_in])
        return objects_to_filtter_in, names

    def filter_electrodes(self, current_file_to_upload):
        print('filter_electrodes')
        source_files = [os.path.join(self.current_activity_path, current_file_to_upload)]
        objects_indices, names = self.get_object_to_filter(source_files)

        for obj in bpy.data.objects:
            obj.select = False

        deep_electrodes_obj = bpy.data.objects['Deep_electrodes']
        for obj in deep_electrodes_obj.children:
            obj.active_material.node_tree.nodes["Layer Weight"].inputs[0].default_value = 1

        if bpy.context.scene.selection_type == 'diff':
            filter_obj_names = [names[ind] for ind in objects_indices]
            for fcurve in deep_electrodes_obj.animation_data.action.fcurves:
                con_name = mmvt_utils.fcurve_name(fcurve)
                fcurve.hide = con_name not in filter_obj_names
                fcurve.select = not fcurve.hide
            deep_electrodes_obj.select = True
        else:
            deep_electrodes_obj.select = False

        for ind in range(min(self.topK, len(objects_indices)) - 1, -1, -1):
            if bpy.data.objects.get(names[objects_indices[ind]]):
                orig_name = bpy.data.objects[names[objects_indices[ind]]].name
                filter_electrode_func(orig_name)
            else:
                print("Can't find {}!".format(names[objects_indices[ind]]))

    def filter_rois(self, current_file_to_upload):
        print('filter_ROIs')
        set_appearance_show_rois_layer(bpy.context.scene, True)
        source_files = [os.path.join(self.current_activity_path, current_file_to_upload.format(hemi=hemi)) for hemi
                        in HEMIS]
        objects_indices, names = self.get_object_to_filter(source_files)
        for obj in bpy.data.objects:
            obj.select = False
            if obj.parent == bpy.data.objects['Subcortical_structures']:
                obj.active_material = bpy.data.materials['unselected_label_Mat_subcortical']
            elif obj.parent == bpy.data.objects['Cortex-lh'] or obj.parent == bpy.data.objects['Cortex-rh']:
                obj.active_material = bpy.data.materials['unselected_label_Mat_cortex']

        if bpy.context.scene.selection_type == 'diff':
            filter_obj_names = [names[ind] for ind in objects_indices]
            brain_obj = bpy.data.objects['Brain']
            for fcurve in brain_obj.animation_data.action.fcurves:
                con_name = mmvt_utils.fcurve_name(fcurve)
                fcurve.hide = con_name not in filter_obj_names
                fcurve.select = not fcurve.hide
            brain_obj.select = True

        for ind in range(min(self.topK, len(objects_indices)) - 1, -1, -1):
            if bpy.data.objects.get(names[objects_indices[ind]]):
                orig_name = bpy.data.objects[names[objects_indices[ind]]].name
                filter_roi_func(orig_name)
            else:
                print("Can't find {}!".format(names[objects_indices[ind]]))
            # print(orig_name)
            # # new_name = '*'+orig_name
            # # print(new_name)
            # # bpy.data.objects[orig_name].name = new_name
            # bpy.data.objects[orig_name].select = True
            # bpy.context.scene.objects.active = bpy.data.objects[orig_name]
            # # if bpy.data.objects[orig_name].parent != bpy.data.objects[orig_name]:
            # if bpy.data.objects[orig_name].active_material == bpy.data.materials['unselected_label_Mat_subcortical']:
            #     bpy.data.objects[orig_name].active_material = bpy.data.materials['selected_label_Mat_subcortical']
            # else:
            #     bpy.data.objects[orig_name].active_material = bpy.data.materials['selected_label_Mat']

    def invoke(self, context, event=None):
        change_view3d()
        setup_layers()
        self.topK = bpy.context.scene.filter_topK
        self.filter_from = bpy.context.scene.filter_from
        self.filter_to = bpy.context.scene.filter_to
        self.current_activity_path = bpy.path.abspath(bpy.context.scene.conf_path)
        # self.current_activity_path = bpy.path.abspath(bpy.context.scene.activity_path)
        self.type_of_filter = bpy.context.scene.filter_curves_type
        self.type_of_func = bpy.context.scene.filter_curves_func
        current_file_to_upload = files_names[self.type_of_filter]

        # print(self.current_root_path)
        # source_files = ["/homes/5/npeled/space3/ohad/mg79/electrodes_data.npz"]
        if self.type_of_filter == 'Electrodes':
            current_file_to_upload = current_file_to_upload.format(
                stat='avg' if bpy.context.scene.selection_type == 'conds' else 'diff')
            self.filter_electrodes(current_file_to_upload)
        elif self.type_of_filter == 'MEG':
            self.filter_rois(current_file_to_upload)

        # bpy.context.screen.areas[2].spaces[0].dopesheet.filter_fcurve_name = '*'
        return {"FINISHED"}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Filter Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Filter Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#
# def filter_draw(self, context):
# 	layout = self.layout
# 	layout.prop(context.scene, "Filter_electrodes", text="Top K")
# 	layout.prop(context.scene, "filter_curves_type", text="")
# 	layout.operator("ohad.filter", text="Filter " + bpy.context.scene.filter_curves_type, icon = 'BORDERMOVE')
# 	layout.operator("ohad.filter_clear", text="Clear Filtering", icon = 'PANEL_CLOSE')
#
# bpy.types.Scene.Filter_electrodes = bpy.props.IntProperty(default=1, min=1,
#                                                           description="The top K electrodes to be shown")
# bpy.types.Scene.filter_curves_type = bpy.props.EnumProperty(items=[("MEG", "MEG time course", "", 1),
#                                                                    ("Electrodes", " Electrodes time course", "", 2)],
#                                                             description="Type of curve to be filtered",
#                                                             update=filter_draw)
#
#
# class FilteringMakerPanel(bpy.types.Panel):
#     bl_space_type = "GRAPH_EDITOR"
#     bl_region_type = "UI"
#     bl_context = "objectmode"
#     bl_category = "Ohad"
#     bl_label = "Filter number of curves"
#
#     def draw(self, context):
#         filter_draw(self, context)
#
# files_names = {'MEG': 'labels_data_', 'Electrodes': 'electrodes_data.npz'}
#
#
# class ClearFiltering(bpy.types.Operator):
#     bl_idname = "ohad.filter_clear"
#     bl_label = "filter clear"
#     bl_options = {"UNDO"}
#
#     @staticmethod
#     def invoke(self, context, event=None):
#         for subHierarchy in bpy.data.objects['Brain'].children:
#             new_mat = bpy.data.materials['unselected_label_Mat_cortex']
#             if subHierarchy.name == 'Subcortical_structures':
#                 new_mat = bpy.data.materials['unselected_label_Mat_subcortical']
#
#             for obj in subHierarchy.children:
#                  obj.active_material = new_mat
#                  if obj.name == 'Left cerebellum cortex' or obj.name == 'Right cerebellum cortex':
#                     obj.active_material = bpy.data.materials['unselected_label_Mat_cerebellum']
#         for obj in bpy.data.objects['Deep_electrodes'].children:
#             obj.active_material.node_tree.nodes["Layer Weight"].inputs[0].default_value = 1
#
#         return {"FINISHED"}
#
#
# class Filtering(bpy.types.Operator):
#     bl_idname = "ohad.filter"
#     bl_label = "Filter deep electrodes"
#     bl_options = {"UNDO"}
#     topK = -1
#     current_root_path = ''
#     type_of_filter = ''
#     current_file_to_upload = ''
#
#     def get_object_to_filter(self, source_files):
#         data, names = [], []
#         for input_file in source_files:
#             f = np.load(input_file)
#             data.append(f['data'])
#             temp_names = [str(name) for name in f['names']]
#             for ind in range(len(temp_names)):
#                 if temp_names[ind][1] == "'":
#                     temp_names[ind] = temp_names[ind][2:-1]
#             names.extend(temp_names)
#         self.topK = min(self.topK, len(names))
#         d = np.vstack((d for d in data))
#         dd = d[:, :, 0]-d[:, :, 1]
#         dd = np.sqrt(np.sum(np.power(dd, 2), 1))
#         # dd = d[:, :, 0]- d[:, :, 1]
#         # amps = np.max(dd,1) - np.min(dd, 1)
#         objects_to_filter_in = np.argsort(dd)[::-1][:self.topK]
#         print(objects_to_filter_in, names)
#         return objects_to_filter_in, names
#
#     def filter_electrodes(self):
#         print('filter_electrodes')
#         source_files = [os.path.join(self.current_root_path, self.current_file_to_upload)]
#         objects_to_filter_in, names = self.get_object_to_filter(source_files)
#
#         for obj in bpy.data.objects:
#             obj.select = False
#
#         for obj in bpy.data.objects['Deep_electrodes'].children:
#             obj.active_material.node_tree.nodes["Layer Weight"].inputs[0].default_value = 1
#
#         for ind in range(self.topK-1, -1, -1):
#             # print(str(names[objects_to_filter_in[ind]]))
#             orig_name = bpy.data.objects[str(names[objects_to_filter_in[ind]])].name
#             # print(orig_name)
#             # new_name = '*'+orig_name
#             # print(new_name)
#             # bpy.data.objects[orig_name].name = new_name
#             bpy.data.objects[orig_name].active_material.node_tree.nodes["Layer Weight"].inputs[0].default_value = 0.3
#
#             bpy.data.objects[orig_name].select = True
#             bpy.context.scene.objects.active = bpy.data.objects[orig_name]
#
#         bpy.context.object.parent.select = False
#
#     def filter_rois(self):
#         print('filter_rois')
#         source_files = [os.path.join(self.current_root_path, self.current_file_to_upload+hemi+'.npz') for hemi
#                         in HEMIS]
#         objects_to_filter_in, names = self.get_object_to_filter(source_files)
#         for obj in bpy.data.objects:
#             obj.select = False
#             if obj.name == 'Left cerebellum cortex' or obj.name == 'Right cerebellum cortex':
#                 obj.active_material = bpy.data.materials['unselected_label_Mat_cerebellum']
#             elif obj.parent == bpy.data.objects['Subcortical_structures']:
#                 obj.active_material = bpy.data.materials['unselected_label_Mat_subcortical']
#             elif obj.parent == bpy.data.objects['Cortex-lh'] or obj.parent == bpy.data.objects['Cortex-rh']:
#                 obj.active_material = bpy.data.materials['unselected_label_Mat_cortex']
#
#         for ind in range(self.topK-1, -1, -1):
#             orig_name = bpy.data.objects[str(names[objects_to_filter_in[ind]])].name
#             print(orig_name)
#             # new_name = '*'+orig_name
#             # print(new_name)
#             # bpy.data.objects[orig_name].name = new_name
#             bpy.data.objects[orig_name].select = True
#             bpy.context.scene.objects.active = bpy.data.objects[orig_name]
#             # if bpy.data.objects[orig_name].parent != bpy.data.objects[orig_name]:
#             if bpy.data.objects[orig_name].active_material == bpy.data.materials['unselected_label_Mat_subcortical']:
#                  bpy.data.objects[orig_name].active_material = bpy.data.materials['selected_label_Mat_subcortical']
#             else:
#                 bpy.data.objects[orig_name].active_material = bpy.data.materials['selected_label_Mat']
#
#             if obj.name == 'Left cerebellum cortex' or obj.name == 'Right cerebellum cortex':
#                 obj.active_material = bpy.data.materials['unselected_label_Mat_cerebellum']
#
#     def invoke(self, context, event=None):
#         change_view3d()
#         setup_layers()
#         self.topK = bpy.context.scene.Filter_electrodes
#         self.current_root_path = bpy.path.abspath(bpy.context.scene.conf_path)
#         self.type_of_filter = bpy.context.scene.filter_curves_type
#         self.current_file_to_upload = files_names[self.type_of_filter]
#
#         # print(self.current_root_path)
#         # source_files = ["/homes/5/npeled/space3/ohad/mg79/electrodes_data.npz"]
#         if self.type_of_filter == 'Electrodes':
#             print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~invoke~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
#             self.filter_electrodes()
#             print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~invoke2~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
#         elif self.type_of_filter == 'MEG':
#             self.filter_rois()
#
#         # bpy.context.screen.areas[2].spaces[0].dopesheet.filter_fcurve_name = '*'
#         return {"FINISHED"}
# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Filter Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Show / Hide objects ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def show_hide_hierarchy(val, obj):
    if bpy.data.objects.get(obj) is not None:
        bpy.data.objects[obj].hide = val
        for child in bpy.data.objects[obj].children:
            child.hide = val
            child.hide_render = val


def show_hide_hemi(val, obj_func_name, obj_brain_name):
    if bpy.data.objects.get(obj_func_name) is not None:
        bpy.data.objects[obj_func_name].hide = val
        bpy.data.objects[obj_func_name].hide_render = val
    show_hide_hierarchy(val, obj_brain_name)


def show_hide_rh(self, context):
    show_hide_hemi(bpy.context.scene.objects_show_hide_rh, "rh", "Cortex-rh")


def show_hide_lh(self, context):
    show_hide_hemi(bpy.context.scene.objects_show_hide_lh, "lh", "Cortex-lh")


def show_hide_sub_cortical(self, context):
    show_hide_hierarchy(bpy.context.scene.objects_show_hide_sub_cortical, "Subcortical_structures")
    # show_hide_hierarchy(bpy.context.scene.objects_show_hide_sub_cortical, "Subcortical_activity_map")
    # We split the activity map into two types: meg for the same activation for the each structure, and fmri
    # for a better resolution, like on the cortex.
    show_hide_hierarchy(bpy.context.scene.objects_show_hide_sub_cortical, "Subcortical_fmri_activity_map")
    show_hide_hierarchy(bpy.context.scene.objects_show_hide_sub_cortical, "Subcortical_meg_activity_map")


bpy.types.Scene.objects_show_hide_lh = bpy.props.BoolProperty(default=True, description="Show left hemisphere",
                                                              update=show_hide_lh)
bpy.types.Scene.objects_show_hide_rh = bpy.props.BoolProperty(default=True, description="Show right hemisphere",
                                                              update=show_hide_rh)
bpy.types.Scene.objects_show_hide_sub_cortical = bpy.props.BoolProperty(default=True, description="Show sub cortical",
                                                                        update=show_hide_sub_cortical)

class ShowHideObjectsPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Show Hide Objects"

    def draw(self, context):
        col1 = self.layout.column(align=True)
        col1.prop(context.scene, 'objects_show_hide_lh', text="Left Hemisphere", icon='RESTRICT_VIEW_OFF')
        col1.prop(context.scene, 'objects_show_hide_rh', text="Right Hemisphere", icon='RESTRICT_VIEW_OFF')
        col1.prop(context.scene, 'objects_show_hide_sub_cortical', text="Sub Cortical", icon='RESTRICT_VIEW_OFF')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Show / Hide objects ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Appearance Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def setup_layers(self=None, context=None):
    empty_layer = EMPTY_LAYER

    for layer_ind in range(len(bpy.context.scene.layers)):
        bpy.context.scene.layers[layer_ind] = layer_ind == empty_layer

    bpy.context.scene.layers[ELECTRODES_LAYER] = bpy.context.scene.appearance_show_electrodes_layer
    bpy.context.scene.layers[ROIS_LAYER] = bpy.context.scene.appearance_show_ROIs_layer
    bpy.context.scene.layers[ACTIVITY_LAYER] = bpy.context.scene.appearance_show_activity_layer
    bpy.context.scene.layers[CONNECTIONS_LAYER] = bpy.context.scene.appearance_show_connections_layer


def change_view3d(self=None, context=None):
    viewport_shade = bpy.context.scene.filter_view_type
    # if viewport_shade == 'RENDERED':
    if viewport_shade == '1':
        bpy.context.scene.layers[LIGHTS_LAYER] = True
        viewport_shade_str = 'RENDERED'
    else:
        bpy.context.scene.layers[LIGHTS_LAYER] = False
        viewport_shade_str = 'SOLID'

    for ii in range(len(bpy.context.screen.areas)):
        if bpy.context.screen.areas[ii].type == 'VIEW_3D':
            bpy.context.screen.areas[ii].spaces[0].viewport_shade = viewport_shade_str


def get_appearance_show_electrodes_layer(self):
    return self['appearance_show_electrodes_layer']


def set_appearance_show_electrodes_layer(self, value):
    self['appearance_show_electrodes_layer'] = value
    bpy.context.scene.layers[ELECTRODES_LAYER] = value


def get_appearance_show_rois_layer(self):
    return self['appearance_show_ROIs_layer']


def set_appearance_show_rois_layer(self, value):
    self['appearance_show_ROIs_layer'] = value
    bpy.context.scene.layers[ROIS_LAYER] = value
    if value:
        set_appearance_show_activity_layer(self, False)
        # bpy.context.scene.layers[LIGHTS_LAYER] = False


def get_appearance_show_activity_layer(self):
    return self['appearance_show_activity_layer']


def set_appearance_show_activity_layer(self, value):
    self['appearance_show_activity_layer'] = value
    bpy.context.scene.layers[ACTIVITY_LAYER] = value
    if value:
        set_appearance_show_rois_layer(self, False)
        # bpy.context.scene.layers[LIGHTS_LAYER] = True


def get_appearance_show_connections_layer(self):
    return self['appearance_show_connections_layer']


def set_appearance_show_connections_layer(self, value):
    self['appearance_show_connections_layer'] = value
    bpy.data.objects.get(connections_panel.PARENT_OBJ).select = value
    bpy.context.scene.layers[CONNECTIONS_LAYER] = value


def get_filter_view_type(self):
    # print('in get_filter_view_type')
    # print(self['filter_view_type'])
    # print(type(self['filter_view_type']))
    if self['filter_view_type'] == 'RENDERED':
        return 1
    elif self['filter_view_type'] == 'SOLID':
        return 2
    elif type(self['filter_view_type']) == int:
        return self['filter_view_type']
    return 3


def set_filter_view_type(self, value):
    # self['filter_view_type'] = value
    bpy.data.scenes['Scene']['filter_view_type'] = value
    change_view3d()


def change_to_rendered_brain():
    set_filter_view_type(None, 1)


def change_to_solid_brain():
    set_filter_view_type(None, 2)


def make_brain_solid_or_transparent(self=None, context=None):
    bpy.data.materials['Activity_map_mat'].node_tree.nodes['transparency_node'].inputs[
        'Fac'].default_value = bpy.context.scene.appearance_solid_slider
    if 'subcortical_activity_mat' in bpy.data.materials:
        subcortical_mat = bpy.data.materials['subcortical_activity_mat']
        subcortical_mat.node_tree.nodes['transparency_node'].inputs['Fac'].default_value = \
            bpy.context.scene.appearance_solid_slider


def update_layers():
    if bpy.context.scene.appearance_depth_Bool:
        bpy.data.materials['Activity_map_mat'].node_tree.nodes["layers_depth"].inputs[
            1].default_value = bpy.context.scene.appearance_depth_slider
    else:
        bpy.data.materials['Activity_map_mat'].node_tree.nodes["layers_depth"].inputs[1].default_value = 0


def appearance_draw(self, context):
    layout = self.layout
    col1 = self.layout.column(align=True)
    col1.prop(context.scene, 'appearance_show_ROIs_layer', text="Show ROIs", icon='RESTRICT_VIEW_OFF')
    col1.prop(context.scene, 'appearance_show_activity_layer', text="Show activity maps", icon='RESTRICT_VIEW_OFF')
    col1.prop(context.scene, 'appearance_show_electrodes_layer', text="Show electrodes", icon='RESTRICT_VIEW_OFF')
    col1.prop(context.scene, 'appearance_show_connections_layer', text="Show connections", icon='RESTRICT_VIEW_OFF')
    split = layout.split()
    split.prop(context.scene, "filter_view_type", text="")
    # print(context.scene.filter_view_type)
    # if context.scene.filter_view_type == '1' and bpy.context.scene.appearance_show_activity_layer is True:
    # # if context.scene.filter_view_type == 'RENDERED' and bpy.context.scene.appearance_show_activity_layer is True:
    #     # print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
    #     layout.prop(context.scene, 'appearance_solid_slider', text="Show solid brain")
    #     split2 = layout.split()
    #     split2.prop(context.scene, 'appearance_depth_Bool', text="Show cortex deep layers")
    #     split2.prop(context.scene, 'appearance_depth_slider', text="Depth")
    #     layout.operator("ohad.appearance_update", text="Update")


def update_solidity(self, context):
    print('in update')
    make_brain_solid_or_transparent()
    update_layers()
    AppearanceMakerPanel.draw()


bpy.types.Scene.appearance_show_electrodes_layer = bpy.props.BoolProperty(default=False, description="Show electrodes",
                                                                          get=get_appearance_show_electrodes_layer,
                                                                          set=set_appearance_show_electrodes_layer)
bpy.types.Scene.appearance_show_ROIs_layer = bpy.props.BoolProperty(default=True, description="Show ROIs",
                                                                    get=get_appearance_show_rois_layer,
                                                                    set=set_appearance_show_rois_layer)
bpy.types.Scene.appearance_show_activity_layer = bpy.props.BoolProperty(default=False, description="Show activity maps",
                                                                        get=get_appearance_show_activity_layer,
                                                                        set=set_appearance_show_activity_layer)
bpy.types.Scene.appearance_show_connections_layer = bpy.props.BoolProperty(default=False, description="Show connectivity",
                                                                        get=get_appearance_show_connections_layer,
                                                                        set=set_appearance_show_connections_layer)

bpy.types.Scene.filter_view_type = bpy.props.EnumProperty(items=[("1", "Rendered Brain", "", 1),
                                                                 ("2", " Solid Brain", "", 2)],
                                                          description="Brain appearance", get=get_filter_view_type,
                                                          set=set_filter_view_type)

class AppearanceMakerPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Appearance"

    def draw(self, context):
        # make_brain_solid_or_transparent(self, context)
        appearance_draw(self, context)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Appearance Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Transparency Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TransparencyPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Transparency"

    def draw(self, context):
        transparency_draw(self, context)


def transparency_draw(self, context):
    if context.scene.filter_view_type == '1' and bpy.context.scene.appearance_show_activity_layer is True:
    # if context.scene.filter_view_type == 'RENDERED' and bpy.context.scene.appearance_show_activity_layer is True:
        layout = self.layout
        layout.prop(context.scene, 'appearance_solid_slider', text="Show solid brain")
        split2 = layout.split()
        split2.prop(context.scene, 'appearance_depth_Bool', text="Show cortex deep layers")
        split2.prop(context.scene, 'appearance_depth_slider', text="Depth")
        layout.operator("ohad.appearance_update", text="Update")


class UpdateAppearance(bpy.types.Operator):
    bl_idname = "ohad.appearance_update"
    bl_label = "filter clear"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        if context.scene.filter_view_type == '1' and bpy.context.scene.appearance_show_activity_layer is True:
            make_brain_solid_or_transparent()
            update_layers()
        else:
            self.report({'ERROR'}, 'You should change the view to Rendered Brain first.')
        return {"FINISHED"}

bpy.types.Scene.appearance_solid_slider = bpy.props.FloatProperty(default=0.0, min=0, max=1, description="",
                                                                  update=transparency_draw)
bpy.types.Scene.appearance_depth_slider = bpy.props.IntProperty(default=1, min=1, max=10, description="")
bpy.types.Scene.appearance_depth_Bool = bpy.props.BoolProperty(default=False, description="")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Coloring Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def object_coloring(obj, rgb):
    bpy.context.scene.objects.active = obj
    # todo: do we need to select the object here? In diff mode it's a problem
    # obj.select = True
    cur_mat = obj.active_material
    # print('***************************************************************')
    # print(cur_mat)
    # print('***************************************************************')
    new_color = (rgb[0], rgb[1], rgb[2], 1)
    cur_mat.node_tree.nodes["RGB"].outputs[0].default_value = new_color


# todo: do something with the threshold parameter
def color_object_homogeneously(data, postfix_str='', threshold=0):
    if data is None:
        print('color_object_homogeneously: No data to color!')
        return

    default_color = (1, 1, 1)
    cur_frame = bpy.context.scene.frame_current
    for obj_name, object_colors, values in zip(data['names'], data['colors'], data['data']):
        obj_name = obj_name.astype(str)
        value = np.diff(values[cur_frame])[0]
        # todo: there is a difference between value and real_value, what should we do?
        # real_value = mmvt_utils.get_fcurve_current_frame_val('Deep_electrodes', obj_name, cur_frame)
        new_color = object_colors[cur_frame] if abs(value) > threshold else default_color
        # todo: check if the stat should be avg or diff
        obj = bpy.data.objects.get(obj_name+postfix_str)
        if obj and not obj.hide:
            # print('trying to color {} with {}'.format(obj_name+postfix_str, new_color))
            object_coloring(obj, new_color)
            print(obj_name, value, new_color)
        # else:
        #     print('color_object_homogeneously: {} was not loaded!'.format(obj_name))

    print('Finished coloring!!')


def init_activity_map_coloring(map_type):
    set_appearance_show_activity_layer(bpy.context.scene, True)
    set_filter_view_type(bpy.context.scene, 'RENDERS')
    # change_view3d()

    faces_verts = {}
    current_root_path = bpy.path.abspath(bpy.context.scene.conf_path)
    faces_verts['lh'] = np.load(os.path.join(current_root_path, 'faces_verts_lh.npy'))
    faces_verts['rh'] = np.load(os.path.join(current_root_path, 'faces_verts_rh.npy'))
    show_hide_hierarchy(map_type != 'FMRI', 'Subcortical_fmri_activity_map')
    show_hide_hierarchy(map_type != 'MEG', 'Subcortical_meg_activity_map')
    return faces_verts


def load_meg_subcortical_activity():
    meg_sub_activity = None
    current_root_path = bpy.path.abspath(bpy.context.scene.conf_path)
    subcortical_activity_file = os.path.join(current_root_path,'subcortical_meg_activity.npz')
    if os.path.isfile(subcortical_activity_file):
        meg_sub_activity = np.load(subcortical_activity_file)
    return meg_sub_activity


def activity_map_coloring(map_type):
    faces_verts = init_activity_map_coloring(map_type)
    threshold = bpy.context.scene.coloring_threshold
    meg_sub_activity = None
    if map_type == 'MEG':
        meg_sub_activity = load_meg_subcortical_activity()
    plot_activity(map_type, faces_verts, threshold, meg_sub_activity)
    # setup_environment_settings()


def meg_labels_coloring(self, context, aparc_name='laus250', override_current_mat=True):
    faces_verts = init_activity_map_coloring('MEG')
    threshold = bpy.context.scene.coloring_threshold
    hemispheres = [hemi for hemi in HEMIS if not bpy.data.objects[hemi].hide]
    user_fol = mmvt_utils.get_user_fol()
    t = bpy.context.scene.frame_current
    for hemi in hemispheres:
        cur_obj = bpy.data.objects[hemi]
        # 'labels_indices', 'labels_names'
        d = mmvt_utils.load(os.path.join(user_fol, 'labels_dic_{}_{}.pkl'.format(aparc_name, hemi)))
        names = ['{}-{}'.format(label.astype(str), hemi) for label in d['labels_names']]
        # data, colors, names
        labels_data = np.load(os.path.join(user_fol, 'labels_data_no_conds_{}.npz'.format(hemi)))
        # for ind, (label_name, labenamesl_vertices) in enumerate(zip(names, d['labels_indices'])):
        vertices_num = sum([len(verts) for verts in d['labels_indices']])
        all_vertices, all_data = np.empty((0, 1)), np.empty((0, 4))
        for label_data, label_colors, label_name in zip(labels_data['data'], labels_data['colors'], labels_data['names']):
            label_index = names.index(label_name)
            label_vertices = np.array(d['labels_indices'][label_index])
            if len(label_vertices) > 0:
                print('coloring {} with {}'.format(label_name, label_colors[t]))
                colors_data = np.hstack((label_data[t], label_colors[t]))
                colors_data = np.tile(colors_data, (len(label_vertices), 1))
                all_data = np.vstack((all_data, colors_data))
                all_vertices = np.vstack((all_vertices, label_vertices.reshape((len(label_vertices), 1))))
        all_vertices = all_vertices.ravel()
        activity_map_obj_coloring(cur_obj, all_data, faces_verts[hemi], threshold, True, all_vertices)


def plot_activity(map_type, faces_verts, threshold, meg_sub_activity=None,
        plot_subcorticals=True, override_current_mat=True):
    current_root_path = bpy.path.abspath(bpy.context.scene.conf_path)
    hemispheres = [hemi for hemi in HEMIS if not bpy.data.objects[hemi].hide]
    frame_str = str(bpy.context.scene.frame_current)

    # loop_indices = {}
    for hemi in hemispheres:
        if map_type == 'MEG':
            f = np.load(os.path.join(current_root_path, 'activity_map_' + hemi, 't' + frame_str + '.npy'))
        elif map_type == 'FMRI':
            f = np.load(os.path.join(current_root_path, 'fmri_' + hemi + '.npy'))
        cur_obj = bpy.data.objects[hemi]
        # loop_indices[hemi] =
        activity_map_obj_coloring(cur_obj, f, faces_verts[hemi], threshold, override_current_mat)

    if plot_subcorticals:
        if map_type == 'MEG':
            if not bpy.data.objects['Subcortical_meg_activity_map'].hide:
                color_object_homogeneously(meg_sub_activity, '_meg_activity', threshold)
        if map_type == 'FMRI':
            fmri_subcortex_activity_color(threshold, override_current_mat)

    # return loop_indices
    # Noam: not sure this is necessary
    #deselect_all()
    #bpy.data.objects['Brain'].select = True


def fmri_subcortex_activity_color(threshold, override_current_mat=True):
    current_root_path = bpy.path.abspath(bpy.context.scene.conf_path)
    subcoticals = glob.glob(os.path.join(current_root_path, 'subcortical_fmri_activity', '*.npy'))
    for subcortical_file in subcoticals:
        subcortical = os.path.splitext(os.path.basename(subcortical_file))[0]
        cur_obj = bpy.data.objects.get('{}_fmri_activity'.format(subcortical))
        if cur_obj is None:
            print("Can't find the object {}!".format(subcortical))
        else:
            lookup_file = os.path.join(current_root_path, 'subcortical', '{}_faces_verts.npy'.format(subcortical))
            verts_file = os.path.join(current_root_path, 'subcortical_fmri_activity', '{}.npy'.format(subcortical))
            if os.path.isfile(lookup_file) and os.path.isfile(verts_file):
                lookup = np.load(lookup_file)
                verts_values = np.load(verts_file)
                activity_map_obj_coloring(cur_obj, verts_values, lookup, threshold, override_current_mat)


def activity_map_obj_coloring(cur_obj, vert_values, lookup, threshold, override_current_mat, verts=None):
    mesh = cur_obj.data
    scn = bpy.context.scene

    valid_verts = np.where(np.abs(vert_values[:,0])>threshold)[0]
    if not verts is None:
        valid_verts = verts[valid_verts]
    #check if our mesh already has Vertex Colors, and if not add some... (first we need to make sure it's the active object)
    scn.objects.active = cur_obj
    cur_obj.select = True
    if override_current_mat:
        bpy.ops.mesh.vertex_color_remove()
    vcol_layer = mesh.vertex_colors.new()
    # else:
    #     vcol_layer = mesh.vertex_colors.active
        # loop_indices = set()
    print('max vert in lookup: {}, vcol_layer len: {}'.format(np.max(lookup), len(vcol_layer.data)))
    for ind, vert in enumerate(valid_verts):
        x = lookup[vert]
        for loop_ind in x[x>-1]:
            vcol_layer.data[loop_ind].color = vert_values[ind, 1:]
            # loop_indices.add(loop_ind)
    # return loop_indices


def default_coloring(loop_indices):
    for hemi, indices in loop_indices.items():
        cur_obj = bpy.data.objects[hemi]
        mesh = cur_obj.data
        vcol_layer = mesh.vertex_colors.active
        for loop_ind in indices:
            vcol_layer.data[loop_ind].color = [1, 1, 1]


class ColorElectrodes(bpy.types.Operator):
    bl_idname = "ohad.electrodes_color"
    bl_label = "ohad electrodes color"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        threshold = bpy.context.scene.coloring_threshold
        data = np.load(os.path.join(mmvt_utils.get_user_fol(),'electrodes_data_{}.npz'.format(
            'avg' if bpy.context.scene.selection_type == 'conds' else 'diff')))
        color_object_homogeneously(data, threshold=threshold)
        # deselect_all()
        # mmvt_utils.select_hierarchy('Deep_electrodes', False)
        set_appearance_show_electrodes_layer(bpy.context.scene, True)
        # bpy.data.objects['Deep_electrodes'].select = True
        # for cur_obj in bpy.data.objects['Deep_electrodes'].children:
        #     cur_obj.select = True
        change_to_rendered_brain()
        return {"FINISHED"}


class ColorMeg(bpy.types.Operator):
    bl_idname = "ohad.meg_color"
    bl_label = "ohad meg color"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        activity_map_coloring('MEG')
        return {"FINISHED"}


class ColorMegLabels(bpy.types.Operator):
    bl_idname = "ohad.meg_labels_color"
    bl_label = "ohad meg labels color"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        # todo: should send also aparc_name
        meg_labels_coloring(self, context)
        return {"FINISHED"}


class ColorFmri(bpy.types.Operator):
    bl_idname = "ohad.fmri_color"
    bl_label = "ohad fmri color"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        activity_map_coloring('FMRI')
        return {"FINISHED"}


class ClearColors(bpy.types.Operator):
    bl_idname = "ohad.colors_clear"
    bl_label = "ohad colors clear"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        hemispheres = HEMIS
        for hemisphere in hemispheres:
            cur_obj = bpy.data.objects[hemisphere]
            mesh = cur_obj.data
            scn = bpy.context.scene
            scn.objects.active = cur_obj
            cur_obj.select = True
            bpy.ops.mesh.vertex_color_remove()
            vcol_layer = mesh.vertex_colors.new()
        # for obj in bpy.data.objects['Subcortical_activity_map'].children:
        for cur_obj in bpy.data.objects['Subcortical_fmri_activity_map'].children:
            print('in clear subcortical ' + cur_obj.name)
            # obj.active_material.node_tree.nodes['RGB'].outputs['Color'].default_value = (1, 1, 1, 1)
            mesh = cur_obj.data
            scn = bpy.context.scene
            scn.objects.active = cur_obj
            cur_obj.select = True
            bpy.ops.mesh.vertex_color_remove()
            vcol_layer = mesh.vertex_colors.new()
        for root in ['Subcortical_meg_activity_map', 'Deep_electrodes']:
            if bpy.data.objects.get(root) is not None:
                for obj in bpy.data.objects[root].children:
                    if 'RGB' in obj.active_material.node_tree.nodes:
                        obj.active_material.node_tree.nodes['RGB'].outputs['Color'].default_value=(1,1,1,1)
        # for obj in bpy.data.objects['Deep_electrodes'].children:
        #     obj.active_material.node_tree.nodes['RGB'].outputs['Color'].default_value = (1, 1, 1, 1)
        return {"FINISHED"}


bpy.types.Scene.coloring_fmri = bpy.props.BoolProperty(default=True, description="Plot FMRI")
bpy.types.Scene.coloring_electrodes = bpy.props.BoolProperty(default=False, description="Plot Deep electrodes")
bpy.types.Scene.coloring_threshold = bpy.props.FloatProperty(default=0.5, min=0, description="")


class ColoringMakerPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Activity Maps"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, 'coloring_threshold', text="Threshold")
        layout.operator(ColorMeg.bl_idname, text="Plot MEG ", icon='POTATO')
        layout.operator(ColorMegLabels.bl_idname, text="Plot MEG Labels ", icon='POTATO')
        layout.operator(ColorFmri.bl_idname, text="Plot FMRI ", icon='POTATO')
        layout.operator(ColorElectrodes.bl_idname, text="Plot Electrodes ", icon='POTATO')
        layout.operator(ClearColors.bl_idname, text="Clear", icon='PANEL_CLOSE')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Coloring Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Where am I Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
bpy.types.Scene.where_am_i_str = ''


def where_i_am_draw(self, context):
    try:
        layout = self.layout
        # col = layout.column(align=True)
        layout.operator("ohad.where_i_am", text="Where Am I?", icon='SNAP_SURFACE')
        layout.operator("ohad.where_am_i_clear", text="Clear", icon='PANEL_CLOSE')
        layout.label(text=bpy.types.Scene.where_am_i_str)
    except:
        #Noam: try not to write pass in except, then we'll never know the try block failed
        print('Error in where_i_am_draw!')


class WhereAmI(bpy.types.Operator):
    bl_idname = "ohad.where_i_am"
    bl_label = "ohad where i am"
    bl_options = {"UNDO"}

    where_am_I_selected_obj = None
    where_am_I_selected_obj_org_hide = True

    @staticmethod
    def setup_environment(self):
        set_appearance_show_rois_layer(bpy.context.scene, True)
        # pass

    @staticmethod
    def main_func(self):
        distances = []
        names = []

        bpy.data.objects['Brain'].select = False
        for subHierarchy in bpy.data.objects['Brain'].children:
            if subHierarchy == bpy.data.objects['Subcortical_structures']:
                cur_material = bpy.data.materials['unselected_label_Mat_subcortical']
            else:
                cur_material = bpy.data.materials['unselected_label_Mat_cortex']
            for obj in subHierarchy.children:
                obj.active_material = cur_material
                obj.select = False
                obj.hide = subHierarchy.hide

                # 3d cursor relative to the object data
                cursor = bpy.context.scene.cursor_location
                # try:
                #     if bpy.context.object.parent == bpy.data.objects['Deep_electrodes']:
                #         cursor = bpy.context.object.location
                # except KeyError:
                #     pass

                # Noam: Maybe this is better?
                if bpy.context.object.parent == bpy.data.objects.get('Deep_electrodes', None):
                    cursor = bpy.context.object.location

                co_find = cursor * obj.matrix_world.inverted()

                mesh = obj.data
                size = len(mesh.vertices)
                kd = mathutils.kdtree.KDTree(size)

                for i, v in enumerate(mesh.vertices):
                    kd.insert(v.co, i)

                kd.balance()

                # Find the closest 10 points to the 3d cursor
                # print("Close 1 points")
                for (co, index, dist) in kd.find_n(co_find, 1):
                    # print("    ", obj.name,co, index, dist)
                    if 'unknown' not in obj.name:
                        distances.append(dist)
                        names.append(obj.name)

        # print(np.argmin(np.array(distances)))
        min_index = np.argmin(np.array(distances))
        closest_area = names[np.argmin(np.array(distances))]
        bpy.types.Scene.where_am_i_str = closest_area

        print('closest area is: '+closest_area)
        print('dist: {}'.format(np.min(np.array(distances))))
        print('closets vert is {}'.format(bpy.data.objects[closest_area].data.vertices[min_index].co))
        WhereAmI.where_am_I_selected_obj = bpy.data.objects[closest_area]
        WhereAmI.where_am_I_selected_obj_org_hide = bpy.data.objects[closest_area].hide

        bpy.context.scene.objects.active = bpy.data.objects[closest_area]
        bpy.data.objects[closest_area].select = True
        bpy.data.objects[closest_area].hide = False
        bpy.data.objects[closest_area].active_material = bpy.data.materials['selected_label_Mat']

    def invoke(self, context, event=None):
        self.setup_environment(self)
        self.main_func(self)
        return {"FINISHED"}


class ClearWhereAmI(bpy.types.Operator):
    bl_idname = "ohad.where_am_i_clear"
    bl_label = "where am i clear"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        for subHierarchy in bpy.data.objects['Brain'].children:
            new_mat = bpy.data.materials['unselected_label_Mat_cortex']
            if subHierarchy.name == 'Subcortical_structures':
                new_mat = bpy.data.materials['unselected_label_Mat_subcortical']
            for obj in subHierarchy.children:
                obj.active_material = new_mat

        # Noam: I think this is better than a try block
        if 'Deep_electrodes' in bpy.data.objects:
            for obj in bpy.data.objects['Deep_electrodes'].children:
                obj.active_material.node_tree.nodes["Layer Weight"].inputs[0].default_value = 1
        if bpy.data.objects.get(' '):
            context.scene.objects.active = bpy.data.objects[' ']

        for obj in bpy.data.objects:
            obj.select = False

        if WhereAmI.where_am_I_selected_obj is not None:
            WhereAmI.where_am_I_selected_obj.hide = WhereAmI.where_am_I_selected_obj_org_hide
            WhereAmI.where_am_I_selected_obj = None

        bpy.types.Scene.where_am_i_str = ''
        where_i_am_draw(self, context)
        return {"FINISHED"}


bpy.types.Scene.where_am_i = bpy.props.StringProperty(description="Find closest curve to cursor",
                                                      update=where_i_am_draw)


class WhereAmIMakerPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Where Am I"

    def draw(self, context):
        where_i_am_draw(self, context)
        layout = self.layout
        # layout.operator("ohad.where_i_am", text="Where Am I?", icon = 'SNAP_SURFACE')
        # layout.operator("ohad.where_am_i_clear", text="Clear", icon = 'PANEL_CLOSE')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Where am I Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Search Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class SearchFilter(bpy.types.Operator):
    bl_idname = "ohad.selection_filter"
    bl_label = "selection filter"
    bl_options = {"UNDO"}
    marked_objects_select = {}

    def invoke(self, context, event=None):
        label_name = context.scene.labels_regex
        SearchMark.marked_objects_select = {}
        for obj in bpy.data.objects:
            SearchFilter.marked_objects_select[obj.name] = bpy.data.objects[obj.name].select
            obj.select = label_name in obj.name
        return {"FINISHED"}


class SearchClear(bpy.types.Operator):
    bl_idname = "ohad.selection_clear"
    bl_label = "selection clear"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        # Copy from where am I clear
        for subHierchy in bpy.data.objects['Brain'].children:
            new_mat = bpy.data.materials['unselected_label_Mat_cortex']
            if subHierchy.name == 'Subcortical strutures':
                new_mat = bpy.data.materials['unselected_label_Mat_subcortical']
            for obj in subHierchy.children:
                 obj.active_material = new_mat

        for obj in bpy.data.objects['Deep_electrodes'].children:
            obj.active_material.node_tree.nodes["Layer Weight"].inputs[0].default_value = 1

        for obj_name, h in SearchMark.marked_objects_hide.items():
            bpy.data.objects[obj_name].hide = bool(h)
        for obj_name, h in SearchFilter.marked_objects_select.items():
            print('bpy.data.objects[{}].select = {}'.format(obj_name, bool(h)))
            bpy.data.objects[obj_name].select = bool(h)
        return {"FINISHED"}


class SearchMark(bpy.types.Operator):
    bl_idname = "ohad.selection_mark"
    bl_label = "selection mark"
    bl_options = {"UNDO"}
    marked_objects_hide = {}

    def invoke(self, context, event=None):
        label_name = context.scene.labels_regex
        SearchMark.marked_objects_hide = {}
        for obj in bpy.data.objects:
            if label_name in obj.name:
                bpy.context.scene.objects.active = bpy.data.objects[obj.name]
                bpy.data.objects[obj.name].select = True
                SearchMark.marked_objects_hide[obj.name] = bpy.data.objects[obj.name].hide
                bpy.data.objects[obj.name].hide = False
                bpy.data.objects[obj.name].active_material = bpy.data.materials['selected_label_Mat']

        return {"FINISHED"}

bpy.types.Scene.labels_regex = bpy.props.StringProperty(default= '', description="labels regex")

class SearchPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Search Panel"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "labels_regex", text="Labels regex")
        row = layout.row(align=0)
        row.operator(SearchFilter.bl_idname, text="Search", icon = 'BORDERMOVE')
        row.operator(SearchMark.bl_idname, text="Mark", icon = 'GREASEPENCIL')
        layout.operator(SearchClear.bl_idname, text="Clear", icon = 'PANEL_CLOSE')


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Search Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ freeview Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class FreeviewGotoCursor(bpy.types.Operator):
    bl_idname = "ohad.freeview_goto_cursor"
    bl_label = "Goto Cursor"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        root = bpy.path.abspath(bpy.context.scene.conf_path)
        point = np.genfromtxt(os.path.join(root, 'freeview', 'edit.dat'))
        bpy.context.scene.cursor_location = point / 10.0
        return {"FINISHED"}


class FreeviewOpen(bpy.types.Operator):
    bl_idname = "ohad.freeview_open"
    bl_label = "Open Freeview"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        root = bpy.path.abspath(bpy.context.scene.conf_path)
        sig = os.path.join(root, 'freeview', 'sig_subject.mgz')
        T1 = os.path.join(root, 'freeview', 'T1.mgz')
        aseg = os.path.join(root, 'freeview', 'laus250+aseg.mgz')
        lut = os.path.join(root, 'freeview', 'laus250ColorLUT.txt')
        electrodes = self.get_electrodes_groups(root)
        cmd = 'freeview -v {}:colormap=heat {}:opacity=0.3 {}:opacity=0.05:colormap=lut:lut={} -c {}'.format(sig, T1, aseg, lut, electrodes)
        utils.run_command_in_new_thread(cmd)
        return {"FINISHED"}

    def get_electrodes_groups(self, root):
        groups = set([obj.name[:3] for obj in bpy.data.objects['Deep_electrodes'].children])
        groups_files = ''
        for group in groups:
            groups_files = groups_files + os.path.join(root, 'freeview', '{}.dat '.format(group))
        return groups_files

class FreeviewPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Freeview Panel"

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=0)
        row.operator(FreeviewOpen.bl_idname, text="Freeview", icon = 'PARTICLES')
        row.operator(FreeviewGotoCursor.bl_idname, text="Goto Cursor", icon = 'HAND')


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ freeview Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Show data of vertex Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ClearVertexData(bpy.types.Operator):
    bl_idname = "ohad.vertex_data_clear"
    bl_label = "vertex data clear"
    bl_options = {"UNDO"}

    @staticmethod
    def invoke(self, context, event=None):
        for obj in bpy.data.objects:
            if obj.name.startswith('Activity_in_vertex'):
                obj.select = True
                bpy.context.scene.objects.unlink(obj)
                bpy.data.objects.remove(obj)

        return {"FINISHED"}


class CreateVertexData(bpy.types.Operator):
    bl_idname = "ohad.vertex_data_create"
    bl_label = "vertex data create"
    bl_options = {"UNDO"}

    @staticmethod
    def find_vertex_index_and_mesh_closest_to_cursor(self):
        # 3d cursor relative to the object data
        print('cursor at:' + str(bpy.context.scene.cursor_location))
        # co_find = context.scene.cursor_location * obj.matrix_world.inverted()
        distances = []
        names = []
        vertices_idx = []
        vertices_co = []

        # base_obj = bpy.data.objects['Functional maps']
        # meshes = HEMIS
        #        for obj in base_obj.children:
        for cur_obj in HEMIS:
            obj = bpy.data.objects[cur_obj]
            co_find = bpy.context.scene.cursor_location * obj.matrix_world.inverted()
            mesh = obj.data
            size = len(mesh.vertices)
            kd = mathutils.kdtree.KDTree(size)

            for i, v in enumerate(mesh.vertices):
                kd.insert(v.co, i)

            kd.balance()
            print(obj.name)
            for (co, index, dist) in kd.find_n(co_find, 1):
                print('cursor at {} ,vertex {}, index {}, dist {}'.format(str(co_find), str(co), str(index),str(dist)))
                distances.append(dist)
                names.append(obj.name)
                vertices_idx.append(index)
                vertices_co.append(co)

        closest_mesh_name = names[np.argmin(np.array(distances))]
        print('closest_mesh =' + str(closest_mesh_name))
        vertex_ind = vertices_idx[np.argmin(np.array(distances))]
        print('vertex_ind =' + str(vertex_ind))
        vertex_co = vertices_co[np.argmin(np.array(distances))] * obj.matrix_world
        return closest_mesh_name, vertex_ind, vertex_co

    @staticmethod
    def create_empty_in_vertex_location(self, vertex_location):
        layer = [False] * 20
        #todo: Why 11 (activity layer)?
        layer[11] = True
        bpy.ops.object.empty_add(type='PLAIN_AXES', radius=1, view_align=False, location=vertex_location, layers=layer)
        bpy.context.object.name = "Activity_in_vertex"

    @staticmethod
    def insert_keyframe_to_custom_prop(self, obj, prop_name, value, keyframe):
        bpy.context.scene.objects.active = obj
        obj.select = True
        obj[prop_name] = value
        obj.keyframe_insert(data_path='[' + '"' + prop_name + '"' + ']', frame=keyframe)

    @staticmethod
    def keyframe_empty(self, empty_name, closest_mesh_name, vertex_ind, data_path):
        obj = bpy.data.objects[empty_name]
        number_of_time_points = len(glob.glob(os.path.join(data_path, 'activity_map_' + closest_mesh_name + '2', '', ) + '*.npy'))
        insert_keyframe_to_custom_prop(obj, 'data', 0, 0)
        insert_keyframe_to_custom_prop(obj, 'data', 0, number_of_time_points + 1)
        for ii in range(number_of_time_points):
            # print(ii)
            frame_str = str(ii)
            f = np.load(os.path.join(data_path, 'activity_map_' + closest_mesh_name + '2', 't' + frame_str + '.npy'))
            insert_keyframe_to_custom_prop(obj, 'data', float(f[vertex_ind, 0]), ii + 1)

        fcurves = bpy.data.objects[empty_name].animation_data.action.fcurves[0]
        mod = fcurves.modifiers.new(type='LIMITS')

    def keyframe_empty_test(self, empty_name, closest_mesh_name, vertex_ind, data_path):
        obj = bpy.data.objects[empty_name]
        lookup = np.load(os.path.join(data_path, 'activity_map_' + closest_mesh_name + '_verts_lookup.npy'))
        file_num_str = str(int(lookup[vertex_ind, 0]))
        line_num = int(lookup[vertex_ind, 1])
        data_file = np.load(
            os.path.join(data_path, 'activity_map_' + closest_mesh_name + '_verts', file_num_str + '.npy'))
        data = data_file[line_num, :].squeeze()

        number_of_time_points = len(data)
        self.insert_keyframe_to_custom_prop(self, obj, 'data', 0, 0)
        self.insert_keyframe_to_custom_prop(self, obj, 'data', 0, number_of_time_points + 1)
        for ii in range(number_of_time_points):
            print(ii)
            frame_str = str(ii)
            self.insert_keyframe_to_custom_prop(self, obj, 'data', float(data[ii]), ii + 1)
            # insert_keyframe_to_custom_prop(obj,'data',0,ii+1)
        fcurves = bpy.data.objects[empty_name].animation_data.action.fcurves[0]
        mod = fcurves.modifiers.new(type='LIMITS')

    def invoke(self, context, event=None):
        # Noam: is was self.find_vertex_index_and_mesh_closest_to_cursor(self) before, are you sure we need to send the self?
        closest_mesh_name, vertex_ind, vertex_co = self.find_vertex_index_and_mesh_closest_to_cursor()
        print(vertex_co)
        self.create_empty_in_vertex_location(self, vertex_co)
        # data_path = '/homes/5/npeled/space3/MEG/ECR/mg79'
        data_path = bpy.path.abspath(bpy.context.scene.conf_path)
        # keyframe_empty('Activity_in_vertex',closest_mesh_name,vertex_ind,data_path)
        self.keyframe_empty_test('Activity_in_vertex', closest_mesh_name, vertex_ind, data_path)
        return {"FINISHED"}


class DataInVertMakerPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Data in vertex"

    def draw(self, context):
        layout = self.layout
        layout.operator("ohad.vertex_data_create", text="Get data in vertex", icon='ROTATE')
        layout.operator("ohad.vertex_data_clear", text="Clear", icon='PANEL_CLOSE')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Show data of vertex Panel ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~RENDER~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
bpy.types.Scene.output_path = bpy.props.StringProperty(name="Output Path", default="",
                                                       description="Define the path for the output files",
                                                       subtype='DIR_PATH')


def render_draw(self, context):
    layout = self.layout
    col = layout.column(align=True)
    col.prop(context.scene, "X_rotation", text='X rotation')
    col.prop(context.scene, "Y_rotation", text='Y rotation')
    col.prop(context.scene, "Z_rotation", text='Z rotation')
    layout.prop(context.scene, "quality", text='Quality')
    layout.prop(context.scene, 'output_path')
    layout.prop(context.scene, 'smooth_figure')
    layout.operator("ohad.rendering", text="Render", icon='SCENE')


def update_rotation(self, context):
    bpy.data.objects['Target'].rotation_euler.x = math.radians(bpy.context.scene.X_rotation)
    bpy.data.objects['Target'].rotation_euler.y = math.radians(bpy.context.scene.Y_rotation)
    bpy.data.objects['Target'].rotation_euler.z = math.radians(bpy.context.scene.Z_rotation)


def update_quality(self, context):
    print(bpy.context.scene.quality)
    bpy.context.scene.quality = bpy.context.scene.quality


bpy.types.Scene.X_rotation = bpy.props.FloatProperty(default=0, min=-360, max=360,
                                                     description="Camera rotation around x axis",
                                                     update=update_rotation)
bpy.types.Scene.Y_rotation = bpy.props.FloatProperty(default=0, min=-360, max=360,
                                                     description="Camera rotation around y axis",
                                                     update=update_rotation)
bpy.types.Scene.Z_rotation = bpy.props.FloatProperty(default=0, min=-360, max=360,
                                                     description="Camera rotation around z axis",
                                                     update=update_rotation)
bpy.types.Scene.quality = bpy.props.FloatProperty(default=20, min=1, max=100,
                                                  description="quality of figure in parentage", update=update_quality)
bpy.types.Scene.smooth_figure = bpy.props.BoolProperty(name='smooth image',
                                                       description="This significantly affect rendering speed")


class RenderFigure(bpy.types.Operator):
    bl_idname = "ohad.rendering"
    bl_label = "Render figure"
    bl_options = {"UNDO"}
    current_output_path = bpy.path.abspath(bpy.context.scene.output_path)
    x_rotation = bpy.context.scene.X_rotation
    y_rotation = bpy.context.scene.Y_rotation
    z_rotation = bpy.context.scene.Z_rotation
    quality = bpy.context.scene.quality

    def invoke(self, context, event=None):
        render_image()
        return {"FINISHED"}


def render_image():
    x_rotation = bpy.context.scene.X_rotation
    y_rotation = bpy.context.scene.Y_rotation
    z_rotation = bpy.context.scene.Z_rotation
    quality = bpy.context.scene.quality
    use_square_samples = bpy.context.scene.smooth_figure

    print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$In Render$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
    bpy.data.objects['Target'].rotation_euler.x = math.radians(x_rotation)
    bpy.data.objects['Target'].rotation_euler.y = math.radians(y_rotation)
    bpy.data.objects['Target'].rotation_euler.z = math.radians(z_rotation)
    bpy.context.scene.render.resolution_percentage = quality
    print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
    print(use_square_samples)
    print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
    bpy.context.scene.cycles.use_square_samples = use_square_samples

    # print('Output folder:')
    # print(self.current_output_path)
    cur_frame = bpy.context.scene.frame_current
    print('file name:')
    # print('f'+str(cur_frame))
    # print('folder:'+self.current_output_path)
    file_name = os.path.join(bpy.path.abspath(bpy.context.scene.output_path), 'f{}'.format(cur_frame))
    # file_name = os.path.join(mmvt_utils.get_user_fol(), 'images', mmvt_utils.rand_letters(5))
    print(file_name)
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

    def draw(self, context):
        current_root_path = bpy.path.abspath(bpy.context.scene.conf_path)
        render_draw(self, context)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~RENDER~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class helper_class():
    # bpy.types.Scene.conf_path = bpy.props.StringProperty(name="Root Path", default="", description="Define the root path of the project", subtype='DIR_PATH')
    # bpy.types.Scene.brain_imported = False
    # bpy.types.Scene.electrodes_imported = False
    # bpy.types.Scene.brain_data_exist = False
    # bpy.types.Scene.electrodes_data_exist = False
    # bpy.types.Scene.closest_curve_str = ''
    # bpy.types.Scene.filter_is_on = False
    # files_names = {'MEG': 'labels_data_', 'Electrodes': 'electrodes_data.npz'}
    # bpy.types.Scene.closest_curve = bpy.props.StringProperty(description="Find closest curve to cursor", update=filter_draw)
    # bpy.types.Scene.filter_topK = bpy.props.IntProperty(default=1, min=0, description="The top K elements to be shown")
    # bpy.types.Scene.filter_topK = bpy.props.IntProperty(default=1, min=0, description="The top K elements to be shown")
    # bpy.types.Scene.filter_from = bpy.props.IntProperty(default=0, min=0, description="When to filter from")
    # bpy.types.Scene.filter_to = bpy.props.IntProperty(default=bpy.context.scene.frame_end, min=0, description="When to filter to")
    # bpy.types.Scene.filter_curves_type = bpy.props.EnumProperty(items=[("MEG", "MEG time course", "", 1), ("Electrodes", " Electrodes time course", "", 2)], description="Type of curve to be filtered", update=filter_draw)
    # bpy.types.Scene.filter_curves_func = bpy.props.EnumProperty(items=[("RMS", "RMS", "RMS between the two conditions", 1), ("SumAbs", "SumAbs", "Sum of the abs values", 2)], description="Filtering function", update=filter_draw)
    # bpy.types.Scene.objects_show_hide_lh = bpy.props.BoolProperty(default=True, description="Show left hemisphere", update=show_hide_lh)
    # bpy.types.Scene.objects_show_hide_rh = bpy.props.BoolProperty(default=True, description="Show right hemisphere",update=show_hide_rh)
    # bpy.types.Scene.objects_show_hide_sub_cortical = bpy.props.BoolProperty(default=True, description="Show sub cortical", update=show_hide_sub_cortical)
    # bpy.types.Scene.appearance_show_electrodes_layer = bpy.props.BoolProperty(default=False, description="Show electrodes", get=get_appearance_show_electrodes_layer, set=set_appearance_show_electrodes_layer)
    # bpy.types.Scene.appearance_show_ROIs_layer = bpy.props.BoolProperty(default=True, description="Show ROIs", get=get_appearance_show_rois_layer, set=set_appearance_show_rois_layer)
    # bpy.types.Scene.appearance_show_activity_layer = bpy.props.BoolProperty(default=False, description="Show activity maps", get=get_appearance_show_activity_layer, set=set_appearance_show_activity_layer)
    # bpy.types.Scene.filter_view_type = bpy.props.EnumProperty(items=[("RENDERED", "Rendered Brain", "", 1), ("SOLID", " Solid Brain", "", 2)], description="Brain appearance", get=get_filter_view_type, set=set_filter_view_type)
    # bpy.types.Scene.appearance_solid_slider = bpy.props.FloatProperty(default=0.0, min=0, max=1, description="", update=appearance_draw)
    # bpy.types.Scene.appearance_depth_slider = bpy.props.IntProperty(default=1, min=1, max=10, description="")
    # bpy.types.Scene.appearance_depth_Bool = bpy.props.BoolProperty(default=False, description="")
    # bpy.types.Scene.coloring_fmri = bpy.props.BoolProperty(default=True, description="Plot FMRI")
    # bpy.types.Scene.coloring_electrodes = bpy.props.BoolProperty(default=False, description="Plot Deep electrodes")
    # bpy.types.Scene.coloring_threshold = bpy.props.FloatProperty(default=0.5, min=0, description="")
    # bpy.types.Scene.where_am_i_str = ''
    # bpy.types.Scene.where_am_i = bpy.props.StringProperty(description="Find closest curve to cursor", update=where_i_am_draw)
    # bpy.types.Scene.output_path = bpy.props.StringProperty(name="Output Path", default="", description="Define the path for the output files", subtype='DIR_PATH')
    # bpy.types.Scene.X_rotation = bpy.props.FloatProperty(default=0, min=-360, max=360, description="Camera rotation around x axis", update=update_rotation)
    # bpy.types.Scene.Y_rotation = bpy.props.FloatProperty(default=0, min=-360, max=360, description="Camera rotation around y axis", update=update_rotation)
    # bpy.types.Scene.Z_rotation = bpy.props.FloatProperty(default=0, min=-360, max=360, description="Camera rotation around z axis", update=update_rotation)
    # bpy.types.Scene.quality = bpy.props.FloatProperty(default=20, min=1, max=100, description="quality of figure in parentage", update=update_quality)
    # bpy.types.Scene.smooth_figure = bpy.props.BoolProperty(name='smooth image', description="This significantly affect rendering speed")
    conf_path = bpy.props.StringProperty(name="Root Path", default="",
                                         description="Define the root path of the project", subtype='DIR_PATH')
    brain_imported = False
    electrodes_imported = False
    brain_data_exist = False
    electrodes_data_exist = False
    closest_curve_str = ''
    filter_is_on = False
    # files_names = {'MEG': 'labels_data_', 'Electrodes': 'electrodes_data.npz'}
    closest_curve = bpy.props.StringProperty(description="Find closest curve to cursor", update=filter_draw)
    filter_topK = bpy.props.IntProperty(default=1, min=0, description="The top K elements to be shown")
    filter_topK = bpy.props.IntProperty(default=1, min=0, description="The top K elements to be shown")
    filter_from = bpy.props.IntProperty(default=0, min=0, description="When to filter from")
    filter_to = bpy.props.IntProperty(default=1000, min=0, description="When to filter to")
    filter_curves_type = bpy.props.EnumProperty(
        items=[("MEG", "MEG time course", "", 1), ("Electrodes", " Electrodes time course", "", 2)],
        description="Type of curve to be filtered", update=filter_draw)
    filter_curves_func = bpy.props.EnumProperty(
        items=[("RMS", "RMS", "RMS between the two conditions", 1), ("SumAbs", "SumAbs", "Sum of the abs values", 2)],
        description="Filtering function", update=filter_draw)
    objects_show_hide_lh = bpy.props.BoolProperty(default=True, description="Show left hemisphere", update=show_hide_lh)
    objects_show_hide_rh = bpy.props.BoolProperty(default=True, description="Show right hemisphere",
                                                  update=show_hide_rh)
    objects_show_hide_sub_cortical = bpy.props.BoolProperty(default=True, description="Show sub cortical",
                                                            update=show_hide_sub_cortical)
    appearance_show_electrodes_layer = bpy.props.BoolProperty(default=False, description="Show electrodes",
                                                              get=get_appearance_show_electrodes_layer,
                                                              set=set_appearance_show_electrodes_layer)
    appearance_show_ROIs_layer = bpy.props.BoolProperty(default=True, description="Show ROIs",
                                                        get=get_appearance_show_rois_layer,
                                                        set=set_appearance_show_rois_layer)
    appearance_show_activity_layer = bpy.props.BoolProperty(default=False, description="Show activity maps",
                                                            get=get_appearance_show_activity_layer,
                                                            set=set_appearance_show_activity_layer)
    appearance_show_connections_layer = bpy.props.BoolProperty(default=False, description="Show connectivity",
                                                            get=get_appearance_show_connections_layer,
                                                            set=set_appearance_show_connections_layer)

    filter_view_type = bpy.props.EnumProperty(
        items=[('1', "Rendered Brain", ""), ('2', " Solid Brain", "")], description="Brain appearance",
        get=get_filter_view_type, set=set_filter_view_type)
    appearance_solid_slider = bpy.props.FloatProperty(default=0.0, min=0, max=1, description="", update=appearance_draw)
    appearance_depth_slider = bpy.props.IntProperty(default=1, min=1, max=10, description="")
    appearance_depth_Bool = bpy.props.BoolProperty(default=False, description="")
    coloring_fmri = bpy.props.BoolProperty(default=True, description="Plot FMRI")
    coloring_electrodes = bpy.props.BoolProperty(default=False, description="Plot Deep electrodes")
    coloring_threshold = bpy.props.FloatProperty(default=0.5, min=0, description="")
    where_am_i_str = ''
    where_am_i = bpy.props.StringProperty(description="Find closest curve to cursor", update=where_i_am_draw)
    output_path = bpy.props.StringProperty(name="Output Path", default="",
                                           description="Define the path for the output files", subtype='DIR_PATH')
    X_rotation = bpy.props.FloatProperty(default=0, min=-360, max=360, description="Camera rotation around x axis",
                                         update=update_rotation)
    Y_rotation = bpy.props.FloatProperty(default=0, min=-360, max=360, description="Camera rotation around y axis",
                                         update=update_rotation)
    Z_rotation = bpy.props.FloatProperty(default=0, min=-360, max=360, description="Camera rotation around z axis",
                                         update=update_rotation)
    quality = bpy.props.FloatProperty(default=20, min=1, max=100, description="quality of figure in parentage",
                                      update=update_quality)
    smooth_figure = bpy.props.BoolProperty(name='smooth image', description="This significantly affect rendering speed")


def register():
    tmp = helper_class()
    bpy.types.Scene.conf_path = tmp.conf_path
    bpy.types.Scene.brain_imported = tmp.brain_imported
    bpy.types.Scene.electrodes_imported = tmp.electrodes_imported
    bpy.types.Scene.brain_data_exist = tmp.brain_data_exist
    bpy.types.Scene.electrodes_data_exist = tmp.electrodes_data_exist
    bpy.types.Scene.closest_curve_str = tmp.closest_curve_str
    bpy.types.Scene.filter_is_on = tmp.filter_is_on
    # files_names = {'MEG': 'labels_data_', 'Electrodes': 'electrodes_data.npz'}
    bpy.types.Scene.closest_curve = tmp.closest_curve
    bpy.types.Scene.filter_topK = tmp.filter_topK
    bpy.types.Scene.filter_topK = tmp.filter_topK
    bpy.types.Scene.filter_from = tmp.filter_from
    bpy.types.Scene.filter_to = tmp.filter_to
    bpy.types.Scene.filter_curves_type = tmp.filter_curves_type
    bpy.types.Scene.filter_curves_func = tmp.filter_curves_func
    bpy.types.Scene.objects_show_hide_lh = tmp.objects_show_hide_lh
    bpy.types.Scene.objects_show_hide_rh = tmp.objects_show_hide_rh
    bpy.types.Scene.objects_show_hide_sub_cortical = tmp.objects_show_hide_sub_cortical
    bpy.types.Scene.appearance_show_electrodes_layer = tmp.appearance_show_electrodes_layer
    bpy.types.Scene.appearance_show_ROIs_layer = tmp.appearance_show_ROIs_layer
    bpy.types.Scene.appearance_show_activity_layer = tmp.appearance_show_activity_layer
    bpy.types.Scene.appearance_show_connections_layer = tmp.appearance_show_connections
    bpy.types.Scene.filter_view_type = tmp.filter_view_type
    bpy.types.Scene.appearance_solid_slider = tmp.appearance_solid_slider
    bpy.types.Scene.appearance_depth_slider = tmp.appearance_depth_slider
    bpy.types.Scene.appearance_depth_Bool = tmp.appearance_depth_Bool
    bpy.types.Scene.coloring_fmri = tmp.coloring_fmri
    bpy.types.Scene.coloring_electrodes = tmp.coloring_electrodes
    bpy.types.Scene.coloring_threshold = tmp.coloring_threshold
    bpy.types.Scene.where_am_i_str = tmp.where_am_i_str
    bpy.types.Scene.X_rotation = tmp.X_rotation
    bpy.types.Scene.Y_rotation = tmp.Y_rotation
    bpy.types.Scene.Z_rotation = tmp.Z_rotation
    bpy.types.Scene.quality = tmp.quality
    bpy.types.Scene.smooth_figure = tmp.smooth_figure


def main():
    bpy.context.scene.appearance_show_electrodes_layer = False
    bpy.context.scene.appearance_show_activity_layer = False
    bpy.context.scene.appearance_show_ROIs_layer = True
    bpy.context.scene.appearance_show_connections_layer = False

    setup_layers()
    try:
        # mmvt_utils.insert_external_path()
        current_module = sys.modules[__name__]
        connections_panel.init(current_module)
        play_panel.init(current_module)
        bpy.utils.register_class(UpdateAppearance)
        bpy.utils.register_class(SelectAllRois)
        bpy.utils.register_class(SelectAllSubcorticals)
        bpy.utils.register_class(SelectAllElectrodes)
        bpy.utils.register_class(SelectAllConnections)
        bpy.utils.register_class(ClearSelection)
        bpy.utils.register_class(FitSelection)
        bpy.utils.register_class(Filtering)
        bpy.utils.register_class(FindCurveClosestToCursor)
        bpy.utils.register_class(GrabFromFiltering)
        bpy.utils.register_class(GrabToFiltering)
        bpy.utils.register_class(ClearFiltering)
        bpy.utils.register_class(SearchFilter)
        bpy.utils.register_class(SearchClear)
        bpy.utils.register_class(SearchMark)
        bpy.utils.register_class(FreeviewGotoCursor)
        bpy.utils.register_class(FreeviewOpen)
        bpy.utils.register_class(ColorMeg)
        bpy.utils.register_class(ColorMegLabels)
        bpy.utils.register_class(ColorFmri)
        bpy.utils.register_class(ClearColors)
        bpy.utils.register_class(ColorElectrodes)
        bpy.utils.register_class(WhereAmI)
        bpy.utils.register_class(ClearWhereAmI)
        bpy.utils.register_class(CreateVertexData)
        bpy.utils.register_class(ClearVertexData)
        bpy.utils.register_class(AddDataToElectrodes)
        bpy.utils.register_class(AddDataToBrain)
        bpy.utils.register_class(AddDataNoCondsToBrain)
        bpy.utils.register_class(ImportElectrodes)
        bpy.utils.register_class(ImportBrain)
        bpy.utils.register_class(ImportRoisClass)
        bpy.utils.register_class(RenderFigure)

        bpy.utils.register_class(AppearanceMakerPanel)
        bpy.utils.register_class(TransparencyPanel)
        bpy.utils.register_class(ShowHideObjectsPanel)
        bpy.utils.register_class(SelectionMakerPanel)
        bpy.utils.register_class(FilteringMakerPanel)
        bpy.utils.register_class(ColoringMakerPanel)
        bpy.utils.register_class(WhereAmIMakerPanel)
        bpy.utils.register_class(DataInVertMakerPanel)
        bpy.utils.register_class(DataMakerPanel)
        bpy.utils.register_class(RenderingMakerPanel)
        bpy.utils.register_class(SearchPanel)
        bpy.utils.register_class(FreeviewPanel)
    except:
        print('The classes are already registered!')
        print(traceback.format_exc())


if __name__ == "__main__":
    main()

# ###############################################################
