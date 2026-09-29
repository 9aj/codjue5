using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
namespace Husky {
    // Entity metadata only: no model meshes, scripts or textures are loaded.
    public static class MapEntities {
        public static List<Dictionary<string,string>> Parse(string text) {
            var tokens = new List<string>();
            int offset=0;
            var lexer=new Regex(@"\G\s*(?:(//[^\r\n]*(?:\r?\n|$))|([{}])|""((?:\\.|[^""\\])*)"")");
            while(offset<text.Length) {
                if(string.IsNullOrWhiteSpace(text.Substring(offset))) break;
                var match=lexer.Match(text,offset);
                if(!match.Success) throw new InvalidDataException("Invalid map entity syntax at character "+offset);
                offset=match.Index+match.Length;
                if(match.Groups[1].Success) continue;
                tokens.Add(match.Groups[2].Success ? match.Groups[2].Value : "q"+match.Groups[3].Value);
            }
            var result=new List<Dictionary<string,string>>(); int i=0;
            while(i<tokens.Count) {
                if(tokens[i++]!="{") throw new InvalidDataException("Expected entity opening brace");
                var entity=new Dictionary<string,string>(StringComparer.Ordinal);
                while(i<tokens.Count && tokens[i]!="}") {
                    if(i+1>=tokens.Count || !tokens[i].StartsWith("q") || !tokens[i+1].StartsWith("q")) throw new InvalidDataException("Expected entity key/value pair");
                    string key=tokens[i++].Substring(1),value=tokens[i++].Substring(1);
                    if(entity.ContainsKey(key)) throw new InvalidDataException("Duplicate entity key: "+key+"; raw text preserved");
                    entity.Add(key,value);
                }
                if(i>=tokens.Count) throw new InvalidDataException("Unclosed entity");
                i++; result.Add(entity);
            }
            return result;
        }
        public static void Save(string prefix,string text) {
            File.WriteAllText(prefix+"_mapEnts.txt",text);
            var entities=Parse(text);
            File.WriteAllText(prefix+"_entities.json",ExportContext.Json(new {
                schema_version=1,coordinates="COD4 source coordinates; multiply positions by 2.54 for cm, then apply verified axis mapping",
                note="Properties retained as source text, including escape sequences. Model keys are references only. Trigger shapes and scripted behaviour require reconstruction; entities may not include script-created spawns/teleports.",
                entities=entities.Select((e,index)=>new {index=index,category=Category(e),properties=e}).ToArray()
            }));
            File.WriteAllText(prefix+"_worldsettings.json",ExportContext.Json(entities.FirstOrDefault(e=>e.ContainsKey("classname") && e["classname"]=="worldspawn") ?? new Dictionary<string,string>()));
        }
        public static string Category(Dictionary<string,string> e) {
            string c=e.ContainsKey("classname") ? e["classname"] : "";
            if(c=="worldspawn") return "world";
            if(c.StartsWith("mp_") || c.StartsWith("info_player_")) return "spawn_candidate";
            if(c.StartsWith("trigger_")) return "trigger";
            if(c.Contains("teleport")) return "teleport_candidate";
            if(c=="script_origin" || c=="info_null" || c=="info_notnull") return "marker";
            return "other";
        }
    }
}
