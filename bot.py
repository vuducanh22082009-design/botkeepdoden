import threading
import asyncio
import discord
from discord import app_commands
import random
import time
import sqlite3
import os
import json
import urllib.request
from typing import Optional
from dotenv import load_dotenv
from flask import Flask


# =========================================================
# CẤU HÌNH ADMIN & BOT
# =========================================================

ADMIN_ID = 1026417896114630676
FOOTER_TEXT = "code bot by ducanh | MinaBot"

NEON_COLORS = [
    0xff00cc,
    0x00e5ff,
    0x7d2cff,
    0x39ff14,
    0xff1493,
]

RANKS = [
    ("Đồng", "🥉", 0, "Huy hiệu Đồng và giao diện neon cơ bản"),
    ("Bạc", "🥈", 100, "Được mở khóa lệnh bói vui và khung hồ sơ Bạc"),
    ("Vàng", "🥇", 500, "Được dùng danh hiệu Vàng trong các lệnh tương tác"),
    ("Kim Cương", "💎", 1500, "Huy hiệu Kim Cương và hiệu ứng neon đặc biệt"),
    ("Cao Thủ", "👑", 5000, "Huy hiệu Cao Thủ và danh hiệu tối thượng"),
]

SHOP_ITEMS = {
    "bua_x2_15p": {
        "name": "Bùa May Mắn x2 · 15 phút",
        "price": 50_000_000,
        "duration": 15 * 60,
        "multiplier": 2,
        "description": "Nhân đôi tỷ lệ thắng trong Tài Xỉu và Cướp tiền.",
    },
    "bua_x2_1h": {
        "name": "Bùa May Mắn x2 · 1 giờ",
        "price": 200_000_000,
        "duration": 60 * 60,
        "multiplier": 2,
        "description": "Nhân đôi tỷ lệ thắng trong Tài Xỉu và Cướp tiền.",
    },
    "bua_x3_30p": {
        "name": "Bùa May Mắn x3 · 30 phút",
        "price": 500_000_000,
        "duration": 30 * 60,
        "multiplier": 3,
        "description": "Nhân ba tỷ lệ thắng trong Tài Xỉu và Cướp tiền.",
    },
}

MEME_API_URL = "https://api.imgflip.com/get_memes"
MEME_CACHE = {"expires": 0.0, "memes": []}
MEME_CACHE_TTL = 3600
FAMOUS_MEME_KEYWORDS = (
    "Drake Hotline Bling",
    "Distracted Boyfriend",
    "Two Buttons",
    "One Does Not Simply",
    "Disaster Girl",
    "Change My Mind",
    "Expanding Brain",
    "Mocking SpongeBob",
    "Always Has Been",
    "This Is Fine",
    "Hide the Pain Harold",
)


# =========================================================
# FLASK SERVER CHO RENDER
# =========================================================

app = Flask('')


@app.route('/')
def home():
    return 'MinaBot is alive!'


def run_http():
    port = int(os.environ.get('PORT', 10000))
    app.run(
        host='0.0.0.0',
        port=port,
        use_reloader=False
    )


threading.Thread(target=run_http, daemon=True).start()


# =========================================================
# CẤU HÌNH BIẾN MÔI TRƯỜNG
# =========================================================

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')


# =========================================================
# KHỞI TẠO BOT
# =========================================================

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
guild_commands_synced = False


# =========================================================
# CƠ SỞ DỮ LIỆU
# =========================================================

conn = sqlite3.connect(
    'economy.db',
    check_same_thread=False
)


def neon_color():
    """Đổi màu neon theo thời gian để mỗi embed có cảm giác chuyển màu."""
    return NEON_COLORS[int(time.time() / 2) % len(NEON_COLORS)]


def neon_embed(title: str, description: str = "", **kwargs):
    """Tạo embed giao diện neon dùng chung cho các tính năng giải trí."""
    embed = discord.Embed(
        title=f"✨ {title} ✨",
        description=description,
        color=neon_color(),
        **kwargs
    )
    embed.set_footer(text=f"🌈 {FOOTER_TEXT} • neon mode")
    return embed


def style_embed(embed: discord.Embed):
    """Áp dụng màu neon chuyển đổi cho cả embed cũ và embed mới."""
    embed.color = neon_color()
    embed.set_footer(text=f"🌈 {FOOTER_TEXT} • neon mode")
    return embed


def rank_for_xp(xp: int):
    current = RANKS[0]
    for rank in RANKS:
        if xp >= rank[2]:
            current = rank
    return current


def next_rank_for_xp(xp: int):
    for rank in RANKS:
        if xp < rank[2]:
            return rank
    return None


def _fetch_meme_templates():
    request = urllib.request.Request(
        MEME_API_URL,
        headers={"User-Agent": "MinaBot/1.0 meme-command"}
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("success"):
        raise RuntimeError("Imgflip không trả về dữ liệu meme")
    return payload["data"]["memes"]


async def get_random_meme():
    now = time.time()
    if now >= MEME_CACHE["expires"] or not MEME_CACHE["memes"]:
        try:
            MEME_CACHE["memes"] = await asyncio.to_thread(_fetch_meme_templates)
            MEME_CACHE["expires"] = now + MEME_CACHE_TTL
        except Exception:
            return None
    famous = [
        meme for meme in MEME_CACHE["memes"]
        if any(keyword.lower() in meme.get("name", "").lower() for keyword in FAMOUS_MEME_KEYWORDS)
    ]
    return random.choice(famous or MEME_CACHE["memes"])


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

        conn.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER NOT NULL,
                item_key TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                expires_at REAL DEFAULT 0,
                PRIMARY KEY (user_id, item_key)
            )
        ''')

        columns = {
            row[1]
            for row in conn.execute('PRAGMA table_info(users)').fetchall()
        }
        if 'xp' not in columns:
            conn.execute('ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0')
        if 'last_xp' not in columns:
            conn.execute('ALTER TABLE users ADD COLUMN last_xp REAL DEFAULT 0')


init_db()


# =========================================================
# HÀM TIỆN ÍCH ĐỊNH DẠNG TIỀN
# =========================================================

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

    cursor.execute(
        'SELECT balance, last_daily FROM users WHERE user_id = ?',
        (user_id,)
    )

    row = cursor.fetchone()

    if row is None:
        cursor.execute(
            'INSERT INTO users (user_id, balance, last_daily) VALUES (?, 0, 0)',
            (user_id,)
        )

        conn.commit()

        return 0, 0.0

    return row


def set_balance(
    user_id: int,
    new_balance: int,
    last_daily: Optional[float] = None
):
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO users (user_id, balance, last_daily) VALUES (?, 0, 0)',
        (user_id,)
    )

    if last_daily is not None:
        cursor.execute(
            '''
            UPDATE users
            SET balance = ?, last_daily = ?
            WHERE user_id = ?
            ''',
            (new_balance, last_daily, user_id)
        )

    else:
        cursor.execute(
            '''
            UPDATE users
            SET balance = ?
            WHERE user_id = ?
            ''',
            (new_balance, user_id)
        )

    conn.commit()


def get_xp(user_id: int):
    cursor = conn.cursor()
    cursor.execute(
        'SELECT xp, last_xp FROM users WHERE user_id = ?',
        (user_id,)
    )
    row = cursor.fetchone()
    if row is None:
        get_user(user_id)
        return 0, 0.0
    return row


def add_xp(user_id: int, amount: int = 5):
    xp, _ = get_xp(user_id)
    new_xp = xp + amount
    conn.execute(
        'UPDATE users SET xp = ?, last_xp = ? WHERE user_id = ?',
        (new_xp, time.time(), user_id)
    )
    conn.commit()
    return new_xp


def get_luck_multiplier(user_id: int):
    now = time.time()
    rows = conn.execute(
        '''
        SELECT item_key, quantity, expires_at
        FROM inventory
        WHERE user_id = ? AND quantity > 0 AND expires_at > ?
        ''',
        (user_id, now)
    ).fetchall()
    if not rows:
        return 1, 0
    valid_rows = [row for row in rows if row[0] in SHOP_ITEMS]
    if not valid_rows:
        return 1, 0
    best_item = max(valid_rows, key=lambda row: SHOP_ITEMS[row[0]]['multiplier'])
    return SHOP_ITEMS[best_item[0]]['multiplier'], best_item[2]


def add_shop_item(user_id: int, item_key: str):
    item = SHOP_ITEMS[item_key]
    now = time.time()
    current = conn.execute(
        'SELECT quantity, expires_at FROM inventory WHERE user_id = ? AND item_key = ?',
        (user_id, item_key)
    ).fetchone()
    start_at = max(now, current[1]) if current else now
    expires_at = start_at + item['duration']
    quantity = current[0] + 1 if current and current[1] > now else 1
    conn.execute(
        '''
        INSERT INTO inventory (user_id, item_key, quantity, expires_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, item_key) DO UPDATE SET
            quantity = excluded.quantity,
            expires_at = excluded.expires_at
        ''',
        (user_id, item_key, quantity, expires_at)
    )
    conn.commit()
    return expires_at


def purchase_shop_item(user_id: int, item_key: str):
    """Trừ tiền và thêm vật phẩm trong cùng một transaction SQLite."""
    item = SHOP_ITEMS[item_key]
    now = time.time()
    with conn:
        row = conn.execute(
            'SELECT balance FROM users WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        if row is None or row[0] < item['price']:
            return None

        current = conn.execute(
            'SELECT quantity, expires_at FROM inventory WHERE user_id = ? AND item_key = ?',
            (user_id, item_key)
        ).fetchone()
        start_at = max(now, current[1]) if current else now
        expires_at = start_at + item['duration']
        quantity = current[0] + 1 if current and current[1] > now else 1

        conn.execute(
            'UPDATE users SET balance = balance - ? WHERE user_id = ?',
            (item['price'], user_id)
        )
        conn.execute(
            '''
            INSERT INTO inventory (user_id, item_key, quantity, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, item_key) DO UPDATE SET
                quantity = excluded.quantity,
                expires_at = excluded.expires_at
            ''',
            (user_id, item_key, quantity, expires_at)
        )
    return expires_at, row[0] - item['price']


def parse_bet(
    balance: int,
    amount_str: str
) -> Optional[int]:

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


# =========================================================
# SỰ KIỆN BOT
# =========================================================

@bot.event
async def setup_hook():
    """
    Đồng bộ slash commands một lần khi bot khởi động.
    Không sync trong on_ready để tránh sync lặp khi reconnect.
    """

    try:
        await tree.sync()
        print('✅ Slash commands đã được đồng bộ thành công!')

    except Exception as e:
        print(f'❌ Lỗi đồng bộ lệnh: {e}')


@bot.event
async def on_ready():
    global guild_commands_synced
    print(f'✅ MinaBot ({bot.user}) đã sẵn sàng!')

    if not guild_commands_synced:
        all_guilds_synced = True
        for guild in bot.guilds:
            try:
                tree.copy_global_to(guild=guild)
                synced = await tree.sync(guild=guild)
                print(f'✅ Đã đồng bộ {len(synced)} lệnh cho server: {guild.name}')
            except Exception as e:
                all_guilds_synced = False
                print(f'❌ Không đồng bộ được lệnh cho {guild.name}: {e}')
        guild_commands_synced = bool(bot.guilds) and all_guilds_synced


@bot.event
async def on_message(message: discord.Message):
    """Cộng XP tối đa một lần mỗi phút để khuyến khích trò chuyện, chống spam."""
    if message.author.bot or message.guild is None:
        return

    _, last_xp = get_xp(message.author.id)
    if time.time() - last_xp >= 60:
        add_xp(message.author.id, random.randint(5, 12))


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Không để lệnh lỗi im lặng; báo lỗi thân thiện và ghi log để sửa nhanh."""
    print(f'❌ Lỗi slash command: {type(error).__name__}: {error}')
    message = 'Lệnh chưa chạy được. Hãy thử lại sau giây lát nhé!'
    if isinstance(error, app_commands.CommandInvokeError):
        message = 'Lệnh gặp lỗi khi xử lý. Mình đã ghi log để kiểm tra.'
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


# =========================================================
# LỆNH MENU
# =========================================================

@tree.command(
    name='menu',
    description='Hiển thị danh sách lệnh đa năng của MinaBot'
)
async def menu(interaction: discord.Interaction):

    embed = discord.Embed(
        title='🤖 MINABOT - MENU LỆNH ĐA LĨNH VỰC',
        color=0x9b59b6
    )

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
            '`/shop` | `/shop_buy` | `/inventory` - Shop và vật phẩm\n'
            '`/tx_history` - Lịch sử cược Tài Xỉu\n'
            '`/rank` | `/rank_top` - XP và bảng rank'
        ),
        inline=False
    )

    embed.add_field(
        name='👤 THÔNG TIN & GIẢI TRÍ',
        value=(
            '`/avatar [@user]` - Xem ảnh đại diện\n'
            '`/profile [@user]` - Xem thông tin người dùng\n'
            '`/memebot` - Spam tên vui nhộn\n'
            '`/donate` - Ủng hộ nhà phát triển\n'
            '`/ship` | `/roast` | `/hug` | `/rps` - Tương tác vui\n'
            '`/meme` | `/joke` | `/quote` | `/fact` - Nội dung giải trí\n'
            '`/cat` | `/dog` - Ảnh động vật ngẫu nhiên\n'
            '`/fortune` - Bói vui từ rank Bạc'
        ),
        inline=False
    )

    if (
        interaction.user.id == ADMIN_ID
        or interaction.user.guild_permissions.administrator
    ):
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

    await interaction.response.send_message(embed=style_embed(embed))


# =========================================================
# NHÓM LỆNH THÔNG TIN & TIỆN ÍCH
# =========================================================

@tree.command(
    name='avatar',
    description='Gửi ảnh đại diện (avatar) của người dùng'
)
@app_commands.describe(
    member='Chọn người dùng cần xem avatar (để trống nếu muốn xem của bản thân)'
)
async def avatar(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):

    target = member if member is not None else interaction.user

    embed = discord.Embed(
        title=f'🖼️ Ảnh đại diện của {target.display_name}',
        color=0x3498db
    )

    embed.set_image(url=target.display_avatar.url)
    embed.set_footer(text=FOOTER_TEXT)

    await interaction.response.send_message(embed=style_embed(embed))


@tree.command(
    name='profile',
    description='Hiển thị thông tin hồ sơ của người dùng'
)
@app_commands.describe(
    member='Chọn người dùng cần xem thông tin'
)
async def profile(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None
):

    target = member if member is not None else interaction.user

    balance, _ = get_user(target.id)

    created_at = target.created_at.strftime('%d/%m/%Y %H:%M')

    joined_at = (
        target.joined_at.strftime('%d/%m/%Y %H:%M')
        if target.joined_at
        else "Không rõ"
    )

    embed = discord.Embed(
        title=f'👤 HỒ SƠ NGƯỜI DÙNG - {target.name}',
        color=0x1abc9c
    )

    embed.set_thumbnail(url=target.display_avatar.url)

    embed.add_field(
        name='🏷️ Tên hiển thị',
        value=target.mention,
        inline=True
    )

    embed.add_field(
        name='🆔 Discord ID',
        value=f'`{target.id}`',
        inline=True
    )

    embed.add_field(
        name='💰 Tài sản MinaBot',
        value=f'**{format_money(balance)}**',
        inline=False
    )

    embed.add_field(
        name='📅 Ngày tạo tài khoản',
        value=created_at,
        inline=True
    )

    embed.add_field(
        name='📥 Ngày tham gia Server',
        value=joined_at,
        inline=True
    )

    embed.set_footer(text=FOOTER_TEXT)

    await interaction.response.send_message(embed=style_embed(embed))


@tree.command(
    name='memebot',
    description='In tên của bạn 10 lần liên tiếp'
)
async def memebot(interaction: discord.Interaction):

    user_name = interaction.user.display_name

    lines = [
        f"kid {user_name}"
        for _ in range(10)
    ]

    content = (
        "\n".join(lines)
        + f"\n\n*{FOOTER_TEXT}*"
    )

    await interaction.response.send_message(content)


# =========================================================
# QUẢN TRỊ SERVER
# =========================================================

@tree.command(
    name='delete',
    description='[ADMIN] Xóa số lượng tin nhắn trong kênh'
)
@app_commands.describe(
    amount='Số lượng tin nhắn muốn xóa (1 - 100)'
)
async def delete_chat(
    interaction: discord.Interaction,
    amount: int
):

    if (
        interaction.user.id != ADMIN_ID
        and not interaction.user.guild_permissions.manage_messages
    ):
        await interaction.response.send_message(
            f'❌ Bạn không có quyền xóa tin nhắn.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    if amount < 1 or amount > 100:
        await interaction.response.send_message(
            f'Số lượng tin nhắn xóa phải từ 1 đến 100.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    deleted = await interaction.channel.purge(limit=amount)

    await interaction.followup.send(
        f'🧹 Đã xóa thành công **{len(deleted)}** tin nhắn!\n\n*{FOOTER_TEXT}*',
        ephemeral=True
    )


@tree.command(
    name='kick',
    description='[ADMIN] Kick người dùng khỏi Server'
)
@app_commands.describe(
    member='Người dùng muốn kick',
    reason='Lý do kick'
)
async def kick_user(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: Optional[str] = "Không có lý do"
):

    if (
        interaction.user.id != ADMIN_ID
        and not interaction.user.guild_permissions.kick_members
    ):
        await interaction.response.send_message(
            f'❌ Bạn không có quyền kick thành viên.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    try:
        await member.kick(reason=reason)

        await interaction.response.send_message(
            f'👞 Đã kick {member.mention} khỏi Server.\n'
            f'**Lý do:** {reason}\n\n'
            f'*{FOOTER_TEXT}*'
        )

    except Exception as e:
        await interaction.response.send_message(
            f'❌ Không thể kick người dùng này: {e}\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )


# =========================================================
# CHỨC NĂNG CƯỚP TIỀN
# =========================================================

class RobView(discord.ui.View):

    def __init__(
        self,
        robber_id: int,
        victim: discord.Member
    ):
        super().__init__(timeout=30)

        self.robber_id = robber_id
        self.victim = victim

    async def handle_rob(
        self,
        interaction: discord.Interaction
    ):

        if interaction.user.id != self.robber_id:
            await interaction.response.send_message(
                "Đây không phải lượt cướp của bạn!",
                ephemeral=True
            )
            return

        robber_bal, _ = get_user(self.robber_id)
        victim_bal, _ = get_user(self.victim.id)

        if victim_bal <= 0:
            await interaction.response.send_message(
                f"Nạn nhân {self.victim.mention} không có xu nào để cướp!",
                ephemeral=True
            )
            return

        # Disable tất cả nút bấm
        for item in self.children:
            item.disabled = True

        # Tỷ lệ cơ bản 10%, bùa x2/x3 nhân tỷ lệ và không vượt quá 100%.
        luck_multiplier, _ = get_luck_multiplier(self.robber_id)
        success = random.random() < min(1.0, 0.10 * luck_multiplier)

        if success:

            stolen = max(
                1,
                int(victim_bal * random.uniform(0.1, 0.4))
            )

            set_balance(
                self.victim.id,
                victim_bal - stolen
            )

            set_balance(
                self.robber_id,
                robber_bal + stolen
            )

            embed = discord.Embed(
                title="🥷 CƯỚP THÀNH CÔNG!",
                color=0x2ecc71
            )

            embed.description = (
                f"🎉 {interaction.user.mention} đã cướp thành công "
                f"**{format_money(stolen)}** từ "
                f"{self.victim.mention}!\n\n"
                f"🍀 Bùa may mắn: **x{luck_multiplier}**"
            )

        else:

            # Cướp thất bại sẽ mất toàn bộ số dư hiện có.
            set_balance(
                self.robber_id,
                0
            )

            embed = discord.Embed(
                title="💥 CƯỚP THẤT BẠI!",
                color=0xe74c3c
            )

            embed.description = (
                f"🚨 **ban la 1 thang gayyyy**\n\n"
                f"{interaction.user.mention} cướp thất bại "
                f"và mất toàn bộ số tiền đang có!"
            )

        embed.set_footer(text=FOOTER_TEXT)

        await interaction.response.edit_message(
            embed=style_embed(embed),
            view=self
        )

    @discord.ui.button(
        label="Tôi đồng tính",
        style=discord.ButtonStyle.primary
    )
    async def btn_dong_tinh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.handle_rob(interaction)

    @discord.ui.button(
        label="Tôi không đồng tính",
        style=discord.ButtonStyle.danger
    )
    async def btn_khong_dong_tinh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.handle_rob(interaction)


@tree.command(
    name='cuop',
    description='Cướp tiền người chơi khác (Tỷ lệ thắng 10%)'
)
@app_commands.describe(
    member='Nạn nhân muốn cướp tiền'
)
async def cuop(
    interaction: discord.Interaction,
    member: discord.Member
):

    if member.id == interaction.user.id:
        await interaction.response.send_message(
            f'Bạn không thể tự cướp chính mình!\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🕵️ THỬ THÁCH CƯỚP TIỀN",
        description=(
            f"{interaction.user.mention} đang muốn cướp tiền "
            f"của {member.mention}!\n\n"
            f"**Ban co dong tinh khong?**"
        ),
        color=0xf39c12
    )

    embed.set_footer(text=FOOTER_TEXT)

    view = RobView(
        robber_id=interaction.user.id,
        victim=member
    )

    await interaction.response.send_message(
        embed=style_embed(embed),
        view=view
    )


# =========================================================
# NHÓM LỆNH MONEY
# =========================================================

money_group = app_commands.Group(
    name='money',
    description='Quản lý tiền MinaBot'
)


@money_group.command(
    name='daily',
    description='Nhận tiền thưởng hàng ngày (5 phút hồi)'
)
async def money_daily(
    interaction: discord.Interaction
):

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
            f'⏳ Bạn cần chờ thêm **{mins} phút {secs} giây** '
            f'để dùng lại lệnh này.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )

        return

    reward = random.randint(
        1000,
        1000000
    )

    new_balance = balance + reward

    set_balance(
        user_id,
        new_balance,
        now
    )

    await interaction.response.send_message(
        f'🎁 Bạn nhận được **{format_money(reward)}**! '
        f'Số dư hiện tại: **{format_money(new_balance)}**.\n\n'
        f'*{FOOTER_TEXT}*'
    )


@money_group.command(
    name='check',
    description='Kiểm tra số dư của bạn'
)
async def money_check(
    interaction: discord.Interaction
):

    balance, _ = get_user(
        interaction.user.id
    )

    await interaction.response.send_message(
        f'💰 Số dư của bạn: **{format_money(balance)}**.\n\n'
        f'*{FOOTER_TEXT}*'
    )


@money_group.command(
    name='top',
    description='Bảng xếp hạng người giàu nhất'
)
async def money_top(
    interaction: discord.Interaction
):

    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT user_id, balance
        FROM users
        ORDER BY balance DESC
        LIMIT 10
        '''
    )

    rows = cursor.fetchall()

    if not rows:
        await interaction.response.send_message(
            f'Chưa có dữ liệu người chơi.\n\n*{FOOTER_TEXT}*'
        )
        return

    embed = discord.Embed(
        title='🏆 BẢNG XẾP HẠNG TÀI SẢN MINABOT',
        color=0xe67e22
    )

    for idx, (uid, bal) in enumerate(
        rows,
        start=1
    ):

        try:
            user = await bot.fetch_user(uid)
            name = user.name

        except Exception:
            name = f'ID: {uid}'

        embed.add_field(
            name=f'{idx}. {name}',
            value=format_money(bal),
            inline=False
        )

    embed.set_footer(text=FOOTER_TEXT)

    await interaction.response.send_message(
        embed=style_embed(embed)
    )


@money_group.command(
    name='pay',
    description='Chuyển tiền cho người chơi khác'
)
@app_commands.describe(
    amount='Số tiền muốn chuyển (VD: 50k, 1M)',
    member='Người nhận'
)
async def money_pay(
    interaction: discord.Interaction,
    amount: str,
    member: discord.Member
):

    sender_id = interaction.user.id
    receiver_id = member.id

    if sender_id == receiver_id:
        await interaction.response.send_message(
            f'Không thể tự chuyển tiền cho chính mình.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    sender_balance, _ = get_user(sender_id)

    parsed_amount = parse_bet(
        sender_balance,
        amount
    )

    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message(
            f'Số tiền chuyển không hợp lệ.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    if sender_balance < parsed_amount:
        await interaction.response.send_message(
            f'Bạn không đủ tiền để chuyển.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    set_balance(
        sender_id,
        sender_balance - parsed_amount
    )

    receiver_balance, _ = get_user(
        receiver_id
    )

    set_balance(
        receiver_id,
        receiver_balance + parsed_amount
    )

    await interaction.response.send_message(
        f'✅ Đã chuyển **{format_money(parsed_amount)}** '
        f'cho {member.mention}.\n\n'
        f'*{FOOTER_TEXT}*'
    )


@money_group.command(
    name='pay_all',
    description='Chia đều số tiền thưởng cho tất cả người chơi trong hệ thống'
)
@app_commands.describe(
    amount='Tổng số tiền phát lì xì (VD: 1M, 10M)'
)
async def money_pay_all(
    interaction: discord.Interaction,
    amount: str
):

    sender_id = interaction.user.id

    sender_balance, _ = get_user(sender_id)

    parsed_amount = parse_bet(
        sender_balance,
        amount
    )

    if (
        parsed_amount is None
        or parsed_amount <= 0
        or sender_balance < parsed_amount
    ):
        await interaction.response.send_message(
            f'Số tiền không hợp lệ hoặc số dư không đủ.\n\n'
            f'*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    cursor = conn.cursor()

    cursor.execute(
        'SELECT user_id FROM users WHERE user_id != ?',
        (sender_id,)
    )

    users = cursor.fetchall()

    if not users:
        await interaction.response.send_message(
            f'Không có người chơi khác để phát lì xì.\n\n'
            f'*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    each_amount, remainder = divmod(parsed_amount, len(users))

    set_balance(
        sender_id,
        sender_balance - parsed_amount
    )

    for index, (uid,) in enumerate(users):

        bal, _ = get_user(uid)
        share = each_amount + (1 if index < remainder else 0)

        set_balance(
            uid,
            bal + share
        )

    await interaction.response.send_message(
        f'🎉 {interaction.user.mention} đã phát lì xì tổng cộng '
        f'**{format_money(parsed_amount)}** '
        f'cho **{len(users)}** người chơi!\n\n'
        f'*{FOOTER_TEXT}*'
    )


tree.add_command(money_group)


# =========================================================
# NHÓM LỆNH ADMIN
# =========================================================

admin_group = app_commands.Group(
    name='admin',
    description='Quyền hạn Admin'
)


@admin_group.command(
    name='pay',
    description='[ADMIN] Cộng tiền cho bản thân hoặc người khác'
)
@app_commands.describe(
    amount='Số tiền cấp',
    member='Người nhận'
)
async def admin_pay(
    interaction: discord.Interaction,
    amount: str,
    member: Optional[discord.Member] = None
):

    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(
            f'❌ Bạn không có quyền Admin.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    parsed_amount = parse_bet(
        1_000_000_000_000,
        amount
    )

    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message(
            f'❌ Số tiền không hợp lệ. Hãy nhập ví dụ `50k`, `1M` hoặc `all`.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    target_user = (
        member
        if member is not None
        else interaction.user
    )

    balance, _ = get_user(
        target_user.id
    )

    set_balance(
        target_user.id,
        balance + parsed_amount
    )

    await interaction.response.send_message(
        f'👑 **[ADMIN]** Đã cộng '
        f'**{format_money(parsed_amount)}** '
        f'cho {target_user.mention}.\n\n'
        f'*{FOOTER_TEXT}*'
    )


@admin_group.command(
    name='take',
    description='[ADMIN] Trừ tiền người chơi'
)
@app_commands.describe(
    amount='Số tiền trừ',
    member='Người chơi bị trừ'
)
async def admin_take(
    interaction: discord.Interaction,
    amount: str,
    member: discord.Member
):

    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(
            f'❌ Bạn không có quyền Admin.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    balance, _ = get_user(
        member.id
    )

    parsed_amount = parse_bet(
        balance,
        amount
    )

    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message(
            f'❌ Số tiền không hợp lệ. Hãy nhập ví dụ `50k`, `1M` hoặc `all`.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    new_balance = max(
        0,
        balance - parsed_amount
    )

    set_balance(
        member.id,
        new_balance
    )

    await interaction.response.send_message(
        f'👑 **[ADMIN]** Đã tịch thu '
        f'**{format_money(parsed_amount)}** '
        f'từ {member.mention}.\n\n'
        f'*{FOOTER_TEXT}*'
    )


@admin_group.command(
    name='setbalance',
    description='[ADMIN] Đặt lại số dư người chơi'
)
async def admin_setbalance(
    interaction: discord.Interaction,
    amount: str,
    member: discord.Member
):

    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(
            f'❌ Bạn không có quyền Admin.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    parsed_amount = parse_bet(
        1_000_000_000_000,
        amount
    )

    if parsed_amount is None or parsed_amount <= 0:
        await interaction.response.send_message(
            f'❌ Số tiền không hợp lệ. Hãy nhập ví dụ `50k`, `1M` hoặc `all`.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    set_balance(
        member.id,
        parsed_amount
    )

    await interaction.response.send_message(
        f'👑 **[ADMIN]** Đã đặt số dư của '
        f'{member.mention} thành '
        f'**{format_money(parsed_amount)}**.\n\n'
        f'*{FOOTER_TEXT}*'
    )


tree.add_command(admin_group)


# =========================================================
# RESET MONEY
# =========================================================

reset_group = app_commands.Group(
    name='reset',
    description='Lệnh Reset dữ liệu'
)


@reset_group.command(
    name='money',
    description='[ADMIN] Reset số dư về 0'
)
async def reset_money(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None,
    reset_all: Optional[bool] = False
):

    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message(
            f'❌ Bạn không có quyền Admin.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    cursor = conn.cursor()

    if reset_all:

        cursor.execute(
            'UPDATE users SET balance = 0'
        )

        conn.commit()

        await interaction.response.send_message(
            f'⚠️ **[ADMIN]** Đã reset số dư của '
            f'**TẤT CẢ** người chơi về **0 VNĐ**!\n\n'
            f'*{FOOTER_TEXT}*'
        )

    elif member is not None:

        set_balance(
            member.id,
            0
        )

        await interaction.response.send_message(
            f'🧹 **[ADMIN]** Đã reset số dư của '
            f'{member.mention} về **0 VNĐ**.\n\n'
            f'*{FOOTER_TEXT}*'
        )

    else:
        await interaction.response.send_message(
            f'❌ Hãy chọn một người chơi hoặc bật `reset_all`.\n\n*{FOOTER_TEXT}*',
            ephemeral=True
        )


tree.add_command(reset_group)


# =========================================================
# LỆNH TÀI XỈU & DONATE
# =========================================================

@tree.command(
    name='donate',
    description='Ủng hộ nhà phát triển MinaBot'
)
async def donate(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title='☕ ỦNG HỘ MINABOT / DONATE',
        description=(
            'Cảm ơn bạn đã đồng hành cùng MinaBot!\n\n'
            '🏦 **Ngân hàng:** MB Bank\n'
            '💳 **STK:** 0915779767\n\n'
            '*"cam on vi da den"*'
        ),
        color=0x3498db
    )

    embed.set_footer(
        text=FOOTER_TEXT
    )

    await interaction.response.send_message(
        embed=style_embed(embed)
    )


@tree.command(
    name='tx',
    description='Cược Tài Xỉu'
)
@app_commands.describe(
    choice='Chọn "tài" hoặc "xỉu"',
    amount='Số tiền cược (VD: 10k, 1M, all)'
)
async def tx(
    interaction: discord.Interaction,
    choice: str,
    amount: str
):

    choice = choice.strip().lower()

    if choice not in ('tài', 'xỉu'):

        await interaction.response.send_message(
            f'Lựa chọn phải là `tài` hoặc `xỉu`.\n\n'
            f'*{FOOTER_TEXT}*',
            ephemeral=True
        )

        return

    user_id = interaction.user.id

    balance, _ = get_user(
        user_id
    )

    bet = parse_bet(
        balance,
        amount
    )

    if (
        bet is None
        or bet <= 0
        or bet > balance
    ):
        await interaction.response.send_message(
            f'Số tiền cược không hợp lệ hoặc không đủ số dư.\n\n'
            f'*{FOOTER_TEXT}*',
            ephemeral=True
        )
        return

    luck_multiplier, _ = get_luck_multiplier(user_id)
    win = False
    dice = []
    result = 'xỉu'
    total = 0

    # Mỗi hệ số cho thêm một lượt gieo; kết quả cuối vẫn là xúc xắc thật.
    for _ in range(luck_multiplier):
        dice = [random.randint(1, 6) for _ in range(3)]
        total = sum(dice)
        result = 'tài' if 11 <= total <= 18 else 'xỉu'
        win = choice == result
        if win:
            break

    dice_str = ', '.join(
        map(str, dice)
    )

    new_balance = (
        balance + bet
        if win
        else balance - bet
    )

    set_balance(
        user_id,
        new_balance
    )

    cursor = conn.cursor()

    cursor.execute(
        '''
        INSERT INTO tx_history
        (user_id, choice, bet, result, dice, win, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            user_id,
            choice,
            bet,
            result,
            dice_str,
            1 if win else 0,
            time.time()
        )
    )

    conn.commit()

    embed = discord.Embed(
        title='🎲 KẾT QUẢ TÀI XỈU - MINABOT',
        color=(
            0x2ecc71
            if win
            else 0xe74c3c
        )
    )

    embed.add_field(
        name='👤 Người chơi',
        value=interaction.user.name,
        inline=True
    )

    embed.add_field(
        name='💰 Cược',
        value=(
            f'{choice.upper()} - '
            f'{format_money(bet)}'
        ),
        inline=False
    )

    embed.add_field(
        name='🎲 Xúc xắc',
        value=(
            f'[{dice_str}] '
            f'(Tổng {total}) → '
            f'**{result.upper()}**'
        ),
        inline=False
    )

    embed.add_field(
        name='📢 Kết quả',
        value=(
            f'{"THẮNG +" if win else "THUA -"}'
            f'{format_money(bet)}'
        ),
        inline=False
    )

    embed.add_field(
        name='💳 Số dư mới',
        value=format_money(new_balance),
        inline=False
    )

    if luck_multiplier > 1:
        embed.add_field(
            name='🍀 Bùa may mắn',
            value=f'Đang hoạt động: **x{luck_multiplier}**',
            inline=False
        )

    embed.set_footer(
        text=FOOTER_TEXT
    )

    await interaction.response.send_message(
        embed=style_embed(embed)
    )


@tree.command(
    name='tx_history',
    description='Xem lịch sử ván cược Tài Xỉu'
)
async def tx_history(
    interaction: discord.Interaction
):

    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT choice, bet, result, dice, win
        FROM tx_history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
        ''',
        (interaction.user.id,)
    )

    rows = cursor.fetchall()

    if not rows:

        await interaction.response.send_message(
            f'Bạn chưa tham gia ván Tài Xỉu nào.\n\n'
            f'*{FOOTER_TEXT}*',
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title=f'📜 LỊCH SỬ CƯỢC - {interaction.user.name}',
        color=0x3498db
    )

    for idx, (
        choice,
        bet,
        result,
        dice,
        win
    ) in enumerate(
        rows,
        start=1
    ):

        status_icon = (
            "🟢 THẮNG"
            if win
            else "🔴 THUA"
        )

        embed.add_field(
            name=f'Ván {idx}: {status_icon}',
            value=(
                f'Đặt: `{choice.upper()}` '
                f'({format_money(bet)}) | '
                f'Ra: `{result.upper()}` '
                f'[{dice}]'
            ),
            inline=False
        )

    embed.set_footer(
        text=FOOTER_TEXT
    )

    await interaction.response.send_message(
        embed=style_embed(embed),
        ephemeral=True
    )


# =========================================================
# SHOP VẬT PHẨM
# =========================================================

@tree.command(name='shop', description='Xem cửa hàng vật phẩm MinaBot')
async def shop(interaction: discord.Interaction):
    lines = []
    for key, item in SHOP_ITEMS.items():
        lines.append(
            f'`{key}`\n'
            f'**{item["name"]}** — **{format_money(item["price"])}**\n'
            f'{item["description"]}'
        )
    embed = neon_embed(
        'SHOP VẬT PHẨM',
        'Dùng `/shop_buy` và chọn vật phẩm để mua. Giá được đặt rất cao để bùa là vật phẩm hiếm.\n\n'
        + '\n\n'.join(lines)
    )
    embed.add_field(
        name='🍀 Cách hoạt động',
        value='Bùa tự kích hoạt sau khi mua, áp dụng cho `/tx` và `/cuop` đến khi hết thời gian. Nếu mua cùng loại khi đang hoạt động, thời gian sẽ được cộng dồn.',
        inline=False
    )
    await interaction.response.send_message(embed=style_embed(embed))


@tree.command(name='shop_buy', description='Mua một vật phẩm trong shop')
@app_commands.describe(item='Vật phẩm muốn mua')
@app_commands.choices(item=[
    app_commands.Choice(name='Bùa x2 · 15 phút · 50M', value='bua_x2_15p'),
    app_commands.Choice(name='Bùa x2 · 1 giờ · 200M', value='bua_x2_1h'),
    app_commands.Choice(name='Bùa x3 · 30 phút · 500M', value='bua_x3_30p'),
])
async def shop_buy(interaction: discord.Interaction, item: app_commands.Choice[str]):
    item_data = SHOP_ITEMS[item.value]
    balance, _ = get_user(interaction.user.id)
    if balance < item_data['price']:
        embed = neon_embed(
            'MUA HÀNG THẤT BẠI',
            f'Bạn cần **{format_money(item_data["price"])}** nhưng hiện chỉ có **{format_money(balance)}**.'
        )
        await interaction.response.send_message(embed=style_embed(embed), ephemeral=True)
        return

    purchase = purchase_shop_item(interaction.user.id, item.value)
    if purchase is None:
        await interaction.response.send_message(
            embed=style_embed(neon_embed('MUA HÀNG THẤT BẠI', 'Số dư vừa thay đổi, vui lòng kiểm tra lại rồi thử lại nhé.')),
            ephemeral=True
        )
        return

    expires_at, new_balance = purchase
    remaining_minutes = max(1, int((expires_at - time.time()) / 60))
    embed = neon_embed(
        'MUA HÀNG THÀNH CÔNG',
        f'🍀 Bạn đã mua **{item_data["name"]}** với giá **{format_money(item_data["price"])}**.\n\n'
        f'Bùa đã tự kích hoạt, còn khoảng **{remaining_minutes} phút**.\n'
        f'Số dư còn lại: **{format_money(new_balance)}**.'
    )
    await interaction.response.send_message(embed=style_embed(embed))


@tree.command(name='inventory', description='Xem bùa đang sở hữu và bùa đang hoạt động')
async def inventory(interaction: discord.Interaction):
    rows = conn.execute(
        'SELECT item_key, quantity, expires_at FROM inventory WHERE user_id = ? AND quantity > 0',
        (interaction.user.id,)
    ).fetchall()
    if not rows:
        await interaction.response.send_message(
            embed=style_embed(neon_embed('TÚI ĐỒ TRỐNG', 'Bạn chưa sở hữu bùa nào. Dùng `/shop` để xem vật phẩm.')),
            ephemeral=True
        )
        return

    now = time.time()
    lines = []
    for item_key, quantity, expires_at in rows:
        item_data = SHOP_ITEMS.get(item_key)
        if not item_data:
            continue
        if expires_at > now:
            status = f'đang hoạt động, còn **{max(1, int((expires_at - now) / 60))} phút**'
        else:
            status = 'đã hết hạn'
        lines.append(f'🍀 **{item_data["name"]}** ×{quantity} — {status}')
    await interaction.response.send_message(
        embed=style_embed(neon_embed('TÚI ĐỒ CỦA BẠN', '\n'.join(lines))),
        ephemeral=True
    )


# =========================================================
# TƯƠNG TÁC, XP/RANK VÀ NỘI DUNG GIẢI TRÍ
# =========================================================

ROASTS = [
    "hôm nay trông bạn như vừa thua 7 ván Tài Xỉu liên tiếp vậy 😭",
    "bạn không lười, bạn chỉ đang chạy chế độ tiết kiệm năng lượng thôi 🔋",
    "vũ trụ có nhiều bí ẩn, nhưng sự tự tin của bạn là bí ẩn lớn nhất 🌌",
    "bạn là phiên bản beta rất có tiềm năng của chính mình 🧪",
]

JOKES = [
    "Tại sao máy tính đi khám bệnh? Vì nó bị virus.",
    "Lập trình viên thích mùa đông vì có nhiều bug để bắt.",
    "Tôi định kể một câu đùa về UDP... nhưng không chắc bạn sẽ nhận được.",
    "Con mèo nói gì khi dùng Discord? Meow-derator!",
]

QUOTES = [
    "Không cần nhanh nhất, chỉ cần đừng bỏ cuộc giữa chừng.",
    "Hôm nay là một ngày tốt để tạo thêm một kỷ niệm vui.",
    "Bạn không cần hoàn hảo để trở nên đáng nhớ.",
    "Một tin nhắn vui có thể cứu cả một ngày buồn.",
]

FACTS = [
    "Bạch tuộc có ba trái tim.",
    "Mật ong có thể bảo quản rất lâu nếu được giữ kín.",
    "Một ngày trên sao Kim dài hơn một năm trên sao Kim.",
    "Chuối là một loại quả mọng theo định nghĩa thực vật học.",
]

FORTUNES = [
    "Hôm nay vận may đang đứng về phía bạn. Hãy thử một điều mới! 🌟",
    "Một người bạn sắp gửi cho bạn một tin nhắn rất vui. 💌",
    "Bạn sẽ có một khoảnh khắc cười thật to trong hôm nay. 😄",
    "Cơ hội tốt thường đến khi bạn chủ động bước lên trước. 🚀",
]


@tree.command(name='ship', description='Tính độ hợp nhau vui giữa hai người')
@app_commands.describe(member='Người muốn ghép đôi')
async def ship(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    member = member or interaction.user
    score = 100 if member.id == interaction.user.id else random.randint(1, 100)
    mood = 'định mệnh rồi đó 💞' if score >= 80 else 'có tiềm năng, cứ nói chuyện thêm nhé ✨' if score >= 50 else 'bạn bè cũng là một loại duyên mà 😄'
    embed = neon_embed('SHIP METER', f'{interaction.user.mention} 💘 {member.mention}')
    embed.add_field(name='💖 Độ hợp nhau', value=f'**{score}%**', inline=False)
    embed.add_field(name='🔮 Kết luận', value=mood, inline=False)
    await interaction.response.send_message(embed=style_embed(embed))


@tree.command(name='roast', description='Cà khịa vui, không ác ý')
@app_commands.describe(member='Người muốn cà khịa')
async def roast(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    target = member or interaction.user
    embed = neon_embed('ROAST NHẸ NHÀNG', f'🎤 {target.mention}\n\n{random.choice(ROASTS)}')
    await interaction.response.send_message(embed=style_embed(embed))


@tree.command(name='hug', description='Gửi một cái ôm ảo')
@app_commands.describe(member='Người nhận cái ôm')
async def hug(interaction: discord.Interaction, member: discord.Member):
    embed = neon_embed('CÁI ÔM NEON', f'🤗 {interaction.user.mention} đã ôm {member.mention}!\n\nLan tỏa năng lượng tích cực nhé ✨')
    await interaction.response.send_message(embed=style_embed(embed))


@tree.command(name='rps', description='Chơi kéo búa bao với một thành viên')
@app_commands.describe(member='Đối thủ', choice='Chọn keo, bua hoặc bao')
@app_commands.choices(choice=[
    app_commands.Choice(name='Kéo', value='keo'),
    app_commands.Choice(name='Búa', value='bua'),
    app_commands.Choice(name='Bao', value='bao'),
])
async def rps(interaction: discord.Interaction, member: discord.Member, choice: app_commands.Choice[str]):
    options = ['keo', 'bua', 'bao']
    bot_choice = random.choice(options)
    wins = {('keo', 'bao'), ('bua', 'keo'), ('bao', 'bua')}
    result = 'Hòa!' if choice.value == bot_choice else 'Bạn thắng!' if (choice.value, bot_choice) in wins else 'Bạn thua!'
    embed = neon_embed('KÉO BÚA BAO', f'{interaction.user.mention} đấu với {member.mention}')
    embed.add_field(name='🎮 Lựa chọn của bạn', value=choice.value.upper(), inline=True)
    embed.add_field(name='🤖 Bot chọn', value=bot_choice.upper(), inline=True)
    embed.add_field(name='🏆 Kết quả', value=result, inline=False)
    await interaction.response.send_message(embed=style_embed(embed))


@tree.command(name='rank', description='Xem rank và đặc quyền giải trí')
@app_commands.describe(member='Người muốn xem rank')
async def rank(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    target = member or interaction.user
    xp, _ = get_xp(target.id)
    name, logo, threshold, perk = rank_for_xp(xp)
    next_rank = next_rank_for_xp(xp)
    progress = f'{xp} XP'
    if next_rank:
        progress += f' • còn {next_rank[2] - xp} XP để lên {next_rank[0]}'
    embed = neon_embed(f'{logo} RANK {name.upper()}', f'{target.mention}\n\n**{progress}**')
    embed.add_field(name='🎖️ Logo rank', value=f'{logo} **{name}**', inline=True)
    embed.add_field(name='✨ Đặc quyền', value=perk, inline=False)
    embed.add_field(name='🛡️ Phạm vi', value='Chỉ là đặc quyền giải trí/giao diện, không có quyền Admin hay quyền tiền tệ server.', inline=False)
    await interaction.response.send_message(embed=style_embed(embed))


@tree.command(name='rank_top', description='Bảng xếp hạng XP hoạt động')
async def rank_top(interaction: discord.Interaction):
    rows = conn.execute('SELECT user_id, xp FROM users ORDER BY xp DESC LIMIT 10').fetchall()
    if not rows:
        await interaction.response.send_message(embed=neon_embed('BẢNG RANK', 'Chưa có dữ liệu XP.'))
        return
    lines = []
    for index, (user_id, xp) in enumerate(rows, 1):
        user = interaction.guild.get_member(user_id) if interaction.guild else None
        display = user.display_name if user else f'ID {user_id}'
        rank_name, logo, _, _ = rank_for_xp(xp)
        lines.append(f'**{index}.** {logo} {display} — `{xp} XP` ({rank_name})')
    await interaction.response.send_message(embed=neon_embed('BẢNG XẾP HẠNG XP', '\n'.join(lines)))


@tree.command(name='meme', description='Gửi meme nổi tiếng ngẫu nhiên')
async def meme(interaction: discord.Interaction):
    await interaction.response.defer()
    template = await get_random_meme()
    if template:
        embed = neon_embed(f"MEME: {template['name']}", 'Meme nổi tiếng từ kho Imgflip • dùng `/meme` để đổi meme')
        embed.set_image(url=template['url'])
        embed.url = template['url']
    else:
        embed = neon_embed('MEME', 'Kho meme đang tạm thời không phản hồi. Thử lại sau nhé!')
    await interaction.followup.send(embed=style_embed(embed))


@tree.command(name='joke', description='Gửi một câu đùa ngẫu nhiên')
async def joke(interaction: discord.Interaction):
    await interaction.response.send_message(embed=neon_embed('JOKE TIME', f'😂 {random.choice(JOKES)}'))


@tree.command(name='quote', description='Gửi một câu nói ngẫu nhiên')
async def quote(interaction: discord.Interaction):
    await interaction.response.send_message(embed=neon_embed('QUOTE OF THE DAY', f'💫 “{random.choice(QUOTES)}”'))


@tree.command(name='fact', description='Một sự thật thú vị')
async def fact(interaction: discord.Interaction):
    await interaction.response.send_message(embed=style_embed(neon_embed('FUN FACT', f'🧠 {random.choice(FACTS)}')))


@tree.command(name='fortune', description='Bói vui dành cho rank Bạc trở lên')
async def fortune(interaction: discord.Interaction):
    xp, _ = get_xp(interaction.user.id)
    rank_name, logo, _, _ = rank_for_xp(xp)
    if xp < RANKS[1][2]:
        embed = neon_embed(
            'KHÓA RANK',
            f'🔒 Lệnh `/fortune` mở từ rank **Bạc**.\n\n'
            f'Bạn đang ở {logo} **{rank_name}** với **{xp} XP**. '
            f'Cần thêm **{RANKS[1][2] - xp} XP** để mở khóa!'
        )
    else:
        embed = neon_embed('BÓI VUI NEON', f'🔮 {random.choice(FORTUNES)}\n\nRank hiện tại: {logo} **{rank_name}**')
    await interaction.response.send_message(embed=style_embed(embed), ephemeral=True)


async def send_media_fact(interaction: discord.Interaction, kind: str):
    api_url = f'https://api.the{kind}api.com/v1/images/search'
    try:
        request = urllib.request.Request(api_url, headers={'User-Agent': 'MinaBot/1.0'})
        data = await asyncio.to_thread(lambda: json.loads(urllib.request.urlopen(request, timeout=8).read().decode('utf-8')))
        image_url = data[0]['url']
        embed = neon_embed(f'{kind.upper()} NEON', f'Ảnh {kind} ngẫu nhiên cho bạn ✨')
        embed.set_image(url=image_url)
    except Exception:
        embed = neon_embed(f'{kind.upper()} NEON', f'Không tải được ảnh {kind} lúc này, thử lại sau nhé!')
    await interaction.response.send_message(embed=style_embed(embed))


@tree.command(name='cat', description='Gửi ảnh mèo ngẫu nhiên')
async def cat(interaction: discord.Interaction):
    await send_media_fact(interaction, 'cat')


@tree.command(name='dog', description='Gửi ảnh chó ngẫu nhiên')
async def dog(interaction: discord.Interaction):
    await send_media_fact(interaction, 'dog')


# =========================================================
# CHẠY BOT
# =========================================================

if __name__ == '__main__':

    if not TOKEN:

        print(
            "❌ Lỗi: Chưa tìm thấy DISCORD_TOKEN "
            "trong file .env!"
        )

    else:

        bot.run(TOKEN)
