# Receta de PyInstaller para ROBIN (modo carpeta: arranque rápido, sin descomprimir en cada inicio).
# Uso: packaging\build.ps1
import os
import sysconfig

from PyInstaller.utils.hooks import collect_all, copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SITE = sysconfig.get_paths()["purelib"]

datas, binaries, hiddenimports = [], [], []
for package in ("openai_codex", "faster_whisper", "ctranslate2", "onnxruntime", "sherpa_onnx", "edge_tts",
                "sounddevice", "_sounddevice_data", "certifi", "tokenizers", "av"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

# La SDK de Codex valida las versiones instaladas leyendo los metadatos de los paquetes.
for dist in ("openai-codex", "openai-codex-cli-bin", "faster-whisper", "sherpa-onnx", "edge-tts"):
    datas += copy_metadata(dist)

# Runtime de Codex completo (codex.exe y sus auxiliares). OJO: codex-code-mode-host.exe y
# codex-exec-server.exe SÍ son necesarios: sin ellos fallan las herramientas y las apps conectadas.
cli_dir = os.path.join(SITE, "codex_cli_bin")
for folder, _, files in os.walk(cli_dir):
    if "__pycache__" in folder:
        continue
    for name in files:
        if name.endswith(".py"):
            continue
        datas.append((os.path.join(folder, name), os.path.relpath(folder, SITE)))
hiddenimports += ["codex_cli_bin"]

a = Analysis(
    [os.path.join(ROOT, "src", "robin", "__main__.py")],
    pathex=[os.path.join(ROOT, "src")],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "PyInstaller"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ROBIN",
    icon=os.path.join(SPECPATH, "robin.ico"),
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="ROBIN", upx=False)
