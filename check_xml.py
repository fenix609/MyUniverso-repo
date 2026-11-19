#!/usr/bin/env python3
"""Comprueba los XML de la carpeta Código antes de subirlos a GitHub.
Uso:  python check_xml.py [carpeta]        (por defecto: Código)
Para cada error muestra la línea y la columna exactas. Los fallos que el addon sabe tolerar
(comillas dobles dentro de un texto, & sin escapar) salen como AVISO.
También dice cuántos episodios de un <tree> siguen sin enlace."""
import glob, os, re, sys, xml.etree.ElementTree as ET

BARE_AMP = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);)")
TAG = re.compile(r"<([A-Za-z_][\w:.-]*)(\s.*?)?(/?)>(?=\s*(?:<|$))", re.DOTALL)
ATTR = re.compile(r'\s*([\w:.-]+)\s*=\s*"(.*?)"(?=\s+[\w:.-]+\s*=\s*"|\s*$)', re.DOTALL)


def fix_value(v):
    return BARE_AMP.sub("&amp;", v).replace('"', "&quot;").replace("<", "&lt;")


def fix_tag(m):
    name, attrs, slash = m.group(1), m.group(2) or "", m.group(3)
    pos, parts = 0, []
    for a in ATTR.finditer(attrs):
        if attrs[pos:a.start()].strip():
            return m.group(0)
        parts.append(' {}="{}"'.format(a.group(1), fix_value(a.group(2))))
        pos = a.end()
    return m.group(0) if attrs[pos:].strip() else "<{}{}{}>".format(name, "".join(parts), slash)


def repair(text):
    pieces = re.split(r"(<!--.*?-->|<\?.*?\?>)", text, flags=re.DOTALL)
    for i in range(0, len(pieces), 2):
        pieces[i] = TAG.sub(fix_tag, pieces[i])
    return "".join(pieces)


def show(text, exc):
    m = re.search(r"line (\d+), column (\d+)", str(exc))
    if not m:
        return
    line, col = int(m.group(1)), int(m.group(2))
    lines = text.splitlines()
    if 0 < line <= len(lines):
        print("       línea {}: {}".format(line, lines[line - 1].strip()[:160]))
        print("       " + " " * (len("línea {}: ".format(line)) + max(col - (len(lines[line - 1]) - len(lines[line - 1].lstrip())), 0)) + "^")


bad = 0
folder = sys.argv[1] if len(sys.argv) > 1 else "Código"
for path in sorted(glob.glob(os.path.join(folder, "*.xml"))):
    name = os.path.basename(path)
    text = open(path, encoding="utf-8-sig").read()
    try:
        root = ET.fromstring(text.encode("utf-8"))
        note = ""
    except ET.ParseError as exc:
        try:
            root = ET.fromstring(repair(BARE_AMP.sub("&amp;", text)).encode("utf-8"))
            print("AVISO  {}: {}".format(name, exc))
            show(text, exc)
            print("       Hay comillas dobles (\") o un & dentro de un texto. El addon lo tolera, pero cámbialas por ' o « » y escribe &amp; en vez de &.")
            note = ""
        except ET.ParseError:
            bad += 1
            print("ERROR  {}: {}".format(name, exc))
            show(text, exc)
            print("       Revisa comillas sin cerrar, etiquetas sin cerrar o un '<' dentro de un texto.")
            continue
    if root.tag == "tree":
        items = list(root.iter("item"))
        sin = [i for i in items if not (i.get("drive") or i.get("url"))]
        note = "  ({} episodios, {} sin enlace)".format(len(items), len(sin))
    print("OK     {}{}".format(name, note))
sys.exit(1 if bad else 0)
