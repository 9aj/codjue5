import argparse
import json
from pathlib import Path
import sys
from .prepare import prepare, digest
from .parser import MapError


def read_config(path):
    if not path:return {}
    path=Path(path).resolve()
    config=json.loads(path.read_text(encoding='utf-8-sig'))
    for key in ('scripts',):
        if config.get(key):config[key]=str((path.parent/config[key]).resolve())
    if config.get('texture_roots'):config['texture_roots']=[str((path.parent/v).resolve()) for v in config['texture_roots']]
    for spec in config.get('materials',{}).values():
        if spec.get('texture'):spec['texture']=str((path.parent/spec['texture']).resolve())
    sky=config.get('sky',{})
    for key in ('cubemap',):
        if sky.get(key):sky[key]=str((path.parent/sky[key]).resolve())
    if sky.get('faces'):sky['faces']={k:str((path.parent/v).resolve()) for k,v in sky['faces'].items()}
    return config


def validate(path):
    path=Path(path).resolve();data=json.loads(path.read_text(encoding='utf-8-sig'))
    if data.get('schema_version')!=1:raise MapError('Unsupported manifest schema')
    if digest(path.parent/'source.map')!=data['source_sha256']:raise MapError('Source snapshot changed')
    for filename,expected in data.get('dependencies',{}).items():
        if digest(filename)!=expected:raise MapError('Input dependency changed: '+filename)
    ids=set()
    for row in data['objects']:
        if row['id'] in ids:raise MapError('Duplicate object id')
        ids.add(row['id'])
        obj=(path.parent/row['obj']).resolve()
        if obj.parent!=path.parent or digest(obj)!=row['obj_sha256']:raise MapError('Invalid or changed object: '+row['id'])
    for spec in data['materials'].values():
        if spec.get('texture') and digest(spec['texture'])!=spec['texture_sha256']:raise MapError('Texture changed: '+spec['texture'])
    if len(ids)!=data['summary']['prepared_objects']:raise MapError('Manifest count mismatch')
    return data


def main():
    parser=argparse.ArgumentParser(description='COD4 .map to independent UE actors/assets')
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('prepare');p.add_argument('source');p.add_argument('--output',required=True);p.add_argument('--config');p.add_argument('--profile',choices=['generic','project_jump']);p.add_argument('--map-id');p.add_argument('--allow-partial',action='store_true')
    p=commands.add_parser('validate');p.add_argument('manifest')
    p=commands.add_parser('extract-assets');p.add_argument('source');p.add_argument('--output',required=True)
    args=parser.parse_args()
    try:
        if args.command=='extract-assets':
            from .assets import extract_assets
            report=extract_assets(args.source,args.output)
            print(json.dumps({'extracted':len(report['extracted']),'unsupported':len(report['unsupported'])}));return 0
        if args.command=='prepare':
            config=read_config(args.config)
            if args.profile:config['profile']=args.profile
            if args.map_id:config.setdefault('map_id',args.map_id)
            data=prepare(args.source,args.output,config)
            print(json.dumps({'status':data['status'],'summary':data['summary'],'issues':len(data['issues']),'fallback_hulls':len(data['fallback_hulls']),'unresolved_gameplay':len(data['gameplay']['unresolved'])},indent=2))
            return 2 if data['issues'] and not args.allow_partial else 0
        data=validate(args.manifest);print(json.dumps({'status':'validated','map_id':data['map_id'],'objects':len(data['objects'])}));return 0
    except (OSError,ValueError,KeyError) as exc:
        print('Conversion failed: '+str(exc),file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
