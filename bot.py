from telepot import Bot, glance
from time import sleep
from threading import Thread
from modules import helpers, keyboards
from random import choice

try:
    f = open('token.txt', 'r')
    token = f.readline().strip()
    f.close()
except FileNotFoundError:
    token = input(" * Incolla qui il token di BotFather: ")
    f = open('token.txt', 'w')
    f.write(token)
    f.close()

bot = Bot(token)

forwardChannel = 123456789
messages = [
    "Grazie!", "Grazie per la segnalazione!", "Grazie dell'aiuto!",
    "Grazie 💪🏻", "Grazie per la segnalazione 💚", "Grazie dell'aiuto 💚"
]


def reply(msg):
    chatId = msg['chat']['id']
    name = msg['from']['first_name']
    if msg['from']['last_name']:
        name += " " + msg['from']['last_name']

    if "text" in msg:
        text = msg['text']
    elif "caption" in msg:
        text = msg['caption']
    else:
        text = ""

    ## Messaggio non contiene un link: modalità limitatibot
    if not helpers.getLink(msg):
        for a in helpers.isAdmin():
            bot.forwardMessage(a, chatId, msg['message_id'])
        bot.sendMessage(chatId, "<i>Messaggio inviato.</i>", parse_mode="HTML")

    ## Admin ha risposto ad un messaggio di testo
    elif "reply_to_message" in msg and helpers.isAdmin(chatId):
        try:
            userId = msg['reply_to_message']['forward_from']['id']
            userName = msg['reply_to_message']['forward_from']['first_name']
            if msg['reply_to_message']['forward_from']['last_name']:
                name += " " + msg['reply_to_message']['forward_from']['last_name']

            bot.sendMessage(userId, "💬 <b>Risposta dello staff</b>\n"
                                    "{}".format(text), parse_mode="HTML")
            bot.sendMessage(chatId, "Risposta inviata!")
            otherAdmins = [a for a in helpers.isAdmin() if a != chatId]
            for a in otherAdmins:
                bot.sendMessage(a, "<a href=\"tg://user?id={}\">{}</a> ha risposto a <a href=\"tg://user?id={}\">{}</a>: <i>{}</i>"
                                   "".format(chatId, name, userId, userName, text), parse_mode="HTML")
        except Exception:
            bot.sendMessage(chatId, "Errore nell'invio.")

    ## Messaggio contiene link: logga offerta e rispondi
    else:
        link = helpers.getLink(msg)
        sent = bot.sendMessage(forwardChannel, "<b>Nuovo messaggio!</b>\n"
                                               "<i>Da:</i> <a href=\"tg://user?id={}\">{}</a>\n\n"
                                               "{}".format(chatId, name, text),
                               parse_mode="HTML", disable_web_page_preview=True, reply_markup=None)

        if helpers.short(link):
            bot.editMessageReplyMarkup((forwardChannel, sent['message_id']), keyboards.open_scontino(helpers.short(link), sent['message_id']))
        else:
            bot.editMessageReplyMarkup((forwardChannel, sent['message_id']), keyboards.link_error(sent['message_id']))
        bot.sendMessage(chatId, choice(messages), parse_mode="HTML")


def button_press(msg):
    chatId, query_data = glance(msg, flavor="callback_query")[1:3]
    query_split = query_data.split("#")
    message_id = int(query_split[1])
    button = query_split[0]

    if button == "openscontino":
        bot.deleteMessage((forwardChannel, message_id))


def accept_message(msg):
    Thread(target=reply, args=[msg]).start()

def accept_button(msg):
    Thread(target=button_press, args=[msg]).start()

bot.message_loop({'chat': accept_message, 'callback_query': accept_button})

while True:
    sleep(60)
