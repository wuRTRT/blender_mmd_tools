# -*- coding: utf-8 -*-

import itertools
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Callable, Dict, Set, Tuple, Union

import bpy
from mmd_tools.core.model import FnModel, Model
from mmd_tools.translations import DictionaryEnum
from mmd_tools.utils import convertLRToName, convertNameToLR

if TYPE_CHECKING:
    from mmd_tools.properties.morph import _MorphBase
    from mmd_tools.properties.root import MMDRoot
    from mmd_tools.properties.translations import (MMDDataQuery,
                                                   MMDDataReference,
                                                   MMDDataReferenceIndex)


class MMDDataType(Enum):
    BONE = 'Bones'
    MORPH = 'Morphs'
    MATERIAL = 'Materials'
    DISPLAY = 'Display'
    PHYSICS = 'Physics'
    INFO = 'Information'


class MMDDataHandlerABC(ABC):
    @classmethod
    @property
    @abstractmethod
    def type_name(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def draw_item(cls, layout: bpy.types.UILayout, mmd_data_ref: 'MMDDataReference', index: int):
        pass

    @classmethod
    @abstractmethod
    def collect_data(cls, mmd_data_query: 'MMDDataQuery'):
        pass

    @classmethod
    @abstractmethod
    def update_index(cls, mmd_data_ref: 'MMDDataReference'):
        pass

    @classmethod
    @abstractmethod
    def update_query(cls, mmd_data_query: 'MMDDataQuery', filter_selected: bool, filter_visible: bool, check_blank_name: Callable[[str, str], bool]):
        pass

    @classmethod
    @abstractmethod
    def set_names(cls, mmd_data_ref: 'MMDDataReference', name: Union[str, None], name_j: Union[str, None], name_e: Union[str, None]):
        pass

    @classmethod
    @abstractmethod
    def get_names(cls, mmd_data_ref: 'MMDDataReference') -> Tuple[str, str, str]:
        """Returns (name, name_j, name_e)"""

    @classmethod
    def is_restorable(cls, mmd_data_ref: 'MMDDataReference') -> bool:
        return (mmd_data_ref.name, mmd_data_ref.name_j, mmd_data_ref.name_e) != cls.get_names(mmd_data_ref)

    @classmethod
    def check_data_visible(cls, filter_selected: bool, filter_visible: bool, select: bool, hide: bool) -> bool:
        return (
            filter_selected and not select
            or
            filter_visible and hide
        )

    @classmethod
    def prop_restorable(cls, layout: bpy.types.UILayout, mmd_data_ref: 'MMDDataReference', prop_name: str, original_value: str, index: int):
        row = layout.row(align=True)
        row.prop(mmd_data_ref, prop_name, text='')

        if getattr(mmd_data_ref, prop_name) == original_value:
            row.label(text='', icon='BLANK1')
            return

        op = row.operator('mmd_tools.restore_mmd_data_ref_name', text='', icon='FILE_REFRESH')
        op.index = index
        op.prop_name = prop_name
        op.restore_value = original_value

    @classmethod
    def prop_disabled(cls, layout: bpy.types.UILayout, mmd_data_ref: 'MMDDataReference', prop_name: str):
        row = layout.row(align=True)
        row.enabled = False
        row.prop(mmd_data_ref, prop_name, text='')
        row.label(text='', icon='BLANK1')


class MMDBoneHandler(MMDDataHandlerABC):
    @classmethod
    @property
    def type_name(cls) -> str:
        return MMDDataType.BONE.name

    @classmethod
    def draw_item(cls, layout: bpy.types.UILayout, mmd_data_ref: 'MMDDataReference', index: int):
        pose_bone: bpy.types.PoseBone = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        row = layout.row(align=True)
        row.label(text='', icon='BONE_DATA')
        prop_row = row.row()
        cls.prop_restorable(prop_row, mmd_data_ref, 'name', pose_bone.name, index)
        cls.prop_restorable(prop_row, mmd_data_ref, 'name_j', pose_bone.mmd_bone.name_j, index)
        cls.prop_restorable(prop_row, mmd_data_ref, 'name_e', pose_bone.mmd_bone.name_e, index)
        row.prop(pose_bone.bone, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if pose_bone.bone.select else 'RESTRICT_SELECT_ON')
        row.prop(pose_bone.bone, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if pose_bone.bone.hide else 'HIDE_OFF')

    @classmethod
    def collect_data(cls, mmd_data_query: 'MMDDataQuery'):
        armature_object: bpy.types.Object = FnModel.find_armature(mmd_data_query.id_data)
        armature: bpy.types.Armature = armature_object.data
        visible_layer_indices = {i for i, visible in enumerate(armature.layers) if visible}
        pose_bone: bpy.types.PoseBone
        for index, pose_bone in enumerate(armature_object.pose.bones):
            layers = pose_bone.bone.layers
            if not any(layers[i] for i in visible_layer_indices):
                continue

            mmd_data_ref: 'MMDDataReference' = mmd_data_query.data.add()
            mmd_data_ref.type = MMDDataType.BONE.name
            mmd_data_ref.object = armature_object
            mmd_data_ref.data_path = f'pose.bones[{index}]'
            mmd_data_ref.name = pose_bone.name
            mmd_data_ref.name_j = pose_bone.mmd_bone.name_j
            mmd_data_ref.name_e = pose_bone.mmd_bone.name_e

    @classmethod
    def update_index(cls, mmd_data_ref: 'MMDDataReference'):
        bpy.context.view_layer.objects.active = mmd_data_ref.object
        mmd_data_ref.object.id_data.data.bones.active = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path).bone

    @classmethod
    def update_query(cls, mmd_data_query: 'MMDDataQuery', filter_selected: bool, filter_visible: bool, check_blank_name: Callable[[str, str], bool]):
        mmd_data_ref: 'MMDDataReference'
        for index, mmd_data_ref in enumerate(mmd_data_query.data):
            if mmd_data_ref.type != MMDDataType.BONE.name:
                continue

            pose_bone: bpy.types.PoseBone = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)

            if cls.check_data_visible(filter_selected, filter_visible, pose_bone.bone.select, pose_bone.bone.hide):
                continue

            if check_blank_name(mmd_data_ref.name_j, mmd_data_ref.name_e):
                continue

            if mmd_data_query.filter_restorable and not cls.is_restorable(mmd_data_ref):
                continue

            mmd_data_ref_index: 'MMDDataReferenceIndex' = mmd_data_query.result_data_indices.add()
            mmd_data_ref_index.value = index

    @classmethod
    def set_names(cls, mmd_data_ref: 'MMDDataReference', name: Union[str, None], name_j: Union[str, None], name_e: Union[str, None]):
        pose_bone: bpy.types.PoseBone = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        if name is not None:
            pose_bone.name = name
        if name_j is not None:
            pose_bone.mmd_bone.name_j = name_j
        if name_e is not None:
            pose_bone.mmd_bone.name_e = name_e

    @classmethod
    def get_names(cls, mmd_data_ref: 'MMDDataReference') -> Tuple[str, str, str]:
        pose_bone: bpy.types.PoseBone = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        return (pose_bone.name, pose_bone.mmd_bone.name_j, pose_bone.mmd_bone.name_e)


class MMDMorphHandler(MMDDataHandlerABC):
    @classmethod
    @property
    def type_name(cls) -> str:
        return MMDDataType.MORPH.name

    @classmethod
    def draw_item(cls, layout: bpy.types.UILayout, mmd_data_ref: 'MMDDataReference', index: int):
        morph: '_MorphBase' = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        row = layout.row(align=True)
        row.label(text='', icon='SHAPEKEY_DATA')
        prop_row = row.row()
        cls.prop_disabled(prop_row, mmd_data_ref, 'name')
        cls.prop_restorable(prop_row, mmd_data_ref, 'name', morph.name, index)
        cls.prop_restorable(prop_row, mmd_data_ref, 'name_e', morph.name_e, index)
        row.label(text='', icon='BLANK1')
        row.label(text='', icon='BLANK1')

    MORPH_DATA_PATH_EXTRACT = re.compile(r"mmd_root\.(?P<morphs_name>[^\[]*)\[(?P<index>\d*)\]")

    @classmethod
    def collect_data(cls, mmd_data_query: 'MMDDataQuery'):
        root_object: bpy.types.Object = mmd_data_query.id_data
        mmd_root: 'MMDRoot' = root_object.mmd_root

        for morphs_name, morphs in {
            'material_morphs': mmd_root.material_morphs,
            'uv_morphs': mmd_root.uv_morphs,
            'bone_morphs': mmd_root.bone_morphs,
            'vertex_morphs': mmd_root.vertex_morphs,
            'group_morphs': mmd_root.group_morphs,
        }.items():
            morph: '_MorphBase'
            for index, morph in enumerate(morphs):
                mmd_data_ref: 'MMDDataReference' = mmd_data_query.data.add()
                mmd_data_ref.type = MMDDataType.MORPH.name
                mmd_data_ref.object = root_object
                mmd_data_ref.data_path = f'mmd_root.{morphs_name}[{index}]'
                mmd_data_ref.name = morph.name
                # mmd_data_ref.name_j = None
                mmd_data_ref.name_e = morph.name_e

    @classmethod
    def update_index(cls, mmd_data_ref: 'MMDDataReference'):
        match = cls.MORPH_DATA_PATH_EXTRACT.match(mmd_data_ref.data_path)
        if not match:
            return

        mmd_data_ref.object.mmd_root.active_morph_type = match['morphs_name']
        mmd_data_ref.object.mmd_root.active_morph = int(match['index'])

    @classmethod
    def update_query(cls, mmd_data_query: 'MMDDataQuery', filter_selected: bool, filter_visible: bool, check_blank_name: Callable[[str, str], bool]):
        mmd_data_ref: 'MMDDataReference'
        for index, mmd_data_ref in enumerate(mmd_data_query.data):
            if mmd_data_ref.type != MMDDataType.MORPH.name:
                continue

            morph: '_MorphBase' = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
            if check_blank_name(morph.name, morph.name_e):
                continue

            if mmd_data_query.filter_restorable and not cls.is_restorable(mmd_data_ref):
                continue

            mmd_data_ref_index: 'MMDDataReferenceIndex' = mmd_data_query.result_data_indices.add()
            mmd_data_ref_index.value = index

    @classmethod
    def set_names(cls, mmd_data_ref: 'MMDDataReference', name: Union[str, None], name_j: Union[str, None], name_e: Union[str, None]):
        morph: '_MorphBase' = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        if name is not None:
            morph.name = name
        if name_e is not None:
            morph.name_e = name_e

    @classmethod
    def get_names(cls, mmd_data_ref: 'MMDDataReference') -> Tuple[str, str, str]:
        morph: '_MorphBase' = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        return (morph.name, '', morph.name_e)


class MMDMaterialHandler(MMDDataHandlerABC):
    @classmethod
    @property
    def type_name(cls) -> str:
        return MMDDataType.MATERIAL.name

    @classmethod
    def draw_item(cls, layout: bpy.types.UILayout, mmd_data_ref: 'MMDDataReference', index: int):
        mesh_object: bpy.types.Object = mmd_data_ref.object
        material: bpy.types.Material = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        row = layout.row(align=True)
        row.label(text='', icon='MATERIAL_DATA')
        prop_row = row.row()
        cls.prop_restorable(prop_row, mmd_data_ref, 'name', material.name, index)
        cls.prop_restorable(prop_row, mmd_data_ref, 'name_j', material.mmd_material.name_j, index)
        cls.prop_restorable(prop_row, mmd_data_ref, 'name_e', material.mmd_material.name_e, index)
        row.prop(mesh_object, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if mesh_object.select else 'RESTRICT_SELECT_ON')
        row.prop(mesh_object, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if mesh_object.hide else 'HIDE_OFF')

    MATERIAL_DATA_PATH_EXTRACT = re.compile(r"data\.materials\[(?P<index>\d*)\]")

    @classmethod
    def collect_data(cls, mmd_data_query: 'MMDDataQuery'):
        checked_materials: Set[bpy.types.Material] = set()
        mesh_object: bpy.types.Object
        for mesh_object in FnModel.child_meshes(FnModel.find_armature(mmd_data_query.id_data)):
            material: bpy.types.Material
            for index, material in enumerate(mesh_object.data.materials):
                if material in checked_materials:
                    continue

                checked_materials.add(material)

                if not hasattr(material, 'mmd_material'):
                    continue

                mmd_data_ref: 'MMDDataReference' = mmd_data_query.data.add()
                mmd_data_ref.type = MMDDataType.MATERIAL.name
                mmd_data_ref.object = mesh_object
                mmd_data_ref.data_path = f'data.materials[{index}]'
                mmd_data_ref.name = material.name
                mmd_data_ref.name_j = material.mmd_material.name_j
                mmd_data_ref.name_e = material.mmd_material.name_e

    @classmethod
    def update_index(cls, mmd_data_ref: 'MMDDataReference'):
        id_data: bpy.types.Object = mmd_data_ref.object
        bpy.context.view_layer.objects.active = id_data

        match = cls.MATERIAL_DATA_PATH_EXTRACT.match(mmd_data_ref.data_path)
        if not match:
            return

        id_data.active_material_index = int(match['index'])

    @classmethod
    def update_query(cls, mmd_data_query: 'MMDDataQuery', filter_selected: bool, filter_visible: bool, check_blank_name: Callable[[str, str], bool]):
        mmd_data_ref: 'MMDDataReference'
        for index, mmd_data_ref in enumerate(mmd_data_query.data):
            if mmd_data_ref.type != MMDDataType.MATERIAL.name:
                continue

            mesh_object: bpy.types.Object = mmd_data_ref.object
            if cls.check_data_visible(filter_selected, filter_visible, mesh_object.select, mesh_object.hide):
                continue

            material: bpy.types.Material = mesh_object.path_resolve(mmd_data_ref.data_path)
            if check_blank_name(material.mmd_material.name_j, material.mmd_material.name_e):
                continue

            if mmd_data_query.filter_restorable and not cls.is_restorable(mmd_data_ref):
                continue

            mmd_data_ref_index: 'MMDDataReferenceIndex' = mmd_data_query.result_data_indices.add()
            mmd_data_ref_index.value = index

    @classmethod
    def set_names(cls, mmd_data_ref: 'MMDDataReference', name: Union[str, None], name_j: Union[str, None], name_e: Union[str, None]):
        material: bpy.types.Material = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        if name is not None:
            material.name = name
        if name_j is not None:
            material.mmd_material.name_j = name_j
        if name_e is not None:
            material.mmd_material.name_e = name_e

    @classmethod
    def get_names(cls, mmd_data_ref: 'MMDDataReference') -> Tuple[str, str, str]:
        material: bpy.types.Material = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        return (material.name, material.mmd_material.name_j, material.mmd_material.name_e)


class MMDDisplayHandler(MMDDataHandlerABC):
    @classmethod
    @property
    def type_name(cls) -> str:
        return MMDDataType.DISPLAY.name

    @classmethod
    def draw_item(cls, layout: bpy.types.UILayout, mmd_data_ref: 'MMDDataReference', index: int):
        bone_group: bpy.types.BoneGroup = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        row = layout.row(align=True)
        row.label(text='', icon='GROUP_BONE')

        prop_row = row.row()
        cls.prop_restorable(prop_row, mmd_data_ref, 'name', bone_group.name, index)
        cls.prop_disabled(prop_row, mmd_data_ref, 'name')
        cls.prop_disabled(prop_row, mmd_data_ref, 'name_e')
        row.prop(mmd_data_ref.object, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if mmd_data_ref.object.select else 'RESTRICT_SELECT_ON')
        row.prop(mmd_data_ref.object, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if mmd_data_ref.object.hide else 'HIDE_OFF')

    DISPLAY_DATA_PATH_EXTRACT = re.compile(r"pose\.bone_groups\[(?P<index>\d*)\]")

    @classmethod
    def collect_data(cls, mmd_data_query: 'MMDDataQuery'):
        armature_object: bpy.types.Object = FnModel.find_armature(mmd_data_query.id_data)
        bone_group: bpy.types.BoneGroup
        for index, bone_group in enumerate(armature_object.pose.bone_groups):
            mmd_data_ref: 'MMDDataReference' = mmd_data_query.data.add()
            mmd_data_ref.type = MMDDataType.DISPLAY.name
            mmd_data_ref.object = armature_object
            mmd_data_ref.data_path = f'pose.bone_groups[{index}]'
            mmd_data_ref.name = bone_group.name
            # mmd_data_ref.name_j = None
            # mmd_data_ref.name_e = None

    @classmethod
    def update_index(cls, mmd_data_ref: 'MMDDataReference'):
        id_data: bpy.types.Object = mmd_data_ref.object
        bpy.context.view_layer.objects.active = id_data

        match = cls.DISPLAY_DATA_PATH_EXTRACT.match(mmd_data_ref.data_path)
        if not match:
            return

        id_data.pose.bone_groups.active_index = int(match['index'])

    @classmethod
    def update_query(cls, mmd_data_query: 'MMDDataQuery', filter_selected: bool, filter_visible: bool, check_blank_name: Callable[[str, str], bool]):
        mmd_data_ref: 'MMDDataReference'
        for index, mmd_data_ref in enumerate(mmd_data_query.data):
            if mmd_data_ref.type != MMDDataType.DISPLAY.name:
                continue

            obj: bpy.types.Object = mmd_data_ref.object
            if cls.check_data_visible(filter_selected, filter_visible, obj.select_get(), obj.hide_get()):
                continue

            bone_group: bpy.types.BoneGroup = obj.path_resolve(mmd_data_ref.data_path)
            if check_blank_name(bone_group.name, ''):
                continue

            if mmd_data_query.filter_restorable and not cls.is_restorable(mmd_data_ref):
                continue

            mmd_data_ref_index: 'MMDDataReferenceIndex' = mmd_data_query.result_data_indices.add()
            mmd_data_ref_index.value = index

    @classmethod
    def set_names(cls, mmd_data_ref: 'MMDDataReference', name: Union[str, None], name_j: Union[str, None], name_e: Union[str, None]):
        bone_group: bpy.types.BoneGroup = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        if name is not None:
            bone_group.name = name

    @classmethod
    def get_names(cls, mmd_data_ref: 'MMDDataReference') -> Tuple[str, str, str]:
        bone_group: bpy.types.BoneGroup = mmd_data_ref.object.path_resolve(mmd_data_ref.data_path)
        return (bone_group.name, '', '')


class MMDPhysicsHandler(MMDDataHandlerABC):
    @classmethod
    @property
    def type_name(cls) -> str:
        return MMDDataType.PHYSICS.name

    @classmethod
    def draw_item(cls, layout: bpy.types.UILayout, mmd_data_ref: 'MMDDataReference', index: int):
        obj: bpy.types.Object = mmd_data_ref.object

        if FnModel.is_rigid_body_object(obj):
            icon = 'MESH_ICOSPHERE'
            mmd_object = obj.mmd_rigid
        elif FnModel.is_joint_object(obj):
            icon = 'CONSTRAINT'
            mmd_object = obj.mmd_joint

        row = layout.row(align=True)
        row.label(text='', icon=icon)
        prop_row = row.row()
        cls.prop_restorable(prop_row, mmd_data_ref, 'name', obj.name, index)
        cls.prop_restorable(prop_row, mmd_data_ref, 'name_j', mmd_object.name_j, index)
        cls.prop_restorable(prop_row, mmd_data_ref, 'name_e', mmd_object.name_e, index)
        row.prop(obj, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if obj.select else 'RESTRICT_SELECT_ON')
        row.prop(obj, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if obj.hide else 'HIDE_OFF')

    @classmethod
    def collect_data(cls, mmd_data_query: 'MMDDataQuery'):
        root_object: bpy.types.Object = mmd_data_query.id_data
        model = Model(root_object)

        obj: bpy.types.Object
        for obj in model.rigidBodies():
            mmd_data_ref: 'MMDDataReference' = mmd_data_query.data.add()
            mmd_data_ref.type = MMDDataType.PHYSICS.name
            mmd_data_ref.object = obj
            mmd_data_ref.data_path = 'mmd_rigid'
            mmd_data_ref.name = obj.name
            mmd_data_ref.name_j = obj.mmd_rigid.name_j
            mmd_data_ref.name_e = obj.mmd_rigid.name_e

        obj: bpy.types.Object
        for obj in model.joints():
            mmd_data_ref: 'MMDDataReference' = mmd_data_query.data.add()
            mmd_data_ref.type = MMDDataType.PHYSICS.name
            mmd_data_ref.object = obj
            mmd_data_ref.data_path = 'mmd_joint'
            mmd_data_ref.name = obj.name
            mmd_data_ref.name_j = obj.mmd_joint.name_j
            mmd_data_ref.name_e = obj.mmd_joint.name_e

    @classmethod
    def update_index(cls, mmd_data_ref: 'MMDDataReference'):
        bpy.context.view_layer.objects.active = mmd_data_ref.object

    @classmethod
    def update_query(cls, mmd_data_query: 'MMDDataQuery', filter_selected: bool, filter_visible: bool, check_blank_name: Callable[[str, str], bool]):
        mmd_data_ref: 'MMDDataReference'
        for index, mmd_data_ref in enumerate(mmd_data_query.data):
            if mmd_data_ref.type != MMDDataType.PHYSICS.name:
                continue

            obj: bpy.types.Object = mmd_data_ref.object
            if cls.check_data_visible(filter_selected, filter_visible, obj.select_get(), obj.hide_get()):
                continue

            if FnModel.is_rigid_body_object(obj):
                mmd_object = obj.mmd_rigid
            elif FnModel.is_joint_object(obj):
                mmd_object = obj.mmd_joint

            if check_blank_name(mmd_object.name_j, mmd_object.name_e):
                continue

            if mmd_data_query.filter_restorable and not cls.is_restorable(mmd_data_ref):
                continue

            mmd_data_ref_index: 'MMDDataReferenceIndex' = mmd_data_query.result_data_indices.add()
            mmd_data_ref_index.value = index

    @classmethod
    def set_names(cls, mmd_data_ref: 'MMDDataReference', name: Union[str, None], name_j: Union[str, None], name_e: Union[str, None]):
        obj: bpy.types.Object = mmd_data_ref.object

        if FnModel.is_rigid_body_object(obj):
            mmd_object = obj.mmd_rigid
        elif FnModel.is_joint_object(obj):
            mmd_object = obj.mmd_joint

        if name is not None:
            obj.name = name
        if name_j is not None:
            mmd_object.name_j = name_j
        if name_e is not None:
            mmd_object.name_e = name_e

    @classmethod
    def get_names(cls, mmd_data_ref: 'MMDDataReference') -> Tuple[str, str, str]:
        obj: bpy.types.Object = mmd_data_ref.object

        if FnModel.is_rigid_body_object(obj):
            mmd_object = obj.mmd_rigid
        elif FnModel.is_joint_object(obj):
            mmd_object = obj.mmd_joint

        return (obj.name, mmd_object.name_j, mmd_object.name_e)


class MMDInfoHandler(MMDDataHandlerABC):
    @classmethod
    @property
    def type_name(cls) -> str:
        return MMDDataType.INFO.name

    TYPE_TO_ICONS = {
        'EMPTY': 'EMPTY_DATA',
        'ARMATURE': 'ARMATURE_DATA',
        'MESH': 'MESH_DATA',
    }

    @classmethod
    def draw_item(cls, layout: bpy.types.UILayout, mmd_data_ref: 'MMDDataReference', index: int):
        info_object: bpy.types.Object = mmd_data_ref.object
        row = layout.row(align=True)
        row.label(text='', icon=MMDInfoHandler.TYPE_TO_ICONS.get(info_object.type, 'OBJECT_DATA'))
        prop_row = row.row()
        cls.prop_restorable(prop_row, mmd_data_ref, 'name', info_object.name, index)
        cls.prop_disabled(prop_row, mmd_data_ref, 'name')
        cls.prop_disabled(prop_row, mmd_data_ref, 'name_e')
        row.prop(info_object, 'select', text='', emboss=False, icon_only=True, icon='RESTRICT_SELECT_OFF' if info_object.select else 'RESTRICT_SELECT_ON')
        row.prop(info_object, 'hide', text='', emboss=False, icon_only=True, icon='HIDE_ON' if info_object.hide else 'HIDE_OFF')

    @classmethod
    def collect_data(cls, mmd_data_query: 'MMDDataQuery'):
        root_object: bpy.types.Object = mmd_data_query.id_data
        armature_object: bpy.types.Object = FnModel.find_armature(root_object)

        info_object: bpy.types.Object
        for info_object in itertools.chain([root_object, armature_object], FnModel.child_meshes(armature_object)):
            mmd_data_ref: 'MMDDataReference' = mmd_data_query.data.add()
            mmd_data_ref.type = MMDDataType.INFO.name
            mmd_data_ref.object = info_object
            mmd_data_ref.data_path = ''
            mmd_data_ref.name = info_object.name
            # mmd_data_ref.name_j = None
            # mmd_data_ref.name_e = None

    @classmethod
    def update_index(cls, mmd_data_ref: 'MMDDataReference'):
        bpy.context.view_layer.objects.active = mmd_data_ref.object

    @classmethod
    def update_query(cls, mmd_data_query: 'MMDDataQuery', filter_selected: bool, filter_visible: bool, check_blank_name: Callable[[str, str], bool]):
        mmd_data_ref: 'MMDDataReference'
        for index, mmd_data_ref in enumerate(mmd_data_query.data):
            if mmd_data_ref.type != MMDDataType.INFO.name:
                continue

            info_object: bpy.types.Object = mmd_data_ref.object
            if cls.check_data_visible(filter_selected, filter_visible, info_object.select, info_object.hide):
                continue

            if check_blank_name(info_object.name, ''):
                continue

            if mmd_data_query.filter_restorable and not cls.is_restorable(mmd_data_ref):
                continue

            mmd_data_ref_index: 'MMDDataReferenceIndex' = mmd_data_query.result_data_indices.add()
            mmd_data_ref_index.value = index

    @classmethod
    def set_names(cls, mmd_data_ref: 'MMDDataReference', name: Union[str, None], name_j: Union[str, None], name_e: Union[str, None]):
        info_object: bpy.types.Object = mmd_data_ref.object
        if name is not None:
            info_object.name = name

    @classmethod
    def get_names(cls, mmd_data_ref: 'MMDDataReference') -> Tuple[str, str, str]:
        info_object: bpy.types.Object = mmd_data_ref.object
        return (info_object.name, '', '')


MMD_DATA_HANDLERS: Set[MMDDataHandlerABC] = {
    MMDBoneHandler,
    MMDMorphHandler,
    MMDMaterialHandler,
    MMDDisplayHandler,
    MMDPhysicsHandler,
    MMDInfoHandler,
}

MMD_DATA_TYPE_TO_HANDLERS: Dict[str, MMDDataHandlerABC] = {h.type_name: h for h in MMD_DATA_HANDLERS}


class FnTranslations:
    @staticmethod
    def apply_translations(root_object: bpy.types.Object):
        mmd_data_query: 'MMDDataQuery' = root_object.mmd_data_query
        mmd_data_ref_index: 'MMDDataReferenceIndex'
        for mmd_data_ref_index in mmd_data_query.result_data_indices:
            mmd_data_ref: 'MMDDataReference' = mmd_data_query.data[mmd_data_ref_index.value]
            handler: MMDDataHandlerABC = MMD_DATA_TYPE_TO_HANDLERS[mmd_data_ref.type]
            name, name_j, name_e = handler.get_names(mmd_data_ref)
            handler.set_names(
                mmd_data_ref,
                mmd_data_ref.name if mmd_data_ref.name != name else None,
                mmd_data_ref.name_j if mmd_data_ref.name_j != name_j else None,
                mmd_data_ref.name_e if mmd_data_ref.name_e != name_e else None,
            )

    @staticmethod
    def execute_translation_batch(root_object: bpy.types.Object) -> Tuple[Dict[str, str], Union[bpy.types.Text, None]]:
        mmd_data_query: 'MMDDataQuery' = root_object.mmd_data_query
        operation_script = mmd_data_query.operation_script
        if not operation_script:
            return ({}, None)

        translator = DictionaryEnum.get_translator(mmd_data_query.dictionary)

        def translate(name: str) -> str:
            if translator:
                return translator.translate(name, name)
            return name

        operation_script_ast = compile(mmd_data_query.operation_script, '<string>', 'eval')
        operation_target: str = mmd_data_query.operation_target

        mmd_data_ref_index: 'MMDDataReferenceIndex'
        for mmd_data_ref_index in mmd_data_query.result_data_indices:
            mmd_data_ref: 'MMDDataReference' = mmd_data_query.data[mmd_data_ref_index.value]

            handler: MMDDataHandlerABC = MMD_DATA_TYPE_TO_HANDLERS[mmd_data_ref.type]

            name = mmd_data_ref.name
            name_j = mmd_data_ref.name_j
            name_e = mmd_data_ref.name_e
            org_name, org_name_j, org_name_e = handler.get_names(mmd_data_ref)

            # pylint: disable=eval-used
            result_name = str(eval(
                operation_script_ast,
                {'__builtins__': {}},
                {
                    'to_english': translate,
                    'to_mmd_lr': convertLRToName,
                    'to_blender_lr': convertNameToLR,
                    'name': name,
                    'name_j': name_j if name_j != '' else name,
                    'name_e': name_e if name_e != '' else name,
                    'org_name': org_name,
                    'org_name_j': org_name_j if org_name_j != '' else org_name,
                    'org_name_e': org_name_e if org_name_e != '' else org_name,
                }
            ))

            if operation_target == 'BLENDER':
                mmd_data_ref.name = result_name
            elif operation_target == 'JAPANESE':
                mmd_data_ref.name_j = result_name
            elif operation_target == 'ENGLISH':
                mmd_data_ref.name_e = result_name

        return (translator.fails, translator.save_fails())

    @staticmethod
    def update_index(mmd_data_query: 'MMDDataQuery'):
        if mmd_data_query.result_data_index < 0:
            return

        mmd_data_ref_index: 'MMDDataReferenceIndex' = mmd_data_query.result_data_indices[mmd_data_query.result_data_index]
        mmd_data_ref: 'MMDDataReferenceIndex' = mmd_data_query.data[mmd_data_ref_index.value]

        MMD_DATA_TYPE_TO_HANDLERS[mmd_data_ref.type].update_index(mmd_data_ref)

    @staticmethod
    def collect_data(mmd_data_query: 'MMDDataQuery'):
        mmd_data_query.data.clear()
        for handler in MMD_DATA_HANDLERS:
            handler.collect_data(mmd_data_query)

    @staticmethod
    def update_query(mmd_data_query: 'MMDDataQuery'):
        mmd_data_query.result_data_indices.clear()
        mmd_data_query.result_data_index = -1

        filter_japanese_blank: bool = mmd_data_query.filter_japanese_blank
        filter_english_blank: bool = mmd_data_query.filter_english_blank

        filter_selected: bool = mmd_data_query.filter_selected
        filter_visible: bool = mmd_data_query.filter_visible

        def check_blank_name(name_j: str, name_e: str) -> bool:
            return (
                filter_japanese_blank and name_j
                or
                filter_english_blank and name_e
            )

        for handler in MMD_DATA_HANDLERS:
            if handler.type_name in mmd_data_query.filter_types:
                handler.update_query(mmd_data_query, filter_selected, filter_visible, check_blank_name)

    @staticmethod
    def clear_data(mmd_data_query: 'MMDDataQuery'):
        mmd_data_query.data.clear()
        mmd_data_query.result_data_indices.clear()
        mmd_data_query.result_data_index = -1
        mmd_data_query.filter_restorable = False
