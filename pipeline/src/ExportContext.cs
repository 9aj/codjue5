using System;
using System.IO;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
namespace Husky {
    public static class ExportContext {
        public static string Map;
        public static string Root;
        public static bool Completed;
        public static bool IncludeModelPlacements;
        public static string Output(string map) {
            ValidateMap(map);
            if(map != Map) throw new InvalidDataException("Loaded map is " + map + "; expected " + Map);
            return Path.Combine(Root,map);
        }
        public static void ValidateMap(string map) {
            if(map == null || !Regex.IsMatch(map,@"\Amp_[A-Za-z0-9_]{1,80}\z")) throw new ArgumentException("Map must be a plain mp_ identifier");
        }
        public static void Count(int count,int max,string name) {
            if(count < 0 || count > max) throw new InvalidDataException("Invalid " + name + " count: " + count);
        }
        public static string Json(object value) { return new JavaScriptSerializer { MaxJsonLength=int.MaxValue }.Serialize(value); }
    }
}
