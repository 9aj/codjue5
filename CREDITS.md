# Credits and provenance

## Included source and upstream lineage

| Project / author | Contribution | Included material / terms |
|---|---|---|
| [C2M — SHEILAN / sheilan102](https://github.com/sheilan102/C2M) | COD map exporter, COD4 game research and the maintained Husky fork used as our starting point | Modified subset in `pipeline/vendor/`; pinned revision `9a3accfb75c9a2f9780446c2b7bef040570357cf`; GPL-3.0-or-later per source headers |
| [Husky — Philip / Scobalula](https://github.com/Scobalula/Husky) | Original BSP extraction architecture, geometry structures and export code underlying C2M | Original copyright and GPL-3.0-or-later headers retained in vendored files |
| [PhilLibX — Philip / Scobalula](https://github.com/Scobalula/PhilLibX) | Byte/structure conversion utilities | Modified `pipeline/vendor/ByteUtil.cs`; MIT notice retained in the file and [copied here](docs/PHILLIBX-MIT.txt) |
| [DTZxPorter](https://github.com/dtzxporter) / Wraith research | Normal unpacking, half floats and related information credited by C2M | Upstream lineage acknowledgement; Wraith itself is not bundled or invoked by this workflow |

The pinned upstream source is [available here](https://github.com/sheilan102/C2M/tree/9a3accfb75c9a2f9780446c2b7bef040570357cf). See [the modification notice](pipeline/NOTICE.md) for our changes. The `PhilLibX.IO` namespace in our new process reader is for compatibility; that reader is a replacement implementation, not the full PhilLibX distribution.

## Consulted engine-layout and collision references

- **[OpenAssetTools — Laupetin and contributors](https://github.com/Laupetin/OpenAssetTools)**: IW3 asset structures, notably [`IW3_Assets.h`](https://github.com/Laupetin/OpenAssetTools/blob/main/src/Common/Game/IW3/IW3_Assets.h), were used to cross-check model and collision layouts. We did not run or bundle an OAT executable. Full reference headers are not redistributed here.
- **[CoD4x — callofduty4x and contributors](https://github.com/callofduty4x/CoD4x_Server)**: contents/surface flags and shared definitions were consulted when distinguishing solid, player-clip, trigger and other geometry. The local reference headers acknowledge Ninja, TheKelm and id Software. No CoD4x source header or binary is bundled here; its own license governs that project.
- **[iw3xo — xoxor4d and contributors](https://github.com/xoxor4d/iw3xo-dev)**: IW3 structure definitions were consulted during research. It is not a required runtime dependency or an included exporter. No iw3xo code or binary is bundled here.

These acknowledgements describe research actually used. They are not claims that the upstream authors endorse this conversion pipeline or that their projects provide the map-specific UE5 implementation.

## Replacement art used in the Tunnel case study

**Powered by [Poly Haven](https://polyhaven.com/).** The following scans supplied diffuse, DirectX normal and packed AO/roughness/metalness maps for the local material pass:

- [Rock Boulder Cracked](https://polyhaven.com/a/rock_boulder_cracked)
- [Rock Boulder Dry](https://polyhaven.com/a/rock_boulder_dry)
- [Wooden Rough Planks](https://polyhaven.com/a/wooden_rough_planks)

Poly Haven assets use [CC0](https://polyhaven.com/license). Their pixels and Unreal derivatives are not included in this repository. Download assets directly, retain their source records and record the licence of any alternatives. Our procedural sky shader and bevelled support-mesh generator are included as project-authored examples.

## Development environment and map authors

The workflow used Microsoft Visual Studio / Roslyn and .NET Framework, Python, PowerShell, Git, and Epic Games' Unreal Engine. These are separate dependencies, not bundled parts of the exporter. Unreal Engine is source-available under its own terms; it is not presented here as an open-source GPL component.

`mp_descent` and `mp_tunnel` were test maps. The Tunnel conversion's creator permission was reported by the project owner; that permission is not transferred to repository users. The map author's preferred public credit name and the full original model provenance still need to be recorded before distributing that converted level. No authorship name is invented here, and no map is included.

Project Jump's custom conversion stages, validation, material work and documentation were developed with AI assistance and checked locally. This does not replace the original authors' credits or their licence terms.
