# Changes in this fork

This is FreeRDP 3.32.0 (tag `3.32.0`, unmodified upstream history) with the
changes below, made by Aleksandr Ševčenko for sdl-rdp, which consumes
FreeRDP as a conan package. FreeRDP is licensed under the Apache License
2.0 (`LICENSE`); the changes are under the same licence. Each change is one
commit on branch `sdl-rdp` above `3.32.0`; releases are tagged
`3.32.0-sdl-rdp.<n>`.

## Packaging

- `conanfile.py` and `test_package/`: a conan recipe that builds
  `freerdp/3.32.0` from this tree (version read from
  `cmake/GetProjectVersion.cmake`), shared by default, server and client
  libraries only, OpenSSL, zlib and OpenH264 from conan, every host-probed
  feature switched off so nothing from the build machine leaks into the
  binary. `find_package(FreeRDP)` gives `freerdp::winpr`, `freerdp::freerdp`,
  `freerdp::freerdp-client` and `freerdp::freerdp-server`, with the upstream
  names as aliases and the aggregate as `FreeRDP::FreeRDP`.
- OpenH264 is linked static with hidden symbols into libfreerdp, so a
  consumer never needs `libopenh264.so` on its runtime path.
- MD4 and RC4 are built into WinPR (`WITH_INTERNAL_MD4`, `WITH_INTERNAL_RC4`)
  instead of loaded from OpenSSL's legacy provider, which conan's shared
  OpenSSL cannot find at run time; without them every NLA logon fails.

- `conanfile.py`, `CMakeCPack.cmake` (`3.32.0-sdl-rdp.2`): the recipe builds
  for macOS arm64 and Windows msvc as well as Linux. `-Wl,--exclude-libs,ALL`
  is ELF-only; Apple targets hide OpenH264 with `-Wl,-load_hidden,<archive>`,
  Windows exports only what is declared. The archive name follows the
  openh264 recipe (`openh264.lib` under msvc and clang-cl). System libraries
  are per OS: Windows winpr links upstream's eight public Win32 libraries,
  Apple has no librt, everything else keeps `pthread dl rt m`. CPack's
  `InstallRequiredSystemLibraries` runs only on a Windows host, so a cross
  build configures. A worktree's `.git` file is never exported.

## Fixes

- `winpr/libwinpr/utils/ssl.c`: do not load OpenSSL's legacy provider when
  MD4 and RC4 are built in; the failed load only logged a misleading warning.
- `channels/drive/client/drive_file.c`: query the size of the file handle,
  not of the `DRIVE_FILE` structure; every redirected-drive read failed with
  `STATUS_UNSUCCESSFUL`.
- `channels/drive/client/drive_main.c`: clear the thread's last error before
  closing a file, so a close after a finished directory listing no longer
  reports `STATUS_NO_MORE_FILES`.
- `libfreerdp/core/listener.c` (`3.32.0-sdl-rdp.3`): a server that opens
  its own listening socket can hand it to FreeRDP on Windows too.
  `freerdp_listener_open_from_socket` returned `FALSE` under `_WIN32`; it
  now switches the socket to non-blocking with `ioctlsocket(FIONBIO)` where
  POSIX uses `fcntl(O_NONBLOCK)`, checks `WSAEventSelect`, and stores the
  socket and its event only once both succeeded, so a failed adoption leaves
  the socket with its caller. The recipe version carries the fork release
  (`3.32.0-sdl-rdp.<n>`), so a consumer pins a release by version.
