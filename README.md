# Liga Mayor Unofficial

Sitio no oficial de la Liga Mayor ONEFA: https://ligamayorunofficial.com

- `site/` es la página que publica Netlify.
- Los datos salen del Google Sheet publicado. La página principal, la Nacional y las de equipos los leen en vivo.
- `build/generate.py` crea una página por partido (`site/juegos/2026/...`), una por semana y el calendario, y actualiza `site/sitemap.xml`.
- `.github/workflows/actualizar.yml` corre el generador cada 30 minutos. Si la hoja cambió, guarda los cambios y Netlify publica solo.

Para forzar una actualización: pestaña **Actions** → "Actualizar partidos desde Google Sheets" → **Run workflow**.
