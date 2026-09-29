# Reference implementation: configure paths, source hashes and project dependencies first.
"""Keep dark rock silhouettes readable without flattening local light contrast."""
import json,pathlib,unreal as u
root=pathlib.Path(__file__).resolve().parents[1];lib=u.MaterialEditingLibrary
for path in json.loads((root/'artifacts/tunnel-cave-style.json').read_text())['materials']:
    mat=u.load_asset(path)
    normal=lib.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL)
    code=normal.get_editor_property('code')
    code=code.replace('float3 grad=broad.yzw*.34+mid.yzw*.29+fine.yzw*.17;', 'float4 micro=r.ng(P*.65+113); float3 grad=broad.yzw*.24+mid.yzw*.29+fine.yzw*.26+micro.yzw*.12;')
    normal.set_editor_property('code',code)
    base=lib.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)
    assert base
    multiply=lib.create_material_expression(mat,u.MaterialExpressionMultiply)
    multiply.set_editor_property('const_b',.022)
    assert lib.connect_material_expressions(base,'',multiply,'A')
    assert lib.connect_material_property(multiply,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat)
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
(root/'artifacts/tunnel-cave-readability.json').write_text(json.dumps({'saved':True,'rock_color_visibility_floor':.022,'purpose':'Subtle shadow detail; local lights remain the dominant illumination'}))
