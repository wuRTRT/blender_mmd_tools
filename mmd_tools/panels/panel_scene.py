# -*- coding: utf-8 -*-

from typing import Dict

import bpy
from bpy.types import Panel
from mmd_tools import register_wrap
from mmd_tools.core import model
from mmd_tools.core.sdef import FnSDEF


@register_wrap
class RigidBodyBake(bpy.types.Operator):
    bl_idname = 'mmd_tools.ptcache_rigid_body_bake'
    bl_label = 'Bake'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context: bpy.types.Context):
        override: Dict = context.copy()
        override.update({
            'scene': context.scene,
            'point_cache': context.scene.rigidbody_world.point_cache
        })
        bpy.ops.ptcache.bake(override, 'INVOKE_DEFAULT',  bake=True)

        return {'FINISHED'}


@register_wrap
class RigidBodyBake(bpy.types.Operator):
    bl_idname = 'mmd_tools.ptcache_rigid_body_free_bake'
    bl_label = 'Bake'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context: bpy.types.Context):
        override: Dict = context.copy()
        override.update({
            'scene': context.scene,
            'point_cache': context.scene.rigidbody_world.point_cache
        })
        bpy.ops.ptcache.free_bake(override, 'INVOKE_DEFAULT')

        return {'FINISHED'}


@register_wrap
class MMDToolsSceneSetupPanel(Panel):
    bl_idname = 'OBJECT_PT_mmd_tools_scene_setup'
    bl_label = 'Scene Setup'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MMD'

    def draw(self, context: bpy.types.Context):
        layout = self.layout

        col = layout.column(align=True)
        col.label(text='Import:', icon='IMPORT')
        row = col.row(align=True)
        row.operator('mmd_tools.import_model', text='Model', icon='OUTLINER_OB_ARMATURE')
        row.operator('mmd_tools.import_vmd', text='Motion', icon='ANIM')
        row.operator('mmd_tools.import_vpd', text='Pose', icon='POSE_HLT')

        col = layout.column(align=True)
        row = col.row(align=False)
        row.label(text='Timeline:', icon='TIME')
        row.prop(context.scene, 'frame_current')
        row = col.row(align=True)
        row.prop(context.scene, 'frame_start')
        row.prop(context.scene, 'frame_end')

        col = layout.column(align=True)
        col.label(text='Rigid Body Physics:', icon='PHYSICS')

        row = col.row(align=True)
        row.operator('mmd_tools.rigid_body_world_update', text='Update Rigid Body World')

        rigidbody_world = context.scene.rigidbody_world

        if rigidbody_world:
            row = col.row(align=True)
            row.prop(rigidbody_world, 'substeps_per_frame', text='Substeps')
            row.prop(rigidbody_world, 'solver_iterations', text='Iteration')

            point_cache = rigidbody_world.point_cache

            col = layout.column(align=True)
            row = col.row(align=True)
            row.enabled = not point_cache.is_baked
            row.prop(point_cache, 'frame_start')
            row.prop(point_cache, 'frame_end')

            row = col.row(align=True)
            if point_cache.is_baked is True:
                row.operator("mmd_tools.ptcache_rigid_body_free_bake", text="Delete Bake")
            else:
                row.operator("mmd_tools.ptcache_rigid_body_bake", text="Bake")


@register_wrap
class MMDToolsModelSetupPanel(Panel):
    bl_idname = 'OBJECT_PT_mmd_tools_model_setup'
    bl_label = 'Model Setup'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MMD'

    def draw(self, context: bpy.types.Context):
        layout = self.layout

        active_object: bpy.types.Object = context.active_object
        mmd_root_object = model.Model.findRoot(active_object)

        if mmd_root_object is None:
            layout.label(text='MMD Model is not selected.', icon='ERROR')
            return

        mmd_root = mmd_root_object.mmd_root

        col = layout.column(align=True)
        col.label(text=mmd_root.name, icon='OUTLINER_OB_ARMATURE')
        col.operator('mmd_tools.show_global_translation_popup', text='(Experimental) Global Translation')

        col = layout.column(align=False)
        row = col.row(align=True)
        row.label(text='Assembly:', icon='MODIFIER_ON')

        grid = col.row()

        row = grid.row(align=True)
        row.operator('mmd_tools.assemble_all', text='All', icon='SETTINGS')
        row.operator('mmd_tools.disassemble_all', text='', icon='TRASH')

        row = grid.row(align=True)
        row.operator('mmd_tools.sdef_bind', text='SDEF', icon='MOD_SIMPLEDEFORM')
        if len(FnSDEF.g_verts) > 0:
            row.operator('mmd_tools.sdef_cache_reset', text='', icon='FILE_REFRESH')
        row.operator('mmd_tools.sdef_unbind', text='', icon='TRASH')

        grid = col.row()
        row = grid.row(align=True)
        row.operator('mmd_tools.apply_additional_transform', text='Bone', icon='CONSTRAINT_BONE')
        row.operator('mmd_tools.clean_additional_transform', text='', icon='TRASH')

        row = grid.row(align=True)
        row.operator('mmd_tools.morph_slider_setup', text='Morph', icon='SHAPEKEY_DATA').type = 'BIND'
        row.operator('mmd_tools.morph_slider_setup', text='', icon='TRASH').type = 'UNBIND'

        grid = col.row()
        row = grid.row(align=True)
        row.active = getattr(context.scene.rigidbody_world, 'enabled', False)
        if not mmd_root.is_built:
            row.operator('mmd_tools.build_rig', text='Physics', icon='PHYSICS', depress=False)
        else:
            row.operator('mmd_tools.clean_rig', text='Physics', icon='PHYSICS', depress=True)

        row = grid.row(align=True)
        row.prop(mmd_root, 'use_property_driver', text='Property', toggle=True, icon='DRIVER')

        col = layout.column(align=True)
        row = col.row(align=False)
        row.label(text='Visibility:', icon='HIDE_OFF')
        row.operator('mmd_tools.separate_by_materials', text='Reset')

        row = col.row(align=True)
        row.prop(mmd_root, 'show_meshes', toggle=True, icon_only=True, icon='MESH_DATA')
        row.prop(mmd_root, 'show_armature', toggle=True, icon_only=True, icon='ARMATURE_DATA')
        row = row.row()
        row.prop(mmd_root, 'show_temporary_objects', toggle=True, icon_only=True, icon='EMPTY_AXIS')
        cell = row.row(align=True)
        cell.prop(mmd_root, 'show_rigid_bodies', toggle=True, icon_only=True, icon='RIGID_BODY')
        cell.prop(mmd_root, 'show_names_of_rigid_bodies', toggle=True, icon_only=True, icon='SHORTDISPLAY')
        cell = row.row(align=True)
        cell.prop(mmd_root, 'show_joints', toggle=True, icon_only=True, icon='RIGID_BODY_CONSTRAINT')
        cell.prop(mmd_root, 'show_names_of_joints', toggle=True, icon_only=True, icon='SHORTDISPLAY')

        col = layout.column(align=True)
        col.label(text='Mesh:', icon='MESH_DATA')
        row = col.row(align=True)
        row.operator('mmd_tools.separate_by_materials', text='Separate', icon='MOD_EXPLODE')
        row.operator('mmd_tools.join_meshes', text='Join', icon='MESH_CUBE')

        col = layout.column(align=False)
        col.label(text='Material:', icon='MATERIAL')
        row = col.row(align=True)
        row.prop(mmd_root, 'use_toon_texture', text='Toon Texture', toggle=True, icon='SHADING_RENDERED')
        row.prop(mmd_root, 'use_sphere_texture', text='Sphere Texture', toggle=True, icon='MATSPHERE')
        row = col.row(align=True)
        row.operator('mmd_tools.edge_preview_setup', text='Edge Preview', icon='ANTIALIASED').action = 'CREATE'
        row.operator('mmd_tools.edge_preview_setup', text='', icon='TRASH').action = 'CLEAN'
