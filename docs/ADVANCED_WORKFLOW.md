# From greybox to playable map

These are separate stages. Preserve a working checkpoint after each. The [reference catalogue](../reference/README.md) identifies the original implementation scripts and the configuration they need.

## Collision

Our Tunnel pipeline decoded the compiled map's collision data, rather than generating a convex hull around the render mesh.

1. Hash the original `.ff`. Match it to the exact profile before interpreting offsets.
2. Decode axis-aligned solid/player-clip brushes into boxes. Decode sloped brushes from their planes into convex hulls; their bounding boxes are not accurate replacements.
3. Reconstruct terrain triangles and model collision separately.
4. Use the same units and axis convention as the render import.
5. Keep collision actors hidden, with rendering disabled, and visible render actors non-colliding. Avoid simultaneous provisional render collision and recovered collision.
6. Trace samples through faces, across slopes and onto terrain. Check for cracks, unexpected solids, low ceilings and reversed normals.
7. Test movement with your actual player controller. COD4 movement is not reproduced simply by importing COD4 geometry into UE's default character.

The reference Tunnel extractor accepts this exact source SHA-256:

```text
5e6b87d5f96320669af9968d9cc14aec805e41e4159e0077251dc92e97172ee9
```

It is a profile identifier, not a download location. Do not remove the hash check or substitute another map's offsets. A new fastfile requires its own structural validation, including counts, pointer ranges, planes and bounds. The supporting OpenAssetTools/CoD4x research is credited in [CREDITS.md](../CREDITS.md).

## Static models

With the same map still loaded, the core tool can capture static-model buffers separately:

```powershell
$gameProcessId = 1234 # Current PID from JumpConvert.exe list
$mapName = 'mp_tunnel'
& .\pipeline\bin\JumpConvert.exe capture-models $gameProcessId $mapName (Join-Path $PWD 'artifacts')
```

The new `models-...` directory contains raw model buffers and capture metadata. Check its `status.json` for `captured` before attempting decoding. This command does not produce ready-made Unreal assets or import textures.

Tunnel's decoder in `reference/pipeline/decode_tunnel_models.py` demonstrates LOD0 vertex/index decoding, UV/normal handling and bounds checks. Configure `SOURCE` to your model capture. It is validated against that map/build, not every COD4 model format.

Import meshes once, then place instances using source position, rotation and scale. Apply the 2.54 scale/axis conversion exactly once. Preserve unusually scaled instances: Tunnel contained a very large palm. Captured Tunnel vertices were already in model space; applying base-bone transforms again double-transformed them.

Compare model bounds and silhouettes in both games. Use recovered model collision or deliberately authored collision, and record any difference. Replacement materials do not automatically clear rights to the underlying model geometry.

## Gameplay entities and teleports

The exporter retains entity properties, including origins, angles, targets and trigger model references. These are metadata, not executable gameplay.

For a simple teleport in your own UE project:

1. Create an Actor Blueprint with a Box Collision component.
2. Set its location and box half-extents from the decoded trigger bounds.
3. Enable overlap events and use a trigger collision profile compatible with your pawn.
4. On Begin Overlap, filter to the intended player/pawn and call your movement system's teleport/reset function, or UE's appropriate teleport operation.
5. Convert and set the destination position; explicitly decide how velocity and camera direction should behave.
6. Recreate source timing and destination view angles if those matter. Prevent accidental repeated overlap loops.
7. Check the destination floor/headroom and test entry at normal movement speed.

`place_tunnel_teleports.py` used a local `/Descent/Generated/BP_DescentReturnTeleport` template and Blueprint graph-editing APIs. They are not part of this public repository or a promise that a clean UE installation can run the script. Use it to understand the mapping, then implement your own project-specific actor.

The original Tunnel pass had six tested teleports. Seven interaction triggers and some source timing/view-angle behaviour remained unfinished. Script-created logic must be inspected separately from map entity text.

## Materials and atmosphere

Populate `material-replacements.json` with source identifiers, replacement asset names, tiling, provenance and licence details. Download texture assets directly from their credited source; no originals or replacement pixels are shipped here.

For the example cave treatment:

- Use scanned rock colour, normal and roughness/AO maps with consistent real-world tiling.
- World-space/triplanar projection can reduce stretching across imported faces; use approximately 1.8–2.2 m repeats as an initial artistic setting, then inspect at player height.
- Use stronger normal detail on walls and gentler normals on landing surfaces. Avoid displacement that changes jump geometry unintentionally.
- Use local light pools, restrained ambient light and controlled exposure. Inspect dark passages and bright wall hotspots rather than judging a single screenshot.
- Add decorative timber or rock detail with collision disabled unless it is an intentional gameplay change.
- Profile the whole route and a packaged build. Large monolithic meshes and many shadow-casting lights may need partitioning and optimisation.

The 4K Tunnel material script expects a local `reference/artifacts/tunnel-pbr/manifest.json` array with one entry per texture. Example shape (repeat for Diffuse, nor_dx and arm for each asset):

```json
[
  {
    "asset": "rock_boulder_cracked",
    "map": "Diffuse",
    "file": "C:/YourAssets/rock_boulder_cracked_diff_4k.jpg",
    "source": "https://polyhaven.com/a/rock_boulder_cracked",
    "license": "CC0"
  }
]
```

This shows the schema, not a complete manifest. The script requires all three map types for `rock_boulder_cracked`, `rock_boulder_dry` and `wooden_rough_planks`. Normal maps must use the expected DirectX convention; colour is sRGB, normals and masks are linear. Wait for texture compilation/streaming before judging resolution: initial queries can report temporary low dimensions.

## Deliberate geometry edits

Keep the original mesh asset. Make an edited copy, update visible faces and matching collision, and record the edit in source coordinates. Do not stack steps on top of an unchanged blocking floor if they need to descend below it.

The Tunnel staircase example clipped a local rectangle out of two render surfaces, split two collision boxes into preserved remainder pieces, and inserted three solid treads. A remaining front-face strip was caught and removed during visual review. Runtime height/riser/clearance probes were then run. That test does not certify the entire route.

## Release checklist

- Full route tested using the intended movement settings, including teleports and resets.
- No missing material slots, unexpected transparent surfaces, invalid model scales or sky shells.
- Creator credits and third-party asset provenance complete.
- Packaged/cooked build tested independently of the editor.
- Performance measured in representative sections, not only at spawn.
- Separate backups of source assets, edited assets and reports.
- Publish this source repository separately from the map package; only distribute content for which you have the necessary permission.
