from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import requests
from bs4 import BeautifulSoup

# === BOT TOKEN ===
TOKEN = '8102817571:AAFsJzs-9egfiJEf46wrx6EzCoTzwd7s1xg'
SABIT_SIFRE = '123456'

# === DERS KONTROL FONKSİYONU ===
def ders_kontrol(ogr_no):
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Görünmez çalışır
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

# === DUYURU ÇEKME FONKSİYONU ===
def get_announcements():
    url = "https://makina.deu.edu.tr/tr/tum-duyurular/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find("div", class_="su-tabs-panes")

    if not container:
        return ["❌ Duyuru alanı bulunamadı."]

    duyurular = []
    for i, div in enumerate(container.find_all("div", recursive=False)[:3], 1):
        title_tag = div.find("h3")
        link_tag = div.find("a", href=True)

        title = title_tag.get_text(strip=True) if title_tag else "Başlık bulunamadı"
        link = link_tag["href"] if link_tag else "Bağlantı yok"

        duyurular.append(f"{i}. {title}\n🔗 {link}")
    return duyurular

# === TELEGRAM BOT İŞLEYİCİLERİ ===
def mesaj_yanita(update: Update, context: CallbackContext):
    ogr_no = update.message.text.strip()

    if not ogr_no.isdigit() or len(ogr_no) != 10:
        update.message.reply_text("❗ Lütfen geçerli 10 haneli öğrenci numarası girin.")
        return

    update.message.reply_text("🔍 Ders kaydınız kontrol ediliyor...")
    sonuc = ders_kontrol(ogr_no)
    update.message.reply_text(sonuc)

def duyurular(update: Update, context: CallbackContext):
    update.message.reply_text("📢 Son duyurular getiriliyor...")
    for duyuru in get_announcements():
        update.message.reply_text(duyuru)

# === BOTU BAŞLAT ===
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("duyurular", duyurular))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, mesaj_yanita))

    print("✅ Bot çalışıyor. /duyurular komutu veya öğrenci numarası girilebilir.")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
