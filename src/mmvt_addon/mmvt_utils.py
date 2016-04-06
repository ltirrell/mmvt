import bpy
import traceback
import math
import mathutils
import numpy as np
import sys
import os
import os.path as op
import uuid
from collections import OrderedDict
import time
import subprocess
from subprocess import Popen, PIPE, STDOUT
from multiprocessing.connection import Client
import threading
from queue import Queue
import cProfile
from itertools import chain
from sys import platform as _platform

IS_LINUX = _platform == "linux" or _platform == "linux2"
IS_MAC = _platform == "darwin"
IS_WINDOWS = _platform == "win32"
print('platform: {}'.format(_platform))

HEMIS = ['rh', 'lh']
OBJ_TYPE_CORTEX_RH, OBJ_TYPE_CORTEX_LH, OBJ_TYPE_SUBCORTEX, OBJ_TYPE_ELECTRODE = range(4)
# IS_WINDOWS = (os.name == 'nt')

try:
    import cPickle as pickle
except:
    import pickle

import re
floats_const_pattern = r"""
     [-+]?
     (?: \d* \. \d+ )
     """
floats_pattern_rx = re.compile(floats_const_pattern, re.VERBOSE)

numeric_const_pattern = r"""
     [-+]? # optional sign
     (?:
         (?: \d* \. \d+ ) # .1 .12 .123 etc 9.1 etc 98.1 etc
         |
         (?: \d+ \.? ) # 1. 12. 123. etc 1 12 123 etc
     )
     # followed by optional exponent part if desired
     (?: [Ee] [+-]? \d+ ) ?
     """
numeric_pattern_rx = re.compile(numeric_const_pattern, re.VERBOSE)


def read_floats_rx(str):
    return floats_pattern_rx.findall(str)


def read_numbers_rx(str):
    return numeric_pattern_rx.findall(str)


def is_mac():
    return IS_MAC


def is_windows():
    return IS_WINDOWS


def is_linux():
    return IS_LINUX


def namebase(file_name):
    return op.splitext(op.basename(file_name))[0]


def save(obj, fname):
    with open(fname, 'wb') as fp:
        pickle.dump(obj, fp, protocol=4)


def load(fname):
    with open(fname, 'rb') as fp:
        obj = pickle.load(fp)
    return obj


class Bag( dict ):
    """ a dict with d.key short for d["key"]
        d = Bag( k=v ... / **dict / dict.items() / [(k,v) ...] )  just like dict
    """
        # aka Dotdict

    def __init__(self, *args, **kwargs):
        dict.__init__( self, *args, **kwargs )
        self.__dict__ = self

    def __getnewargs__(self):  # for cPickle.dump( d, file, protocol=-1)
        return tuple(self)


def add_keyframe(parent_obj, conn_name, value, T):
    try:
        insert_keyframe_to_custom_prop(parent_obj, conn_name, 0, 0)
        insert_keyframe_to_custom_prop(parent_obj, conn_name, value, 1)
        insert_keyframe_to_custom_prop(parent_obj, conn_name, value, T)
        insert_keyframe_to_custom_prop(parent_obj, conn_name, 0, T + 1)
        # print('insert keyframe with value of {}'.format(value))
    except:
        print("Can't add a keyframe! {}, {}, {}".format(parent_obj, conn_name, value))
        print(traceback.format_exc())


def insert_keyframe_to_custom_prop(obj, prop_name, value, keyframe):
    bpy.context.scene.objects.active = obj
    obj.select = True
    obj[prop_name] = value
    obj.keyframe_insert(data_path='[' + '"' + prop_name + '"' + ']', frame=keyframe)


def create_and_set_material(obj):
    # curMat = bpy.data.materials['OrigPatchesMat'].copy()
    if obj.active_material is None or obj.active_material.name != obj.name + '_Mat':
        if obj.name + '_Mat' in bpy.data.materials:
            cur_mat = bpy.data.materials[obj.name + '_Mat']
        else:
            cur_mat = bpy.data.materials['Deep_electrode_mat'].copy()
            cur_mat.name = obj.name + '_Mat'
        # Wasn't it originally (0, 0, 1, 1)?
        cur_mat.node_tree.nodes["RGB"].outputs[0].default_value = (0, 0, 1, 1) # (0, 1, 0, 1)
        obj.active_material = cur_mat


def mark_objects(objs_names):
    for obj_name in objs_names:
        if bpy.data.objects.get(obj_name):
            bpy.data.objects[obj_name].active_material = bpy.data.materials['selected_label_Mat']


def cylinder_between(p1, p2, r, layers_array):
    # From http://blender.stackexchange.com/questions/5898/how-can-i-create-a-cylinder-linking-two-points-with-python
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    dx = x2 - x1
    dy = y2 - y1
    dz = z2 - z1
    dist = math.sqrt(dx**2 + dy**2 + dz**2)

    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=dist, location=(dx/2 + x1, dy/2 + y1, dz/2 + z1))#, layers=layers_array)

    phi = math.atan2(dy, dx)
    theta = math.acos(dz/dist)
    bpy.context.object.rotation_euler[1] = theta
    bpy.context.object.rotation_euler[2] = phi
    bpy.ops.object.move_to_layer(layers=layers_array)


def create_empty_if_doesnt_exists(name, brain_layer, layers_array=None, root_fol='Brain'):
    if not bpy.data.objects.get(root_fol):
        print('root fol, {}, does not exist'.format(root_fol))
        return
    if layers_array is None:
        # layers_array = bpy.context.scene.layers
        layers_array = [False] * 20
        layers_array[brain_layer] = True
    if bpy.data.objects.get(name) is None:
        # layers_array[brain_layer] = True
        bpy.ops.object.empty_add(type='PLAIN_AXES', radius=1, view_align=False, location=(0, 0, 0), layers=layers_array)
        bpy.ops.object.move_to_layer(layers=layers_array)
        bpy.data.objects['Empty'].name = name
        if name != root_fol:
            bpy.data.objects[name].parent = bpy.data.objects[root_fol]


def select_hierarchy(obj, val=True, select_parent=True):
    if bpy.data.objects.get(obj) is not None:
        bpy.data.objects[obj].select = select_parent
        for child in bpy.data.objects[obj].children:
            child.select = val


def create_material(name, diffuseColors, transparency, copy_material=True):
    curMat = bpy.context.active_object.active_material
    if copy_material or 'MyColor' not in curMat.node_tree.nodes:
        #curMat = bpy.data.materials['OrigPatchesMat'].copy()
        curMat = bpy.data.materials['OrigPatchMatTwoCols'].copy()
        curMat.name = name
        bpy.context.active_object.active_material = curMat
    curMat.node_tree.nodes['MyColor'].inputs[0].default_value = diffuseColors
    curMat.node_tree.nodes['MyColor1'].inputs[0].default_value = diffuseColors
    curMat.node_tree.nodes['MyTransparency'].inputs['Fac'].default_value = transparency
    bpy.context.active_object.active_material.diffuse_color = diffuseColors[:3]


def delete_hierarchy(parent_obj_name, exceptions=(), delete_only_animation=False):
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects.get(parent_obj_name)
    if obj is None:
        return
    obj.animation_data_clear()
    # Go over all the objects in the hierarchy like @zeffi suggested:
    names = set()
    def get_child_names(obj):
        for child in obj.children:
            names.add(child.name)
            if child.children:
                get_child_names(child)

    get_child_names(obj)
    names = names - set(exceptions)
    # Remove the animation from the all the child objects
    for child_name in names:
        bpy.data.objects[child_name].animation_data_clear()

    bpy.context.scene.objects.active = obj
    if not delete_only_animation:
        objects = bpy.data.objects
        [setattr(objects[n], 'select', True) for n in names]
        result = bpy.ops.object.delete()
        if result == {'FINISHED'}:
            print ("Successfully deleted object")
        else:
            print ("Could not delete object")


def get_user():
    return namebase(bpy.data.filepath).split('_')[0]


def get_atlas(default='laus250'):
    name_split = namebase(bpy.data.filepath).split('_')
    if len(name_split) > 1:
        return name_split[1]
    else:
        return default


def get_user_fol():
    root_fol = bpy.path.abspath('//')
    user = get_user()
    return op.join(root_fol, user)


def view_all_in_graph_editor(context):
    graph_area = [context.screen.areas[k] for k in range(len(context.screen.areas)) if
                  context.screen.areas[k].type == 'GRAPH_EDITOR'][0]
    graph_window_region = [graph_area.regions[k] for k in range(len(graph_area.regions)) if
                           graph_area.regions[k].type == 'WINDOW'][0]

    c = context.copy()  # copy the context
    c['area'] = graph_area
    c['region'] = graph_window_region
    bpy.ops.graph.view_all(c)


def show_hide_hierarchy(val, obj, also_parent=False):
    if bpy.data.objects.get(obj) is not None:
        if also_parent:
            bpy.data.objects[obj].hide_render = not val
        for child in bpy.data.objects[obj].children:
            child.hide = not val
            child.hide_render = not val
            child.select = val


def rand_letters(num):
    return str(uuid.uuid4())[:num]


def evaluate_fcurves(parent_obj, time_range):
    data = OrderedDict()
    colors = OrderedDict()
    for fcurve in parent_obj.animation_data.action.fcurves:
        if fcurve.hide:
            continue
        name = fcurve.data_path.split('"')[1]
        print('{} extrapolation'.format(name))
        for kf in fcurve.keyframe_points:
            kf.interpolation = 'BEZIER'
        data[name] = []
        for t in time_range:
            d = fcurve.evaluate(t)
            data[name].append(d)
        colors[name] = tuple(fcurve.color)
    return data, colors


def get_fcurve_current_frame_val(parent_obj_name, obj_name, cur_frame):
    for fcurve in bpy.data.objects[parent_obj_name].animation_data.action.fcurves:
        name = fcurve_name(fcurve)
        if name == obj_name:
            return fcurve.evaluate(cur_frame)


def fcurve_name(fcurve):
    return fcurve.data_path.split('"')[1]


def show_only_selected_fcurves(context):
    space = context.space_data
    dopesheet = space.dopesheet
    dopesheet.show_only_selected = True


def get_fcurve_values(parent_name, fcurve_name):
    xs, ys = [], []
    parent_obj = bpy.data.objects[parent_name]
    for fcurve in parent_obj.animation_data.action.fcurves:
        if fcurve_name(fcurve) == fcurve_name:
            for kp in fcurve.keyframe_points:
                xs.append(kp.co[0])
                ys.append(kp.co[1])
    return xs, ys


def time_to_go(now, run, runs_num, runs_num_to_print=10):
    if run % runs_num_to_print == 0 and run != 0:
        time_took = time.time() - now
        more_time = time_took / run * (runs_num - run)
        print('{}/{}, {:.2f}s, {:.2f}s to go!'.format(run, runs_num, time_took, more_time))


def show_hide_obj_and_fcurves(objs, val):
    for obj in objs:
        obj.select = val
        if obj.animation_data:
            for fcurve in obj.animation_data.action.fcurves:
                if val:
                    fcurve.hide = not val
                    fcurve.hide = not val
                fcurve.select = val
        else:
            pass
            # print('No animation in {}'.format(obj.name))


def message(self, message):
    # todo: Find how to send messaages without the self
    if self:
        self.report({'ERROR'}, message)
    else:
        print(message)


def show_only_group_objects(context, objects, group_name):
    space = context.space_data
    dopesheet = space.dopesheet
    selected_group = bpy.data.groups.get(group_name, bpy.data.groups.new(group_name))
    for obj in objects:
        selected_group.objects.link(obj)
    dopesheet.filter_group = selected_group
    dopesheet.show_only_group_objects = True


def create_sphere(loc, rad, my_layers, name):
    bpy.ops.mesh.primitive_uv_sphere_add(
        ring_count=30, size=rad, view_align=False, enter_editmode=False, location=loc, layers=my_layers)
    bpy.ops.object.shade_smooth()
    bpy.context.active_object.name = name


def create_spline(points, layers_array, bevel_depth=0.045, resolution_u=5):
    # points = [ [1,1,1], [-1,1,1], [-1,-1,1], [1,-1,-1] ]
    curvedata = bpy.data.curves.new(name="Curve", type='CURVE')
    curvedata.dimensions = '3D'
    curvedata.fill_mode = 'FULL'
    curvedata.bevel_depth = bevel_depth
    ob = bpy.data.objects.new("CurveObj", curvedata)
    bpy.context.scene.objects.link(ob)

    spline = curvedata.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for num in range(len(spline.bezier_points)):
        spline.bezier_points[num].co = points[num]
        spline.bezier_points[num].handle_right_type = 'AUTO'
        spline.bezier_points[num].handle_left_type = 'AUTO'
    spline.resolution_u = resolution_u
    #spline.order_u = 6
    #spline.use_bezier_u = True
    #spline.radius_interpolation = 'BSPLINE'
    #print(spline.type)
    #spline.use_smooth = True
    bpy.ops.object.move_to_layer(layers=layers_array)
    return ob


def get_subfolders(fol):
    return [os.path.join(fol,subfol) for subfol in os.listdir(fol) if os.path.isdir(os.path.join(fol,subfol))]


def hemi_files_exists(fname):
    return os.path.isfile(fname.format(hemi='rh')) and \
           os.path.isfile(fname.format(hemi='lh'))


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    # http://stackoverflow.com/questions/5967500/how-to-correctly-sort-a-string-with-a-number-inside
    import re
    return [ atoi(c) for c in re.split('(\d+)', text) ]


def elec_group_number(elec_name, bipolar=False):
    if bipolar:
        elec_name2, elec_name1 = elec_name.split('-')
        group, num1 = elec_group_number(elec_name1, False)
        _, num2 = elec_group_number(elec_name2, False)
        return group, (num1, num2)
    else:
        ind = np.where([int(s.isdigit()) for s in elec_name])[-1][0]
        num = int(elec_name[ind:])
        group = elec_name[:ind]
        return group, num


def elec_group(elec_name, bipolar):
    if bipolar:
        group, _, _ = elec_group_number(elec_name, bipolar)
    else:
        group, _ = elec_group_number(elec_name, bipolar)
    return group



def csv_file_reader(csv_fname, delimiter=','):
    import csv
    with open(csv_fname, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=delimiter)
        for row in reader:
            yield [val.strip() for val in row]


def check_obj_type(obj_name):
    obj = bpy.data.objects.get(obj_name, None)
    if obj is None:
        obj_type = None
    elif obj.parent == bpy.data.objects['Cortex-lh']:
        obj_type = OBJ_TYPE_CORTEX_LH
    elif obj.parent == bpy.data.objects['Cortex-rh']:
        obj_type = OBJ_TYPE_CORTEX_RH
    elif obj.parent == bpy.data.objects['Subcortical_structures']:
        obj_type = OBJ_TYPE_SUBCORTEX
    elif obj.parent == bpy.data.objects['Deep_electrodes']:
        obj_type = OBJ_TYPE_ELECTRODE
    else:
        obj_type = None
    return obj_type


def get_obj_hemi(obj_name):
    obj_type = check_obj_type(obj_name)
    if obj_type == OBJ_TYPE_CORTEX_LH:
        hemi = 'lh'
    elif obj_type == OBJ_TYPE_CORTEX_RH:
        hemi = 'rh'
    else:
        hemi = None
    return hemi


def run_command_in_new_thread(cmd, shell=True):
    q_in, q_out = Queue(), Queue()
    thread = threading.Thread(target=run_command_and_read_queue, args=(cmd, q_in, q_out, shell))
    print('start!')
    thread.start()
    return q_in, q_out


def run_command_and_read_queue(cmd, q_in, q_out, shell=True):

    def write_to_stdin(proc, q_in):
        while True:
            # Get some data
            data = q_in.get()
            try:
                print('Writing data into stdin: {}'.format(data))
                output = proc.stdin.write(data.decode('utf-8'))
                proc.stdin.flush()
                print('stdin output: {}'.format(output))
            except:
                print("Pipe is close, can't write to stdin")

    def read_from_stdout(proc, q_out):
        while True:
            line = proc.stdout.readline()
            if line != b'':
                q_out.put(line)
                print('stdout: {}'.format(line))

    def read_from_stderr(proc):
        while True:
            line = proc.stderr.readline()
            if line != b'':
                print('stderr: {}'.format(line))

    p = Popen(cmd, shell=shell, stdout=PIPE, stdin=PIPE, stderr=PIPE, bufsize=1) #, universal_newlines=True)
    thread_write_to_stdin = threading.Thread(target=write_to_stdin, args=(p, q_in,))
    thread_read_from_stdout = threading.Thread(target=read_from_stdout, args=(p, q_out,))
    thread_read_from_stderr = threading.Thread(target=read_from_stderr, args=(p, ))
    thread_write_to_stdin.start()
    thread_read_from_stdout.start()
    thread_read_from_stderr.start()


def run_command(cmd, shell=True, pipe=False):
    # global p
    from subprocess import Popen, PIPE, STDOUT
    print('run: {}'.format(cmd))
    if (IS_WINDOWS):
        os.system(cmd)
        return None
    else:
        if pipe:
            p = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        else:
            p = subprocess.call(cmd, shell=shell)
        # p = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        # p.stdin.write(b'-zoom 2\n')
        return p


# class Unbuffered(object):
#    def __init__(self, stream):
#        self.stream = stream
#    def write(self, data):
#        self.stream.write(data)
#        self.stream.flush()
#    def __getattr__(self, attr):
#        return getattr(self.stream, attr)
#
# import sys
# sys.stdout = Unbuffered(sys.stdout)


def make_dir(fol):
    if not os.path.isdir(fol):
        os.makedirs(fol)
    return fol


def profileit(sort_field='cumtime'):
    """
    Parameters
    ----------
    prof_fname
        profile output file name
    sort_field
        "calls"     : (((1,-1),              ), "call count"),
        "ncalls"    : (((1,-1),              ), "call count"),
        "cumtime"   : (((3,-1),              ), "cumulative time"),
        "cumulative": (((3,-1),              ), "cumulative time"),
        "file"      : (((4, 1),              ), "file name"),
        "filename"  : (((4, 1),              ), "file name"),
        "line"      : (((5, 1),              ), "line number"),
        "module"    : (((4, 1),              ), "file name"),
        "name"      : (((6, 1),              ), "function name"),
        "nfl"       : (((6, 1),(4, 1),(5, 1),), "name/file/line"),
        "pcalls"    : (((0,-1),              ), "primitive call count"),
        "stdname"   : (((7, 1),              ), "standard name"),
        "time"      : (((2,-1),              ), "internal time"),
        "tottime"   : (((2,-1),              ), "internal time"),
    Returns
    -------
    None

    """

    def actual_profileit(func):
        def wrapper(*args, **kwargs):
            prof = cProfile.Profile()
            retval = prof.runcall(func, *args, **kwargs)
            make_dir(op.join(get_user_fol(), 'profileit'))
            prof_fname = op.join(get_user_fol(), 'profileit', func.__name__)
            stat_fname = '{}.stat'.format(prof_fname)
            prof.dump_stats(prof_fname)
            print_profiler(prof_fname, stat_fname, sort_field)
            print('dump stat in {}'.format(stat_fname))
            return retval
        return wrapper
    return actual_profileit


def print_profiler(profile_input_fname, profile_output_fname, sort_field='cumtime'):
    import pstats
    with open(profile_output_fname, 'w') as f:
        stats = pstats.Stats(profile_input_fname, stream=f)
        stats.sort_stats(sort_field)
        stats.print_stats()


def timeit(func):
    def wrapper(*args, **kwargs):
        now = time.time()
        retval = func(*args, **kwargs)
        print('{} took {:.2f}s'.format(func.__name__, time.time() - now))
        return retval

    return wrapper


def dump_args(func):
    # Decorator to print function call details - parameters names and effective values
    # http://stackoverflow.com/a/25206079/1060738
    def wrapper(*func_args, **func_kwargs):
        arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]
        args = func_args[:len(arg_names)]
        defaults = func.__defaults__ or ()
        args = args + defaults[len(defaults) - (func.__code__.co_argcount - len(args)):]
        params = list(zip(arg_names, args))
        args = func_args[len(arg_names):]
        if args: params.append(('args', args))
        if func_kwargs: params.append(('kwargs', func_kwargs))
        print(func.__name__ + ' (' + ', '.join('%s = %r' % p for p in params) + ' )')
        return func(*func_args, **func_kwargs)
    return wrapper


def get_all_children(parents):
    return list(chain.from_iterable([obj for obj in [bpy.data.objects[parent].children for parent in parents]]))


def get_non_functional_objects():
    return get_all_children((['Cortex-lh', 'Cortex-rh', 'Subcortical_structures', 'Deep_electrodes']))


def add_box_line(col, text1, text2='', percentage=0.3, align=True):
    row = col.split(percentage=percentage, align=align)
    row.label(text=text1)
    if text2 != '':
        row.label(text=text2)


def current_path():
    return os.path.dirname(os.path.realpath(__file__))


def get_parent_fol():
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.split(curr_dir)[0]


def get_mmvt_root():
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.dirname(os.path.split(curr_dir)[0])


def change_fol_to_mmvt_root():
    os.chdir(get_mmvt_root())


class connection_to_listener(object):
    # http://stackoverflow.com/a/6921402/1060738

    conn = None
    handle_is_open = False

    @staticmethod
    def check_if_open():
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(('localhost', 6000))

        if result == 0:
            print('socket is open')
        s.close()

    def init(self):
        try:
            connection_to_listener.check_if_open()
            # connection_to_listener.run_addon_listener()
            address = ('localhost', 6000)
            self.conn = Client(address, authkey=b'mmvt')
            self.handle_is_open = True
            return True
        except:
            print('Error in connection_to_listener.init()!')
            print(traceback.format_exc())
            return False

    @staticmethod
    def run_addon_listener():
        cmd = 'python {}'.format(op.join(current_path(), 'addon_listener.py'))
        print('Running {}'.format(cmd))
        run_command_in_new_thread(cmd, shell=True)
        time.sleep(1)

    def send_command(self, cmd):
        if self.handle_is_open:
            self.conn.send(cmd)
            return True
        else:
            # print('Handle is close')
            return False

    def close(self):
        self.send_command('close\n')
        self.conn.close()
        self.handle_is_open = False

conn_to_listener = connection_to_listener()


def min_cdist_from_obj(obj, Y):
    vertices = obj.data.vertices
    kd = mathutils.kdtree.KDTree(len(vertices))
    for ind, x in enumerate(vertices):
        kd.insert(x.co, ind)
    kd.balance()
    # Find the closest point to the 3d cursor
    res = []
    for y in Y:
        res.append(kd.find_n(y, 1)[0])
    # co, index, dist
    return res


def min_cdist(X, Y):
    kd = mathutils.kdtree.KDTree(X.shape[0])
    for ind, x in enumerate(X):
        kd.insert(x, ind)
    kd.balance()
    # Find the closest point to the 3d cursor
    res = []
    for y in Y:
        res.append(kd.find_n(y, 1)[0])
    # co, index, dist
    return res


# def cdist(x, y):
#     return np.sqrt(np.dot(x, x) - 2 * np.dot(x, y) + np.dot(y, y))


# Warning! This method is really slow, ~3s per hemi
def obj_has_activity(obj):
    activity = False
    for mesh_loop_color_layer_data in obj.data.vertex_colors.active.data:
        if tuple(mesh_loop_color_layer_data.color) != (1, 1, 1):
            activity = True
            break
    return activity


def other_hemi(hemi):
    return 'lh' if hemi == 'rh' else 'rh'


# http://blender.stackexchange.com/a/30739/16364
def show_progress(job_name):
    sys.stdout.write('{}: '.format(job_name))
    sys.stdout.flush()
    some_list = [0] * 100
    for idx, item in enumerate(some_list):
        msg = "item %i of %i" % (idx, len(some_list)-1)
        sys.stdout.write(msg + chr(8) * len(msg))
        sys.stdout.flush()
        time.sleep(0.02)

    sys.stdout.write("DONE" + " "*len(msg)+"\n")
    sys.stdout.flush()


def update_progress(job_title, progress):
    length = 20 # modify this to change the length
    block = int(round(length*progress))
    msg = "\r{0}: [{1}] {2}%".format(job_title, "#"*block + "-"*(length-block), round(progress*100, 2))
    if progress >= 1: msg += " DONE\r\n"
    sys.stdout.write(msg)
    sys.stdout.flush()

    def test():
        for i in range(100):
            time.sleep(0.1)
            update_progress("Some job", i / 100.0)
        update_progress("Some job", 1)

