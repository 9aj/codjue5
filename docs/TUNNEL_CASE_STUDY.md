# Case study: mp_tunnel

This describes the local September 2026 conversion, not a downloadable finished map. The creator's permission was reported by the project owner. Original maps, props, captures and Unreal assets are excluded from this repository.

## Sequence

1. Extracted world geometry and entity metadata from the loaded COD4 map, validated it and prepared neutral material slots.
2. Converted positions consistently at 2.54 cm per CoD unit, with the tested legacy-import Y-axis mapping.
3. Recovered ten model instances: five crates, four palms and one rock. Retained their placements, rotations and scales. An initial memory-read failure was resolved before accepting the capture; unsupported captures were not imported.
4. Reconstructed 303 axis-aligned blocking boxes, sloped brushes, terrain and model collision. Kept render and collision geometry separate.
5. Created six teleport actors using the local project's Blueprint template and checked overlap destinations.
6. Replaced the flat presentation with rock materials, 271 local light pools and 26 hanging lamps. These counts describe the art pass, not a recommended performance budget for another map.
7. Added nine 4K Poly Haven texture maps across two rock scans and weathered timber, a procedural storm-night sky and nine timber support frames. Decorative additions were non-colliding.
8. Made a requested local gameplay edit: replaced a Z864 landing with three 32-unit-deep treads at Z852, Z840 and Z828. The lowest approach edge is 36 CoD units / 91.44 cm below the original landing. Updated visible geometry and collision together.

## Validation performed locally

- Export geometry checks, scale/orientation comparisons and grounded-spawn checks.
- Collision traces over reconstructed sloped, terrain and model surfaces; very thin precision slivers were reported separately.
- Six teleport overlap/destination tests.
- Nine tread-height probes, standing-height clearance and two internal riser checks for the stair edit.
- Visual inspection of the start room, selected exits, sky and stair profile.
- Before the intentional stair edit, 47 original mesh/gameplay assets were byte-identical through the visual overhaul.
- Verified archives before major changes. A spawn preview reached 120 render FPS on the development machine; this is not a whole-map or cross-hardware benchmark.

## What remained

Full-route traversal, final source teleport timing/view angles, seven interaction triggers, foliage opacity work, complete release credits/provenance and packaged Workshop testing remained pending. A later stair-side gap was discussed, but the follow-up at that point was instruction-only and did not modify it.

The useful lesson is to validate geometry and collision before art, preserve the original assets, and treat any gameplay alteration as a deliberate, documented change. A map can look convincing while still having incorrect collision or movement behaviour.
