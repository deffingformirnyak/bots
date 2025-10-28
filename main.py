import discord
from discord.ext import commands
import json
import re
import os
from datetime import datetime

# ID канала для логов
LOG_CHANNEL_ID = 1432798738451267706

# Загрузка конфигурации
def load_banned_users():
    try:
        with open('ban.json', 'r') as f:
            data = json.load(f)
            return data.get('banned_ids', [])
    except FileNotFoundError:
        return []

def save_banned_users(banned_ids):
    with open('ban.json', 'w') as f:
        json.dump({'banned_ids': banned_ids}, f, indent=2)

# Настройка бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Регулярные выражения для обнаружения рекламы
INVITE_PATTERN = re.compile(
    r'(discord\.gg/|discord\.com/invite/|discordapp\.com/invite/)[a-zA-Z0-9]+',
    re.IGNORECASE
)

async def send_log(message: str, color: discord.Color = discord.Color.blue()):
    """Отправка лога в специальный канал"""
    try:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                description=message,
                color=color,
                timestamp=datetime.utcnow()
            )
            await channel.send(embed=embed)
    except Exception as e:
        print(f'Ошибка отправки лога: {e}')

@bot.event
async def on_ready():
    print(f'Бот {bot.user} запущен и готов к работе!')
    print(f'ID бота: {bot.user.id}')
    
    await send_log(
        f'🟢 **Бот запущен**\n'
        f'Имя: {bot.user.name}\n'
        f'ID: {bot.user.id}\n'
        f'Серверов: {len(bot.guilds)}',
        discord.Color.green()
    )

@bot.event
async def on_member_join(member):
    """Проверка при входе нового пользователя"""
    banned_ids = load_banned_users()
    
    if member.id in banned_ids:
        try:
            await member.ban(reason="Пользователь в бан-листе")
            print(f'Забанен пользователь при входе: {member.name} ({member.id})')
            
            await send_log(
                f'🔨 **Автобан при входе**\n'
                f'Пользователь: {member.mention} (`{member.name}`)\n'
                f'ID: `{member.id}`\n'
                f'Причина: Пользователь в бан-листе',
                discord.Color.red()
            )
        except discord.Forbidden:
            print(f'Нет прав для бана: {member.name}')
            await send_log(
                f'⚠️ **Ошибка бана**\n'
                f'Не удалось забанить: {member.mention}\n'
                f'ID: `{member.id}`\n'
                f'Причина: Недостаточно прав',
                discord.Color.orange()
            )
        except Exception as e:
            print(f'Ошибка при бане: {e}')
            await send_log(
                f'❌ **Ошибка**\n'
                f'При бане {member.mention}: {str(e)}',
                discord.Color.red()
            )

@bot.event
async def on_message(message):
    # Игнорируем сообщения от ботов
    if message.author.bot:
        return
    
    # Проверка бан-листа
    banned_ids = load_banned_users()
    if message.author.id in banned_ids:
        try:
            await message.delete()
            await message.author.ban(reason="Пользователь в бан-листе")
            print(f'Забанен: {message.author.name} ({message.author.id})')
            
            await send_log(
                f'🔨 **Забанен пользователь**\n'
                f'Пользователь: {message.author.mention} (`{message.author.name}`)\n'
                f'ID: `{message.author.id}`\n'
                f'Канал: {message.channel.mention}\n'
                f'Причина: Обнаружен в бан-листе',
                discord.Color.red()
            )
        except discord.Forbidden:
            print(f'Нет прав для бана: {message.author.name}')
            await send_log(
                f'⚠️ **Ошибка бана**\n'
                f'Не удалось забанить: {message.author.mention}\n'
                f'Причина: Недостаточно прав',
                discord.Color.orange()
            )
        return
    
    # Проверка на рекламу Discord серверов
    if INVITE_PATTERN.search(message.content):
        try:
            msg_preview = message.content[:100] + '...' if len(message.content) > 100 else message.content
            await message.delete()
            
            # Предупреждение пользователю
            warning = await message.channel.send(
                f'{message.author.mention}, реклама Discord серверов запрещена!'
            )
            
            # Удаление предупреждения через 5 секунд
            await warning.delete(delay=5)
            
            print(f'Удалено сообщение с рекламой от {message.author.name}')
            
            await send_log(
                f'🗑️ **Удалено сообщение с рекламой**\n'
                f'Пользователь: {message.author.mention} (`{message.author.name}`)\n'
                f'ID: `{message.author.id}`\n'
                f'Канал: {message.channel.mention}\n'
                f'Сообщение: ```{msg_preview}```',
                discord.Color.orange()
            )
            
        except discord.Forbidden:
            print(f'Нет прав для удаления сообщения')
            await send_log(
                f'⚠️ **Ошибка удаления**\n'
                f'Не удалось удалить рекламу от {message.author.mention}\n'
                f'Причина: Недостаточно прав',
                discord.Color.orange()
            )
        except Exception as e:
            print(f'Ошибка: {e}')
            await send_log(
                f'❌ **Ошибка**\n'
                f'При удалении сообщения: {str(e)}',
                discord.Color.red()
            )
    
    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def addban(ctx, user_id: int):
    """Добавить ID в бан-лист"""
    banned_ids = load_banned_users()
    
    if user_id not in banned_ids:
        banned_ids.append(user_id)
        save_banned_users(banned_ids)
        await ctx.send(f'✅ ID `{user_id}` добавлен в бан-лист')
        
        await send_log(
            f'➕ **Добавлен в бан-лист**\n'
            f'ID: `{user_id}`\n'
            f'Администратор: {ctx.author.mention}',
            discord.Color.blue()
        )
        
        # Попытка забанить, если пользователь на сервере
        try:
            user = await bot.fetch_user(user_id)
            await ctx.guild.ban(user, reason="Добавлен в бан-лист")
            await ctx.send(f'Пользователь {user.name} забанен')
            
            await send_log(
                f'🔨 **Пользователь забанен**\n'
                f'Пользователь: `{user.name}`\n'
                f'ID: `{user_id}`\n'
                f'Администратор: {ctx.author.mention}',
                discord.Color.red()
            )
        except:
            pass
    else:
        await ctx.send(f'❌ ID `{user_id}` уже в бан-листе')

@bot.command()
@commands.has_permissions(administrator=True)
async def removeban(ctx, user_id: int):
    """Удалить ID из бан-листа"""
    banned_ids = load_banned_users()
    
    if user_id in banned_ids:
        banned_ids.remove(user_id)
        save_banned_users(banned_ids)
        await ctx.send(f'✅ ID `{user_id}` удален из бан-листа')
        
        await send_log(
            f'➖ **Удален из бан-листа**\n'
            f'ID: `{user_id}`\n'
            f'Администратор: {ctx.author.mention}',
            discord.Color.green()
        )
    else:
        await ctx.send(f'❌ ID `{user_id}` не найден в бан-листе')

@bot.command()
@commands.has_permissions(administrator=True)
async def banlist(ctx):
    """Показать список забаненных ID"""
    banned_ids = load_banned_users()
    
    if banned_ids:
        ids_text = '\n'.join([f'`{id}`' for id in banned_ids])
        await ctx.send(f'**Забаненные ID ({len(banned_ids)}):**\n{ids_text}')
        
        await send_log(
            f'📋 **Запрошен бан-лист**\n'
            f'Администратор: {ctx.author.mention}\n'
            f'Всего забанено: {len(banned_ids)}',
            discord.Color.blue()
        )
    else:
        await ctx.send('Бан-лист пуст')

@bot.command()
@commands.has_permissions(administrator=True)
async def checkuser(ctx, user_id: int):
    """Проверить статус пользователя"""
    banned_ids = load_banned_users()
    
    if user_id in banned_ids:
        await ctx.send(f'🔴 ID `{user_id}` **ЗАБАНЕН**')
    else:
        await ctx.send(f'🟢 ID `{user_id}` не в бан-листе')
    
    await send_log(
        f'🔍 **Проверка пользователя**\n'
        f'ID: `{user_id}`\n'
        f'Статус: {"🔴 Забанен" if user_id in banned_ids else "🟢 Не забанен"}\n'
        f'Проверил: {ctx.author.mention}',
        discord.Color.blue()
    )

# Обработка ошибок команд
@addban.error
@removeban.error
@banlist.error
async def command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ У вас нет прав администратора!')
        
        await send_log(
            f'⛔ **Отказано в доступе**\n'
            f'Пользователь: {ctx.author.mention}\n'
            f'Команда: `{ctx.message.content}`\n'
            f'Причина: Недостаточно прав',
            discord.Color.red()
        )

# Запуск бота
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if not TOKEN:
        print('ОШИБКА: Установите переменную окружения DISCORD_TOKEN')
    else:
        bot.run(TOKEN)
