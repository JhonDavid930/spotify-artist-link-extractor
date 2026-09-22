# Spotify Artist Link Extractor

Aplicación de escritorio para obtener y organizar los enlaces oficiales de las canciones publicadas en un perfil de artista, álbum o canción de Spotify.

Solo utiliza la API oficial de Spotify. No descarga audio, no extrae reproducciones y no modifica cuentas.

![Spotify Artist Link Extractor mostrando resultados](docs/images/app-main.jpg)

## Elige tu guía

No necesitas leer todo el repositorio. Abre únicamente la guía que corresponda a tu caso:

| Quiero... | Guía |
| --- | --- |
| Instalar y utilizar la aplicación | [Guía para clientes](docs/GUIA_CLIENTE.md) |
| Resolver un error | [Solución de problemas](docs/SOLUCION_PROBLEMAS.md) |
| Crear, renovar o administrar licencias | [Guía privada del propietario](docs/GUIA_PROPIETARIO.md) |
| Ejecutar el código o generar un paquete | [Guía de desarrollo y empaquetado](docs/DEPLOY_GUIDE.md) |
| Comprender la arquitectura | [Especificación técnica](docs/TECH_SPEC.md) |

## Inicio rápido para clientes

1. Recibe el archivo `SpotifyArtistLinkExtractor-Windows.zip` del distribuidor.
2. Descomprime el archivo.
3. Abre `SpotifyArtistLinkExtractor.exe`.
4. Introduce tu `Client ID`, `Client Secret` y licencia.
5. Pega un enlace de Spotify y pulsa **Extraer enlaces**.
6. Pulsa **Exportar** para guardar los resultados.

La explicación completa, con todos los pasos y sin comandos, está en la [Guía para clientes](docs/GUIA_CLIENTE.md).

## Qué puedes hacer

- Extraer todos los enlaces oficiales de las canciones de un artista.
- Procesar enlaces de artista, álbum o canción.
- Incluir álbumes, singles, apariciones y recopilatorios.
- Buscar, ordenar, copiar y pausar resultados.
- Continuar una extracción pausada sin repetir álbumes terminados.
- Exportar a CSV, TXT, Excel y JSON.
- Obtener opcionalmente ISRC y otros metadatos cuando la API lo permita.
- Evitar duplicados por identificador de Spotify y, opcionalmente, por ISRC.

## Requisitos del cliente

- Un equipo con Windows 10 u 11 para el paquete de Windows.
- Conexión a Internet.
- Una cuenta gratuita de Spotify for Developers.
- Credenciales `Client ID` y `Client Secret`.
- Una licencia válida suministrada por el propietario del software.

El cliente no necesita instalar Python, Git ni utilizar una terminal.

## Descargar la última versión

El repositorio es privado. Los usuarios autorizados pueden consultar la [última Release](https://github.com/JhonDavid930/spotify-artist-link-extractor/releases/latest). Los clientes finales deben recibir el paquete de instalación directamente del distribuidor.

## Crear credenciales de Spotify

1. Abre [Spotify for Developers](https://developer.spotify.com/dashboard).
2. Inicia sesión con tu cuenta de Spotify.
3. Pulsa **Create app**.
4. Escribe un nombre y una descripción.
5. Si el formulario exige una dirección, añade `http://127.0.0.1:8888/callback` en **Redirect URI**.
6. Marca **Web API**, acepta las condiciones y guarda.
7. Abre **Settings** para ver el `Client ID` y el `Client Secret`.

No compartas el `Client Secret` por mensajes, capturas ni documentos públicos.

La aplicación utiliza Client Credentials para consultar datos públicos y no inicia sesión en la cuenta del usuario. La dirección local anterior solo completa el registro de la aplicación en el Dashboard.

## Vista de License Studio

![License Studio para administración privada](docs/images/license-studio.jpg)

License Studio es una herramienta interna. No forma parte del paquete entregado a clientes y nunca debe distribuirse junto con la clave privada o el inventario de licencias.

## Seguridad y privacidad

- Las credenciales se guardan localmente en el equipo del usuario.
- La aplicación utiliza conexiones HTTPS con Spotify.
- Las licencias se verifican sin incluir la clave privada en el programa del cliente.
- `.env`, claves privadas, inventarios y paquetes locales están excluidos de Git.
- Consulta la [auditoría de seguridad](docs/SECURITY_AUDIT.md) para información técnica.

## Documentación

- [Guía para clientes](docs/GUIA_CLIENTE.md)
- [Solución de problemas](docs/SOLUCION_PROBLEMAS.md)
- [Guía privada del propietario](docs/GUIA_PROPIETARIO.md)
- [Guía de desarrollo y empaquetado](docs/DEPLOY_GUIDE.md)
- [Especificación técnica](docs/TECH_SPEC.md)
- [Historial de cambios](docs/CHANGELOG.md)

## Autoría

Copyright (c) 2026 Jhon David (art. David Appleton). Todos los derechos reservados.

Consulta [COPYRIGHT.md](COPYRIGHT.md) para ver el aviso completo de autoría.
