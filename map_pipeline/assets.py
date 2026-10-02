"""Optional asset staging: image/script files and explicitly supported IW3 formats."""
import hashlib,json,re,struct,zipfile,zlib
from pathlib import Path,PurePosixPath
from .parser import MapError


def decode_bc1_tga(data):
    if len(data)<28 or data[:4]!=b'IWi\x06' or data[4]!=11 or not data[5]&2:
        raise MapError('IWI decoder supports version 6, BC1/DXT1, no-mipmap 2D images only')
    width,height,depth=struct.unpack_from('<HHH',data,6)
    size=((width+3)//4)*((height+3)//4)*8
    if depth!=1 or not width or not height or width*height>16_777_216 or len(data)!=28+size:
        raise MapError('Invalid/unsupported IWI size, mipmaps or depth')
    def rgb(value):return [((value>>11)&31)*255//31,((value>>5)&63)*255//63,(value&31)*255//31,255]
    pixels=bytearray(width*height*4);offset=28
    for by in range((height+3)//4):
        for bx in range((width+3)//4):
            a,b,bits=struct.unpack_from('<HHI',data,offset);offset+=8
            palette=[rgb(a),rgb(b)]
            if a>b:
                palette+=[[((2*palette[0][k]+palette[1][k])//3) for k in range(3)]+[255],[(palette[0][k]+2*palette[1][k])//3 for k in range(3)]+[255]]
            else:palette+=[[(palette[0][k]+palette[1][k])//2 for k in range(3)]+[255],[0,0,0,0]]
            for y in range(4):
                for x in range(4):
                    if bx*4+x>=width or by*4+y>=height:continue
                    r,g,b,alpha=palette[(bits>>(2*(y*4+x)))&3];i=((by*4+y)*width+bx*4+x)*4
                    pixels[i:i+4]=bytes((b,g,r,alpha))
    return struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,width,height,32,0x28)+pixels


def script_texts(data):
    if data[:8]!=b'IWffu100' or len(data)<12 or struct.unpack_from('<I',data,8)[0]!=5:
        raise MapError('Source script extraction supports IWffu100/version 5 fastfiles only')
    decoder=zlib.decompressobj();payload=decoder.decompress(data[12:],128*1024*1024+1)
    if len(payload)>128*1024*1024 or not decoder.eof:raise MapError('Fastfile exceeds supported decompression size or is incomplete')
    result={}
    for m in re.finditer(rb'(?:maps|common_scripts)/[^\x00\s]+\.gsc\x00',payload):
        end=payload.find(b'\0',m.end())
        if end<0:continue
        text=payload[m.end():end]
        try:value=text.decode('ascii')
        except UnicodeDecodeError:continue
        if not re.search(r'\w+\s*\([^)]*\)\s*\{',value[:2000]):continue
        name=m.group()[:-1].decode('ascii')
        if '..' in PurePosixPath(name).parts:continue
        result[name]=value
    return result


def extract_assets(source,out):
    source,out=Path(source).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    report={'source':str(source),'extracted':[],'unsupported':[]}
    def write(name,data):
        parts=PurePosixPath(name.replace('\\','/')).parts
        if any(p in ('..','/') or ':' in p for p in parts):raise MapError('Unsafe archive path: '+name)
        path=out.joinpath(*parts).resolve()
        if not path.is_relative_to(out):raise MapError('Unsafe output path')
        if path.exists() and path.read_bytes()!=data:raise MapError('Refusing to replace different asset: '+str(path))
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        report['extracted'].append({'path':str(path),'sha256':hashlib.sha256(data).hexdigest()})
    if source.suffix.lower()=='.ff':
        for name,text in script_texts(source.read_bytes()).items():write('scripts/'+name,text.encode())
    elif source.suffix.lower() in ('.iwd','.zip'):
        with zipfile.ZipFile(source) as archive:
            for item in archive.infolist():
                if item.is_dir():continue
                if item.file_size>64*1024*1024:report['unsupported'].append({'path':item.filename,'reason':'Asset exceeds 64 MiB'});continue
                suffix=PurePosixPath(item.filename).suffix.lower()
                if suffix not in ('.iwi','.gsc','.tga','.png','.jpg','.jpeg','.dds'):continue
                data=archive.read(item)
                if suffix=='.iwi':
                    try:data=decode_bc1_tga(data)
                    except MapError as exc:report['unsupported'].append({'path':item.filename,'reason':str(exc)});continue
                    name=str(PurePosixPath(item.filename).with_suffix('.tga'))
                else:name=item.filename
                write(name,data)
    else:raise MapError('Asset input must be .iwd/.zip or supported .ff')
    (out/'asset-report.json').write_text(json.dumps(report,indent=2))
    return report
