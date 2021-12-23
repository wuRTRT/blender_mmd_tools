# -*- coding: utf-8 -*-

from enum import Enum
from typing import Dict, List, Tuple

import bpy
from mmd_tools import register_wrap
from mmd_tools.core.translations import MMDDataType, FnTranslations
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
    type: bpy.props.EnumProperty(items=MMD_DATA_TYPE_ENUM_ITEMS)
    object: bpy.props.PointerProperty(type=bpy.types.Object)
    data_path: bpy.props.StringProperty()
    name: bpy.props.StringProperty()
    name_j: bpy.props.StringProperty()
    name_e: bpy.props.StringProperty()


@register_wrap
class MMDDataReferenceIndex(bpy.types.PropertyGroup):
    value: bpy.props.IntProperty()


OPERATION_SCRIPT_PRESETS: Dict[str, Tuple[str, str, str, int]] = {
    'NOTHING': ('', '', '', 1),
    'TO_ENGLISH': ('BLENDER', 'Translate to English', 'to_english(name)', 2),
    'TO_MMD_LR': ('JAPANESE', 'Blender L/R to MMD L/R', 'to_mmd_lr(name)', 3),
    'TO_BLENDER_LR': ('BLENDER', 'MMD L/R to Blender L/R', 'to_blender_lr(name_j)', 4),
}

OPERATION_SCRIPT_PRESET_ITEMS: List[Tuple[str, str, str, int]] = [
    (k, t[1], t[2], t[3])
    for k, t in OPERATION_SCRIPT_PRESETS.items()
]


@register_wrap
class MMDDataQuery(bpy.types.PropertyGroup):
    @staticmethod
    def _update_index(mmd_data_query: 'MMDDataQuery', _context):
        FnTranslations.update_index(mmd_data_query)

    @staticmethod
    def _collect_data(mmd_data_query: 'MMDDataQuery', _context):
        FnTranslations.collect_data(mmd_data_query)

    @staticmethod
    def _update_query(mmd_data_query: 'MMDDataQuery', _context):
        FnTranslations.update_query(mmd_data_query)

    @staticmethod
    def _update_operation_script_preset(mmd_data_query: 'MMDDataQuery', _context):
        if mmd_data_query.operation_script_preset == 'NOTHING':
            return

        id2scripts: Dict[str, str] = {i[0]: i[2] for i in OPERATION_SCRIPT_PRESET_ITEMS}

        operation_script = id2scripts.get(mmd_data_query.operation_script_preset)
        if operation_script is None:
            return

        mmd_data_query.operation_script = operation_script
        mmd_data_query.operation_target = OPERATION_SCRIPT_PRESETS[mmd_data_query.operation_script_preset][0]

    filter_japanese_blank: bpy.props.BoolProperty(name='Japanese Blank', default=False, update=_update_query.__func__)
    filter_english_blank: bpy.props.BoolProperty(name='English Blank', default=False, update=_update_query.__func__)
    filter_restorable: bpy.props.BoolProperty(name='Restorable', default=False, update=_update_query.__func__)
    filter_selected: bpy.props.BoolProperty(name='Selected', default=False, update=_update_query.__func__)
    filter_visible: bpy.props.BoolProperty(name='Visible', default=False, update=_update_query.__func__)
    filter_types: bpy.props.EnumProperty(
        items=MMD_DATA_TYPE_ENUM_ITEMS,
        default={'BONE', 'MORPH', 'MATERIAL', 'DISPLAY', 'PHYSICS', },
        options={'ENUM_FLAG'},
        update=_update_query.__func__,
    )
    data: bpy.props.CollectionProperty(type=MMDDataReference)
    result_data_index: bpy.props.IntProperty(update=_update_index.__func__)
    result_data_indices: bpy.props.CollectionProperty(type=MMDDataReferenceIndex)

    dictionary: bpy.props.EnumProperty(
        items=DictionaryEnum.get_dictionary_items,
        name='Dictionary',
    )

    operation_target: bpy.props.EnumProperty(
        items=[
            ('BLENDER', 'Blender Name (name)', '', 1),
            ('JAPANESE', 'Japanese MMD Name (name_j)', '', 2),
            ('ENGLISH', 'English MMD Name (name_e)', '', 3),
        ],
        name='Operation Target',
        default='JAPANESE',
    )

    operation_script_preset: bpy.props.EnumProperty(
        items=OPERATION_SCRIPT_PRESET_ITEMS,
        name='Operation Script Preset',
        default='NOTHING',
        update=_update_operation_script_preset.__func__,
    )

    operation_script: bpy.props.StringProperty()
