import os
import time
import pytz
from datetime import datetime
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from apscheduler.schedulers.background import BackgroundScheduler
from tinydb import TinyDB, Query
from selenium import webdriver
from selenium.webdriver.common.by import By
import requests
from bs4 import BeautifulSoup

# === Sabitler ===
TOKEN = "7632465441:AAHs-pCXftmiCGGpSDVOaAqp_S_XfgDryWE"
SABIT_SIFRE = "123456"
db = TinyDB("veri.json")
User = Query()

# === Aşamalar ===
OGRENCINO = range(1)

# === Ders kontrol fonksiyonu ===
def ders_kontrol(ogr_no):
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        driver.get("http://vproce.net/OgrenciBilgiSistemi/default.aspx")
        time.sleep(2)

        driver.find_element(By.ID, "txt_ogrNo").send_keys(ogr_no)
        driver.find_element(By.ID, "txt_sifre").send_keys(SABIT_SIFRE)
        driver.find_element(By.ID, "btn_giris").click()
        time.sleep(2)

        menu_items = driver.find_elements(By.CLASS_NAME, "menu_item")
        for item in menu_items:
            if item.get_attribute("sayfa") == "Derslerim":
                item.click()
                break
        time.sleep(2)

        ortakisim = driver.find_element(By.ID, "ortakisim").text.strip()
        driver.quit()

        if ortakisim == "Derslerim":
            return "📭 Ders kaydı bulunamadı."
        else:
            return f"✅ Ders kaydı bulundu: {ortakisim}"

    except Exception as e:
        return f"❌ Hata oluştu:\n{e}"

# === /start komutu ===
def start(update: Update, context: CallbackContext):
    mesaj = (
        "🎓 Merhaba!\n"
        "Lütfen öğrenci numaranızı yazın, ders kaydınız otomatik olarak günde 2 defa kontrol edilecek.\n"
        "Ayrıca /duyurular komutu ile DEÜ Makine Mühendisliği duyurularına erişebilirsiniz.\n"
        "Bilgilerinizi tamamen silmek için /sil yazabilirsiniz."
    )
    update.message.reply_text(mesaj)
    return OGRENCINO

# === Numara kaydet ===
def ogrno_kaydet(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    ogr_no = update.message.text.strip()
    if not ogr_no.isdigit() or len(ogr_no) != 10:
        update.message.reply_text("❗ Lütfen 10 haneli geçerli bir öğrenci numarası girin.")
        return OGRENCINO

    db.upsert({"user_id": user_id, "ogr_no": ogr_no}, User.user_id == user_id)
    update.message.reply_text("✅ Numaran kaydedildi. Artık her gün saat 09:00 ve 17:00'de otomatik kontrol yapılacak.")
    return ConversationHandler.END

# === Otomatik kontrol fonksiyonu ===
def otomatik_kontrol():
    now = datetime.now(pytz.timezone("Europe/Istanbul"))
    for k in db.all():
        ogr_no = k.get("ogr_no")
        if ogr_no:
            sonuc = ders_kontrol(ogr_no)
            updater.bot.send_message(chat_id=k["user_id"], text=f"📢 Otomatik kontrol ({now.strftime('%H:%M')}):\n{sonuc}")

# === /duyurular komutu ===
def duyurular(update: Update, context: CallbackContext):
    url = "https://makina.deu.edu.tr/tr/tum-duyurular/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find("div", class_="su-tabs-panes")

    if not container:
        update.message.reply_text("❌ Duyuru alanı bulunamadı.")
        return

    duyurular = []
    for i, div in enumerate(container.find_all("div", recursive=False)[:3], 1):
        title_tag = div.find("h3")
        link_tag = div.find("a", href=True)

        title = title_tag.get_text(strip=True) if title_tag else "Başlık bulunamadı"
        link = link_tag["href"] if link_tag else "Bağlantı yok"

        duyurular.append(f"{i}. {title}\n🔗 {link}")

    for duyuru in duyurular:
        update.message.reply_text(duyuru)

# === /sil komutu ===
def sil(update: Update, context: CallbackContext):
    db.remove(User.user_id == update.effective_user.id)
    update.message.reply_text("🧨 Tüm verileriniz silindi. /start ile yeniden başlayabilirsiniz.")

# === Botu başlat ===
updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher

# === Komutlar ===
dp.add_handler(ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={OGRENCINO: [MessageHandler(Filters.text & ~Filters.command, ogrno_kaydet)]},
    fallbacks=[]
))

dp.add_handler(CommandHandler("duyurular", duyurular))
dp.add_handler(CommandHandler("sil", sil))

# === Planlayıcı ===
scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Istanbul"))
scheduler.add_job(otomatik_kontrol, 'cron', hour=9, minute=0)
scheduler.add_job(otomatik_kontrol, 'cron', hour=17, minute=0)
scheduler.start()

updater.start_polling()
print("✅ Otomatik kontrol botu çalışıyor...")
updater.idle()
