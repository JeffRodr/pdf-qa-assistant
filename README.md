# Asistente de preguntas y respuestas sobre PDFs

Aplicación Flask que indexa PDFs locales y responde preguntas usando
únicamente el contenido de esos documentos como contexto, a través de la
API de chat de Cohere.

## Cómo funciona

1. `pdf_loader.py` extrae el texto de cada página de los PDFs en `documents/`.
2. `text_index.py` trocea ese texto en fragmentos solapados y construye un
   índice **TF-IDF** (scikit-learn) para buscar los fragmentos más
   relevantes ante una pregunta, por similitud coseno.
3. `cohere_client.py` arma un prompt con esos fragmentos como contexto y un
   system prompt estricto que evita que el modelo invente información.
4. `app.py` expone la interfaz web (`templates/index.html`) y la API REST.

## Requisitos

- Python 3.10+
- API key de Cohere: [dashboard.cohere.com/api-keys](https://dashboard.cohere.com/api-keys)
  (el plan gratuito ("Trial") alcanza para esto)

## Instalación local

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
```

Editá `.env` y completá `COHERE_API_KEY`.

## Uso

1. Copiá tus PDFs a la carpeta `documents/`.
2. Corré el servidor:

```bash
python app.py
```

3. Abrí `http://127.0.0.1:5000` en el navegador.

Si agregás PDFs con el servidor corriendo, llamá a `POST /api/reload` o
reiniciá la app para reindexar.

## API

| Endpoint       | Método | Descripción                                   |
| -------------- | ------ | ---------------------------------------------- |
| `/`            | GET    | Interfaz de chat                               |
| `/api/ask`     | POST   | `{"question": "..."}` → `{"answer", "sources"}`|
| `/api/reload`  | POST   | Reindexa los PDFs de `documents/`              |
| `/api/status`  | GET    | Cantidad de documentos y fragmentos indexados  |

## Estructura

| Archivo/carpeta        | Rol                                              |
| ----------------------- | ------------------------------------------------- |
| `app.py`                | Servidor Flask y rutas                            |
| `pdf_loader.py`         | Extracción de texto con pypdf                      |
| `text_index.py`         | Troceado y búsqueda TF-IDF de fragmentos           |
| `cohere_client.py`      | Llamada a Cohere con system prompt estricto        |
| `templates/index.html`  | Interfaz de chat                                   |
| `static/`               | CSS y JS de la interfaz                            |
| `documents/`            | PDFs a indexar (no se versionan)                   |
| `requirements.txt`      | Dependencias                                       |
| `.env.example`          | Plantilla de variables de entorno                  |
| `deploy/app.service`    | Unidad systemd para correr con gunicorn            |
| `deploy/nginx.conf`     | Proxy inverso nginx con SSL                        |

## Despliegue en un servidor propio

Para producción, usá `gunicorn` en vez del servidor de desarrollo:

```bash
gunicorn --bind 0.0.0.0:8000 --workers 2 app:app
```

Pasos sugeridos para un VPS Linux (por ejemplo una instancia gratuita de
Oracle Cloud, AWS Lightsail, DigitalOcean, etc.):

1. Instalá el proyecto en `/opt/pdf-qa-assistant` (evitá `/home/<usuario>/`
   si el servidor tiene SELinux activo, porque puede bloquear la lectura
   de `EnvironmentFile` ahí).
2. Creá el entorno virtual y las dependencias dentro de esa carpeta final
   (no muevas un venv ya creado; las rutas internas quedan rotas).
3. Copiá `deploy/app.service` a `/etc/systemd/system/` y ajustá rutas y
   usuario. Luego:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now pdf-qa-assistant
   sudo systemctl status pdf-qa-assistant
   ```
4. Copiá `deploy/nginx.conf` a `/etc/nginx/sites-available/` (o
   `conf.d/`), generá un certificado (autofirmado o Let's Encrypt) y
   recargá nginx: `sudo nginx -t && sudo systemctl reload nginx`.
5. Abrí el puerto 443 (y 80 si redirigís) en el firewall/security group
   de tu proveedor de nube.

## Notas

- Las respuestas están limitadas al texto extraíble de los PDF (los
  escaneos sin OCR pueden quedar sin contenido).
- Para documentos largos o muchos PDFs, ajustá `TOP_K` en `.env` y los
  parámetros de troceado (`DEFAULT_CHUNK_WORDS` / `DEFAULT_CHUNK_OVERLAP`)
  en `text_index.py`.
