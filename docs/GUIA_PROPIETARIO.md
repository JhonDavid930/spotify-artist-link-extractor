# Guía privada del propietario

Esta guía es exclusivamente para administrar clientes y licencias. No debe incluirse en el paquete del cliente.

## Abrir License Studio

En Windows, abre:

```text
run_license_studio.bat
```

Si existe la versión compilada, el acceso directo abrirá `dist/SpotifyLicenseStudio.exe`. En caso contrario, utilizará el entorno local de desarrollo sin mostrar una terminal permanente.

## Crear una licencia

1. Escribe el nombre de la persona o empresa.
2. Añade su correo si desea recibir avisos. Es opcional.
3. Introduce el código del equipo si la licencia debe funcionar en un único ordenador.
4. Elige la duración o marca **Licencia de por vida**.
5. Pulsa **Crear licencia**.
6. Utiliza **Copiar licencia**, **Guardar TXT** o **Preparar email**.

![Inventario privado de License Studio](images/license-studio.jpg)

## Renovar una licencia existente

1. Selecciona al cliente en la tabla.
2. Elige la nueva duración.
3. Pulsa **Renovar seleccionada**.
4. Envía al cliente la licencia renovada generada por el sistema.

La renovación conserva el identificador del cliente y mantiene organizado el historial del inventario.

## Suspender, revocar o reactivar

1. Selecciona la licencia en la tabla.
2. Pulsa **Suspender** si quieres marcar una pausa temporal en tu inventario.
3. Pulsa **Revocar** si no deseas volver a renovar esa licencia por accidente.
4. Pulsa **Reactivar** para devolver el registro al estado activo.
5. Confirma siempre que has seleccionado al cliente correcto.

Estas acciones organizan y protegen tu inventario, pero no desactivan remotamente una licencia que el cliente ya tenga instalada. La validación es offline y la copia instalada seguirá funcionando hasta su fecha de vencimiento. Una revocación remota inmediata requeriría un servidor de licencias conectado a Internet.

## Licencia para un solo equipo

1. El cliente debe facilitar el código de equipo mostrado por la aplicación.
2. Copia el código completo en el campo **Equipo**.
3. Genera la licencia.
4. Esa licencia será rechazada en un equipo diferente.

Si el cliente cambia de ordenador, valida su identidad y crea o renueva la activación con el nuevo código siguiendo tu política comercial.

## Inventario

El inventario privado se guarda en:

```text
tools/private/licenses/
```

Realiza copias de seguridad cifradas de esa carpeta. Nunca la subas a Git, no la envíes al cliente y no la incluyas en el instalador.

## Si aparece “Missing private license key”

License Studio necesita la clave privada del propietario para firmar licencias. Debe existir una de estas dos opciones:

```text
tools/private/ed25519_private_key.txt
```

o la variable privada de entorno configurada en el equipo del propietario.

No envíes esa clave a nadie. Si se pierde sin copia de seguridad, no podrás renovar correctamente las licencias existentes con la misma identidad de firma.

## Entrega segura al cliente

Entrega únicamente:

- El paquete de la aplicación para su sistema operativo.
- La licencia del cliente.
- El enlace a la [Guía para clientes](GUIA_CLIENTE.md) o una copia en PDF.

No entregues:

- License Studio.
- La carpeta `tools/private/`.
- La clave privada de firma.
- El inventario de clientes.
- Tu archivo `.env`.
- Credenciales personales de Spotify.
