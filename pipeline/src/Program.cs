using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;
using Husky;
using PhilLibX.IO;

class Program {
    const string Revision = "9a3accfb75c9a2f9780446c2b7bef040570357cf";
    static int Main(string[] args) {
        CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
        CultureInfo.DefaultThreadCurrentUICulture = CultureInfo.InvariantCulture;
        try {
            if(args.Length == 4 && args[0] == "capture-models") { ModelCapture.Run(int.Parse(args[1]),args[2],args[3]); return 0; }
            if(args.Length == 1 && args[0] == "self-test") { SelfTest(); return 0; }
            if(args.Length == 1 && args[0] == "list") {
                foreach(var p in Process.GetProcessesByName("iw3mp")) using(p) Console.WriteLine(p.Id + "\t" + ProcessReader.ExecutablePath(p.Id));
                return 0;
            }
            if(args.Length == 2 && args[0] == "validate") { Console.WriteLine(ExportContext.Json(ValidateObj(args[1]))); return 0; }
            if(args.Length == 4 && args[0] == "prepare-geometry") {
                ExportContext.ValidateMap(args[2]);
                string output=Path.GetFullPath(args[3]);
                if(Directory.Exists(output)) throw new IOException("Choose a new output directory; existing preparation will not be overwritten");
                var validation=ValidateObj(args[1]);
                MakeGreybox(args[1],output,args[2]);
                Json(Path.Combine(output,"validation.json"),validation);
                Json(Path.Combine(output,"status.json"),new {schema_version=1,status="validated_geometry_only",source_obj=Path.GetFullPath(args[1]),source_sha256=Hash(args[1]),models="not recovered",visual_validation="pending",ue5_import="not_run"});
                Console.WriteLine("Prepared geometry only: "+output);
                return 0;
            }
            if((args.Length == 5 || (args.Length == 6 && args[5] == "--include-model-placements")) && args[0] == "export") {
                ExportContext.IncludeModelPlacements=args.Length==6;
                Export(int.Parse(args[1]),args[2],args[3],args[4]); return 0;
            }
            Console.WriteLine("JumpConvert list | self-test | validate <obj> | export <PID> <expected-map> <source-map-directory> <output-root>\nExports geometry and metadata only. Does not launch COD4, download assets or export texture pixels/prop meshes.");
            return args.Length == 0 ? 0 : 2;
        } catch(Exception ex) { Console.Error.WriteLine("FAILED: " + ex.Message); return 1; }
    }
    static string Hash(string file) { using(var stream=File.OpenRead(file)) using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }
    static void Json(string path,object value) { File.WriteAllText(path,ExportContext.Json(value),new UTF8Encoding(false)); }
    static void Export(int pid,string map,string input,string root) {
        ExportContext.ValidateMap(map);
        input=Path.GetFullPath(input); root=Path.GetFullPath(root);
        if(root.Equals(input,StringComparison.OrdinalIgnoreCase) || root.StartsWith(input.TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Output must not be inside the input map directory");
        if(!File.Exists(Path.Combine(input,map+".ff"))) throw new FileNotFoundException("Expected map fastfile missing");
        using(var process=Process.GetProcessById(pid)) {
            if(process.ProcessName != "iw3mp") throw new ArgumentException("Only an explicitly selected iw3mp process is supported");
            string exe=ProcessReader.ExecutablePath(pid);
            string exeHash=Hash(exe);
            var inputs=Directory.GetFiles(input).Where(f=>f.EndsWith(".ff",StringComparison.OrdinalIgnoreCase)||f.EndsWith(".iwd",StringComparison.OrdinalIgnoreCase)).OrderBy(f=>f).Select(f=>new {file=Path.GetFileName(f),bytes=new FileInfo(f).Length,sha256=Hash(f)}).ToArray();
            string run=Path.Combine(root,map,DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffZ")+"-"+Guid.NewGuid().ToString("N").Substring(0,8));
            Directory.CreateDirectory(run);
            Json(Path.Combine(run,"status.json"),new {schema_version=1,status="extracting",map=map});
            try {
                ExportContext.Map=map; ExportContext.Root=Path.Combine(run,"raw"); ExportContext.Completed=false;
                // Probe only the two addresses in the reviewed upstream COD4 implementation.
                long pool=0;
                using(var reader=new ProcessReader(process)) {
                    var probes=new List<string>();
                    pool=ProbePools(candidate => { ModernWarfare.ValidateLoadedMap(reader,candidate,map); return true; }, message => { probes.Add(message); Console.WriteLine(message); });
                    Json(Path.Combine(run,"probe-diagnostics.json"),new {exe=exe,sha256=exeHash,probes=probes});
                    if(pool==0) throw new InvalidDataException("Unsupported COD4 memory layout. No export attempted; do not guess offsets.");
                    ModernWarfare.ExportBSPData(reader,pool,0,"mp",Console.WriteLine);
                }
                if(!ExportContext.Completed) throw new InvalidDataException("Exporter did not finish");
                string obj=Path.Combine(ExportContext.Root,map+".obj");
                var validation=ValidateObj(obj);
                Json(Path.Combine(run,"validation.json"),validation);
                MakeGreybox(obj,Path.Combine(run,"ue5"),map);
                File.Copy(Path.Combine(ExportContext.Root,map+"_entities.json"),Path.Combine(run,"ue5","gameplay-entities.json"));
                Json(Path.Combine(run,"manifest.json"),new {
                    schema_version=1,map=map,source_revision=Revision,exporter_sha256=Hash(System.Reflection.Assembly.GetExecutingAssembly().Location),
                    game=new {pid=pid,exe=exe,sha256=exeHash,asset_pool="0x"+pool.ToString("X")},inputs=inputs,
                    coordinates=new {mesh_units="centimetres",placement_units="COD4 units",placement_to_cm=2.54,axes="source axes preserved; UE import orientation requires calibration",uv="V flipped by C2M"},
                    model_placements_requested=ExportContext.IncludeModelPlacements,
                    limitations=new[]{"No texture pixels or prop meshes", "All material sort keys included; sky/decal/transparency surfaces require visual review", "Collision and movement not converted", "Layout consistency during export requires staying in the same map", "World settings and entities are metadata, not UE gameplay"},
                    artifacts=Directory.GetFiles(run,"*",SearchOption.AllDirectories).Where(f=>Path.GetFileName(f)!="status.json").OrderBy(f=>f).Select(f=>new {path=f.Substring(run.Length+1).Replace('\\','/'),sha256=Hash(f)}).ToArray()
                });
                Json(Path.Combine(run,"status.json"),new {schema_version=1,status="validated_export",map=map,ue5_import="not_run",visual_validation="pending"});
                Console.WriteLine("Validated export: " + run);
            } catch(Exception ex) { Json(Path.Combine(run,"status.json"),new {schema_version=1,status="failed",error=ex.Message,details=ex.ToString()}); Console.Error.WriteLine("Diagnostic run: " + run); throw; }
        }
    }
    static long ProbePools(Func<long,bool> probe,Action<string> log) {
        foreach(long candidate in new long[]{0x7265E0,0x7265E0-0x8008}) {
            try {
                bool match=probe(candidate);
                log("Pool 0x"+candidate.ToString("X")+": "+(match ? "validated map identity and geometry headers" : "map validation failed"));
                if(match) return candidate;
            } catch(InvalidDataException ex) { log("Pool 0x"+candidate.ToString("X")+": "+ex.Message); }
              catch(IOException ex) { log("Pool 0x"+candidate.ToString("X")+": "+ex.Message); }
        }
        return 0;
    }
    public static Dictionary<string,object> ValidateObj(string path) {
        int vertices=0,uvs=0,normals=0,faces=0;
        double[] min={double.PositiveInfinity,double.PositiveInfinity,double.PositiveInfinity},max={double.NegativeInfinity,double.NegativeInfinity,double.NegativeInfinity};
        var materials=new SortedSet<string>(StringComparer.Ordinal);
        foreach(string line in File.ReadLines(path)) {
            string[] p=line.Split(new[]{' ','\t'},StringSplitOptions.RemoveEmptyEntries);
            if(p.Length==0 || p[0].StartsWith("#")) continue;
            if(p[0]=="v" || p[0]=="vn" || p[0]=="vt") {
                int dimensions=p[0]=="vt" ? 2 : 3;
                if(p.Length!=dimensions+1) throw new InvalidDataException("Unexpected vertex format");
                for(int i=0;i<dimensions;i++) {
                    double v=double.Parse(p[i+1],CultureInfo.InvariantCulture);
                    if(double.IsNaN(v)||double.IsInfinity(v)) throw new InvalidDataException("Nonfinite coordinate");
                    if(p[0]=="v") { min[i]=Math.Min(min[i],v); max[i]=Math.Max(max[i],v); }
                }
                if(p[0]=="v") vertices++; else if(p[0]=="vn") normals++; else uvs++;
            } else if(p[0]=="f") {
                if(p.Length!=4) throw new InvalidDataException("Expected triangle");
                foreach(string index in p.Skip(1)) {
                    string[] parts=index.Split('/');
                    if(parts.Length!=3) throw new InvalidDataException("Missing face UV/normal");
                    int[] counts={vertices,uvs,normals};
                    for(int i=0;i<3;i++) { int n=int.Parse(parts[i]); if(n<1||n>counts[i]) throw new InvalidDataException("Out-of-range face index"); }
                }
                faces++;
            } else if(p[0]=="usemtl") {
                if(p.Length!=2) throw new InvalidDataException("Unsupported material name");
                materials.Add(p[1]);
            }
        }
        if(vertices==0||faces==0) throw new InvalidDataException("Empty geometry");
        return new Dictionary<string,object>{{"vertices",vertices},{"triangles",faces},{"uvs",uvs},{"normals",normals},{"bounds_cm",new[]{min,max}},{"materials",materials.ToArray()}};
    }
    static void MakeGreybox(string obj,string output,string map) {
        Directory.CreateDirectory(output);
        var materialNames=(string[])ValidateObj(obj)["materials"];
        var ids=materialNames.Select((name,index)=>new {name,index}).ToDictionary(x=>x.name,x=>"surface_"+x.index.ToString("D4"));
        using(var writer=new StreamWriter(Path.Combine(output,map+"_greybox.obj"),false,new UTF8Encoding(false))) {
            writer.WriteLine("mtllib " + map + "_greybox.mtl");
            foreach(string line in File.ReadLines(obj)) {
                if(line.StartsWith("mtllib ")||line.StartsWith("#")) continue;
                writer.WriteLine(line.StartsWith("usemtl ") ? "usemtl "+ids[line.Substring(7).Trim()] : line);
            }
        }
        using(var writer=new StreamWriter(Path.Combine(output,map+"_greybox.mtl"))) foreach(string id in ids.Values) writer.WriteLine("newmtl "+id+"\nKd 0.5 0.5 0.5\nillum 1\n");
        Json(Path.Combine(output,"material-replacements.json"),new {schema_version=1,map=map,materials=materialNames.Select(n=>new {
            source_material=n,slot=ids[n],replacement_asset="",description="",license="",provenance="",status="unassigned",tiling=1.0
        }).ToArray()});
    }
    static void SelfTest() {
        // Independent IW3 ABI offsets: smodelCount=0x244, surfaces=0x294,
        // smodelDrawInsts=0x29c. Distinguish count from decalSurfsBegin.
        var worldFixture=new byte[0x2a0];
        Array.Copy(BitConverter.GetBytes(10),0,worldFixture,0x244,4);
        Array.Copy(BitConverter.GetBytes(337),0,worldFixture,0x258,4);
        Array.Copy(BitConverter.GetBytes(0x123400),0,worldFixture,0x294,4);
        Array.Copy(BitConverter.GetBytes(0x567800),0,worldFixture,0x29c,4);
        var fixtureWorld=PhilLibX.ByteUtil.BytesToStruct<ModernWarfare.GfxMap>(worldFixture);
        if(fixtureWorld.GfxStaticModelsCount!=10 || fixtureWorld.GfxSurfacesPointer!=0x123400 || fixtureWorld.GfxStaticModelsPointer!=0x567800)
            throw new Exception("IW3 model count/pointer ABI regression");
        var entityFixture=MapEntities.Parse("// fixture\n{\"classname\" \"worldspawn\"}\n{\"classname\" \"mp_dm_spawn\" \"origin\" \"1 2 3\"}\n{\"classname\" \"trigger_multiple\" \"model\" \"*12\" \"target\" \"tele_dest\"}\n{\"classname\" \"script_origin\" \"targetname\" \"tele_dest\"}");
        if(entityFixture.Count!=4 || MapEntities.Category(entityFixture[1])!="spawn_candidate" || entityFixture[2]["model"]!="*12" || entityFixture[3]["targetname"]!="tele_dest") throw new Exception("Gameplay entity metadata lost");
        foreach(string malformed in new[]{"{\"classname\"}","{\"k\" \"v\"","{\"k\" \"v\" \"k\" \"w\"}"}) {
            bool rejected=false; try { MapEntities.Parse(malformed); } catch(InvalidDataException) { rejected=true; }
            if(!rejected) throw new Exception("Malformed entities accepted");
        }
        if(ExportContext.IncludeModelPlacements) throw new Exception("Prop extraction must default off");
        int attempts=0;
        long fallback=ProbePools(address => { attempts++; if(attempts==1) throw new InvalidDataException("Invalid range fixture"); return true; }, message => {});
        if(attempts!=2 || fallback!=0x7265E0-0x8008) throw new Exception("Invalid first pool prevented Steam fallback");
        if(ProbePools(address => { throw new IOException("Unreadable fixture"); }, message => {})!=0) throw new Exception("Unknown build accepted");
        foreach(string bad in new[]{"../mp_bad","mp_../bad","C:\\mp_bad","mp_bad/other","CON","mp_"}) {
            bool rejected=false; try { ExportContext.ValidateMap(bad); } catch(ArgumentException) { rejected=true; }
            if(!rejected) throw new Exception("Unsafe map identifier accepted");
        }
        string dir=Path.Combine(Path.GetTempPath(),"jumpconvert-test-"+Guid.NewGuid().ToString("N")); Directory.CreateDirectory(dir);
        string obj=Path.Combine(dir,"fixture.obj");
        string geometry="v 0 0 0\nv 2.54 0 0\nv 0 2.54 0\nvt 0 0\nvt 1 0\nvt 0 1\nvn 0 0 1\nusemtl original_concrete\nf 1/1/1 2/2/1 3/3/1\n";
        File.WriteAllText(obj,geometry);
        if((int)ValidateObj(obj)["triangles"]!=1) throw new Exception("Triangle validation failed");
        MakeGreybox(obj,Path.Combine(dir,"ue5"),"mp_fixture");
        ValidateObj(Path.Combine(dir,"ue5","mp_fixture_greybox.obj"));
        var json=new JavaScriptSerializer().DeserializeObject(File.ReadAllText(Path.Combine(dir,"ue5","material-replacements.json")));
        // Exercise the actual vendored output writer and replacement JSON serializer.
        var mesh=new WavefrontOBJ();
        mesh.Vertices.Add(new Vector3(0,0,0)); mesh.Vertices.Add(new Vector3(2.54,0,0)); mesh.Vertices.Add(new Vector3(0,2.54,0));
        for(int i=0;i<3;i++) { mesh.Normals.Add(new Vector3(0,0,1)); mesh.UVs.Add(new Vector2(0,0)); }
        mesh.AddMaterial(new WavefrontOBJ.Material("test_material") { DiffuseMap="original_texture" });
        var face=new WavefrontOBJ.Face("test_material");
        for(int i=0;i<3;i++) face.Vertices[i]=new WavefrontOBJ.Face.Vertex(i,i,i);
        mesh.Faces.Add(face);
        string written=Path.Combine(dir,"written.obj"); mesh.Save(written); ValidateObj(written);
        MakeGreybox(written,Path.Combine(dir,"written-greybox"),"mp_written");
        if(File.ReadAllText(Path.Combine(dir,"written-greybox","mp_written_greybox.mtl")).Contains("original_texture")) throw new Exception("Original texture leaked into greybox");
        var metadata=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(dir,"written_matdata.json")));
        if(!metadata.ContainsKey("Materials")) throw new Exception("Material serialization lost schema");
        ExportContext.Map="mp_expected"; ExportContext.Root=dir;
        bool mismatch=false; try { ExportContext.Output("mp_wrong"); } catch(InvalidDataException) { mismatch=true; }
        if(!mismatch) throw new Exception("Wrong map accepted");
        bool badStruct=false; try { PhilLibX.ByteUtil.BytesToStruct<GfxVertex>(new byte[1]); } catch(ArgumentException) { badStruct=true; }
        if(!badStruct) throw new Exception("Truncated native struct accepted");
        foreach(string bad in new[]{geometry.Replace("3/3/1","4/3/1"),geometry.Replace("2.54","NaN"),"# empty"}) {
            File.WriteAllText(obj,bad); bool rejected=false;
            try { ValidateObj(obj); } catch(InvalidDataException) { rejected=true; }
            if(!rejected) throw new Exception("Invalid geometry accepted");
        }
        Console.WriteLine("PASS: map identifiers/mismatch, valid triangle, invalid indices, nonfinite coordinates, empty geometry, native struct bounds, upstream OBJ writer, JSON schema and texture-free greybox. Fixtures: " + dir);
    }
}
