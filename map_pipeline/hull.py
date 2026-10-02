import itertools, math
from .geometry import cross, sub, dot

def cloud_hull(points):
    """Conservative fallback from exported face corners, explicitly flagged."""
    verts=list(dict.fromkeys(tuple(round(x,2) for x in p) for p in points));planes=[];faces=[]
    for a,b,c in itertools.combinations(verts,3):
        n=cross(sub(b,a),sub(c,a));length=math.sqrt(dot(n,n))
        if length<.0001:continue
        n=tuple(x/length for x in n);d=dot(n,a);distances=[dot(n,v)-d for v in verts]
        if min(distances)<-.01 and max(distances)>.01:continue
        if min(distances)>=-.01:n=tuple(-x for x in n);d=-d
        if any(dot(sub(n,p),sub(n,p))<1e-8 and abs(d-pd)<.02 for p,pd in planes):continue
        planes.append((n,d))
        axis=max(range(3),key=lambda k:abs(n[k]));axes=[k for k in range(3) if k!=axis]
        ids=[i for i,v in enumerate(verts) if abs(dot(n,v)-d)<.01]
        ids.sort(key=lambda i:(verts[i][axes[0]],verts[i][axes[1]]))
        def turn(i,j,k):
            a,b,c=verts[i],verts[j],verts[k]
            return (b[axes[0]]-a[axes[0]])*(c[axes[1]]-a[axes[1]])-(b[axes[1]]-a[axes[1]])*(c[axes[0]]-a[axes[0]])
        lower=[];upper=[]
        for i in ids:
            while len(lower)>1 and turn(lower[-2],lower[-1],i)<=.0001:lower.pop()
            lower.append(i)
        for i in reversed(ids):
            while len(upper)>1 and turn(upper[-2],upper[-1],i)<=.0001:upper.pop()
            upper.append(i)
        f=lower[:-1]+upper[:-1]
        if len(f)<3:continue
        if dot(cross(sub(verts[f[1]],verts[f[0]]),sub(verts[f[2]],verts[f[0]])),n)<0:f.reverse()
        faces.append(f)
    if len(faces)<4:raise ValueError('No 3D hull from source corners')
    return verts,faces
