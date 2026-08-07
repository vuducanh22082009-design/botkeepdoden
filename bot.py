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

# ====== CẤU HÌNH ADMIN & BOT ======
ADMIN_ID = 1026417896114630676
FOOTER_TEXT = "code bot by ducanh | MinaBot"

# 1. Tạo Flask server để duy trì uptime trên Render/Replit
app = Flask('')

@app.route('/')
def home():
    return 'MinaBot is alive!'

def run_http():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_http, daemon=True).start()

# ====== CẤU HÌNH BIẾN MÔI TRƯỜNG ======
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ====== KHỞI TẠO BOT ======
intents = discord.Intents.default()
intents.message_content = True  # Cần thiết cho một số thao tác quản lý/tin nhắn
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ====== CƠ SỞ DỮ LIỆU ======
conn = sqlite3.connect('economy.db', check_same_thread=False)

def init_db():
    """Khởi tạo các bảng cơ sở dữ liệu."""
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                last_daily REAL DEFAULT 0
            )
        ''')
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

def get_user(user_id: int):
    cursor = conn.cursor()
    cursor.execute('SELECT balance, last_daily FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute('INSERT INTO users (user_id, balance, last_daily) VALUES (?, 0, 0)', (user_id,))
        conn.commit()
        return 0, 0.0
    return row

def set_balance(user_id: int, new_balance: int, last_daily: Optional[float] = None):
    cursor = conn.cursor()
    if last_daily is not None:
        cursor.execute('UPDATE users SET balance = ?, last_daily = ? WHERE user_id = ?',
                       (new_balance, last_daily, user_id))
    else:
        cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?',
                       (new_balance, user_id))
    conn.commit()

def parse_bet(balance: int, amount_str: str) -> Optional[int]:
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
        await tree.sync()
        print(f'✅ MinaBot ({bot.user}) đã sẵn sàng và đồng bộ lệnh thành công!')
    except Exception as e:
        print(f'❌ Lỗi đồng bộ lệnh: {e}')

# ====== LỆNH MENU ======
@tree.command(name='menu', description='Hiển thị danh sách lệnh đa năng của MinaBot')
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(title='🤖 MINABOT - MENU LỆNH ĐA LĨNH VỰC', color=0x9b59b6)
    
    embed.add_field(
        name='🎮 GAME & KINH TẾ',
        value=(
            '`/money daily` - Nhận thưởng hàng ngày\n'
            '`/money check` - Kiểm tra số dư\n'
            '`/money top` - Bảng xếp hạng đại gia\n'
            '`/money pay` - Chuyển tiền người chơi\n'
            '`/money pay_all` - Phát lì xì toàn server\n'
            '`/tx` - Cược Tài Xỉu\n'
            '`/cuop` - Cướp tiền với câu hỏi hại não (10% thắng)\n'
            '`/tx_history` - Lịch sử cược Tài Xỉu'
        ),
        inline=False
    )
    
    embed.add_field(
        name='👤 THÔNG TIN & GIẢI TRÍ',
        value=(
            '`/avatar [@user]` - Xem ảnh đại diện\n'
            '`/profile [@user]` - Xem thông tin người dùng\n'
            '`/memebot` - Spam tên vui nhộn\n'
            '`/donate` - Ủng hộ nhà phát triển'
        ),
        inline=False
    )

    if interaction.user.id == ADMIN_ID or interaction.user.guild_permissions.administrator:
        embed.add_field(
            name='👑 QUẢN TRỊ SERVER & ADMIN',
            value=(
                '`/delete <số_lượng>` - Xóa tin nhắn rác\n'
                '`/kick @user [lý_do]` - Kick thành viên\n'
                '`/admin pay` | `/admin take` | `/admin setbalance`\n'
                '`/reset money` - Reset số dư người chơi'
            ),
            inline=False
        )

    embed.set_footer(text=FOOTER_TEXT)
    await interaction.response.send_message(embed=embed)

# ====== NHÓM LỆNH THÔNG TIN & TIỆN ÍCH ======
@tree.command(name='avatar', description='Gửi ảnh đại diện (avatar) của người dùng')
@app_commands.describe(member='Chọn người dùng cần xem avatar (để trống nếu muốn xem của bản thân)')
async def avatar(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    target = member if member is not None else interaction.user
    embed = discord.Embed(title=f'🖼️ Ảnh đại diện của {target.display_name}', color=0x3498db)
    embed.set_image(url=target.display_avatar.url)
    embed.set_footer(text=FOOTER_TEXT)
    await interaction.response.send_message(embed=embed)

@tree.command(name='profile', description='Hiển thị thông tin hồ sơ của người dùng')
@app_commands.describe(member='Chọn người dùng cần xem thông tin')
async def profile(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    target = member if member is not None else interaction.user
    balance, _ = get_user(target.id)
    
    created_at = target.created_at.strftime('%d/%m/%Y %H:%M')
    joined_at = target.joined_at.strftime('%d/%m/%Y %H:%M') if target.joined_at else "Không rõ"

    embed = discord.Embed(title=f'👤 HỒ SƠ NGƯỜI DÙNG - {target.name}', color=0x1abc9c)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name='🏷️ Tên hiển thị', value=target.mention, inline=True)
    embed.add_field(name='🆔 Discord ID', value=f'`{target.id}`', inline=True)
    embed.add_field(name='💰 Tài sản MinaBot', value=f'**{format_money(balance)}**', inline=False)
    embed.add_field(name='📅 Ngày tạo tài khoản', value=created_at, inline=True)
    embed.add_field(name='📥 Ngày tham gia Server', value=joined_at, inline=True)
    embed.set_footer(text=FOOTER_TEXT)

    await interaction.response.send_message(embed=embed)

@tree.command(name='memebot', description='In tên của bạn 10 lần liên tiếp')
async def memebot(interaction: discord.Interaction):
    user_name = interaction.user.display_name
    lines = [f"kid {user_name}" for _ in range(10)]
    content = "\n".join(lines) + f"\n\n*{FOOTER_TEXT}*"
    await interaction.response.send_message(content)

# ====== QUẢN TRỊ SERVER (ADMIN) ======
@tree.command(name='delete', description='[ADMIN] Xóa số lượng tin nhắn trong kênh')
@app_commands.describe(amount='Số lượng tin nhắn muốn xóa (1 - 100)')
async def delete_chat(interaction: discord.Interaction, amount: int):
    if interaction.user.id != ADMIN_ID and not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(f'❌ Bạn không có quyền xóa tin nhắn.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    if amount < 1 or amount > 100:
        await interaction.response.send_message(f'Số lượng tin nhắn xóa phải từ 1 đến 100.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f'🧹 Đã xóa thành công **{len(deleted)}** tin nhắn!\n\n*{FOOTER_TEXT}*', ephemeral=True)

@tree.command(name='kick', description='[ADMIN] Kick người dùng khỏi Server')
@app_commands.describe(member='Người dùng muốn kick', reason='Lý do kick')
async def kick_user(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "Không có lý do"):
    if interaction.user.id != ADMIN_ID and not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message(f'❌ Bạn không có quyền kick thành viên.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(
            f'👞 Đã kick {member.mention} khỏi Server.\n**Lý do:** {reason}\n\n*{FOOTER_TEXT}*'
        )
    except Exception as e:
        await interaction.response.send_message(f'❌ Không thể kick người dùng này: {e}\n\n*{FOOTER_TEXT}*', ephemeral=True)

# ====== CHỨC NĂNG CƯỚP TIỀN (INTERACTIVE BUTTONS) ======
class RobView(discord.ui.View):
    def __init__(self, robber_id: int, victim: discord.Member):
        super().__init__(timeout=30)
        self.robber_id = robber_id
        self.victim = victim

    async def handle_rob(self, interaction: discord.Interaction):
        if interaction.user.id != self.robber_id:
            await interaction.response.send_message("Đây không phải lượt cướp của bạn!", ephemeral=True)
            return

        robber_bal, _ = get_user(self.robber_id)
        victim_bal, _ = get_user(self.victim.id)

        if victim_bal <= 0:
            await interaction.response.send_message(f"Nạn nhân {self.victim.mention} không có xu nào để cướp!", ephemeral=True)
            return

        # Disable tất cả nút bấm
        for item in self.children:
            item.disabled = True

        # Tỷ lệ 10% thành công
        success = (random.random() < 0.10)

        if success:
            stolen = max(1, int(victim_bal * random.uniform(0.1, 0.4)))  # Cướp 10%-40%
            set_balance(self.victim.id, victim_bal - stolen)
            set_balance(self.robber_id, robber_bal + stolen)
            
            embed = discord.Embed(title="🥷 CƯỚP THÀNH CÔNG!", color=0x2ecc71)
            embed.description = f"🎉 {interaction.user.mention} đã cướp thành công **{format_money(stolen)}** từ {self.victim.mention}!"
        else:
            penalty = 10000  # Phạt nhẹ khi cướp thất bại
            new_robber_bal = max(0, robber_bal - penalty)
            set_balance(self.robber_id, new_robber_bal)

            embed = discord.Embed(title="💥 CƯỚP THẤT BẠI!", color=0xe74c3c)
            embed.description = f"🚨 **ban la 1 thang gayyyy**\n\n{interaction.user.mention} cướp thất bại và bị phạt **{format_money(penalty)}**!"

        embed.set_footer(text=FOOTER_TEXT)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Tôi đồng tính", style=discord.ButtonStyle.primary)
    async def btn_dong_tinh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rob(interaction)

    @discord.ui.button(label="Tôi không đồng tính", style=discord.ButtonStyle.danger)
    async def btn_khong_dong_tinh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rob(interaction)

@tree.command(name='cuop', description='Cướp tiền người chơi khác (Tỷ lệ thắng 10%)')
@app_commands.describe(member='Nạn nhân muốn cướp tiền')
async def cuop(interaction: discord.Interaction, member: discord.Member):
    if member.id == interaction.user.id:
        await interaction.response.send_message(f'Bạn không thể tự cướp chính mình!\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    embed = discord.Embed(
        title="🕵️ THỬ THÁCH CƯỚP TIỀN",
        description=f"{interaction.user.mention} đang muốn cướp tiền của {member.mention}!\n\n**Ban co dong tinh khong?**",
        color=0xf39c12
    )
    embed.set_footer(text=FOOTER_TEXT)

    view = RobView(robber_id=interaction.user.id, victim=member)
    await interaction.response.send_message(embed=embed, view=view)

# ====== NHÓM LỆNH MONEY ======
money_group = app_commands.Group(name='money', description='Quản lý tiền MinaBot')

@money_group.command(name='daily', description='Nhận tiền thưởng hàng ngày (5 phút hồi)')
async def money_daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    balance, last_daily = get_user(user_id)
    now = time.time()
    cooldown = 300
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

    embed = discord.Embed(title='🏆 BẢNG XẾP HẠNG TÀI SẢN MINABOT', color=0xe67e22)
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
@app_commands.describe(amount='Số tiền muốn chuyển (VD: 50k, 1M)', member='Người nhận')
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

    set_balance(sender_id, sender_balance - parsed_amount)
    receiver_balance, _ = get_user(receiver_id)
    set_balance(receiver_id, receiver_balance + parsed_amount)

    await interaction.response.send_message(
        f'✅ Đã chuyển **{format_money(parsed_amount)}** cho {member.mention}.\n\n*{FOOTER_TEXT}*'
    )

@money_group.command(name='pay_all', description='Chia đều số tiền thưởng cho tất cả người chơi trong hệ thống')
@app_commands.describe(amount='Tổng số tiền phát lì xì (VD: 1M, 10M)')
async def money_pay_all(interaction: discord.Interaction, amount: str):
    sender_id = interaction.user.id
    sender_balance, _ = get_user(sender_id)
    parsed_amount = parse_bet(sender_balance, amount)

    if parsed_amount is None or parsed_amount <= 0 or sender_balance < parsed_amount:
        await interaction.response.send_message(f'Số tiền không hợp lệ hoặc số dư không đủ.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE user_id != ?', (sender_id,))
    users = cursor.fetchall()

    if not users:
        await interaction.response.send_message(f'Không có người chơi khác để phát lì xì.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    each_amount = parsed_amount // len(users)
    set_balance(sender_id, sender_balance - parsed_amount)

    for (uid,) in users:
        bal, _ = get_user(uid)
        set_balance(uid, bal + each_amount)

    await interaction.response.send_message(
        f'🎉 {interaction.user.mention} đã phát lì xì tổng cộng **{format_money(parsed_amount)}** '
        f'cho **{len(users)}** người chơi!\n\n*{FOOTER_TEXT}*'
    )

tree.add_command(money_group)

# ====== NHÓM LỆNH ADMIN ======
admin_group = app_commands.Group(name='admin', description='Quyền hạn Admin')

@admin_group.command(name='pay', description='[ADMIN] Cộng tiền cho bản thân hoặc người khác')
@app_commands.describe(amount='Số tiền cấp', member='Người nhận')
async def admin_pay(interaction: discord.Interaction, amount: str, member: Optional[discord.Member] = None):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(f'❌ Bạn không có quyền Admin.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    parsed_amount = parse_bet(1_000_000_000_000, amount)
    target_user = member if member is not None else interaction.user
    balance, _ = get_user(target_user.id)
    set_balance(target_user.id, balance + parsed_amount)

    await interaction.response.send_message(
        f'👑 **[ADMIN]** Đã cộng **{format_money(parsed_amount)}** cho {target_user.mention}.\n\n*{FOOTER_TEXT}*'
    )

@admin_group.command(name='take', description='[ADMIN] Trừ tiền người chơi')
@app_commands.describe(amount='Số tiền trừ', member='Người chơi bị trừ')
async def admin_take(interaction: discord.Interaction, amount: str, member: discord.Member):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(f'❌ Bạn không có quyền Admin.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    balance, _ = get_user(member.id)
    parsed_amount = parse_bet(balance, amount)
    new_balance = max(0, balance - parsed_amount)
    set_balance(member.id, new_balance)

    await interaction.response.send_message(
        f'👑 **[ADMIN]** Đã tịch thu **{format_money(parsed_amount)}** từ {member.mention}.\n\n*{FOOTER_TEXT}*'
    )

@admin_group.command(name='setbalance', description='[ADMIN] Đặt lại số dư người chơi')
async def admin_setbalance(interaction: discord.Interaction, amount: str, member: discord.Member):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(f'❌ Bạn không có quyền Admin.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    parsed_amount = parse_bet(1_000_000_000_000, amount)
    set_balance(member.id, parsed_amount)
    await interaction.response.send_message(
        f'👑 **[ADMIN]** Đã đặt số dư của {member.mention} thành **{format_money(parsed_amount)}**.\n\n*{FOOTER_TEXT}*'
    )

tree.add_command(admin_group)

# ====== RESET MONEY ======
reset_group = app_commands.Group(name='reset', description='Lệnh Reset dữ liệu')

@reset_group.command(name='money', description='[ADMIN] Reset số dư về 0')
async def reset_money(interaction: discord.Interaction, member: Optional[discord.Member] = None, reset_all: Optional[bool] = False):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(f'❌ Bạn không có quyền Admin.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    cursor = conn.cursor()
    if reset_all:
        cursor.execute('UPDATE users SET balance = 0')
        conn.commit()
        await interaction.response.send_message(f'⚠️ **[ADMIN]** Đã reset số dư của **TẤT CẢ** người chơi về **0 VNĐ**!\n\n*{FOOTER_TEXT}*')
    elif member is not None:
        set_balance(member.id, 0)
        await interaction.response.send_message(f'🧹 **[ADMIN]** Đã reset số dư của {member.mention} về **0 VNĐ**.\n\n*{FOOTER_TEXT}*')

tree.add_command(reset_group)

# ====== LỆNH TÀI XỈU & DONATE ======
@tree.command(name='donate', description='Ủng hộ nhà phát triển MinaBot')
async def donate(interaction: discord.Interaction):
    embed = discord.Embed(
        title='☕ ỦNG HỘ MINABOT / DONATE',
        description='Cảm ơn bạn đã đồng hành cùng MinaBot!\n\n'
                    '🏦 **Ngân hàng:** MB Bank\n'
                    '💳 **STK:** 0915779767\n\n'
                    '*"cam on vi da den"*',
        color=0x3498db
    )
    embed.set_footer(text=FOOTER_TEXT)
    await interaction.response.send_message(embed=embed)

@tree.command(name='tx', description='Cược Tài Xỉu')
@app_commands.describe(choice='Chọn "tài" hoặc "xỉu"', amount='Số tiền cược (VD: 10k, 1M, all)')
async def tx(interaction: discord.Interaction, choice: str, amount: str):
    choice = choice.strip().lower()
    if choice not in ('tài', 'xỉu'):
        await interaction.response.send_message(f'Lựa chọn phải là `tài` hoặc `xỉu`.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    user_id = interaction.user.id
    balance, _ = get_user(user_id)
    bet = parse_bet(balance, amount)

    if bet is None or bet <= 0 or bet > balance:
        await interaction.response.send_message(f'Số tiền cược không hợp lệ hoặc không đủ số dư.\n\n*{FOOTER_TEXT}*', ephemeral=True)
        return

    dice = [random.randint(1, 6) for _ in range(3)]
    total = sum(dice)
    result = 'tài' if 11 <= total <= 18 else 'xỉu'
    win = (choice == result)
    dice_str = ', '.join(map(str, dice))

    new_balance = balance + bet if win else balance - bet
    set_balance(user_id, new_balance)

    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO tx_history (user_id, choice, bet, result, dice, win, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (user_id, choice, bet, result, dice_str, 1 if win else 0, time.time())
    )
    conn.commit()

    embed = discord.Embed(title='🎲 KẾT QUẢ TÀI XỈU - MINABOT', color=0x2ecc71 if win else 0xe74c3c)
    embed.add_field(name='👤 Người chơi', value=interaction.user.name, inline=True)
    embed.add_field(name='💰 Cược', value=f'{choice.upper()} - {format_money(bet)}', inline=False)
    embed.add_field(name='🎲 Xúc xắc', value=f'[{dice_str}] (Tổng {total}) → **{result.upper()}**', inline=False)
    embed.add_field(name='📢 Kết quả', value=f'{"THẮNG +" if win else "THUA -"}{format_money(bet)}', inline=False)
    embed.add_field(name='💳 Số dư mới', value=format_money(new_balance), inline=False)
    embed.set_footer(text=FOOTER_TEXT)

    await interaction.response.send_message(embed=embed)

@tree.command(name='tx_history', description='Xem lịch sử ván cược Tài Xỉu')
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

    embed = discord.Embed(title=f'📜 LỊCH SỬ CƯỢC - {interaction.user.name}', color=0x3498db)
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