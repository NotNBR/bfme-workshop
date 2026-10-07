# Native integration notices

The new bfmeXbar native adapter code is distributed under **GPL-3.0-only**. See `LICENSE.txt` for the license text. Retail BFME assets are separate, user-supplied inputs; this does not license those assets.

## OpenSAGE

Source: https://github.com/OpenSAGE/OpenSAGE

`tools/native/w3d.py` adapts the adaptive-delta decoding algorithm described by `W3dAdaptiveDeltaCodec.cs` and `W3dAdaptiveDeltaBlock.cs`, with the motion-channel layouts from the associated parser files. Copyright remains with the OpenSAGE contributors. The source was retrieved on 7 October 2026.

OpenSAGE's complete license notice is preserved in [OPENSAGE-LICENSE.md](OPENSAGE-LICENSE.md), including its reference to EA-derived components. [OPENSAGE-LICENSE-EA.md](OPENSAGE-LICENSE-EA.md) is also preserved. The adapter does not embed EA game binaries or claim ownership of original art.

## Recoil / Spring

Source and releases: https://github.com/beyond-all-reason/RecoilEngine

Pinned local release: `2026.07.04`, Windows amd64. Archive SHA-256:

`2e0a43744115e6b3cbd7db4a36aecc3d28afdef4fb615d07ab01703e4b5525e1`

The engine is downloaded as a separate ignored runtime. Its GPL source and license are available in that repository. Built-in Lua gadget and unit-script handlers retain the original authors' notices inside the engine's base packages. `unit_script.lua` invokes that existing handler, attributed to Tobi Vollebregt.

## openbfme2 and BFME II

`D:\LAN\openbfme2` supplies read-only reconstruction and file-layout references. Its source notices remain in the original repository. The original-host build uses the complete local game at `D:\LAN\lotrbfme2\local\bfme2`, copied only into ignored runtime files. The older Recoil importer used `D:\LAN\bfme2`.

`native/host/strategic.cpp` uses the recovered BFME2 1.06 camera/object layouts, symbols and Drawable::draw visibility semantics. Runtime helpers are imported from openbfme2 without modifying its checkout. The compiler is the existing MSVC 7.1 toolchain in its reference checkout; the compiler is not redistributed by this project. Direct3D9 interface slots were cross-checked against the locally installed mingw-w64 `d3d9.h` declarations; that header is not copied into the project.

## Python dependencies

NumPy and Pillow are installed separately, using the versions in `tools/native/requirements.txt`; their package distributions include their respective license notices.
