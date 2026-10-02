"""Safe command generation and structural validation for live IW3xo exports."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from .parser import parse, MapError


def export_config(load_frames=600, collision_frames=180):
    # Individual waits also work on clients that do not implement `wait N`.
    if not 1 <= load_frames <= 36000 or not 1 <= collision_frames <= 36000:
        raise ValueError('Frame delays must be between 1 and 36000')
    commands=['wait']*load_frames+['r_drawCollision 3']+['wait']*collision_frames
    commands += ['mapexport_useFilters 0','mapexport_writeTriangles 1',
                 'mapexport_writeQuads 1','mapexport_writeEntities 1',
                 'mapexport_writeModels 1','mapexport_writeDynModels 1','mapexport']
    return '\n'.join(commands)+'\n'


def validate_export(path):
    path=Path(path)
    if not path.is_file() or path.stat().st_size < 32:raise MapError('Missing or empty map export')
    text=path.read_text(encoding='utf-8-sig')
    if not re.match(r'\s*iwmap\s+4\b',text):raise MapError('Export is not an iwmap 4 file')
    entities,objects,unsupported=parse(text)
    if not objects:raise MapError('Export contains no brushes or patches')
    if not any(e['properties'].get('classname')=='worldspawn' for e in entities):raise MapError('Export has no worldspawn')
    return {'status':'validated_capture','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'source_objects':len(objects),'entities':len(entities),
            'unsupported_objects':len(unsupported)}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['config','validate'])
    parser.add_argument('path',type=Path)
    parser.add_argument('--load-frames',type=int,default=600)
    parser.add_argument('--collision-frames',type=int,default=180)
    args=parser.parse_args()
    if args.command=='config':args.path.write_text(export_config(args.load_frames,args.collision_frames),encoding='ascii')
    else:print(json.dumps(validate_export(args.path)))
