import re
from pathlib import Path

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, rmdir
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version


class FreeRDPConan(ConanFile):
  name = "freerdp"
  license = "Apache-2.0"
  url = "https://github.com/2bitsin/FreeRDP"
  package_type = "library"
  settings = "os", "arch", "compiler", "build_type"
  options = {
    "shared": [True, False],
    "fPIC": [True, False],
    "server": [True, False],
    "client": [True, False],
    "shadow": [True, False],
    "x11": [True, False],
    "wayland": [True, False],
    "sample": [True, False],
    "with_openh264": [True, False],
  }
  default_options = {
    "shared": True,
    "fPIC": True,
    "server": True,
    "client": True,
    "shadow": False,
    "x11": False,
    "wayland": False,
    "sample": False,
    "with_openh264": True,
  }
  exports_sources = ("*", "!.git", "!.git/**", "!build/**", "!ci/**", "!docs/**", "!packaging/**", "!test_package/**")

  def set_version(self):
    text = Path(self.recipe_folder, "cmake", "GetProjectVersion.cmake").read_text()
    self.version = re.search(r'set\(RAW_VERSION_STRING "([^"]+)"\)', text).group(1)

  def config_options(self):
    if self.settings.os == "Windows":
      del self.options.fPIC

  def configure(self):
    if self.options.shared:
      self.options.rm_safe("fPIC")
    self.settings.rm_safe("compiler.cppstd")
    self.settings.rm_safe("compiler.libcxx")

  def layout(self):
    cmake_layout(self)

  def requirements(self):
    # A shared FreeRDP over a static OpenSSL would carry a private libcrypto per library.
    self.requires("openssl/[>=3.6 <4]", options={"shared": bool(self.options.shared)})
    self.requires("zlib/[>=1.3 <2]")
    if self.options.with_openh264:
      # Static and hidden in libfreerdp: a consumer's rpath never names a dependency it does not link.
      self.requires("openh264/[>=2.6 <3]", options={"shared": False})
    if self.options.x11:
      self.requires("xorg/system")
    if self.options.wayland:
      self.requires("wayland/[>=1.22 <2]")

  def generate(self):
    tc = CMakeToolchain(self)
    tc.cache_variables.update({
      "USE_VERSION_FROM_GIT_TAG": False,
      "WITH_CLIENT_COMMON": bool(self.options.client),
      "WITH_CLIENT": False,
      "WITH_SERVER": bool(self.options.server),
      "WITH_SHADOW": bool(self.options.shadow),
      "WITH_PLATFORM_SERVER": bool(self.options.shadow),
      "WITH_SAMPLE": bool(self.options.sample),
      "WITH_PROXY": False,
      "WITH_PROXY_MODULES": False,
      "WITH_X11": bool(self.options.x11),
      "WITH_WAYLAND": bool(self.options.wayland),
      "WITH_OPENH264": bool(self.options.with_openh264),
      "WITH_FFMPEG": False,
      "WITH_SWSCALE": False,
      "WITH_ALSA": False,
      "WITH_PULSE": False,
      "WITH_OSS": False,
      "WITH_SNDIO": False,
      "WITH_OPUS": False,
      "WITH_GSM": False,
      "WITH_CUPS": False,
      "WITH_PCSC": False,
      "WITH_FUSE": False,
      "WITH_KRB5": False,
      "WITH_PKCS11": False,
      "WITH_URIPARSER": False,
      "WITH_AAD": False,
      "WITH_WEBVIEW": False,
      "WITH_SYSTEMD": False,
      "WITH_JSON_DISABLED": True,
      "WITH_UNICODE_BUILTIN": True,
      "WITH_INTERNAL_MD4": True,
      "WITH_INTERNAL_RC4": True,
      "WITH_ABSOLUTE_PLUGIN_LOAD_PATHS": False,
      "WITH_WINPR_TOOLS": False,
      "WITH_MANPAGES": False,
      "WITH_CCACHE": False,
      "WITH_CLANG_FORMAT": False,
      "BUILD_TESTING": False,
      "CHANNEL_URBDRC": False,
      "CHANNEL_PRINTER": False,
      "CHANNEL_SMARTCARD": False,
      "CHANNEL_SERIAL": False,
      "CHANNEL_PARALLEL": False,
      "CHANNEL_RDPECAM": False,
      "CHANNEL_TSMF": False,
    })
    if self.options.with_openh264:
      tc.variables.update(self._openh264_variables())
    if self.options.shared:
      tc.extra_sharedlinkflags.extend(self._hiding_link_flags())
    tc.generate()
    deps = CMakeDeps(self)
    # FreeRDP's FindOpenH264 takes the OPENH264_* cache entries above; conan's config would shadow it.
    deps.set_property("openh264", "cmake_find_mode", "none")
    deps.generate()

  def _openh264_archives(self):
    info = self.dependencies["openh264"].cpp_info.aggregated_components()
    # openh264's recipe renames its static archive to openh264.lib under msvc and clang-cl.
    msvc_like = is_msvc(self) or (self.settings.os == "Windows" and self.settings.compiler == "clang")
    name = "{}.lib" if msvc_like else "lib{}.a"
    return [str(Path(info.libdirs[0], name.format(lib))) for lib in info.libs]

  def _openh264_variables(self):
    info = self.dependencies["openh264"].cpp_info.aggregated_components()
    return {
      "OPENH264_INCLUDE_DIR": info.includedirs[0],
      "OPENH264_LIBRARY": ";".join(self._openh264_archives() + info.system_libs),
    }

  def _hiding_link_flags(self):
    # --exclude-libs is ELF-only; ld64 hides per archive; a DLL exports only what is declared.
    if self.settings.os == "Windows":
      return []
    if is_apple_os(self):
      archives = self._openh264_archives() if self.options.with_openh264 else []
      return [f"-Wl,-load_hidden,{archive}" for archive in archives]
    return ["-Wl,--exclude-libs,ALL"]

  def build(self):
    cmake = CMake(self)
    cmake.configure()
    cmake.build()

  def package(self):
    copy(self, "LICENSE", self.source_folder, str(Path(self.package_folder, "licenses")))
    CMake(self).install()
    for generated in ("lib/cmake", "lib/pkgconfig", "share"):
      rmdir(self, str(Path(self.package_folder, generated)))

  def package_info(self):
    self.cpp_info.set_property("cmake_file_name", "FreeRDP")
    # The aggregate would otherwise take freerdp::freerdp, the core library's own target.
    self.cpp_info.set_property("cmake_target_name", "FreeRDP::FreeRDP")
    codecs = ["zlib::zlib"] + (["openh264::openh264"] if self.options.with_openh264 else [])
    system_libs = self._system_libs()
    self._component("winpr", "winpr", ["openssl::ssl", "openssl::crypto"], system_libs["winpr"])
    self._component("freerdp", "freerdp", ["winpr", *codecs], system_libs["freerdp"])
    if self.options.client:
      self._component("freerdp-client", "freerdp", ["freerdp", "winpr"], [])
    if self.options.server:
      self._component("freerdp-server", "freerdp", ["freerdp", "winpr"], [])

  def _system_libs(self):
    # winpr's WINPR_LIBS_PUBLIC; shlwapi and pathcch under MSVC OR MINGW (winpr/libwinpr/path/CMakeLists.txt:27-30).
    if self.settings.os == "Windows":
      msvc_or_mingw = self.settings.compiler in ("msvc", "clang", "gcc")
      shell = ["shlwapi", "pathcch"] if msvc_or_mingw else []
      return {"winpr": ["ws2_32", "rpcrt4", "crypt32", "ncrypt", "ntdsapi", "dbghelp", *shell], "freerdp": []}
    if is_apple_os(self):
      return {"winpr": ["pthread", "dl", "m"], "freerdp": ["m"]}
    return {"winpr": ["pthread", "dl", "rt", "m"], "freerdp": ["m"]}

  def _component(self, name, headers, requires, system_libs):
    major = Version(self.version).major
    component = self.cpp_info.components[name]
    component.set_property("cmake_target_aliases", [name])
    component.libs = [f"{name}{major}"]
    component.includedirs = [f"include/{headers}{major}"]
    component.requires = requires
    component.system_libs = system_libs
