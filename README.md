# MyUniverso-repo

Repositorio de add-ons para Kodi (cine, series, TV, YouTube, archivos).

## Instalar en Kodi
1. Kodi → Ajustes → Sistema → Add-ons → activar **Orígenes desconocidos**.
2. Descarga `repository.myuniverso-1.0.0.zip` (raíz de este repo).
3. Add-ons → Instalar desde archivo zip → selecciona el zip.
4. Add-ons → Instalar desde repositorio → **MyUniverso-repo** → Add-ons de vídeo → **MiAddon**.

## Estructura
- `addons/`  → código fuente de cada add-on (aquí trabajas).
- `repo/`    → generado por el script (addons.xml, md5 y zips). No editar a mano.
- `generar_repo.py` → regenera `repo/`.

## Publicar una actualización
1. Edita el add-on y **sube el número `version`** en su `addon.xml`.
2. `python generar_repo.py TU_USUARIO main`
3. `git add . && git commit -m "Actualización" && git push`
4. Kodi detecta la nueva versión automáticamente (puede tardar unas horas; fuerza con *Add-ons → menú contextual del repo → Buscar actualizaciones*).

## Añadir un add-on nuevo
Crea `addons/plugin.video.nombre/` con su `addon.xml` y ejecuta el script.
