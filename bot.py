import discord
from discord import app_commands
import random
import time
import sqlite3
import os
from typing import Optional
from dotenv import load_dotenv

# ====== CẤU HÌNH BIẾN MÔI TRƯỜNG ======
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ====== KHỞI TẠO BOT ======
intents = discord.Intents.default()
intents.message_content = False  # Slash commands không cần đọc tin nhắn
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ====== CƠ SỞ DỮ LIỆU ======
# check_same_thread=False để tương thích tốt với các hàm async trong discord.py
conn = sqlite3.connect('economy.db', check_same_thread=False)

def init_db():
    """Khởi tạo bảng cơ sở dữ liệu."""
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                last_daily REAL DEFAULT 0
            )
        ''')

init_db()

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
    """Chuyển đổi chuỗi cược thành số tiền thực tế."""
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
    try:
        amount = int(amount_str)
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

# ====== LỆNH MENU ======
@tree.command(name='menu', description='Hiển thị danh sách lệnh của bot')
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(title='📋 MENU BOT TÀI XỈU', color=0xf1c40f)
    embed.add_field(name='/money daily', value='Nhận tiền ngẫu nhiên từ 1k đến 1M (hồi 5 phút)', inline=False)
    embed.add_field(name='/money check', value='Kiểm tra số dư hiện tại', inline=False)
    embed.add_field(name='/money top', value='Bảng xếp hạng người giàu nhất', inline=False)
    embed.add_field(name='/money pay <số_tiền> @người_chơi', value='Chuyển tiền cho người khác', inline=False)
    embed.add_field(name='/tx <tài/xỉu> <số_tiền>', value='Cược tài/xỉu (số tiền, all, 50%, 70%)', inline=False)
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
            f'⏳ Bạn cần chờ thêm **{mins} phút {secs} giây** để dùng lại lệnh này.',
            ephemeral=True
        )
        return

    reward = random.randint(1000, 1000000)
    new_balance = balance + reward
    set_balance(user_id, new_balance, now)
    await interaction.response.send_message(
        f'🎁 Bạn nhận được **{reward:,}** VNĐ! Số dư hiện tại: **{new_balance:,}** VNĐ.'
    )

@money_group.command(name='check', description='Kiểm tra số dư của bạn')
async def money_check(interaction: discord.Interaction):
    balance, _ = get_user(interaction.user.id)
    await interaction.response.send_message(f'💰 Số dư của bạn: **{balance:,}** VNĐ.')

@money_group.command(name='top', description='Bảng xếp hạng người giàu nhất')
async def money_top(interaction: discord.Interaction):
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10')
    rows = cursor.fetchall()
    if not rows:
        await interaction.response.send_message('Chưa có dữ liệu người chơi.')
        return

    embed = discord.Embed(title='🏆 BẢNG XẾP HẠNG TÀI SẢN', color=0xe67e22)
    for idx, (uid, bal) in enumerate(rows, start=1):
        try:
            user = await bot.fetch_user(uid)
            name = user.name
        except Exception:
            name = f'ID: {uid}'
        embed.add_field(name=f'{idx}. {name}', value=f'{bal:,} VNĐ', inline=False)
    await interaction.response.send_message(embed=embed)

@money_group.command(name='pay', description='Chuyển tiền cho người chơi khác')
@app_commands.describe(amount='Số tiền muốn chuyển', member='Người nhận')
async def money_pay(interaction: discord.Interaction, amount: int, member: discord.Member):
    if amount <= 0:
        await interaction.response.send_message('Số tiền phải lớn hơn 0.', ephemeral=True)
        return
    sender_id = interaction.user.id
    receiver_id = member.id
    if sender_id == receiver_id:
        await interaction.response.send_message('Không thể tự chuyển tiền cho chính mình.', ephemeral=True)
        return

    sender_balance, _ = get_user(sender_id)
    if sender_balance < amount:
        await interaction.response.send_message('Bạn không đủ tiền để chuyển.', ephemeral=True)
        return

    # Trừ tiền người gửi
    new_sender_balance = sender_balance - amount
    set_balance(sender_id, new_sender_balance)

    # Cộng tiền người nhận
    receiver_balance, _ = get_user(receiver_id)
    new_receiver_balance = receiver_balance + amount
    set_balance(receiver_id, new_receiver_balance)

    await interaction.response.send_message(
        f'✅ Đã chuyển **{amount:,}** VNĐ cho {member.mention}. '
        f'Số dư của bạn còn **{new_sender_balance:,}** VNĐ.'
    )

tree.add_command(money_group)  # Đăng ký nhóm lệnh /money

# ====== LỆNH TÀI XỈU ======
@tree.command(name='tx', description='Cược Tài hoặc Xỉu với số tiền tùy chọn')
@app_commands.describe(
    choice='Chọn "tài" hoặc "xỉu"',
    amount='Số tiền cược (số, all, 50%, 70%)'
)
async def tx(interaction: discord.Interaction, choice: str, amount: str):
    choice = choice.strip().lower()
    if choice not in ('tài', 'xỉu'):
        await interaction.response.send_message('Lựa chọn phải là `tài` hoặc `xỉu`.', ephemeral=True)
        return

    user_id = interaction.user.id
    balance, _ = get_user(user_id)
    bet = parse_bet(balance, amount)
    if bet is None or bet <= 0:
        await interaction.response.send_message('Số tiền cược không hợp lệ.', ephemeral=True)
        return
    if bet > balance:
        await interaction.response.send_message('Bạn không đủ số dư để cược.', ephemeral=True)
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
        change_text = f'+{profit:,} VNĐ'
    else:
        new_balance = balance - bet
        profit = -bet
        status = 'THUA'
        change_text = f'{profit:,} VNĐ'

    set_balance(user_id, new_balance)

    embed = discord.Embed(title='🎲 KẾT QUẢ TÀI XỈU', color=0x2ecc71 if win else 0xe74c3c)
    embed.add_field(name='👤 Người chơi', value=interaction.user.name, inline=True)
    embed.add_field(name='🆔 ID Discord', value=str(user_id), inline=True)
    embed.add_field(name='💰 Số tiền cược', value=f'{bet:,} VNĐ', inline=False)
    embed.add_field(name='🎲 Xúc xắc', value=f'{dice_str} (tổng {total}) → {result.upper()}', inline=False)
    embed.add_field(name=f'📢 {status}', value=change_text, inline=False)
    embed.set_footer(text=f'Số dư mới: {new_balance:,} VNĐ')

    await interaction.response.send_message(embed=embed)

# ====== CHẠY BOT ======
if __name__ == '__main__':
    if not TOKEN:
        print("❌ Lỗi: Chưa tìm thấy DISCORD_TOKEN trong file .env!")
    else:
        bot.run(TOKEN)