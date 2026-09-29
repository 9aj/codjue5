// Read-only IW3 static-model capture. Layouts: audit/IW3_Assets.h.
// Capture raw geometry buffers for offline decoding; never read texture pixels.
using System;
using System.IO;
using System.Diagnostics;
using System.Collections.Generic;
using Husky;
using PhilLibX.IO;

static class ModelCapture {
    static int I(byte[] b,int o) { return BitConverter.ToInt32(b,o); }
    static int U(byte[] b,int o) { return BitConverter.ToUInt16(b,o); }
    static float F(byte[] b,int o) { float v=BitConverter.ToSingle(b,o); if(float.IsNaN(v)||float.IsInfinity(v)) throw new InvalidDataException("Nonfinite transform"); return v; }
    static void Save(string path,object value) { File.WriteAllText(path,ExportContext.Json(value)); }
    public static void Run(int pid,string map,string root) {
        ExportContext.ValidateMap(map);
        string output=Path.Combine(Path.GetFullPath(root),map,"models-"+DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffZ"));
        Directory.CreateDirectory(output);
        Save(Path.Combine(output,"status.json"),new {status="capturing"});
        try {
            using(var process=Process.GetProcessById(pid)) {
                if(process.ProcessName!="iw3mp") throw new InvalidDataException("Expected iw3mp");
                using(var r=new ProcessReader(process)) {
                    ModernWarfare.GfxMap world=default(ModernWarfare.GfxMap); bool found=false; long selectedPool=0;
                    foreach(long pool in new long[]{0x7265E0,0x71E5D8}) {
                        try {world=ModernWarfare.ValidateLoadedMap(r,pool,map); found=true; selectedPool=pool; break;} catch(IOException) {}
                    }
                    if(!found) throw new InvalidDataException("No validated world");
                    File.WriteAllBytes(Path.Combine(output,"world-header.bin"),r.ReadBytes(r.ReadInt32(selectedPool+0x40),0x2a0));
                    Save(Path.Combine(output,"layout.json"),new {model_count=world.GfxStaticModelsCount,count_offset="0x244",placement_stride=76});
                    Console.WriteLine("Capturing "+world.GfxStaticModelsCount+" static model instances.");
                    byte[] placements=r.ReadBytes(world.GfxStaticModelsPointer,checked(world.GfxStaticModelsCount*76));
                    File.WriteAllBytes(Path.Combine(output,"placements.bin"),placements);
                    // Reject an inconsistent record array before dereferencing model pointers.
                    for(int i=0;i<world.GfxStaticModelsCount;i++) {
                        int o=i*76;
                        for(int row=0;row<3;row++) for(int col=0;col<3;col++) {
                            double dot=0;
                            for(int k=0;k<3;k++) dot+=F(placements,o+16+row*12+k*4)*F(placements,o+16+col*12+k*4);
                            if(Math.Abs(dot-(row==col?1:0))>.002) throw new InvalidDataException("Invalid rotation basis at model instance "+i);
                        }
                    }
                    var instances=new List<object>(); var models=new List<object>(); var ids=new Dictionary<int,int>();
                    for(int i=0;i<world.GfxStaticModelsCount;i++) {
                        int o=i*76, ptr=I(placements,o+56); int id;
                        var origin=new[]{F(placements,o+4),F(placements,o+8),F(placements,o+12)};
                        var axis=new float[9]; for(int k=0;k<9;k++) axis[k]=F(placements,o+16+k*4);
                        float scale=F(placements,o+52); if(scale<=0||scale>1000) throw new InvalidDataException("Invalid instance scale");
                        if(!ids.TryGetValue(ptr,out id)) {
                            id=ids.Count; ids.Add(ptr,id);
                            byte[] h=r.ReadBytes(ptr,220); string name=r.ReadNullTerminatedString(I(h,0));
                            int count=h[6], first=U(h,46), lodCount=U(h,44);
                            if(count==0||lodCount==0||first+lodCount>count) throw new InvalidDataException("Invalid LOD: "+name);
                            string dir=Path.Combine(output,"model_"+id.ToString("D4")); Directory.CreateDirectory(dir);
                            File.WriteAllBytes(Path.Combine(dir,"header.bin"),h);
                            if(h[4]>0) File.WriteAllBytes(Path.Combine(dir,"base-matrices.bin"),r.ReadBytes(I(h,28),h[4]*32));
                            byte[] surfaces=r.ReadBytes(I(h,32),count*56), handles=r.ReadBytes(I(h,36),count*4);
                            File.WriteAllBytes(Path.Combine(dir,"surfaces.bin"),surfaces);
                            var surfaceInfo=new List<object>();
                            for(int s=first;s<first+lodCount;s++) {
                                int so=s*56,nv=U(surfaces,so+2),nt=U(surfaces,so+4),rigids=I(surfaces,so+32);
                                ExportContext.Count(rigids,65535,"rigid groups");
                                if(nv==0||nt==0) throw new InvalidDataException("Empty model surface");
                                string prefix=Path.Combine(dir,"surface_"+s);
                                File.WriteAllBytes(prefix+"_vertices.bin",r.ReadBytes(I(surfaces,so+28),nv*32));
                                byte[] triangles=r.ReadBytes(I(surfaces,so+12),nt*6);
                                for(int t=0;t<nt*3;t++) if(U(triangles,t*2)>=nv) throw new InvalidDataException("Model triangle out of bounds");
                                File.WriteAllBytes(prefix+"_triangles.bin",triangles);
                                if(rigids>0) File.WriteAllBytes(prefix+"_rigids.bin",r.ReadBytes(I(surfaces,so+36),rigids*12));
                                string material=r.ReadNullTerminatedString(r.ReadInt32(I(handles,s*4)));
                                surfaceInfo.Add(new {index=s,vertices=nv,triangles=nt,rigid_groups=rigids,deformed=surfaces[so+1]!=0,material=material});
                            }
                            var modelInfo=new {id=id,name=name,bones=h[4],root_bones=h[5],surfaces=surfaceInfo};
                            models.Add(modelInfo);
                            Save(Path.Combine(dir,"model.json"),modelInfo);
                        }
                        instances.Add(new {index=i,model_id=id,origin_cod=origin,axis=axis,scale=scale});
                    }
                    Save(Path.Combine(output,"models.json"),new {map=map,units="COD4 units",to_cm=2.54,instances=instances,models=models,limitations=new[]{"Static draw models only; script-spawned models excluded","Raw capture requires offline decoding and transform verification","Model collision not captured"}});
                    Save(Path.Combine(output,"status.json"),new {status="captured",instances=instances.Count,models=models.Count});
                    Console.WriteLine("Model capture: "+output);
                }
            }
        } catch(Exception e) {Save(Path.Combine(output,"status.json"),new {status="failed",error=e.ToString()}); throw;}
    }
}
