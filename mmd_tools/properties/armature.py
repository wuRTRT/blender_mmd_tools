# -*- coding: utf-8 -*-

import bpy
from mmd_tools import register_wrap


@register_wrap
class MMDPropertyProxy(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()


@register_wrap
class MMDArmature(bpy.types.PropertyGroup):
    active_index: bpy.props.IntProperty(name='Active Index')
    members: bpy.props.CollectionProperty(type=MMDPropertyProxy)
