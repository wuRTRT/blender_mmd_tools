# -*- coding: utf-8 -*-

from enum import Enum
from typing import Set

import bpy
from mmd_tools import register_wrap
from mmd_tools.core.model import FnModel
from mmd_tools.translations import DictionaryEnum


class MMDDataType(Enum):
    BONE = 'Bones'
    MORPH = 'Morphs'
    MATERIAL = 'Materials'
    DISPLAY = 'Display'
    PHYSICS = 'Physics'
    INFO = 'Information'


MMD_DATA_TYPE_ENUM_ITEMS = [
    (MMDDataType.BONE.name, MMDDataType.BONE.value, 'Bones', 1),
    (MMDDataType.MORPH.name, MMDDataType.MORPH.value, 'Morphs', 2),
    (MMDDataType.MATERIAL.name, MMDDataType.MATERIAL.value, 'Materials', 4),
    (MMDDataType.DISPLAY.name, MMDDataType.DISPLAY.value, 'Display frames', 8),
    (MMDDataType.PHYSICS.name, MMDDataType.PHYSICS.value, 'Rigidbodies and joints', 16),
    (MMDDataType.INFO.name, MMDDataType.INFO.value, 'Model name and comments', 32),
]


@register_wrap
class MMDDataReference(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    type: bpy.props.EnumProperty(items=MMD_DATA_TYPE_ENUM_ITEMS)
    object: bpy.props.PointerProperty(type=bpy.types.Object)
    data_path: bpy.props.StringProperty(get=lambda self: self.name)


@register_wrap
class MMD_TOOLS_UL_PoseBones(bpy.types.UIList):
    def draw_item(self, context, layout: bpy.types.UILayout, data, mmd_data_ref: MMDDataReference, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        if mmd_data_ref.type == 'BONE':
            pose_bone: bpy.types.PoseBone = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
            row.label(text='', icon='BONE_DATA')
            row.prop(pose_bone, 'name', text='')
            row.prop(pose_bone.mmd_bone, 'name_j', text='')
            row.prop(pose_bone.mmd_bone, 'name_e', text='')
            row.prop(pose_bone.bone, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if pose_bone.bone.select else 'RESTRICT_SELECT_ON')
            row.prop(pose_bone.bone, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if pose_bone.bone.hide else 'HIDE_OFF')

        if mmd_data_ref.type == 'MATERIAL':
            mesh_object: bpy.types.Object = mmd_data_ref.object
            material: bpy.types.Material = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
            row.label(text='', icon='MATERIAL_DATA')
            row.prop(material, 'name', text='')
            row.prop(material.mmd_material, 'name_j', text='')
            row.prop(material.mmd_material, 'name_e', text='')
            row.prop(mesh_object, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if mesh_object.select else 'RESTRICT_SELECT_ON')
            row.prop(mesh_object, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if mesh_object.hide else 'HIDE_OFF')


@register_wrap
class MMDDataQuery(bpy.types.PropertyGroup):
    @staticmethod
    def _update_index(mmd_data_query: 'MMDDataQuery', _context):
        """Display the selected data in the Property Editor"""
        if mmd_data_query.result_data_index < 0:
            return

        mmd_data_ref: MMDDataReference = mmd_data_query.result_data[mmd_data_query.result_data_index]

        if mmd_data_ref.type == MMDDataType.BONE.name:
            mmd_data_ref.id_data.data.bones.active = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path).bone

    @staticmethod
    def _update_query(mmd_data_query: 'MMDDataQuery', _context):
        """Update the data by the query"""

        id_data: bpy.types.Object = mmd_data_query.id_data
        mmd_data_query.result_data.clear()
        mmd_data_query.result_data_index = -1

        filter_japanese_blank: bool = mmd_data_query.filter_japanese_blank
        filter_english_blank: bool = mmd_data_query.filter_english_blank

        filter_selected: bool = mmd_data_query.filter_selected
        filter_visible: bool = mmd_data_query.filter_visible

        if 'BONE' in mmd_data_query.filter_types:
            pose_bone: bpy.types.PoseBone
            for pose_bone in id_data.pose.bones:
                if filter_visible and pose_bone.bone.hide:
                    continue

                if filter_selected and not pose_bone.bone.select:
                    continue

                if filter_japanese_blank and pose_bone.mmd_bone.name_j:
                    continue

                if filter_english_blank and pose_bone.mmd_bone.name_e:
                    continue

                mmd_data_ref: MMDDataReference = mmd_data_query.result_data.add()
                mmd_data_ref.name = f'pose.bones["{pose_bone.name}"]'
                mmd_data_ref.type = 'BONE'
                mmd_data_ref.object = id_data

        if 'MATERIAL' in mmd_data_query.filter_types:
            checked_materials: Set[bpy.types.Material] = set()
            mesh_object: bpy.types.Object
            for mesh_object in FnModel.child_meshes(id_data):
                if filter_visible and mesh_object.hide:
                    continue

                if filter_selected and not mesh_object.select:
                    continue

                material: bpy.types.Material
                for material in mesh_object.data.materials:
                    if material in checked_materials:
                        continue
                    checked_materials.add(material)

                    if filter_japanese_blank and material.mmd_material.name_j:
                        continue

                    if filter_english_blank and material.mmd_material.name_e:
                        continue

                    mmd_data_ref: MMDDataReference = mmd_data_query.result_data.add()
                    mmd_data_ref.name = f'data.materials["{material.name}"]'
                    mmd_data_ref.type = 'MATERIAL'
                    mmd_data_ref.object = mesh_object

    @staticmethod
    def _update_operation_script_preset(mmd_data_query: 'MMDDataQuery', _context):
        if mmd_data_query.operation_script_preset == 'NOTHING':
            return

        if mmd_data_query.operation_script_preset == 'TO_MMD_LR':
            mmd_data_query.operation_script = 'to_mmd_lr(name)'
            return

        if mmd_data_query.operation_script_preset == 'TO_BLENDER_LR':
            mmd_data_query.operation_script = 'to_blender_lr(name)'
            return

    filter_japanese_blank: bpy.props.BoolProperty(name='Japanese Blank', default=False, update=_update_query.__func__)
    filter_english_blank: bpy.props.BoolProperty(name='English Blank', default=False, update=_update_query.__func__)
    filter_selected: bpy.props.BoolProperty(name='Selected', default=False, update=_update_query.__func__)
    filter_visible: bpy.props.BoolProperty(name='Visible', default=False, update=_update_query.__func__)
    filter_types: bpy.props.EnumProperty(
        items=MMD_DATA_TYPE_ENUM_ITEMS,
        default={'BONE', 'MORPH', 'MATERIAL', 'DISPLAY', 'PHYSICS', },
        options={'ENUM_FLAG'},
        update=_update_query.__func__,
    )
    result_data_index: bpy.props.IntProperty(update=_update_index.__func__)
    result_data: bpy.props.CollectionProperty(type=MMDDataReference)

    dictionary = bpy.props.EnumProperty(
        items=DictionaryEnum.get_dictionary_items,
        name='Dictionary',
    )

    operation_target: bpy.props.EnumProperty(
        items=[
            ('BLENDER', 'Blender Name (name)', '', 1),
            ('JAPANESE', 'Japanese Name (name_j)', '', 2),
            ('ENGLISH', 'English Name (name_e)', '', 3),
        ],
        name='Operation Target',
        default='JAPANESE',
    )

    operation_script_preset: bpy.props.EnumProperty(
        items=[
            ('NOTHING', '', '', 1),
            ('TO_MMD_LR', 'Blender L/R to MMD L/R', 'to_mmd_lr(name)', 2),
            ('TO_BLENDER_LR', 'MMD L/R to Blender L/R', 'to_blender_lr(name_j)', 3),
        ],
        name='Operation Script Preset',
        default='NOTHING',
        update=_update_operation_script_preset.__func__,
    )

    operation_script: bpy.props.StringProperty()
