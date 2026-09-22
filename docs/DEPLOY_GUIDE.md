# Guía de desarrollo y empaquetado

Esta guía es para el propietario o para desarrolladores. Los clientes finales deben utilizar la [Guía para clientes](GUIA_CLIENTE.md) y no necesitan ejecutar ningún comando.

Copyright (c) 2026 Jhon David (art. David Appleton). Todos los derechos reservados.

## Idea principal

Spotify Artist Link Extractor es una aplicación de escritorio. No necesita un servidor web. Cada paquete debe generarse en el sistema operativo donde se utilizará:

- Compila Windows desde Windows.
- Compila macOS desde macOS.
- Compila Linux desde Linux.

## Preparar un equipo nuevo

### 1. Instalar herramientas

Instala:

- Python 3.11 o superior desde [python.org](https://www.python.org/downloads/).
- Git desde [git-scm.com](https://git-scm.com/downloads).

En Windows, activa **Add Python to PATH** durante la instalación de Python.

### 2. Descargar el proyecto

Abre PowerShell o Terminal y ejecuta:

```bash
git clone https://github.com/JhonDavid930/spotify-artist-link-extractor.git
cd spotify-artist-link-extractor
```

El repositorio es privado. GitHub solicitará una cuenta con permiso de acceso.

### 3. Crear el entorno aislado

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Probar antes de compilar

```bash
python app.py
python -m unittest discover -s tests -v
```

No continúes si alguna prueba falla.

## Generar la aplicación del cliente

Con el entorno activado:

```bash
python tools/build.py app
```

Resultado esperado:

- Windows: `dist/SpotifyArtistLinkExtractor-Licensed.exe`
- macOS: `dist/SpotifyArtistLinkExtractor-Licensed`
- Linux: `dist/SpotifyArtistLinkExtractor-Licensed`

El script utiliza PyInstaller con modo de ventana, por lo que el cliente no verá una terminal al abrir el programa.

## Generar License Studio

License Studio es de uso interno:

```bash
python tools/build.py license-studio
```

No incluyas este programa en el paquete del cliente.

## Crear el paquete de Windows

1. Crea una carpeta llamada `SpotifyArtistLinkExtractor-Windows`.
2. Copia dentro el ejecutable de cliente.
3. Renómbralo como `SpotifyArtistLinkExtractor.exe` si deseas un nombre más sencillo.
4. Añade un `LEEME.txt` con los pasos de activación.
5. Comprime la carpeta como ZIP.
6. Prueba el ZIP en un usuario de Windows diferente antes de distribuirlo.

Para una instalación comercial más pulida, utiliza Inno Setup, MSIX o NSIS y firma digitalmente el ejecutable y el instalador.

## Paquetes de macOS y Linux

PyInstaller no genera desde Windows los paquetes de otros sistemas.

- macOS: genera una aplicación firmada y un archivo `.dmg` desde macOS.
- Linux: genera AppImage, `.deb`, `.rpm` o Flatpak desde Linux.

No anuncies compatibilidad con un sistema hasta probar el flujo completo en ese sistema.

## Publicar una versión en GitHub

1. Actualiza `VERSION`.
2. Registra los cambios en `docs/CHANGELOG.md`.
3. Ejecuta las pruebas.
4. Comprueba que no haya secretos ni archivos privados.
5. Crea un Commit con Conventional Commits.
6. Crea un tag, por ejemplo `v1.0.2`.
7. Publica una GitHub Release.
8. Adjunta únicamente el paquete destinado a clientes.

## Lista de seguridad antes de distribuir

- El paquete no contiene `.env`.
- El paquete no contiene `tools/private/`.
- El paquete no contiene License Studio.
- El paquete no contiene inventario de clientes.
- El paquete no contiene credenciales personales de Spotify.
- La aplicación se abre sin terminal.
- La activación rechaza una licencia inválida.
- La extracción y las cuatro exportaciones funcionan.
- El antivirus no ha detectado modificaciones inesperadas.

## Archivos que nunca deben publicarse

```text
.env
tools/private/
build/
dist/
release/
```

Estos elementos ya están excluidos por `.gitignore`, pero deben revisarse antes de cada Release.
