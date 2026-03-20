import os
os.system("pip install PyTelegramBot")

from utils import Database
import time, telebot, string, random
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot import types

BOT_TOKEN="8622055961:AAFWXLemWrGh-Azhc-4SyzN6yi-a13qJNGk"
ADMINS = [7925361356]
DB_NAME = "DataBasePAYER.db"
DCS = {
	"Checks": {
		"CreateTime": "INTEGER", "Amount": "INTEGER", # Amount -> 1, 2, 3, 20, 100
		"More": "INTEGER", "Payed": "INTEGER", # More -> 0/1; Payed -> 0/1
		"UniqueID": "TEXT", "PayedCount": "INTEGER"
	},
	"Payments": {
		"Payer": 'INTEGER', "Price": 'INTEGER',
		"Date": 'INTEGER', 'rawpayload': 'TEXT',
		"TPCID": 'TEXT', "PPCID": "TEXT",
		"CheckID": "TEXT"
	}
}
bot=telebot.TeleBot(BOT_TOKEN)
Me = bot.get_me()
UserNameBot = Me.username

if not os.path.exists(DB_NAME):
	with Database(DB_NAME) as db:
		for k,v in DCS.items():
			db.create_table(k, v)

def RandomString(length: int) -> str:
	# Набор допустимых символов
	chars = string.ascii_letters + string.digits + '_-'
	return ''.join(random.choices(chars, k=length))

def AdminBroadCast(text: str, pm:str = "HTML") -> bool:
	for aid in ADMINS:
		try:
			bot.send_message(aid, text, parse_mode=pm)
		except Exception as e:
			print(f"Excepted error: {e}")
	else:
		return True
	return False

def ProcessCreateCheck(message, amount) -> bool:
	if message.text.lower() == "нет":
		More=False
	else:
		More=True
	with Database(DB_NAME) as db:
		UniqueId = RandomString(24)
		db.add(
			"Checks", {
				"CreateTime": int(time.time()), "Amount": amount,
				"More": More, "Payed": 0,
				"UniqueID": UniqueId, "PayedCount": 0
			}
		)
		Kb=InlineKeyboardMarkup()
		Kb.add(
			InlineKeyboardButton("Поделиться", url=f"https://t.me/share/url?url=Чек%20для%20оплаты%0A{amount}%20Telegram%20Stars%0At.me/{UserNameBot}?start={UniqueId}</code>")
		)
		bot.send_message(message.chat.id, f"Готово! Ссылка:\n<code>t.me/{UserNameBot}?start={UniqueId}</code>", parse_mode="HTML", reply_markup=Kb)

def ProcessAmountCheck(message) -> bool:
	cid = message.chat.id
	if message.text.lower().startswith("/"):
		return False # Просто молча выходим
	if not message.text.isdigit():
		bot.send_message(cid, f"Ошибка! Введено не число!")
		return False
	UppedAmount = int(float(message.text)) + (float(message.text) > int(float(message.text)))
	if UppedAmount < 1:
		bot.send_message(cid, f"Ошибка! Сумма для оплаты не может быть меньше 1!")
		return False
	markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
	markup.add(
		KeyboardButton("Да"),
		KeyboardButton("Нет")
	)
	msg=bot.send_message(cid, f"Отлично. Сумма: {UppedAmount} звёзд. Теперь, выберите, будет ли чек подходить для многоразовой оплаты:", reply_markup=markup)
	bot.register_next_step_handler(msg, lambda m: ProcessCreateCheck(message=m, amount=UppedAmount))

def send_invoice(chat_id, title, description, payload, price_amount):
	"""
	Отправка счёта
	"""
	try:
		prices = [types.LabeledPrice(label=title, amount=price_amount)]
		bot.send_invoice(
			chat_id=chat_id,
			title=title,             # Check №1
			description=description, # Pay check number one
			invoice_payload=payload, # Paying_1
			provider_token="",
			currency="XTR",
			prices=prices,
			start_parameter="payment",
			need_name=False,
			need_phone_number=False,
			need_email=False,
			need_shipping_address=False,
			is_flexible=False
		)
	except Exception as e:
		print(f"Ошибка отправки счета: {e}")

def ShowChecksList(cid, current_check=None):
	with Database(DB_NAME) as db:
		Checks = db.get_all("Checks")
		if current_check:
			Check = db.get("Checks", {"UniqueID": current_check})
		else:
			Check = Checks[0]
		CIndex = Checks.index(Check)
	text = '\n'.join([
		f"🗓 Создан: <i>{time.ctime(Check['CreateTime'])}</i>",
		f"💰 Ценник: <b>{Check['Amount']}</b>",
		f"🌊 Многоразовый: {'✅ Да' if Check['More'] else '❌ Нет'}"
		f"🏦 Оплачен: {'✅ Да' if Check['Payed'] else '❌ Нет'}",
		f"❓ Сколько раз оплачен: <code>{Check['PayedCount']}</code>",
		f"🔮 Ссылка: <code>t.me/{UserNameBot}?start={Check['UniqueID']}</code>"
	])
	Kb=InlineKeyboardMarkup()
	Kb.add(
		InlineKeyboardButton("🗑", callback_data=f"del_{Check['UniqueID']}")
	)
	Kb.add(
		InlineKeyboardButton("❌", callback_data=f"Close")
	)
	FCB=f"show_check_{Checks[CIndex-1]['UniqueID']}" if CIndex > 0 else "Close"
	SCB=f"show_check_{Checks[CIndex+1]['UniqueID']}" if CIndex > len(Checks)-1 else "Close"
	Kb.add(
		InlineKeyboardButton("◀️" if CIndex > 0 else "❌", callback_data=FCB),
		InlineKeyboardButton("◀️" if CIndex < len(Checks)-1 else "❌", callback_data=SCB)
	)
	bot.send_message(cid, text, reply_markup=Kb, parse_mode="HTML")

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
	"""
	Предварительная обработка платежа
	"""
	payload = pre_checkout_query.invoice_payload
	with Database(DB_NAME) as db:
		Check = db.get("Checks", {"UniqueID": payload})
	if Check:
		if not Check["More"] and Check["Payed"] == 0:
			bot.answer_pre_checkout_query(
				pre_checkout_query.id,
				ok=True,
				error_message=None
			)
		else:
			bot.answer_pre_checkout_query(
				pre_checkout_query.id,
				ok=False,
				error_message="Чек уже оплачен."
			)
	else:
		bot.answer_pre_checkout_query(
			pre_checkout_query.id,
			ok=False,
			error_message=f"Некорректный чек. Оплата невозможна."
		)
		AdminBroadCast(f"🚫 Пользователь <code>{pre_checkout_query.from_user.id}</code> попытался оплатить некорректный чек. Проверьте консоль.")
		print(f"Uncorrect: {payload}")

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
	"""
	Обработка удачного платежа
	"""
	payment = message.successful_payment
	user_id = message.chat.id
	# payload: CheckId
	CheckID = str(payment.invoice_payload)
	payload = payment.invoice_payload

	with Database(DB_NAME) as db:
		db.add(
			"Payments", {
				"Payer": user_id, "Price": payment.total_amount,
				"Date": int(time.time()), "rawpayload": str(payload.invoice_payloadn),
				"TPCID": payment.telegram_payment_charge_id,
				"PPCID": payment.provider_payment_charge_id,
				"CheckID": CheckID
			}
		)
		Check = db.get("Checks", {"UniqueID": CheckID})
		db.update("Checks",
			{
				"Payed": 1, # В любом случае
				"PayedCount": Check["PayedCount"]+1
			},
			{"UniqueID": CheckID}
		)
	bot.send_message(user_id, f"Благодарим за оплату чека!")
	AdminBroadCast('\n'.join([
			f"❗️ ВНИМАНИЕ!",
			f"Пользователь <code>{user_id}</code> оплатил чек!",
			f"<b><i>Данные платежа:</i></b>",
			f"🗓 <i>{time.ctime(int(time.time()))}</i>",
			f"💰 <b>{payment.total_amount} ⭐️</b>",
			f"🤖 <code>{CheckID}</code>"
		]))


@bot.message_handler(content_types=['text'])
def handle_message(message):
	cid = message.chat.id
	mid = message.id
	txt = message.text
	Relink = (
		message.text.strip().split(" ")[1]
		if len(message.text.strip().split(" ")) > 1
		else ""
	)
	if not Relink and txt.lower().startswith('/start'):
		bot.send_message(cid, "Пожалуйста, используйте ссылку для оплаты или QRCode")
		return
		# bot.send_message(cid, '\n'.join([
		# 	"Простите, <b>некорректные данные платежа.</b>",
		# 	"Перейдите по <b>полученной ссылке</b> или <b>отсканируйте Qr-код.</b>",
		# 	"Если вы не получали ничего из этого, просьба <b>перестать использовать бота.</b>"
		# ]), parse_mode="HTML")
	# Full relink: /start LolKekCheburek
	# Short relink (Relink): LolKekCheburek
	if Relink.startswith("pay_") and txt.lower().startswith('/start'):
		PayID = Relink[len("pay_"):]
		with Database(DB_NAME) as db:
			Check = db.get("Checks", {"UniqueID": PayID})
		if not Check:
			bot.send_message(cid, "Некорректный чек для оплаты. Проверьте ссылку.")
		send_invoice(cid, "Оплата", "Оплата счёта", PayID, Check["Amount"])
	else:
		if txt == "/add":
			if cid in ADMINS:
				msg = bot.send_message(cid, f"<b>Создание чека...</b>\n\nВведите сумму:", parse_mode="HTML")
				bot.register_next_step_handler(msg, ProcessAmountCheck)
		elif txt == "/checks":
			if cid in ADMINS:
				ShowChecksList(cid, None)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
	cid = call.message.chat.id
	mid = call.message.message_id
	if call.data == "Close":
		bot.delete_message(cid, mid)
	elif call.data.startswith("del_"):
		if cid in ADMINS:
			with Database(DB_NAME) as db:
				check = db.get("Checks", {"UniqueID": call.data[len("del_"):]})
				if not check:
					bot.answer_callback_query(call.id, "Не найдено!")
					return # None
				db.delete("Checks", {"UniqueID": call.data[len("del_"):]})
				bot.answer_callback_query(call.id, "Удалено!")

	elif call.data.startswith("show_check_"):
		with Database(DB_NAME) as db:
			Check = db.get("Checks", {"UniqueID": call.data[len("show_check_"):]})
		if Check:
			ShowChecksList(cid, Check)
		else:
			bot.answer_callback_query(call.id, "Не найдено!")

if __name__ == '__main__':
	bot.infinity_polling()