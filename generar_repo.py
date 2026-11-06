#!/usr/bin/env python3
"""
Genera la carpeta repo/ (addons.xml, addons.xml.md5 y zips) para Kodi.

Uso:
    python generar_repo.py TU_USUARIO_GITHUB [rama]

Ejemplo:
    python generar_repo.py juanperez main
"""
import hashlib
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
SRC = ROOT / "addons"
OUT = ROOT / "repo"
REPO_NAME = "MyUniverso-repo"
EXCL_DIRS = {"__pycache__", ".git", ".github", ".idea", ".vscode"}
EXCL_EXT = {".pyc", ".pyo", ".zip", ".md5"}


def set_fenix609(user, branch):
    """Actualiza las URLs del addon repository.* con tu usuario y rama."""
    pattern = re.compile(r"raw\.githubusercontent\.com/[^/]+/%s/[^/]+/repo/" % re.escape(REPO_NAME))
    new = "raw.githubusercontent.com/%s/%s/%s/repo/" % (user, REPO_NAME, branch)
    for xml in SRC.glob("repository.*/addon.xml"):
        text = xml.read_text(encoding="utf-8")
        xml.write_text(pattern.sub(new, text), encoding="utf-8")
        print("URLs actualizadas en", xml.relative_to(ROOT))


def make_zip(addon_dir, addon_id, version):
    dest = OUT / addon_id
    dest.mkdir(parents=True, exist_ok=True)
    zip_path = dest / ("%s-%s.zip" % (addon_id, version))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(addon_dir.rglob("*")):
            rel = f.relative_to(addon_dir)
            if f.is_dir() or any(p in EXCL_DIRS for p in rel.parts) or f.suffix in EXCL_EXT:
                continue
            zf.write(f, Path(addon_id) / rel)
    for asset in ("icon.png", "fanart.jpg"):
        if (addon_dir / asset).exists():
            shutil.copy2(addon_dir / asset, dest / asset)
    return zip_path


def main():
    if len(sys.argv) > 1:
        set_fenix609(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "main")

    OUT.mkdir(exist_ok=True)
    blocks = []
    for addon_dir in sorted(p for p in SRC.iterdir() if (p / "addon.xml").exists()):
        root = ET.parse(addon_dir / "addon.xml").getroot()
        addon_id, version = root.get("id"), root.get("version")
        zip_path = make_zip(addon_dir, addon_id, version)
        print("OK  %-28s v%-8s -> %s" % (addon_id, version, zip_path.relative_to(ROOT)))

        text = (addon_dir / "addon.xml").read_text(encoding="utf-8").strip()
        text = re.sub(r"^<\?xml[^>]*\?>\s*", "", text)
        blocks.append(text)

        # zip instalable del repositorio en la raíz del proyecto
        if addon_id.startswith("repository."):
            for old in ROOT.glob(addon_id + "-*.zip"):
                old.unlink()
            shutil.copy2(zip_path, ROOT / zip_path.name)

    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
    xml += "\n".join(blocks) + "\n</addons>\n"
    (OUT / "addons.xml").write_text(xml, encoding="utf-8", newline="\n")
    md5 = hashlib.md5(xml.encode("utf-8")).hexdigest()
    (OUT / "addons.xml.md5").write_text(md5, encoding="utf-8", newline="\n")
    print("\naddons.xml y addons.xml.md5 generados (md5: %s)" % md5)


if __name__ == "__main__":
    main()
