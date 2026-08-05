# LSE6.ORG · ARCHIVO VIVO INDEXABLE

Extensión documental de [LSE6.com](https://lse6.com/) preparada para GitHub y Cloudflare Pages.

## Estado de esta entrega

- 🔥 Release: `LSE6_ORG_TEMPORAL_YOUTUBE_20260805_125937`
- 👁 Página estática visible incluso sin JavaScript.
- 🧬 63 ranuras planeadas, 57 imágenes instaladas y 6 ranuras futuras.
- ⚡ Sitemap principal + sitemap de imágenes.
- ⏳ ANOMALÍAS TEMPORALES: cuatro campos del CSV real y evidencia por año.
- 🧾 CSV ORIGINAL: 256,666 registros preservados en 6 partes indexables y reconstruibles.
- ▶ 7 miniaturas oficiales enlazadas al canal @leydelsexto.
- 551 páginas en PDF web, texto indexable y 8 volúmenes de alta resolución.
- El botón, la firma y las menciones visibles de LSE6.com abren el centro en una pestaña nueva sin cerrar LSE6.ORG.

## Subir a GitHub

1. Crea o abre el repositorio destinado a `lse6.org`.
2. Sube **el contenido de esta carpeta**, no la carpeta contenedora.
3. Confirma que `index.html`, `CNAME`, `_headers`, `_redirects` y `robots.txt` queden en la raíz.
4. Conserva `.nojekyll` para GitHub Pages.

## Conectar Cloudflare Pages

- Framework preset: `None`
- Build command: vacío
- Build output directory: `.`
- Dominio personalizado: `lse6.org`

Cloudflare procesa `_headers` y `_redirects` automáticamente. Las URLs temporales `*.pages.dev` reciben `noindex`; el dominio `lse6.org` permanece indexable.

## Después de publicar

1. Abre `https://lse6.org/robots.txt`.
2. Abre `https://lse6.org/sitemap.xml`.
3. Abre `https://lse6.org/image-sitemap.xml`.
4. Registra la propiedad de dominio en Google Search Console.
5. Envía ambos sitemaps y solicita indexación de `https://lse6.org/`.

## Agregar las imágenes restantes

Las rutas exactas viven en `assets/data/image-manifest.json`. Después de copiar nuevas imágenes:

```bash
python tools/rebuild_release.py
python tools/validate_release.py
```

Esto vuelve a sincronizar miniaturas oficiales de YouTube y a montar HTML, sitemap de imágenes, pulsos e integridad.

## Símbolos funcionales

- 👁 `OBSERVADOR`: confirma que la capa visual está activa.
- 🧬 `ADN`: representa el manifiesto total de ranuras.
- ⚡ `IMÁGENES`: muestra cuántos archivos están conectados realmente.
- 🔥 `ESTADO`: confirma el estado final del archivo.

## Centro

`LSE6.com` es el núcleo. `LSE6.org` es archivo, soporte y extensión.
