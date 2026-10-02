"""Fail early on configuration typos, invalid paths and unsupported policies."""
import math,re
from .parser import MapError

KEYS={'profile','plugin_name','map_id','units_to_cm','patch_subdivisions','allow_fallback_hulls','surface_collision','ambient_emission','nanite','materials','teleports','models','object_overrides','scripts','sky','unreal_root','sun_intensity','skylight_intensity','spawn_height_cm','source_origin_at_feet','checkpoint_interval','texture_roots'}


def validate_config(config):
    unknown=set(config)-KEYS
    if unknown:raise MapError('Unknown configuration keys: '+', '.join(sorted(unknown)))
    if config.get('profile','generic') not in ('generic','project_jump'):raise MapError('Invalid profile')
    if 'plugin_name' in config and not re.fullmatch('[A-Za-z][A-Za-z0-9]{0,63}',config['plugin_name']):raise MapError('plugin_name must contain letters and digits only')
    if config.get('profile')=='project_jump':
        if 'unreal_root' in config:raise MapError('Project Jump uses its own content plugin mount; remove unreal_root')
        if float(config.get('units_to_cm',2.54))!=2.54:raise MapError('Project Jump requires 2.54 cm per game unit')
        if config.get('surface_collision','dop26')=='triangles' or any(v.get('collision')=='triangles' for v in config.get('object_overrides',{}).values()):raise MapError('Project Jump movement surfaces require box/convex collision, not triangles')
    if not re.fullmatch(r'/Game(?:/[A-Za-z_][A-Za-z0-9_]*)*',config.get('unreal_root','/Game/CodMaps')):raise MapError('unreal_root must be a valid path beneath /Game')
    for name in ('materials','models','object_overrides'):
        if not isinstance(config.get(name,{}),dict):raise MapError(name+' must be an object')
    for name in ('ambient_emission','sun_intensity','skylight_intensity','spawn_height_cm'):
        if name in config and (not math.isfinite(float(config[name])) or float(config[name])<0):raise MapError(name+' must be finite and nonnegative')
    if not 1<=int(config.get('checkpoint_interval',100))<=1000:raise MapError('checkpoint_interval must be between 1 and 1000')
    if not isinstance(config.get('teleports',[]),list):raise MapError('teleports must be an array')
    for name in ('allow_fallback_hulls','nanite','source_origin_at_feet'):
        if name in config and not isinstance(config[name],bool):raise MapError(name+' must be a boolean')
    for binding in config.get('teleports',[]):
        if not isinstance(binding,dict) or set(binding)-{'trigger','entity_id','target','delay','cooldown','set_view'}:raise MapError('Invalid teleport binding keys')
        if ('trigger' in binding)==('entity_id' in binding):raise MapError('Teleport requires exactly one trigger or entity_id selector')
        if 'set_view' in binding and not isinstance(binding['set_view'],bool):raise MapError('set_view must be a boolean')
    for name,spec in config.get('object_overrides',{}).items():
        if not isinstance(spec,dict) or set(spec)-{'collision','slick'}:raise MapError('Invalid object override for '+name)
        if 'collision' in spec and spec['collision'] not in ('box','convex','triangles','dop26','none'):raise MapError('Invalid collision override for '+name)
        if 'slick' in spec and not isinstance(spec['slick'],bool):raise MapError('slick must be a boolean')
    if config.get('sky'):
        sky=config['sky']
        if set(sky)-{'faces','orientation'}:raise MapError('Unknown sky config keys')
        if set(sky.get('faces',{}))!={'ft','bk','lf','rt','up','dn'}:raise MapError('Sky requires faces ft,bk,lf,rt,up,dn')
        if any(not isinstance(v,int) or not 0<=v<8 for v in sky.get('orientation',{}).values()):raise MapError('Sky orientation must contain integers from 0 to 7')
    for name,spec in config.get('materials',{}).items():
        if set(spec)-{'texture','unreal_asset','color','roughness'}:raise MapError('Unknown material config keys for '+name)
        if sum(key in spec for key in ('texture','unreal_asset','color'))>1:raise MapError('Choose texture, unreal_asset or color for '+name)
        if 'color' in spec and (len(spec['color'])!=3 or any(not math.isfinite(float(v)) or not 0<=float(v)<=1 for v in spec['color'])):raise MapError('Material color must contain three values between 0 and 1')
        if not 0<=float(spec.get('roughness',.8))<=1:raise MapError('Invalid material roughness')
