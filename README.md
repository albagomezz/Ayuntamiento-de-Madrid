# Bot de Citas - Ayuntamiento de Madrid

Bot automatizado para conseguir citas de Padrón y otros trámites en el Ayuntamiento de Madrid.

## Funcionalidades

- Monitoreo automático de disponibilidad de citas
- Selección automática de categoría, trámite y oficina
- Relleno automático de datos personales
- Notificaciones por Telegram y/o Email cuando se consigue cita
- Modo headless (sin ventana visible)
- Configuración flexible de horarios y oficinas preferidas

## Requisitos

- Python 3.8 o superior
- Google Chrome instalado
- Conexión a Internet

## Instalación

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/tu-usuario/Ayuntamiento-de-Madrid.git
   cd Ayuntamiento-de-Madrid
   ```

2. **Crea un entorno virtual (recomendado):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Linux/Mac
   # o
   venv\Scripts\activate  # En Windows
   ```

3. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura el bot:**
   ```bash
   cp config.example.yaml config.yaml
   # Edita config.yaml con tus datos
   ```

## Configuración

Edita el archivo `config.yaml` con tus datos:

### Datos personales

```yaml
personal:
  nombre: "Tu Nombre"
  apellidos: "Tus Apellidos"
  dni: "12345678A"
  telefono: "600000000"
  email: "tu@email.com"
```

### Trámite

```yaml
tramite:
  categoria: "Padrón"
  nombre: "Alta en el padrón"
```

Trámites disponibles (ejemplos):
- Alta en el padrón
- Cambio de domicilio
- Certificado o volante de empadronamiento

### Notificaciones (opcional)

#### Telegram

1. Habla con [@BotFather](https://t.me/BotFather) y crea un bot
2. Obtén tu chat_id con [@userinfobot](https://t.me/userinfobot)
3. Configura en `config.yaml`:

```yaml
telegram:
  enabled: true
  bot_token: "TU_BOT_TOKEN"
  chat_id: "TU_CHAT_ID"
```

#### Email (Gmail)

1. Activa la verificación en dos pasos en tu cuenta de Google
2. Genera una [contraseña de aplicación](https://myaccount.google.com/apppasswords)
3. Configura en `config.yaml`:

```yaml
email:
  enabled: true
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  sender_email: "tu@gmail.com"
  sender_password: "tu_app_password"
  recipient_email: "tu@email.com"
```

## Uso

### Ejecución básica

```bash
python main.py
```

### Opciones disponibles

```bash
# Usar archivo de configuración personalizado
python main.py --config mi_config.yaml

# Ejecutar en modo headless (sin ventana)
python main.py --headless

# Cambiar intervalo de comprobación (segundos)
python main.py --intervalo 60

# Modo verbose (más información)
python main.py --verbose

# Probar notificaciones
python main.py --test
```

### Ejemplo completo

```bash
python main.py --headless --intervalo 45 --verbose
```

## Cómo funciona

1. El bot navega a la página de citas del Ayuntamiento
2. Selecciona la categoría (ej: Padrón) y el trámite
3. Busca oficinas y citas disponibles
4. Si encuentra disponibilidad, selecciona automáticamente
5. Rellena tus datos personales
6. Confirma la cita
7. Te notifica por Telegram/Email

## Consejos

- **Ejecuta en horas de apertura**: Las citas se suelen abrir a primera hora (08:00-09:00)
- **Usa notificaciones**: Configura Telegram para enterarte al instante
- **Modo no headless**: Para ver qué está haciendo el bot, no uses `--headless`
- **Intervalo corto**: Usa intervalos de 20-30 segundos en horarios de alta demanda

## Estructura del proyecto

```
Ayuntamiento-de-Madrid/
├── config.example.yaml  # Ejemplo de configuración
├── config.yaml          # Tu configuración (no subir a git)
├── main.py              # Punto de entrada
├── requirements.txt     # Dependencias
├── src/
│   ├── __init__.py
│   ├── bot.py          # Bot principal
│   └── notifier.py     # Sistema de notificaciones
└── README.md
```

## Solución de problemas

### El bot no encuentra elementos

La web del Ayuntamiento puede cambiar. Si el bot no funciona:
1. Ejecuta sin `--headless` para ver qué ocurre
2. Las capturas de pantalla se guardan en caso de error

### Error de ChromeDriver

```bash
# El webdriver-manager debería instalarlo automáticamente
# Si falla, instala Chrome y reinicia
```

### Telegram no envía mensajes

1. Verifica que el token es correcto
2. Asegúrate de haber iniciado una conversación con tu bot
3. Prueba con `python main.py --test`

## Aviso legal

Este bot es solo para uso personal. Úsalo de manera responsable y respetando los términos de uso del Ayuntamiento de Madrid. El autor no se hace responsable del mal uso de esta herramienta.

## Licencia

MIT License
