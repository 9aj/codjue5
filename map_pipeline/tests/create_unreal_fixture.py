"""Create an isolated C++ Unreal validation project; no local game assets required."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from map_pipeline.tests.test_conversion import fixture

root=Path(__file__).resolve().parents[2]
(root/'map_pipeline/examples/fixture.map').write_text(fixture())
project=root/'artifacts/fixture-project';project.mkdir(parents=True,exist_ok=True)
(project/'CodMapFixture.uproject').write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Modules':[{'Name':'CodMapFixture','Type':'Runtime','LoadingPhase':'Default'}],'AdditionalPluginDirectories':[str(root/'unreal')],'Plugins':[{'Name':'CodMapRuntime','Enabled':True},{'Name':'PythonScriptPlugin','Enabled':True}]}))
source=project/'Source';module=source/'CodMapFixture';module.mkdir(parents=True,exist_ok=True)
(module/'CodMapFixture.Build.cs').write_text('''using UnrealBuildTool;
public class CodMapFixture : ModuleRules {
 public CodMapFixture(ReadOnlyTargetRules Target) : base(Target) {
  PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs;
  PublicDependencyModuleNames.AddRange(new[]{"Core","CoreUObject","Engine"});
 }
}''')
(module/'CodMapFixture.cpp').write_text('''#include "Modules/ModuleManager.h"
IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, CodMapFixture, "CodMapFixture");''')
for name,target in [('CodMapFixtureEditor','Editor'),('CodMapFixture','Game')]:
    (source/(name+'.Target.cs')).write_text('''using UnrealBuildTool;
public class %sTarget : TargetRules {
 public %sTarget(TargetInfo Target) : base(Target) {
  Type=TargetType.%s;
  DefaultBuildSettings=BuildSettingsVersion.V7;
  IncludeOrderVersion=EngineIncludeOrderVersion.Latest;
  ExtraModuleNames.Add("CodMapFixture");
 }
}'''%(name,name,target))
print(project/'CodMapFixture.uproject')
