# Solución de problemas

Busca aquí el mensaje que aparece en pantalla y sigue únicamente esos pasos.

## La aplicación no abre

1. Confirma que descomprimiste el archivo ZIP antes de abrirlo.
2. Abre la carpeta extraída y ejecuta el archivo `.exe` desde allí.
3. Reinicia el equipo.
4. Comprueba que utilizas Windows 10 u 11 de 64 bits.
5. Descarga de nuevo el paquete desde la fuente autorizada.

No desactives el antivirus para instalar la aplicación. Si el archivo está bloqueado, consulta al distribuidor para verificar su origen e integridad.

## Faltan Client ID o Client Secret

Debes crear una aplicación gratuita en [Spotify for Developers](https://developer.spotify.com/dashboard). Sigue el [Paso 2 de la guía para clientes](GUIA_CLIENTE.md#paso-2-conseguir-las-credenciales-de-spotify).

## Spotify devuelve HTTP 400

- Comprueba que el enlace pertenece realmente a un artista, álbum o canción de Spotify.
- Copia de nuevo el enlace desde Spotify.
- No escribas manualmente el identificador.
- Si el mensaje menciona `Invalid limit`, actualiza a la última versión del programa.

## Credenciales rechazadas

1. Abre tu aplicación en Spotify for Developers.
2. Copia de nuevo el `Client ID` y el `Client Secret`.
3. Evita espacios al principio o al final.
4. Comprueba que **Web API** está habilitada.
5. Si regeneraste el Secret, reemplaza el valor antiguo en **Activación**.

## La licencia no es válida

- Copia la licencia completa, sin espacios adicionales.
- Comprueba que no haya vencido.
- Confirma que corresponde al mismo equipo si está vinculada a un dispositivo.
- Contacta con el propietario para renovar, reactivar o trasladar la licencia.

## La extracción parece detenida

Mira el texto situado junto a la barra de progreso.

- Si indica que está esperando por límite de Spotify, no cierres inmediatamente la aplicación.
- Si la espera es demasiado larga, pulsa **Detener**.
- Podrás pulsar **Continuar** para seguir desde el último álbum terminado.
- Para reducir solicitudes, desactiva los metadatos ISRC/popularidad.

## Spotify muestra HTTP 429 o “rate limit”

Spotify ha pedido que la aplicación espere antes de continuar. No significa que hayas perdido canciones.

1. Deja desactivados los metadatos enriquecidos.
2. Espera unos minutos antes de repetir la extracción.
3. No pulses muchas veces seguidas **Extraer enlaces**.
4. Utiliza álbumes y singles como opciones principales.

## Aparecen menos canciones de las esperadas

- Revisa el mercado seleccionado.
- Activa **Apariciones** o **Recopilatorios** si también los necesitas.
- Desactiva temporalmente el filtro “solo canciones donde aparece este artista” si buscas todo el contenido del lanzamiento.
- Algunos lanzamientos no están disponibles en todos los países.
- Spotify puede devolver versiones duplicadas que la aplicación elimina automáticamente.

## No encuentro el archivo exportado

La aplicación recuerda la última carpeta de exportación. Pulsa de nuevo **Exportar**, observa qué carpeta aparece y cancela la ventana cuando hayas localizado la ruta.

## Excel no se genera

1. Prueba primero con CSV.
2. Cierra el archivo Excel anterior si está abierto.
3. Elige una carpeta donde tengas permiso de escritura, como **Documentos**.
4. Evita nombres con caracteres especiales poco comunes.

## Necesito cambiar mis credenciales

Abre **Activación** desde la pantalla principal, sustituye el `Client ID` y el `Client Secret`, y guarda los cambios. La aplicación validará las nuevas credenciales antes de utilizarlas.

## Todavía necesito ayuda

Envía al distribuidor:

- El texto exacto del error.
- Una captura donde no aparezcan credenciales ni licencias completas.
- Tu versión de Windows o sistema operativo.
- El tipo de enlace utilizado: artista, álbum o canción.

Nunca envíes tu `Client Secret`, la licencia completa ni archivos privados en un grupo público.
