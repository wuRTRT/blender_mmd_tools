# -*- coding: utf-8 -*-

from typing import Any, Set, Union

import bpy

from . import bone, camera, material, rigid_body, root

__properties = {
    bpy.types.Object: {
        'mmd_type': bpy.props.EnumProperty(
            name='Type',
            description='Internal MMD type of this object (DO NOT CHANGE IT DIRECTLY)',
            default='NONE',
            items=[
                ('NONE', 'None', '', 1),
                ('ROOT', 'Root', '', 2),
                ('RIGID_GRP_OBJ', 'Rigid Body Grp Empty', '', 3),
                ('JOINT_GRP_OBJ', 'Joint Grp Empty', '', 4),
                ('TEMPORARY_GRP_OBJ', 'Temporary Grp Empty', '', 5),
                ('PLACEHOLDER', 'Place Holder', '', 6),

                ('CAMERA', 'Camera', '', 21),
                ('JOINT', 'Joint', '', 22),
                ('RIGID_BODY', 'Rigid body', '', 23),
                ('LIGHT', 'Light', '', 24),

                ('TRACK_TARGET', 'Track Target', '', 51),
                ('NON_COLLISION_CONSTRAINT', 'Non Collision Constraint', '', 52),
                ('SPRING_CONSTRAINT', 'Spring Constraint', '', 53),
                ('SPRING_GOAL', 'Spring Goal', '', 54),
            ]
        ),
        'mmd_root': bpy.props.PointerProperty(type=root.MMDRoot),
        'mmd_camera': bpy.props.PointerProperty(type=camera.MMDCamera),
        'mmd_rigid': bpy.props.PointerProperty(type=rigid_body.MMDRigidBody),
        'mmd_joint': bpy.props.PointerProperty(type=rigid_body.MMDJoint),
    },
    bpy.types.Material: {
        'mmd_material': bpy.props.PointerProperty(type=material.MMDMaterial),
    },
    bpy.types.PoseBone: {
        'mmd_bone': bpy.props.PointerProperty(type=bone.MMDBone),
        'is_mmd_shadow_bone': bpy.props.BoolProperty(name='is_mmd_shadow_bone', default=False),
        'mmd_shadow_bone_type': bpy.props.StringProperty(name='mmd_shadow_bone_type'),
        'mmd_ik_toggle': bone._MMDPoseBoneProp.mmd_ik_toggle,
    }
}


def __set_hide(prop, value):
    prop.hide_set(value)
    if getattr(prop, 'hide_viewport'):
        setattr(prop, 'hide_viewport', False)


def __patch(properties):  # temporary patching, should be removed in the future
    prop_obj = properties.setdefault(bpy.types.Object, {})

    prop_obj['select'] = bpy.props.BoolProperty(
        get=lambda prop: prop.select_get(),
        set=lambda prop, value: prop.select_set(value),
        options={'SKIP_SAVE', 'ANIMATABLE', 'LIBRARY_EDITABLE', },
    )
    prop_obj['hide'] = bpy.props.BoolProperty(
        get=lambda prop: prop.hide_get(),
        set=__set_hide,
        options={'SKIP_SAVE', 'ANIMATABLE', 'LIBRARY_EDITABLE', },
    )


if bpy.app.version >= (2, 80, 0):
    __patch(__properties)


def assign_group(destination: bpy.types.PropertyGroup, source: bpy.types.PropertyGroup, merge: bool = False):
    for name in source.keys():
        value = getattr(source, name)
        if isinstance(value, bpy.types.PropertyGroup):
            assign_group(getattr(destination, name), value, merge=merge)
        elif isinstance(value, bpy.types.bpy_prop_collection):
            assign_collection(getattr(destination, name), value, merge=merge)
        else:
            setattr(destination, name, value)


def assign_collection(destination: bpy.types.bpy_prop_collection, source: bpy.types.bpy_prop_collection, merge: bool = False):
    if not merge:
        destination.clear()

    destination_names: Set[str] = set(destination.keys())
    source_names: Set[str] = set(source.keys())

    # remove extras
    for name in destination_names - source_names:
        destination.remove(destination.find(name))

    missing_names = source_names - destination_names

    destination_index = 0
    for name, value in source.items():
        if name in missing_names:
            new_element = destination.add()
            setattr(new_element, 'name', name)

        assign(destination[name], value, merge=merge)
        destination.move(destination.find(name), destination_index)
        destination_index += 1


def assign(destination: Union[bpy.types.PropertyGroup, bpy.types.bpy_prop_collection], source: Union[bpy.types.PropertyGroup, bpy.types.bpy_prop_collection], merge: bool = False):
    if isinstance(destination, bpy.types.PropertyGroup):
        assign_group(destination, source, merge=merge)
    elif isinstance(destination, bpy.types.bpy_prop_collection):
        assign_collection(destination, source, merge=merge)
    else:
        raise ValueError(f'Unsupported destination: {destination}')


def register():
    for typ, t in __properties.items():
        for attr, prop in t.items():
            if hasattr(typ, attr):
                print(' * warning: overwrite ', typ, attr)
            setattr(typ, attr, prop)


def unregister():
    for typ, t in __properties.items():
        for attr in t.keys():
            if hasattr(typ, attr):
                delattr(typ, attr)
