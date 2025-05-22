# Bot de Zonas para Telegram 🤖

Bot de Telegram diseñado para gestionar zonas y listas de espera en grupos con rotación automática.

## 📋 Características

- **Gestión de 3 zonas** (Z1, Z2, Z3) con asignación automática
- **Lista de espera** con rotación automática cada 2 horas
- **Control de autorización** por chat específico
- **Horarios múltiples** en diferentes zonas horarias
- **Comandos administrativos** y de usuario diferenciados
- **Rotación automática** programada
- **Logs detallados** para monitoreo

## 🚀 Instalación

### Prerrequisitos

```bash
pip install python-telegram-bot pytz python-telegram-bot[job-queue]
```

o alternativa con UV

```bash
uv sync
```

### Configuración

1. Clona o descarga el archivo `bot_zonas.py`
2. Modifica las constantes en el código:
   ```python
   TOKEN = "TU_TOKEN_DE_BOT_AQUI"
   CREATOR_USERNAME = "@TU_USERNAME"
   ROTATION_DURATION_MINUTES = 120  # Tiempo de rotación en minutos
   ```
3. Ejecuta el bot:
   ```bash
   python bot_zonas.py
   ```

## 🎮 Comandos

### 👤 Comandos de Usuario

| Comando | Descripción |
|---------|-------------|
| `/z1`, `/z2`, `/z3` | Asignarse a una zona específica |
| `/z1 @usuario` | Asignar a otro usuario a la zona |
| `/exitz1`, `/exitz2`, `/exitz3` | Salir de zona específica |
| `/espera` | Unirse a la lista de espera |
| `/espera @usuario` | Añadir a otro usuario a la espera (solo admins) |
| `/exit` | Salir de zona o lista de espera |
| `/exit @usuario` | Remover a otro usuario |
| `/cambiar @usuario` | Intercambiar posiciones con otro usuario |
| `/cambiar @user1 @user2` | Intercambiar posiciones entre usuarios (admins) |
| `/tomarlibre` | Tomar un lugar libre en la lista de espera |
| `/lista` | Ver estado actual de zonas y espera |
| `/reglas` | Mostrar reglas del sistema |
| `/comandos` | Mostrar menú de comandos |

### 👥 Comandos de Administrador

| Comando | Descripción |
|---------|-------------|
| `/abrir` o `/abrirlista` | Abrir la lista para uso |
| `/cerrar` o `/cerrarlista` | Cerrar la lista |
| `/chatid` | Mostrar ID del chat actual |

### 👑 Comandos del Creador

| Comando | Descripción |
|---------|-------------|
| `/autorizar` | Activar el bot en el chat actual |
| `/desautorizar` | Desactivar el bot |

## ⚙️ Funcionamiento

### Sistema de Zonas
- **3 zonas disponibles**: Z1, Z2, Z3
- Cada zona puede tener **un usuario asignado**
- Los usuarios pueden **auto-asignarse** o ser asignados por admins

### Lista de Espera
- Los usuarios pueden unirse a la **lista de espera**
- Posiciones **"Libre"** disponibles para tomar
- **Rotación automática** cada 2 horas

### Rotación Automática
- Cada **2 horas** (configurable)
- Los usuarios en espera **pasan a las zonas**
- Los usuarios en zonas **salen del sistema**
- **Notificación automática** al grupo

## 🌍 Zonas Horarias Soportadas

El bot muestra horarios en múltiples zonas:
- 🇨🇴 Colombia
- 🇲🇽 México  
- 🇻🇪 Venezuela
- 🇦🇷 Argentina / 🇨🇱 Chile
- 🇪🇸 España

## 🔒 Seguridad

- **Autorización por chat**: Solo funciona en el grupo autorizado
- **Control de permisos**: Comandos diferenciados por rol
- **Rechazo de mensajes privados**: Solo funciona en grupos
- **Logs de seguridad**: Registro de intentos no autorizados

## 📊 Estados del Bot

| Estado | Descripción |
|--------|-------------|
| **No autorizado** | Bot inactivo, requiere `/autorizar` |
| **Autorizado pero cerrado** | Bot activo pero lista cerrada |  
| **Autorizado y abierto** | Funcionamiento completo |

## 🛠️ Estructura del Código

```
bot_zonas.py
├── Constantes y configuración
├── Funciones auxiliares
│   ├── get_time_display()
│   ├── format_list()
│   └── Verificaciones de seguridad
├── Comandos de usuario
├── Comandos administrativos  
├── Comandos del creador
├── Job de rotación automática
└── Función main()
```

## 📝 Logs

El bot genera logs detallados:
- ✅ Acciones exitosas
- ⚠️ Advertencias y errores
- 🚫 Intentos no autorizados
- 🔄 Rotaciones automáticas

## 🐛 Solución de Problemas

### Bot no responde
- Verificar que esté autorizado con `/autorizar`
- Confirmar que la lista esté abierta con `/abrir`

### Rotación no funciona  
- El job se configura al autorizar el bot
- Verificar logs para errores de rotación

### Permisos insuficientes
- Solo el creador puede autorizar/desautorizar
- Solo admins pueden abrir/cerrar listas

## 📄 Reglas de Uso

1. Usar zonas solo si estás disponible
2. Respetar turnos y rotaciones  
3. Usar `/exit` para salir correctamente
4. No abusar del sistema
5. No editar mensajes con comandos

## 🤝 Contribución

Para mejorar el bot:
1. Reporta bugs o sugerencias
2. Propón nuevas características
3. Mejora la documentación

## 📞 Soporte

- Creador: `@Soy_Acos` -> Telegram (configurado en el código)
- Logs del sistema para diagnóstico
- Comando `/chatid` para información del chat

---

**Nota**: Este bot está diseñado para funcionar en **un solo grupo autorizado** a la vez para mantener la integridad del sistema de rotación.