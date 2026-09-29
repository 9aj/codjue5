# Reference implementation: configure paths, source hashes and project dependencies first.
"""Original bevelled timber beam, centimetres, no collision geometry."""
import itertools, math, pathlib
root=pathlib.Path(__file__).resolve().parents[1]
verts=[]
for signs in itertools.product((-1,1),repeat=3):
    for axis in range(3):verts.append(tuple(signs[i]*(50 if i==axis else 48.5) for i in range(3)))
planes=[]
for count,dist in ((1,50),(2,98.5),(3,147)):
    for axes in itertools.combinations(range(3),count):
        for signs in itertools.product((-1,1),repeat=count):
            n=[0,0,0]
            for a,s in zip(axes,signs):n[a]=s
            planes.append((n,dist))
dot=lambda a,b:sum(x*y for x,y in zip(a,b))
cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
unit=lambda a:tuple(x/math.sqrt(dot(a,a)) for x in a)
lines=['# Original Tunnel bevelled timber; Z is beam length'];index=1;triangles=0
for normal,dist in planes:
    points=[p for p in verts if abs(dot(normal,p)-dist)<.001]
    n=unit(normal);center=tuple(sum(p[i] for p in points)/len(points) for i in range(3))
    tangent=unit(cross(n,(0,0,1) if abs(n[2])<.9 else (0,1,0)));bitangent=cross(n,tangent)
    points.sort(key=lambda p:math.atan2(dot(tuple(p[i]-center[i] for i in range(3)),bitangent),dot(tuple(p[i]-center[i] for i in range(3)),tangent)))
    for p in points:
        lines.append('v '+' '.join(map(str,p)))
        # Plank grain runs horizontally in the scan; long beam axis follows U.
        lines.append('vt %.6f %.6f'%((p[2]+50)/100*2.5,.06+(dot(p,tangent)+70)/140*.10))
        lines.append('vn '+' '.join(map(str,n)))
    for j in range(1,len(points)-1):
        lines.append('f '+' '.join('%d/%d/%d'%(k,k,k) for k in (index,index+j,index+j+1)));triangles+=1
    index+=len(points)
path=root/'artifacts/tunnel-pbr/SM_TunnelTimberBeam.obj';path.write_text('\n'.join(lines));print(path,triangles)
