from telepot import Bot, glance
from telepot.exception import TelegramError, BotWasBlockedError
from time import sleep
from threading import Thread
from random import choice
from json import load as jsload
from os.path import abspath, dirname, join
from pony.orm import db_session, select

from modules import helpers, keyboards
from modules.database import User, Message

with open(join(dirname(abspath(__file__)), "settings.json")) as settings_file:
    settings = jsload(settings_file)

bot = Bot(settings["token"])
forwardChannel = settings["forwardChannel"]
messages = {
    "start": "<b>Ciao, {}!</b> Sono il bot di <a href=\"tg://resolve?domain=offerVolt\">offerVolt</a>.\n"
             "Puoi usarmi per richiedere un consulto, un coupon oppure per segnalare un'offerta.\n"
             "Premi /help per vedere come funziono!",
    "help": "Ciao, sono il bot di richiesta e segnalazione di offerte di overVolt.\n\n"
            "🎟 <b>Come richiedo un coupon?</b>\n"
            "Per richiedere un coupon devi mandarci il link del prodotto, e poi noi provvederemo a ricercare coupon "
            "in giro per i meandri più oscuri di qualche magazzino orientale.\n\n"
            "Esempio:\n"
            "- <i>Vorrei un coupon per questo prodotto https://link.del.prodotto/</i>\n"
            "- <i>C'è qualche coupon per questo prodotto? https://link.del.prodotto/</i>\n\n\n"
            "💡 <b>Come richiedo una offerta?</b>\n"
            "Per richiedere una offerta è necessario che tu ci fornisca dei dettagli sul tipo di prodotto che stai "
            "cercando, come per esempio fascia di prezzo e caratteristiche.\n\n"
            "Esempio:\n"
            "- <i>Vorrei un kit per iniziare a volare in FPV sotto i 200€</i>\n"
            "- <i>Sto cercando un telefono per mia mamma, voglio spendere massimo 200€</i>\n"
            "- <i>Sto cercando un tablet per lo studio con la penna inclusa, ho tutto il budget del mondo</i>\n\n\n"
            "Speriamo di poter essere utili!",
    "msg_sent": "<b>Messaggio inviato!</b>\n"
                "Un membro del team ti risponderà il prima possibile.",
    "thanks": [
        "Grazie!", "Grazie per la segnalazione!", "Grazie dell'aiuto!",
        "Grazie 💪🏻", "Grazie per la segnalazione 💚", "Grazie dell'aiuto 💚"
    ]
}


@db_session
def reply(msg):
    chatId = int(msg['chat']['id'])
    msgId = int(msg['message_id'])
    name = msg['from']['first_name']
    if "last_name" in msg['from']:
        name += " " + msg['from']['last_name']

    if "text" in msg:
        text = msg['text']
    elif "caption" in msg:
        text = msg['caption']
    else:
        text = ""

    # Genera entry nel database
    if not User.exists(lambda u: u.chatId == chatId):
        isNewUser = True
        user = User(chatId=chatId, name=name)
    else:
        isNewUser = False
        user = User.get(chatId=chatId)
        user.name = name

    ## Admin ha risposto ad un messaggio di testo
    if "reply_to_message" in msg and helpers.isAdmin(chatId):
        try:
            quotedMessage = msg['reply_to_message']

            # Cerca i dati del messaggio dal database
            origMsg = None
            dbQuery = select(m for m in Message if m.sentIds[str(chatId)] == int(quotedMessage['message_id']))[:]
            if len(dbQuery) > 0:
                origMsg = dbQuery[0]
                userId = origMsg.fromUser.chatId
                userName = origMsg.fromUser.name

            else:
                # Cerca di capire le informazioni da Telegram
                if "forward_from" in quotedMessage:
                    userId = quotedMessage['forward_from']['id']
                    userName = quotedMessage['forward_from']['first_name']
                    if "last_name" in quotedMessage['forward_from']:
                        userName += " " + msg['reply_to_message']['forward_from']['last_name']

                else:
                    bot.sendMessage(chatId, "😔 <b>Errore nell'invio.</b>\n\n"
                                            "L'utente ha attivato la privacy per i messaggi inoltrati, e il "
                                            "messaggio non è nel database.", parse_mode="HTML")
                    return

            # Controlla se è un comando di servizio
            if text.startswith("/"):
                if text == "/mute":
                    origMsg.fromUser.muted = True
                    bot.sendMessage(chatId, "🔇 Utente mutato.\n"
                                            "Usa /smuta per smutarlo.")
                    bot.sendMessage(origMsg.fromUser.chatId, "🔇 Sei stato mutato da un admin.")
                elif text == "/unmute":
                    origMsg.fromUser.muted = False
                    bot.sendMessage(chatId, "🔉 Utente smutato.\n"
                                            "Usa /muta per mutarlo di nuovo.")
                    bot.sendMessage(origMsg.fromUser.chatId, "🔉 Puoi nuovamente inviare messaggi al bot!")
                elif text == "/listmuted":
                    mutedUsers = select(u for u in User if u.muted)[:]
                    mutedList = ""
                    for u in mutedUsers:
                        mutedList += "- <a href=\"tg://user?id={}\">{}</a>\n".format(u.chatId, u.name)
                    bot.sendMessage(chatId, "🔇 <b>Lista utenti mutati</b>\n"
                                            "{}".format(mutedList))
                else:
                    bot.sendMessage(chatId, "🤨 Comando sconosciuto.")

            # Altrimenti, invia risposta a utente
            else:
                replyToId = origMsg.fromMsgId if origMsg else None
                bot.sendMessage(userId, "💬 <b>Risposta dello staff</b>\n"
                                        "{}".format(text), parse_mode="HTML", reply_to_message_id=replyToId)
                bot.sendMessage(chatId, "Risposta inviata!")

                # Segnala ad altri admin la risposta data
                otherAdmins = [a for a in helpers.isAdmin() if a != chatId]
                for a in otherAdmins:
                    try:
                        replyToId = origMsg.sentIds[a] if origMsg else None
                        if replyToId:
                            bot.sendMessage(a, "<a href=\"tg://user?id={}\">{}</a> ha risposto:\n"
                                               "<i>{}</i>".format(chatId, name, text), parse_mode="HTML", reply_to_message_id=replyToId)
                        else:
                            bot.sendMessage(a, "<a href=\"tg://user?id={}\">{}</a> ha risposto a <a href=\"tg://user?id={}\">{}</a>:\n"
                                               "<i>{}</i>".format(chatId, name, userId, userName, text), parse_mode="HTML")
                    except (TelegramError, BotWasBlockedError):
                        pass

        except Exception as e:
            bot.sendMessage(chatId, "😔 <b>Errore nell'invio.</b>\n\n"
                                    "<i>Debug Info:</i>\n"
                                    "<code>{}</code>".format(e), parse_mode="HTML")
            return


    ## Messaggio non contiene un link: modalità limitatibot
    elif not helpers.getLink(msg):
        # Comando bot
        if text == "/start":
            if isNewUser:
                bot.sendMessage(chatId, messages["help"], parse_mode="HTML")
            else:
                bot.sendMessage(chatId, messages["start"].format(msg['from']['first_name']), parse_mode="HTML")

        elif text == "/help":
            bot.sendMessage(chatId, messages["help"], parse_mode="HTML")

        else:
            sentIdsCache = {}
            for a in helpers.isAdmin():
                try:
                    sentMsg = bot.forwardMessage(a, chatId, msg['message_id'])
                    sentIdsCache[str(a)] = int(sentMsg['message_id'])
                except (TelegramError, BotWasBlockedError):
                    pass

            # Se non c'è il messaggio nel database, è nuovo: salvalo
            if not Message.exists(fromUser=user, fromMsgId=msgId):
                Message(fromUser=user, fromMsgId=msgId, sentIds=sentIdsCache)
            # Se esiste già il messaggio nel database, aggiorna i vecchi ID
            else:
                oldMessage = Message.get(fromUser=user, fromMsgId=msgId)
                oldMessage.sentIds = sentIdsCache

            bot.sendMessage(chatId, messages["msg_sent"], parse_mode="HTML")


    ## Messaggio contiene link: logga offerta e rispondi
    else:
        link = helpers.getLink(msg)
        sent = bot.sendMessage(forwardChannel, "<b>Nuovo messaggio!</b>\n"
                                               "<i>Da:</i> <a href=\"tg://user?id={}\">{}</a>\n\n"
                                               "{}".format(chatId, name, text),
                               parse_mode="HTML", disable_web_page_preview=True, reply_markup=None)

        if helpers.short(link):
            bot.editMessageReplyMarkup((forwardChannel, sent['message_id']), keyboards.link_prenota(helpers.short(link), sent['message_id']))
        else:
            bot.editMessageReplyMarkup((forwardChannel, sent['message_id']), keyboards.error_prenota(sent['message_id']))
        bot.sendMessage(chatId, choice(messages["thanks"]), parse_mode="HTML")


@db_session
def button_press(msg):
    query_id, chatId, query_data = glance(msg, flavor="callback_query")
    query_split = query_data.split("#")
    message_id = int(query_split[1])
    button = query_split[0]

    if button == "error":
        bot.answerCallbackQuery(query_id, "Non sono riuscito a creare il link per Scontino.")

    elif button == "prenotato":
        linkid = query_split[2]
        prevText = msg['message']['text']
        bot.answerCallbackQuery(query_id, "Offerta prenotata!")
        bot.editMessageText((forwardChannel, message_id), prevText.replace("Nuovo messaggio!\n",
                                "<b>[Offerta prenotata da {}]</b>\n".format(msg['from']['first_name'])), parse_mode="HTML")
        if linkid != -1:
            bot.editMessageReplyMarkup((forwardChannel, message_id), keyboards.open_scontino(linkid))
        else:
            bot.editMessageReplyMarkup((forwardChannel, message_id), keyboards.error(message_id))


def accept_message(msg):
    Thread(target=reply, args=[msg]).start()

def accept_button(msg):
    Thread(target=button_press, args=[msg]).start()

bot.message_loop({'chat': accept_message, 'callback_query': accept_button})

while True:
    sleep(60)
