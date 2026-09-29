# Pipeline source

Follow the root [README](../README.md) and [conversion guide](../docs/CONVERSION_GUIDE.md).

- `src/`: project-specific CLI, checked read-only process reader, export context, entity parser and model-buffer capture.
- `vendor/`: modified subset of C2M/Husky and the MIT-covered PhilLibX ByteUtil; original notices retained.
- `build.ps1`: local Roslyn/.NET Framework build; no package restore.
- `convert.ps1`: explicit `-Usermaps`, inventory and world export wrapper.
- `prepare_descent_chunks.py`, `prepare_descent_surfaces.py`: experimental geometry algorithms. Their command-line entry points retain historical Descent defaults; they are not the generic importer. Tests import their reusable functions without private assets.
- `tests/`: synthetic geometry tests plus one explicitly optional private-fixture integration test.

For all commands, build `bin/JumpConvert.exe` first:

```text
JumpConvert.exe list
JumpConvert.exe self-test
JumpConvert.exe validate <file.obj>
JumpConvert.exe export <PID> <expected-map> <source-map-directory> <output-root>
JumpConvert.exe capture-models <PID> <expected-map> <output-root>
JumpConvert.exe prepare-geometry <input.obj> <map-name> <new-output-directory>
```

`prepare-geometry` can create a neutral handoff from an existing valid OBJ; it does not recover missing collision or models. Map names must match the supported `mp_...` identifier format. See source and [troubleshooting](../docs/TROUBLESHOOTING.md) for limitations.
