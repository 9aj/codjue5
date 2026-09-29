# Modified source notice

Project Jump modifications dated 2026-09-26 are described in README.md. Upstream source commit: 9a3accfb75c9a2f9780446c2b7bef040570357cf, https://github.com/sheilan102/C2M .

Modified vendored files: ModernWarfare.cs (JSON, map/count/surface validation, output path, bounded entity read, face loop and coverage reporting); WavefrontOBJ.cs (Framework JSON serialization); ByteUtil.cs (struct length validation and guaranteed pinned-handle release).

Other vendor files retain upstream implementations and license headers. New src/*.cs and PowerShell scripts are licensed GPL-3.0-or-later. The included LICENSE contains the GPL text. PhilLibX ByteUtil.cs retains its MIT terms.

No game assets are distributed as part of this source tree. Runtime exports belong in ignored artifacts/. Build products belong in ignored pipeline/bin/.

## Public source package — 2026-09-29

The public codjue5 package adds a standalone conversion guide, credits and reference-stage catalogue, requires an explicit usermaps path in the PowerShell wrapper, skips the optional private Descent fixture when absent, and adds CI/distribution checks. Source whitespace is normalised without changing upstream notices. Historical Tunnel scripts are provided as clearly marked reference implementations with private project paths replaced by placeholders; capture data, game content, audit header copies and binaries are excluded. Project-authored Python/reference code and documentation are GPL-3.0-or-later as stated in the root README.
