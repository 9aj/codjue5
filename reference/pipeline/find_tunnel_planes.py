# Reference implementation: configure paths, source hashes and project dependencies first.
import pathlib,struct,math,json
p=pathlib.Path('artifacts/mp_tunnel/intake/decompressed.bin');d=p.read_bytes()
# Locate complete sequences of stock cplane_s records; candidates need all2240.
patterns=[struct.pack('<3f',*v) for v in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]]
starts=set()
for pat in patterns:
 o=d.find(pat)
 while o>=0:
  starts.add(o);o=d.find(pat,o+1)
def valid(o):
 if o+20>len(d):return False
 x,y,z,dist,t,s=struct.unpack_from('<4fBB',d,o)
 return all(math.isfinite(v) for v in (x,y,z,dist)) and abs(x*x+y*y+z*z-1)<.0001 and abs(dist)<200000 and t<=3 and s<8 and s==sum((1<<i) for i,v in enumerate((x,y,z)) if v<0)
runs=[];covered=set()
for o in sorted(starts):
 if o in covered:continue
 n=0
 while valid(o+n*20):covered.add(o+n*20);n+=1
 if n>=100:runs.append((o,n))
print(runs)
pathlib.Path('artifacts/tunnel-plane-array-candidates.json').write_text(json.dumps(runs))
