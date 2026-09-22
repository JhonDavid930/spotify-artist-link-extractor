# Guía para clientes

Esta guía explica cómo instalar y utilizar Spotify Artist Link Extractor sin conocimientos técnicos.

## Antes de empezar

Necesitas cuatro cosas:

1. El archivo que te ha enviado el distribuidor.
2. Una conexión a Internet.
3. Tus credenciales gratuitas de Spotify: `Client ID` y `Client Secret`.
4. La licencia que te ha enviado el propietario del software.

No necesitas instalar Python, Git ni abrir una terminal.

## Paso 1. Instalar la aplicación en Windows

1. Busca el archivo `SpotifyArtistLinkExtractor-Windows.zip` en **Descargas**.
2. Haz clic derecho sobre el archivo.
3. Pulsa **Extraer todo**.
4. Abre la carpeta extraída.
5. Haz doble clic en `SpotifyArtistLinkExtractor.exe`.

Si Windows muestra una advertencia porque el archivo procede de Internet, comprueba que lo recibiste directamente del distribuidor antes de continuar. No ejecutes copias recibidas desde fuentes desconocidas.

## Paso 2. Conseguir las credenciales de Spotify

Las credenciales identifican tu aplicación ante Spotify. No son tu contraseña de Spotify.

1. Abre [Spotify for Developers](https://developer.spotify.com/dashboard).
2. Inicia sesión con tu cuenta normal de Spotify.
3. Pulsa **Create app**.
4. En **App name**, escribe por ejemplo `Mi extractor de enlaces`.
5. En **App description**, escribe `Herramienta personal para organizar enlaces oficiales de Spotify`.
6. Si el formulario exige una dirección, en **Redirect URI** escribe `http://127.0.0.1:8888/callback` y pulsa **Add**.
7. Marca **Web API**.
8. Acepta las condiciones y pulsa **Save**.
9. Entra en la aplicación que acabas de crear y abre **Settings**.
10. Copia el `Client ID`.
11. Pulsa **View client secret** y copia el `Client Secret`.

Guarda estos dos valores en un lugar privado. No los publiques ni los envíes en capturas.

Spotify Artist Link Extractor utiliza Client Credentials para consultar información pública. No inicia sesión en tu cuenta ni utiliza ese Redirect URI durante las extracciones.

## Paso 3. Activar el programa

1. Abre Spotify Artist Link Extractor.
2. Pega el `Client ID` en su campo.
3. Pega el `Client Secret` en su campo.
4. Pega la licencia que recibiste del propietario.
5. Pulsa **Guardar y activar**.

La licencia puede estar asociada a un único equipo. Si cambias de ordenador, contacta con el propietario antes de intentar una nueva activación.

## Paso 4. Extraer canciones

1. Abre Spotify.
2. Busca el artista que quieres consultar.
3. Pulsa los tres puntos del perfil y selecciona **Compartir** y **Copiar enlace del artista**.
4. Pega el enlace en Spotify Artist Link Extractor.
5. Deja seleccionados **Álbumes** y **Singles** para una extracción normal.
6. Pulsa **Extraer enlaces**.
7. Espera hasta que la barra llegue al 100 % y aparezca el estado **Listo**.

![Resultados de una extracción terminada](images/app-main.jpg)

La opción de metadatos enriquecidos puede consumir más solicitudes de la API. Déjala desactivada cuando solo necesites enlaces.

## Paso 5. Pausar y continuar

- Pulsa **Detener** para pausar una extracción larga.
- Las canciones encontradas no desaparecen.
- Pulsa **Continuar** para seguir desde el último álbum completado.
- Pulsa **Vista amplia** únicamente cuando quieras dar más espacio a la tabla.

## Paso 6. Copiar o exportar

- **Copiar links:** copia los enlaces seleccionados.
- **Copiar todos los links:** copia todos los enlaces encontrados.
- **Exportar > TXT:** guarda un enlace por línea.
- **Exportar > CSV:** crea un archivo compatible con hojas de cálculo.
- **Exportar > Excel:** crea un archivo `.xlsx`.
- **Exportar > JSON:** guarda todos los campos para análisis de datos.

Cuando aparezca la ventana para guardar, elige una carpeta fácil de recordar, como **Documentos** o **Escritorio**.

## Qué enlace puedo pegar

La aplicación acepta enlaces y URI de:

- Artista: `https://open.spotify.com/artist/...`
- Álbum: `https://open.spotify.com/album/...`
- Canción: `https://open.spotify.com/track/...`
- Enlaces regionales: `https://open.spotify.com/intl-es/artist/...`
- URI: `spotify:artist:...`

## Qué no hace la aplicación

- No descarga canciones ni audio.
- No aumenta reproducciones.
- No entra en cuentas de Spotify.
- No modifica perfiles, álbumes ni playlists.
- No garantiza que Spotify muestre el mismo catálogo en todos los países.

Si algo no funciona, abre la [Solución de problemas](SOLUCION_PROBLEMAS.md).
