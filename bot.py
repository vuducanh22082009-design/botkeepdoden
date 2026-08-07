import threading
import discord
from discord import app_commands
import random
import time
import sqlite3
import os
from typing import Optional
from dotenv import load_dotenv
from flask import Flask

# ====== CẤU HÌNH ADMIN ======
ADMIN_ID = 1026417896114630676
FOOTER_TEXT = "code bot by ducanh"

# 1. Tạo Flask server để duy trì uptime trên Render/Replit
app = Flask('')

@app.route('/')
def home():
    return 'Bot is alive!'

def run_http():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_http, daemon=True).start()

# ====== CẤU HÌNH BIẾN MÔI TRƯỜNG ======
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ====== KHỞI TẠO BOT ======
intents = discord.Intents.default()
intents.message_content = False  # Slash commands không cần đọc tin nhắn
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ====== CƠ SỞ DỮ LIỆU ======
conn = sqlite3.connect('economy.db', check_same_thread=False)

def init_db():
    """Khởi tạo các bảng cơ sở dữ liệu."""
    with conn:
        # Bảng người dùng
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                last_daily REAL DEFAULT 0
            )
        ''')
        # Bảng lịch sử cược Tài Xỉu
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tx_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                choice TEXT,
                bet INTEGER,
                result TEXT,
                dice TEXT,
                win INTEGER,
                timestamp REAL
            )
        ''')

init_db()

# ====== HÀM TIỆN ÍCH DỊNH DẠNG TIỀN ======
def format_money(amount: int) -> str:
    """Chuyển đổi số tiền thành định dạng k, M, B."""
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    
    if amount >= 1_000_000_000:
        val = amount / 1_000_000_000
        return f"{sign}{val:.2f}".rstrip('0').rstrip('.') + "B VNĐ"
    elif amount >= 1_000_000:
        val = amount / 1_000_000
        return f"{sign}{val:.2f}".rstrip('0').rstrip('.') + "M VNĐ"
    elif amount >= 1_000:
        val = amount / 1_000
        return f"{sign}{val:.2f}".rstrip('0').rstrip('.') + "k VNĐ"
    return f"{sign}{amount} VNĐ"

# ====== HÀM TIỆN ÍCH DATABASE ======
def get_user(user_id: int):
    """Lấy dữ liệu người dùng, tự động tạo mới nếu chưa tồn tại."""
    cursor = conn.cursor()
    cursor.execute('SELECT balance, last_daily FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute('INSERT INTO users (user_id, balance, last_daily) VALUES (?, 0, 0)', (user_id,))
        conn.commit()
        return 0, 0.0
    return row  # (balance, last_daily)

def set_balance(user_id: int, new_balance: int, last_daily: Optional[float] = None):
    """Cập nhật số dư và tùy chọn thời gian daily mới."""
    cursor = conn.cursor()
    if last_daily is not None:
        cursor.execute('UPDATE users SET balance = ?, last_daily = ? WHERE user_id = ?',
                       (new_balance, last_daily, user_id))
    else:
        cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?',
                       (new_balance, user_id))
    conn.commit()

def parse_bet(balance: int, amount_str: str) -> Optional[int]:
    """Chuyển đổi chuỗi cược (VD: 100k, 1M, 50%, all) thành số tiền thực tế."""
    amount_str = amount_str.strip().lower()
    if amount_str == 'all':
        return balance
    if amount_str.endswith('%'):
        try:
            percent = float(amount_str[:-1])
            if 0 < percent <= 100:
                return int(balance * (percent / 100))
        except ValueError:
            return None
            
    # Hỗ trợ ký tự viết tắt k, m, b khi nhập cược
    multiplier = 1
    if amount_str.endswith('k'):
        multiplier = 1_000
        amount_str = amount_str[:-1]
    elif amount_str.endswith('m'):
        multiplier = 1_000_000
        amount_str = amount_str[:-1]
    elif amount_str.endswith('b'):
        multiplier = 1_000_000_000
        amount_str = amount_str[:-1]

    try:
        amount = int(float(amount_str) * multiplier)
        if amount > 0:
            return amount
    except ValueError:
        pass
    return None

# ====== SỰ KIỆN SẴN SÀNG ======
@bot.event
async def on_ready():
    try:
        await tree.sync()  # Đồng bộ các lệnh Slash Command lên Discord
        print(f'✅ Bot {bot.user} đã đăng nhập và đồng bộ lệnh thành công!')
    except Exception as e:
        print(f'❌ Lỗi đồng bộ lệnh: {e}')

# ====== LỆNH DONATE ======
@tree.command(name='donate', description='Ủng hộ nhà phát triển bot')
async def donate(interaction: discord.Interaction):
    embed = discord.Embed(
        title='☕ ỦNG HỘ BỘT / DONATE',
        description='Cảm ơn bạn đã sử dụng và ủng hộ bot!\n\n'
                    '🏦 **Ngân hàng:** MB Bank\n'
                    '💳 **STK:** 0915779767\n\n'
                    '*"cam on vi da den"*',
        color=0x3498db
    )
    embed.set_footer(text=FOOTER_TEXT)
    await interaction.response.send_message(embed=embed)

# ====== LỆNH MENU ======
@tree.command(name='menu', description='Hiển thị danh sách lệnh của bot')
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(title='📋 MENU BOT TÀI XỈU', color=0xf1c40f)
    embed.add_field(name='💰 /money daily', value='Nhận tiền ngẫu nhiên từ 1k đến 1M (hồi 5 phút)', inline=False)
    embed.add_field(name='💳 /money check', value='Kiểm tra số dư hiện tại', inline=False)
    embed.add_field(name='🏆 /money top', value='Bảng xếp hạng người giàu nhất', inline=False)
    embed.add_field(name='💸 /money pay <số_tiền> @người_chơi', value='Chuyển tiền cho người khác', inline=False)
    embed.add_field(name='🎁 /money pay_all <số_tiền>', value='Chia đều tiền thưởng cho tất cả người chơi', inline=False)
    embed.add_field(name='🎲 /tx <tài/xỉu> <số_tiền>', value='Cược tài/xỉu (số tiền, 100k, 1M, all, 50%)', inline=False)
    embed.add_field(name='📜 /tx_history', value='Xem 10 ván cược Tài Xỉu gần nhất của bạn', inline=False)
    embed.add_field(name='☕ /donate', value='Ủng hộ nhà phát triển bot', inline=False)
    
    # Chỉ Admin mới thấy phần này
    if interaction.user.id == ADMIN_ID:
        embed.add_field(
            name='👑 LỆNH DÀNH CHO ADMIN',
            value=(
                '`/admin pay <số_tiền> [@người_chơi]` - Cộng tiền cho bản thân hoặc người khác\n'
                '`/admin take <số_tiền> @người_chơi` - Tịch thu/Trừ tiền người chơi\n'
                '`/admin setbalance <số_tiền> @người_chơi` - Đặt lại số dư\n'
                '`/reset money [@người_chơi] [reset_all]` - Reset số dư (1 người hoặc tất cả)'
            ),
            inline=False
        )

    embed.set_footer(text=FOOTER_TEXT)
    await interaction.response.send_message(embed=embed)

# ====== NHÓM LỆNH MONEY ======
money_group = app_commands.Group(name='money', description='Quản lý tiền của bạn')

@money_group.command(name='daily', description='Nhận tiền thưởng hàng ngày (5 phút hồi)')
async def money_daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    balance, last_daily = get_user(user_id)
    now = time.time()
    cooldown = 300  # 5 phút
    remaining = now - last_daily
    if remaining < cooldown:
        left = int(cooldown - remaining)
        mins = left // 60
        secs = left % 60
        await interaction.response.send_message(
            f'⏳ Bạn cần chờ thêm **{mins} phút {secs} giây** để dùng lại lệnh này.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    reward = random.randint(1000, 1000000)
    new_balance = balance + reward
    set_balance(user_id, new_balance, now)
    await interaction.response.send_message(
        f'🎁 Bạn nhận được **{format_money(reward)}**! Số dư hiện tại: **{format_money(new_balance)}**.\n\n*{FOOTER_TEXT}*'
    )

@money_group.command(name='check', description='Kiểm tra số dư của bạn')
async def money_check(interaction: discord.Interaction):
    balance, _ = get_user(interaction.user.id)
    await interaction.response.send_message(f'💰 Số dư của bạn: **{format_money(balance)}**.\n\n*{FOOTER_TEXT}*')

@money_group.command(name='top', description='Bảng xếp hạng người giàu nhất')
async def money_top(interaction: discord.Interaction):
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10')
    rows = cursor.fetchall()
    if not rows:
        await interaction.response.send_message(f'Chưa có dữ liệu người chơi.\n\n*{FOOTER_TEXT}*')
        return

    embed = discord.Embed(title='🏆 BẢNG XẾP HẠNG TÀI SẢN', color=0xe67e22)
    for idx, (uid, bal) in enumerate(rows, start=1):
        try:
            user = await bot.fetch_user(uid)
            name = user.name
        except Exception:
            name = f'ID: {uid}'
        embed.add_field(name=f'{idx}. {name}', value=format_money(bal), inline=False)
    
    embed.set_footer(text=FOOTER_TEXT)
    await interaction.response.send_message(embed=embed)

@money_group.command(name='pay', description='Chuyển tiền cho người chơi khác')
@app_commands.describe(amount='Số tiền muốn chuyển (VD: 50k, 1M, 100000)', member='Người nhận')
async def money_pay(interaction: discord.Interaction, amount: str, member: discord.Member):
    sender_id = interaction.user.id
    receiver_id = member.id
    if sender_id == receiver_id:
        await interaction.response.send_message(f'Không thể tự chuyển tiền cho chính mình.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    sender_balance, _ = get_user(sender_id)
    parsed_amount = parse_bet(sender_balance, amount)

    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message(f'Số tiền chuyển không hợp lệ.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    if sender_balance < parsed_amount:
        await interaction.response.send_message(f'Bạn không đủ tiền để chuyển.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    # Trừ tiền người gửi
    new_sender_balance = sender_balance - parsed_amount
    set_balance(sender_id, new_sender_balance)

    # Cộng tiền người nhận
    receiver_balance, _ = get_user(receiver_id)
    new_receiver_balance = receiver_balance + parsed_amount
    set_balance(receiver_id, new_receiver_balance)

    await interaction.response.send_message(
        f'✅ Đã chuyển **{format_money(parsed_amount)}** cho {member.mention}. '
        f'Số dư của bạn còn **{format_money(new_sender_balance)}**.\n\n*{FOOTER_TEXT}*'
    )

@money_group.command(name='pay_all', description='Chia đều số tiền thưởng cho tất cả người chơi trong hệ thống')
@app_commands.describe(amount='Tổng số tiền muốn phát lì xì (VD: 1M, 10M)')
async def money_pay_all(interaction: discord.Interaction, amount: str):
    sender_id = interaction.user.id
    sender_balance, _ = get_user(sender_id)
    parsed_amount = parse_bet(sender_balance, amount)

    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message(f'Số tiền không hợp lệ.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    if sender_balance < parsed_amount:
        await interaction.response.send_message(f'Bạn không đủ tiền để thực hiện lì xì.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE user_id != ?', (sender_id,))
    users = cursor.fetchall()

    if not users:
        await interaction.response.send_message(f'Không có người chơi khác để nhận lì xì.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    each_amount = parsed_amount // len(users)
    if each_amount <= 0:
        await interaction.response.send_message(f'Số tiền quá nhỏ để chia cho tất cả mọi người.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    # Trừ tiền người phát
    set_balance(sender_id, sender_balance - parsed_amount)

    # Cộng tiền cho từng người
    for (uid,) in users:
        bal, _ = get_user(uid)
        set_balance(uid, bal + each_amount)

    await interaction.response.send_message(
        f'🎉 {interaction.user.mention} đã phát lì xì tổng cộng **{format_money(parsed_amount)}** '
        f'cho **{len(users)}** người chơi (mỗi người nhận **{format_money(each_amount)}**)!\n\n*{FOOTER_TEXT}*'
    )

tree.add_command(money_group)

# ====== NHÓM LỆNH ADMIN ======
admin_group = app_commands.Group(name='admin', description='Quyền hạn Admin')

@admin_group.command(name='pay', description='[ADMIN] Cộng tiền cho bản thân hoặc người chơi khác')
@app_commands.describe(amount='Số tiền muốn cấp (VD: 1M, 10B)', member='Người nhận (để trống nếu tự cấp cho bản thân)')
async def admin_pay(interaction: discord.Interaction, amount: str, member: Optional[discord.Member] = None):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(f'❌ Bạn không có quyền sử dụng lệnh của Admin.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    parsed_amount = parse_bet(1_000_000_000_000, amount)
    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message(f'Số tiền cấp không hợp lệ.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    target_user = member if member is not None else interaction.user
    target_id = target_user.id

    balance, _ = get_user(target_id)
    new_balance = balance + parsed_amount
    set_balance(target_id, new_balance)

    if target_id == interaction.user.id:
        await interaction.response.send_message(
            f'👑 **[ADMIN]** Bạn đã tự cộng **{format_money(parsed_amount)}** vào tài khoản. '
            f'Số dư hiện tại: **{format_money(new_balance)}**.\n\n*{FOOTER_TEXT}*'
        )
    else:
        await interaction.response.send_message(
            f'👑 **[ADMIN]** Đã cộng **{format_money(parsed_amount)}** cho {target_user.mention}. '
            f'Số dư mới của họ: **{format_money(new_balance)}**.\n\n*{FOOTER_TEXT}*'
        )

@admin_group.command(name='take', description='[ADMIN] Trừ tiền/Tịch thu tiền của người chơi')
@app_commands.describe(amount='Số tiền muốn trừ', member='Người chơi bị trừ tiền')
async def admin_take(interaction: discord.Interaction, amount: str, member: discord.Member):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(f'❌ Bạn không có quyền sử dụng lệnh của Admin.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    balance, _ = get_user(member.id)
    parsed_amount = parse_bet(balance, amount)

    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message(f'Số tiền trừ không hợp lệ.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    new_balance = max(0, balance - parsed_amount)
    set_balance(member.id, new_balance)

    await interaction.response.send_message(
        f'👑 **[ADMIN]** Đã tịch thu **{format_money(parsed_amount)}** từ {member.mention}. '
        f'Số dư còn lại của họ: **{format_money(new_balance)}**.\n\n*{FOOTER_TEXT}*'
    )

@admin_group.command(name='setbalance', description='[ADMIN] Đặt lại số dư của người chơi')
@app_commands.describe(amount='Số tiền thiết lập', member='Người chơi cần đặt lại số dư')
async def admin_setbalance(interaction: discord.Interaction, amount: str, member: discord.Member):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(f'❌ Bạn không có quyền sử dụng lệnh của Admin.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    parsed_amount = parse_bet(1_000_000_000_000, amount)
    if parsed_amount is None or parsed_amount < 0:
        await interaction.response.send_message(f'Số tiền không hợp lệ.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    target_id = member.id
    get_user(target_id)
    set_balance(target_id, parsed_amount)

    await interaction.response.send_message(
        f'👑 **[ADMIN]** Đã thiết lập số dư của {member.mention} thành **{format_money(parsed_amount)}**.\n\n*{FOOTER_TEXT}*'
    )

tree.add_command(admin_group)

# ====== LỆNH RESET MONEY (ADMIN) ======
reset_group = app_commands.Group(name='reset', description='Lệnh Reset dữ liệu')

@reset_group.command(name='money', description='[ADMIN] Reset số dư của người chơi về 0')
@app_commands.describe(
    member='Chọn người chơi cụ thể để reset',
    reset_all='Chọn True nếu muốn RESET TẤT CẢ NGƯỜI CHƠI'
)
async def reset_money(
    interaction: discord.Interaction, 
    member: Optional[discord.Member] = None, 
    reset_all: Optional[bool] = False
):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(f'❌ Bạn không có quyền sử dụng lệnh của Admin.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    cursor = conn.cursor()

    if reset_all:
        cursor.execute('UPDATE users SET balance = 0')
        conn.commit()
        await interaction.response.send_message(f'⚠️ **[ADMIN]** Đã reset số dư của **TẤT CẢ** người chơi về **0 VNĐ**!\n\n*{FOOTER_TEXT}*')
    elif member is not None:
        get_user(member.id)
        set_balance(member.id, 0)
        await interaction.response.send_message(f'🧹 **[ADMIN]** Đã reset số dư của {member.mention} về **0 VNĐ**.\n\n*{FOOTER_TEXT}*')
    else:
        await interaction.response.send_message(
            f'⚠️ Vui lòng chọn một người chơi `@member` hoặc đặt `reset_all: True` để thực hiện reset.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )

tree.add_command(reset_group)

# ====== LỆNH TÀI XỈU ======
@tree.command(name='tx', description='Cược Tài hoặc Xỉu với số tiền tùy chọn')
@app_commands.describe(
    choice='Chọn "tài" hoặc "xỉu"',
    amount='Số tiền cược (VD: 10k, 500k, 1M, all, 50%)'
)
async def tx(interaction: discord.Interaction, choice: str, amount: str):
    choice = choice.strip().lower()
    if choice not in ('tài', 'xỉu'):
        await interaction.response.send_message(f'Lựa chọn phải là `tài` hoặc `xỉu`.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    user_id = interaction.user.id
    balance, _ = get_user(user_id)
    bet = parse_bet(balance, amount)
    if bet is None or bet <= 0:
        await interaction.response.send_message(f'Số tiền cược không hợp lệ.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return
    if bet > balance:
        await interaction.response.send_message(f'Bạn không đủ số dư để cược.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    # Tung 3 xúc xắc
    dice = [random.randint(1, 6) for _ in range(3)]
    total = sum(dice)
    result = 'tài' if 11 <= total <= 18 else 'xỉu'

    win = (choice == result)
    dice_str = ', '.join(map(str, dice))

    if win:
        new_balance = balance + bet
        profit = bet
        status = 'THẮNG'
        change_text = f'+{format_money(profit)}'
    else:
        new_balance = balance - bet
        profit = -bet
        status = 'THUA'
        change_text = f'-{format_money(bet)}'

    set_balance(user_id, new_balance)

    # Lưu lịch sử ván cược
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO tx_history (user_id, choice, bet, result, dice, win, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (user_id, choice, bet, result, dice_str, 1 if win else 0, time.time())
    )
    conn.commit()

    embed = discord.Embed(title='🎲 KẾT QUẢ TÀI XỈU', color=0x2ecc71 if win else 0xe74c3c)
    embed.add_field(name='👤 Người chơi', value=interaction.user.name, inline=True)
    embed.add_field(name='🆔 ID Discord', value=str(user_id), inline=True)
    embed.add_field(name='💰 Cược', value=f'{choice.upper()} - {format_money(bet)}', inline=False)
    embed.add_field(name='🎲 Xúc xắc', value=f'[{dice_str}] (Tổng {total}) → **{result.upper()}**', inline=False)
    embed.add_field(name=f'📢 {status}', value=change_text, inline=False)
    embed.add_field(name='💳 Số dư mới', value=format_money(new_balance), inline=False)
    embed.set_footer(text=FOOTER_TEXT)

    await interaction.response.send_message(embed=embed)

@tree.command(name='tx_history', description='Xem 10 ván cược Tài Xỉu gần nhất của bạn')
async def tx_history(interaction: discord.Interaction):
    cursor = conn.cursor()
    cursor.execute(
        'SELECT choice, bet, result, dice, win FROM tx_history WHERE user_id = ? ORDER BY id DESC LIMIT 10',
        (interaction.user.id,)
    )
    rows = cursor.fetchall()
    if not rows:
        await interaction.response.send_message(f'Bạn chưa tham gia ván Tài Xỉu nào.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    embed = discord.Embed(title=f'📜 LỊCH SỬ CƯỢC TÀI XỈU - {interaction.user.name}', color=0x3498db)
    for idx, (choice, bet, result, dice, win) in enumerate(rows, start=1):
        status_icon = "🟢 THẮNG" if win else "🔴 THUA"
        embed.add_field(
            name=f'Ván {idx}: {status_icon}',
            value=f'Đặt: `{choice.upper()}` ({format_money(bet)}) | Ra: `{result.upper()}` [{dice}]',
            inline=False
        )

    embed.set_footer(text=FOOTER_TEXT)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ====== CHẠY BOT ======
if __name__ == '__main__':
    if not TOKEN:
        print("❌ Lỗi: Chưa tìm thấy DISCORD_TOKEN trong file .env!")
    else:
        bot.run(TOKEN)