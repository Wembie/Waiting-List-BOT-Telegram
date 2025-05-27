# bot_zonas.py
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackContext,
)
from pytz import timezone
from datetime import datetime, timedelta
from logging import basicConfig, getLogger, INFO, WARNING

# Constants
TOKEN = "TU_TOKEN_AQUI"
CREATOR_USERNAME = "@Soy_Acos"
ROTATION_DURATION_MINUTES = 120
DICE_NAME = "EXAMPLE"

# Setup logging
basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=INFO)

logger = getLogger(__name__)

getLogger("httpx").setLevel(WARNING)
getLogger("httpcore").setLevel(WARNING)

# In-memory data
zones = {"z1": None, "z2": None, "z3": None}
waiting_list = []
authorized = False
list_open = False
last_rotation_time = None
rotation_job = None
authorized_chat_id = None  # Solo este chat podrá usar el bot

# Time zones for display
timezones = {
    "🇨🇴 Hora Colombia 🇨🇴": "America/Bogota",
    "🇲🇽 Hora México 🇲🇽": "America/Mexico_City",
    "🇻🇪 Hora Venezuela 🇻🇪": "America/Caracas",
    "🇦🇷 Hora Argentina / Chile 🇨🇱": "America/Argentina/Buenos_Aires",
    "🇪🇸 Hora España 🇪🇸": "Europe/Madrid",
}


# Helper functions
def get_time_display():
    now = datetime.now()
    if last_rotation_time:
        start = last_rotation_time
    else:
        start = now
    end = start + timedelta(minutes=ROTATION_DURATION_MINUTES)

    lines = []
    for country, tz in timezones.items():
        t_start = start.astimezone(timezone(tz)).strftime("%H:%M")
        t_end = end.astimezone(timezone(tz)).strftime("%H:%M")
        lines.append(f"{country} \n⏰ {t_start} ➖ {t_end}")
    return "\n".join(lines)


def is_creator(user):
    return user.username == CREATOR_USERNAME[1:]


async def is_admin(context, chat_id, user_id):
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]


def format_list():
    zona_display = "\n\n🏷️ Zonas Actuales:\n"
    for z, u in zones.items():
        display = (
            u if u else "⚪ Vacío"
        )  # Siempre mostrar "Vacío" para zonas sin usuarios
        zona_display += f"🔹 Zona {z[1]}⃣: {display}\n"

    # Para la lista de espera, usar "Libre" para huecos vacíos
    formatted_waiting_list = []
    for i, item in enumerate(waiting_list, 1):
        formatted_waiting_list.append(f"🔸 {item}")
        if i % 3 == 0 and i < len(waiting_list):  # Si es el tercero y no es el último
            formatted_waiting_list.append("")  # Añade línea vacía

    espera = "\n".join(formatted_waiting_list) if waiting_list else "🔘 Ninguno"
    mins_left = (
        ROTATION_DURATION_MINUTES
        - int((datetime.now() - last_rotation_time).seconds / 60)
        if last_rotation_time
        else 0
    )
    if mins_left < 0:
        mins_left = 0  # Prevenir números negativos

    return (
        f"⚜️ Estado de la Lista de Zonas {DICE_NAME} ⚜️\n\n"
        f"⏰ Horarios de Rotación:\n{get_time_display()}"
        f"{zona_display}"
        f"\n⏳ Próxima rotación en: {mins_left} minutos\n"
        f"\n📋 Lista de Espera:\n{espera}"
    )


async def validate_message(update: Update):
    """Validar que el mensaje no es None (para evitar errores con mensajes editados)"""
    if not update.message:
        logger.warning("⚠️  Mensaje editado ignorado - no se procesarán comandos en mensajes editados")
        return False
    return True


async def reject_private_messages(update: Update):
    if not await validate_message(update):
        return False
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "🚫 Este bot no funciona por mensajes privados."
        )
        logger.warning(
            f"⛔ Mensaje privado rechazado de @{update.effective_user.username}"
        )
        return False
    return True


async def check_authorized_chat(update: Update):
    """Verificar que el comando viene del chat autorizado"""
    if not await validate_message(update):
        return False
        
    current_chat_id = update.effective_chat.id

    if not authorized or authorized_chat_id is None:
        await update.message.reply_text("🚫 Este bot no está autorizado actualmente.")
        return False

    if current_chat_id != authorized_chat_id:
        await update.message.reply_text(
            "🚫 Este bot solo funciona en el grupo autorizado."
        )
        logger.warning(
            f"⛔ Intento de uso desde chat no autorizado: {current_chat_id} (autorizado: {authorized_chat_id})"
        )
        return False

    return True


# Comandos
async def cmd_autorizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global authorized, authorized_chat_id
    if not await reject_private_messages(update):
        return
    user = update.effective_user

    # Obtener el ID del chat actual
    current_chat_id = update.effective_chat.id

    if is_creator(user):
        authorized = True
        authorized_chat_id = current_chat_id  # Guardar el ID del chat autorizado

        # Reset the zones
        for zone in zones:
            zones[zone] = None

        # Clear waiting list
        waiting_list.clear()

        # Set up the rotation job with the current chat ID
        setup_rotation_job(context, current_chat_id)

        await update.message.reply_text(
            f"🔓 Bot autorizado correctamente para este grupo.\n🆔 Chat ID autorizado: `{current_chat_id}`"
        )
        logger.info(f"✅ Bot autorizado por el creador en chat ID: {current_chat_id}")
    else:
        await update.message.reply_text(
            f"🚫 Solo {CREATOR_USERNAME} puede autorizar el uso del bot."
        )
        logger.warning(
            f"⛔ Usuario no autorizado intentó activar el bot: @{user.username}"
        )


def setup_rotation_job(context, chat_id):
    global rotation_job

    # Remove any existing job
    if rotation_job:
        rotation_job.schedule_removal()

    # Create a new job with the current chat ID
    rotation_job = context.job_queue.run_repeating(
        job_rotacion,
        interval=ROTATION_DURATION_MINUTES * 60,
        first=ROTATION_DURATION_MINUTES * 60,
        data=chat_id,  # Pass the chat_id as data to the job
    )
    logger.info(f"🔄 Rotation job scheduled for chat ID: {chat_id}")


async def cmd_desautorizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global authorized, authorized_chat_id, rotation_job, list_open
    if not await reject_private_messages(update):
        return
    user = update.effective_user

    if is_creator(user):
        # Verificar que el comando viene del chat autorizado (si existe)
        if authorized_chat_id and update.effective_chat.id != authorized_chat_id:
            await update.message.reply_text(
                "🚫 Solo puedes desautorizar desde el chat autorizado."
            )
            return

        authorized = False
        authorized_chat_id = None  # Limpiar el ID del chat autorizado
        list_open = False  # Cerrar la lista también

        # Reset zones and waiting list
        for zone in zones:
            zones[zone] = None
        waiting_list.clear()

        # Remove the rotation job
        if rotation_job:
            rotation_job.schedule_removal()
            rotation_job = None

        await update.message.reply_text(
            "🔒 Bot desactivado correctamente.\n🆔 Chat autorizado limpiado."
        )
        logger.info("🔻 Bot desactivado por el creador.")
    else:
        await update.message.reply_text("🚫 Solo el creador puede desautorizar el bot.")
        logger.warning(
            f"⛔ Usuario no autorizado intentó desactivar el bot: @{user.username}"
        )


async def check_authorized(update):
    return await check_authorized_chat(update)


async def check_list_open(update):
    if not await validate_message(update):
        return False
    if not list_open:
        await update.message.reply_text(
            "🚫 La lista está cerrada actualmente. Usa /abrir o /abrirlista para habilitarla."
        )
        return False
    return True


async def cmd_lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await reject_private_messages(update):
        return
    if not await check_authorized(update):
        return
    if not await check_list_open(update):
        return
    await update.message.reply_text(format_list())


async def assign_zone(update, zone, context: ContextTypes.DEFAULT_TYPE):
    if not await reject_private_messages(update):
        return
    if not await check_authorized(update):
        return
    if not await check_list_open(update):
        return

    username = context.args[0] if context.args else f"@{update.effective_user.username}"

    # Verificar si el usuario ya está en otra zona
    for current_zone, occupant in zones.items():
        if occupant == username:
            await update.message.reply_text(
                f"⚠️ Ya estás en la zona {current_zone[1]}⃣. Primero usa /exit para salir."
            )
            return

    # Verificar si el usuario está en la lista de espera
    if username in waiting_list:
        await update.message.reply_text(
            "⚠️ Estás en la lista de espera. Usa /exit para salir de ella primero."
        )
        return

    # Asignar a la zona solicitada si está disponible
    if zones[zone] is None:
        zones[zone] = username
        await update.message.reply_text(f"✅ {username} asignado a Zona {zone[1]}⃣")
        logger.info(f"{username} asignado a {zone}")
    else:
        await update.message.reply_text(f"⚠️ La zona {zone[1]}⃣ ya está ocupada.")
    await update.message.reply_text(format_list())


async def remove_zone(update, zone):
    if not await reject_private_messages(update):
        return
    if not await check_authorized(update):
        return
    if not await check_list_open(update):
        return
    username = f"@{update.effective_user.username}"

    # Verificar que el usuario esté en la zona específica
    if zones[zone] == username:
        zones[zone] = None  # Dejar como vacío, no como "Libre"
        await update.message.reply_text(f"🚫 {username} ha salido de Zona {zone[1]}⃣")
        logger.info(f"{username} eliminado de {zone}")
    else:
        await update.message.reply_text(
            f"⚠️ No estás en la zona {zone[1]}⃣ o no tienes permiso."
        )
    await update.message.reply_text(format_list())


async def cmd_espera(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await reject_private_messages(update):
        return
    if not await check_authorized(update):
        return
    if not await check_list_open(update):
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Si hay argumentos, validamos si el usuario es admin
    if context.args:
        if not await is_admin(context, chat_id, user_id):
            await update.message.reply_text(
                "🚫 Solo los administradores pueden añadir a otros usuarios a la lista de espera."
            )
            return
        username = context.args[0]
    else:
        username = f"@{update.effective_user.username}"

    # Verificar si el usuario ya está en alguna zona
    for zone, occupant in zones.items():
        if occupant == username:
            await update.message.reply_text(
                f"⚠️ {username} ya está en la zona {zone[1]}⃣. Usa /exit para salir primero."
            )
            return

    # Verificar si ya está en la lista de espera
    if username in waiting_list:
        await update.message.reply_text(f"⚠️ {username} ya está en la lista de espera.")
    else:
        waiting_list.append(username)
        await update.message.reply_text(f"📥 {username} añadido a la lista de espera")
        logger.info(f"{username} añadido a espera")

    await update.message.reply_text(format_list())


async def cmd_cambiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await reject_private_messages(update):
        return
    if not await check_authorized(update):
        return
    if not await check_list_open(update):
        return

    args = context.args
    user = update.effective_user
    username1 = f"@{user.username}"

    if len(args) == 0:
        await update.message.reply_text(
            "❌ Usa /cambiar @Usuario o /cambiar @Usuario1 @Usuario2"
        )
        return

    # Cambio a nombre propio
    if len(args) == 1:
        username2 = args[0]
    elif len(args) == 2:
        if not is_creator(user) and not await is_admin(
            context, update.effective_chat.id, user.id
        ):
            await update.message.reply_text(
                "🚫 Solo administradores pueden intercambiar a otros."
            )
            return
        username1, username2 = args
    else:
        await update.message.reply_text(
            "❌ Formato incorrecto. Usa /cambiar @Usuario o /cambiar @Usuario1 @Usuario2"
        )
        return

    if username1 == username2:
        await update.message.reply_text("❌ No puedes intercambiarte contigo mismo.")
        return

    # Buscar posiciones
    def find_user_position(username):
        for zone, occupant in zones.items():
            if occupant == username:
                return ("zone", zone)
        if username in waiting_list:
            return ("wait", waiting_list.index(username))
        return None

    pos1 = find_user_position(username1)
    pos2 = find_user_position(username2)

    if not pos1 and not pos2:
        await update.message.reply_text(
            "❌ Ninguno de los usuarios está en zonas ni en lista de espera."
        )
        return

    if pos1 and pos2:
        if pos1[0] == "zone" and pos2[0] == "zone":
            zones[pos1[1]], zones[pos2[1]] = zones[pos2[1]], zones[pos1[1]]
        elif pos1[0] == "zone" and pos2[0] == "wait":
            zones[pos1[1]] = username2
            waiting_list[pos2[1]] = username1
        elif pos1[0] == "wait" and pos2[0] == "zone":
            zones[pos2[1]] = username1
            waiting_list[pos1[1]] = username2
        elif pos1[0] == "wait" and pos2[0] == "wait":
            waiting_list[pos1[1]], waiting_list[pos2[1]] = (
                waiting_list[pos2[1]],
                waiting_list[pos1[1]],
            )
    elif pos1 and not pos2:
        if pos1[0] == "zone":
            zones[pos1[1]] = username2
        elif pos1[0] == "wait":
            waiting_list[pos1[1]] = username2
    elif pos2 and not pos1:
        if pos2[0] == "zone":
            zones[pos2[1]] = username1
        elif pos2[0] == "wait":
            waiting_list[pos2[1]] = username1

    await update.message.reply_text(
        f"🔁 {username1} ha sido intercambiado con {username2}"
    )
    await update.message.reply_text(format_list())


async def cmd_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await reject_private_messages(update):
        return
    if not await check_authorized(update):
        return
    if not await check_list_open(update):
        return

    user_requesting = update.effective_user
    args = context.args
    target_username = f"@{user_requesting.username}"  # Por defecto, él mismo

    # Si se pasa un @usuario como argumento
    if args:
        # if not await is_admin(context, update.effective_chat.id, user_requesting.id) and not is_creator(user_requesting):
        #     await update.message.reply_text("🚫 Solo administradores pueden expulsar a otros usuarios.")
        #     return
        if args[0].startswith("@"):
            target_username = args[0]
        else:
            await update.message.reply_text("⚠️ Usa el formato /exit @usuario")
            return

    removed = False

    # Eliminar de zonas
    for zone in zones:
        if zones[zone] == target_username:
            zones[zone] = None
            removed = True
            logger.info(f"{target_username} fue eliminado de {zone}")

    # Eliminar de lista de espera
    for i, user in enumerate(waiting_list):
        if user == target_username:
            waiting_list[i] = "Libre"
            removed = True
            logger.info(f"{target_username} fue eliminado de la lista de espera")
            break

    if removed:
        if target_username == f"@{user_requesting.username}":
            await update.message.reply_text("✅ Saliste correctamente.")
        else:
            await update.message.reply_text(
                f"✅ {target_username} fue removido correctamente."
            )
    else:
        await update.message.reply_text(
            f"⚠️ {target_username} no se encontraba en ninguna zona ni en la lista."
        )

    await update.message.reply_text(format_list())


async def cmd_tomarlibre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await reject_private_messages(update):
        return
    if not await check_authorized(update):
        return
    if not await check_list_open(update):
        return
    if not waiting_list:
        await update.message.reply_text(f"⚠️ No hay ningun espacio libre.")
        return
    username = f"@{update.effective_user.username}"

    # Verificar que el usuario no esté ya en ninguna zona
    for zone, occupant in zones.items():
        if occupant == username:
            await update.message.reply_text(
                f"⚠️ Ya estás en la zona {zone[1]}⃣. Primero usa /exit para salir."
            )
            return

    # Verificar que el usuario no esté en la lista de espera
    if username in waiting_list:
        await update.message.reply_text(
            "⚠️ Estás en la lista de espera. Usa /exit para salir de ella primero."
        )
        return

    # Buscar si hay posiciones "Libre" en la lista de espera
    libre_index = None
    for i, user in enumerate(waiting_list):
        if user == "Libre":
            libre_index = i
            break

    # Si hay un "Libre" en la lista de espera, asignar al usuario allí
    if libre_index is not None:
        waiting_list[libre_index] = username
        await update.message.reply_text(
            f"✅ {username} tomó un lugar libre en la lista de espera"
        )
        logger.info(f"{username} tomó lugar libre en la lista de espera")
        await update.message.reply_text(format_list())
        return

    await update.message.reply_text("⚠️ No hay lugares libres disponibles.")


async def cmd_abrir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await reject_private_messages(update):
        return
    if not await check_authorized(update):
        return
    global list_open
    if list_open is True:
        await update.message.reply_text("🔓 La lista ya esta abierta.")
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if await is_admin(context, chat_id, user_id):
        global last_rotation_time
        list_open = True
        last_rotation_time = datetime.now()

        # Actualizar el trabajo de rotación con el tiempo correcto
        if rotation_job:
            setup_rotation_job(context, authorized_chat_id)

        await update.message.reply_text(
            "🔓 Lista abierta. ¡Ya puedes usar los comandos!"
        )
        await update.message.reply_text(format_list())
        logger.info("Lista abierta")
    else:
        await update.message.reply_text(
            "🚫 Solo los administradores pueden abrir la lista."
        )


async def cmd_cerrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await reject_private_messages(update):
        return
    if not await check_authorized(update):
        return
    global list_open
    if list_open is False:
        await update.message.reply_text("🔓 La lista ya esta cerrada.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if await is_admin(context, chat_id, user_id):
        list_open = False
        for zone in zones:
            zones[zone] = None
        waiting_list.clear()

        await update.message.reply_text("🔒 Lista cerrada.")
        logger.info("Lista cerrada")
    else:
        await update.message.reply_text(
            "🚫 Solo los administradores pueden cerrar la lista."
        )


async def cmd_reglas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await reject_private_messages(update):
        return
    if not await check_authorized(update):
        return
    await update.message.reply_text(
        """📜 Reglas del Sistema de Zonas:
1️⃣ Usa las zonas solo si estás disponible.
2️⃣ Respeta los turnos y rotaciones.
3️⃣ Usa /exit para salir de zona o lista.
4️⃣ No abuses del sistema.
5️⃣ No editar mensajes con comandos.

✅ ¡Convivencia primero!"""
    )


async def cmd_comandos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorized(update):
        return
    if not await validate_message(update):
        return
    await update.message.reply_text(
        """📌 Menú de Comandos:

▶️ Usuarios:
/z1 /z2 /z3 - Asignarte a zona
/z1 @usuario /z2 @usuario /z3 @usuario - Asignar a otro usuario
/exitz1 /exitz2 /exitz3 - Salir de zona
/espera - Unirse a la lista de espera
/exit o /exitlista - Salir de zona o lista
/exit @usuario - Sacar a otro usuario
/cambiar @usuario - Cambiar zonas/espera entre usuarios                             
/cambiar @usuario1 @usuario2 - Cambiar zonas/espera entre usuarios
/tomarlibre - Tomar lugar libre en espera
/lista - Ver estado actual
/reglas - Reglas
/comandos - Ver este menú

▶️ Admins:
/abrir - Abrir lista
/cerrar - Cerrar lista
/abrirlista - Abrir lista (Diferente comando)
/cerrarlista - Cerrar lista (Diferente comando)

▶️ Creador:
/autorizar - Activar bot
/desautorizar - Desactivar bot

▶️ Utilidades:
/chatid - Mostrar ID del chat actual"""
    )


# JOB: Rotar zonas automáticamente
async def job_rotacion(context: CallbackContext):
    global zones, waiting_list, last_rotation_time
    if not list_open or not authorized_chat_id:
        return

    # Get the chat_id from the job data (should be the authorized chat)
    chat_id = context.job.data

    # Verificar que el job esté corriendo para el chat autorizado
    if chat_id != authorized_chat_id:
        logger.warning(f"🚫 Job de rotación cancelado - chat no autorizado: {chat_id}")
        return

    logger.info(f"🔁 Rotando zonas automáticamente en chat autorizado ID: {chat_id}...")

    # Crear nuevas zonas vacías
    new_zones = {zone: None for zone in zones}

    # Mover usuarios en orden
    for i, zone in enumerate(zones.keys()):
        if i < len(waiting_list):
            if waiting_list[i] != "Libre":
                # Asignar el usuario de la lista de espera a la zona
                new_zones[zone] = waiting_list[i]
                logger.info(f"🔁 Asignando {waiting_list[i]} a {zone}")
            else:
                # Si la posición es "Libre", dejarla vacía
                new_zones[zone] = None

    # Actualizar la lista de espera eliminando a los asignados
    waiting_list = waiting_list[len(zones) :] if len(waiting_list) > len(zones) else []

    # Actualizar las zonas
    zones = new_zones
    last_rotation_time = datetime.now()

    # Enviar mensaje al grupo autorizado
    await context.bot.send_message(
        chat_id=chat_id,
        text="🔁 Rotación realizada automáticamente\n\n" + format_list(),
    )


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await reject_private_messages(update):
        return
    if not await check_authorized(update):
        return
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if await is_admin(context, chat_id, user_id):
        """Comando para mostrar el ID del chat actual - útil para depuración"""
        authorized_status = (
            "✅ AUTORIZADO" if chat_id == authorized_chat_id else "❌ NO AUTORIZADO"
        )
        await update.message.reply_text(
            f"🆔 ID de este chat: `{chat_id}`\n📊 Estado: {authorized_status}"
        )
        logger.info(f"Solicitud de ID de chat: {chat_id}")
    else:
        await update.message.reply_text(
            "🚫 Solo los administradores pueden usar este comando."
        )
        logger.warning(
            f"⛔ Usuario no autorizado intentó obtener el ID del chat: @{update.effective_user.username}"
        )


# MAIN
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("autorizar", cmd_autorizar))
    app.add_handler(CommandHandler("desautorizar", cmd_desautorizar))
    app.add_handler(CommandHandler("lista", cmd_lista))
    app.add_handler(
        CommandHandler("z1", lambda update, context: assign_zone(update, "z1", context))
    )
    app.add_handler(
        CommandHandler("z2", lambda update, context: assign_zone(update, "z2", context))
    )
    app.add_handler(
        CommandHandler("z3", lambda update, context: assign_zone(update, "z3", context))
    )
    app.add_handler(CommandHandler("exitz1", lambda u, c: remove_zone(u, "z1")))
    app.add_handler(CommandHandler("exitz2", lambda u, c: remove_zone(u, "z2")))
    app.add_handler(CommandHandler("exitz3", lambda u, c: remove_zone(u, "z3")))
    app.add_handler(CommandHandler("espera", cmd_espera))
    app.add_handler(CommandHandler("cambiar", cmd_cambiar))
    app.add_handler(CommandHandler("exit", cmd_exit))
    app.add_handler(CommandHandler("exitlista", cmd_exit))
    app.add_handler(CommandHandler("tomarlibre", cmd_tomarlibre))
    app.add_handler(CommandHandler("abrir", cmd_abrir))
    app.add_handler(CommandHandler("abrirlista", cmd_abrir))
    app.add_handler(CommandHandler("cerrar", cmd_cerrar))
    app.add_handler(CommandHandler("cerrarlista", cmd_cerrar))
    app.add_handler(CommandHandler("reglas", cmd_reglas))
    app.add_handler(CommandHandler("comandos", cmd_comandos))
    app.add_handler(
        CommandHandler("chatid", cmd_chatid)
    )  # Comando para obtener el ID del chat

    # We don't set up the rotation job here - it will be set up when /autorizar is called

    logger.info("🚀 Bot en ejecución...")
    app.run_polling()


if __name__ == "__main__":
    main()
