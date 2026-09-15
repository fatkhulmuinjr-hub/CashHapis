import os
import sqlite3
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Server Flask Sederhana
app = Flask('')

@app.route('/')
def home():
    return "Bot Keuangan Online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Database SQLite
DB_NAME = "keuangan.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tipe TEXT,
            nominal INTEGER,
            keterangan TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Logika Bot Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = (
        "**Bot Keuangan Online**\n\n"
        "Format Perintah:\n"
        "• `/masuk <jumlah> <keterangan>`\n"
        "• `/keluar <jumlah> <keterangan>`\n"
        "• `/rekap` - Lihat saldo & riwayat"
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def catat(update: Update, context: ContextTypes.DEFAULT_TYPE, tipe: str):
    if len(context.args) < 2:
        await update.message.reply_text(f"Format salah. Gunakan: `/{tipe} <jumlah> <keterangan>`")
        return

    try:
        nominal = int(context.args[0])
        keterangan = " ".join(context.args[1:])
        user_id = update.effective_user.id

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO transaksi (user_id, tipe, nominal, keterangan) VALUES (?, ?, ?, ?)",
                       (user_id, tipe, nominal, keterangan))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"Berhasil dicatat!\n{tipe.capitalize()}: Rp{nominal:,}\nKeterangan: {keterangan}")
    except ValueError:
        await update.message.reply_text("Nominal harus berupa angka saja.")

async def masuk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await catat(update, context, "masuk")

async def keluar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await catat(update, context, "keluar")

async def rekap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT tipe, nominal, keterangan FROM transaksi WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Belum ada catatan transaksi.")
        return

    tot_masuk = sum(r[1] for r in rows if r[0] == "masuk")
    tot_keluar = sum(r[1] for r in rows if r[0] == "keluar")
    saldo = tot_masuk - tot_keluar

    respon = f"**REKAP KEUANGAN**\n\n"
    respon += f"Total Pemasukan: Rp{tot_masuk:,}\n"
    respon += f"Total Pengeluaran: Rp{tot_keluar:,}\n"
    respon += f"**Sisa Saldo: Rp{saldo:,}**\n\n"
    respon += "Catatan Terakhir:\n"
    for r in rows[-5:]:
        respon += f"• [{r[0].upper()}] Rp{r[1]:,} - {r[2]}\n"

    await update.message.reply_text(respon, parse_mode="Markdown")

if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_flask).start()
    
    TOKEN = os.environ.get("BOT_TOKEN")
    if TOKEN:
        bot_app = ApplicationBuilder().token(TOKEN).build()
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("masuk", masuk))
        bot_app.add_handler(CommandHandler("keluar", keluar))
        bot_app.add_handler(CommandHandler("rekap", rekap))
        bot_app.run_polling()
