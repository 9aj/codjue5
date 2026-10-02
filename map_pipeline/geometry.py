"""Convex plane-brush reconstruction, independent of map names and game processes."""
import argparse, collections, hashlib, itertools, json, math, pathlib, re

def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def reconstruct(sides):
    planes=[]
    for points,material in sides:
        n=cross(sub(points[1],points[0]),sub(points[2],points[0]))
        length=math.sqrt(dot(n,n))
        if length<1e-8: continue
        n=tuple(v/length for v in n); plane=(n,dot(n,points[0]))
        if not any(dot(sub(n,pn),sub(n,pn))<1e-10 and abs(plane[1]-pd)<0.01 for pn,pd in planes): planes.append(plane)
    # IW3XO plane points wind towards the interior. Test both conventions,
    # accepting only an intersection with every face represented.
    for sign in (-1,1):
        ps=[(tuple(sign*x for x in n),sign*d) for n,d in planes]
        vertices=[]
        for (a,da),(b,db),(c,dc) in itertools.combinations(ps,3):
            bc=cross(b,c);det=dot(a,bc)
            if abs(det)<1e-8: continue
            ca=cross(c,a);ab=cross(a,b)
            v=tuple((da*bc[k]+db*ca[k]+dc*ab[k])/det for k in range(3))
            if all(dot(n,v)<=d+0.001 for n,d in ps) and not any(dot(sub(v,w),sub(v,w))<0.0001 for w in vertices): vertices.append(v)
        if len(vertices)<4: continue
        faces=[];active=[]
        for n,d in ps:
            ids=[i for i,v in enumerate(vertices) if abs(dot(n,v)-d)<0.025]
            if len(ids)<3: continue
            center=tuple(sum(vertices[i][k] for i in ids)/len(ids) for k in range(3))
            axis=cross(n,(1,0,0) if abs(n[0])<0.9 else (0,1,0));other=cross(n,axis)
            ids.sort(key=lambda i:math.atan2(dot(sub(vertices[i],center),other),dot(sub(vertices[i],center),axis)))
            area=sum(math.sqrt(dot(cross(sub(vertices[ids[j]],vertices[ids[0]]),sub(vertices[ids[j+1]],vertices[ids[0]])),cross(sub(vertices[ids[j]],vertices[ids[0]]),sub(vertices[ids[j+1]],vertices[ids[0]])))) for j in range(1,len(ids)-1))
            if area<0.01 or any(set(ids)==set(f) for f in faces):continue
            faces.append(ids);active.append((n,d))
        if faces:
            edges=collections.Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1]))
            if all(count==2 for count in edges.values()) and len(vertices)-len(edges)+len(faces)==2: return vertices,faces,active
    raise ValueError('No closed convex intersection with all planes represented')
