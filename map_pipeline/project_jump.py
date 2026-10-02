"""Project Jump content-only plugin identity and preflight requirements."""
import json,re
from pathlib import Path
from .parser import MapError

def plugin_name(map_id):
    name=re.sub('[^A-Za-z0-9]','',map_id)
    if not name or not name[0].isalpha():raise MapError('Map plugin name must start with a letter')
    if name.lower() in ('aquatic','jumplevel2','tutorial','mainmenu'):raise MapError('Reserved shipped map name')
    return name

def layout(manifest):
    name=manifest['config'].get('plugin_name') or plugin_name(manifest['map_id'])
    plugin_name(name) # Also validate explicitly supplied reserved names.
    return name,'/'+name+'/Maps/'+name,'/'+name+'/Generated'

def install_content_plugin(project,manifest):
    name,level,destination=layout(manifest)
    folder=Path(project).resolve().parent/'Plugins'/name
    descriptor=folder/(name+'.uplugin');receipt=folder/'codjue5-owner.json'
    owner={'map_id':manifest['map_id'],'fingerprint':manifest['fingerprint']}
    if folder.exists():
        if not receipt.is_file() or json.loads(receipt.read_text())!=owner:raise MapError('Plugin is unowned or has different inputs: '+name)
        spec=json.loads(descriptor.read_text(encoding='utf-8-sig'))
        if spec.get('Modules') or not spec.get('CanContainContent'):raise MapError('Map plugin must be content-only')
    else:
        (folder/'Content'/'Maps').mkdir(parents=True)
        descriptor.write_text(json.dumps({'FileVersion':3,'Version':1,'VersionName':'1.0',
            'FriendlyName':name,'Description':'Converted COD4 map','Category':'Maps',
            'CanContainContent':True,'EnabledByDefault':True,'Installed':False},indent=2)+'\n')
        receipt.write_text(json.dumps(owner,indent=2)+'\n')
    return {'plugin':name,'level':level,'destination':destination,'folder':str(folder)}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('manifest');args=p.parse_args()
    from .__main__ import validate
    print(json.dumps(install_content_plugin(args.project,validate(args.manifest))))
