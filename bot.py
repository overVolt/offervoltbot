from telepotpro import Bot, glance
from telepotpro.exception import TelegramError, BotWasBlockedError
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
    "start": "<b>Ciao, {}!</b> Sono il bot di <a href=\"t.me/offerVolt\">offerVolt</a>.\n"
             "Puoi usarmi per richiedere un coupon per prodotti <b>Banggood</b>, oppure per segnalare un'offerta.\n"
             "<b>Ricorda che abbiamo coupon solo per Banggood, gearbest o geekbuying, per cui non richiederci coupon per altri store come Amazon o AliExpress.</b>\n"
             "Premi /help per vedere come funziono!",
    "help": "Ciao, sono il bot di richiesta e segnalazione di offerte di overVolt.\n\n"
            "🎟 <b>Come richiedo un coupon?</b>\n"
            "Per richiedere un coupon devi mandarci il link del prodotto, e poi noi provvederemo a ricercare coupon "
            "in giro per i meandri più oscuri di qualche magazzino orientale.\n"
            "<b>Nota: Possiamo trovare coupon solo per prodotti Banggood, Gearbest e Geekbuying.</b>\n\n"
            "Esempio:\n"
            "- <i>Vorrei un coupon per questo prodotto https://link.del.prodotto/</i>\n\n"
            "💡 <b>Come richiedo una offerta?</b>\n"
            "Per richiedere una offerta è necessario che tu ci fornisca dei dettagli sul tipo di prodotto che stai "
            "cercando, come per esempio fascia di prezzo e caratteristiche.\n\n"
            "Esempio:\n"
            "- <i>Sto cercando un tablet per lo studio con la penna inclusa, voglio spendere massimo 400€</i>\n\n"
            "<b>Potrebbe capitare che in mezzo a tutti i messaggi che ci arrivano ne perdiamo di vista qualcuno: se proprio vedi "
            "che dopo un giorno non ti abbiamo ancora risposto, invia di nuovo il messaggio e ti risponderemo!</b>\n"
            "<b>Possiamo trovare coupon solo per prodotti Banggood, Gearbest e Geekbuying.</b>",
    "msg_sent": "<b>Messaggio inviato!</b>\n"
                "<b>Ricorda che abbiamo coupon solo per Banggood, gearbest o geekbuying, per cui non richiederci coupon per altri store come Amazon o AliExpress.</b>\n"
                "Un membro del team ti risponderà il prima possibile.\n"
                "⚠️ <b>Ricordati che <u>siamo in pochi</u> a gestire tutte le richieste</b> che ci arrivano: ci piacerebbe rispondere a "
                "tutti in poco tempo ma è impossibile, porta pazienza se non rispondiamo subito!\n"
                "Se non ricevi risposta entro qualche giorno probabilmente ci è sfuggito il tuo messaggio, "
                "per cui inviacelo di nuovo avendo cura di fornirci tutti i dettagli necessari a soddisfare la tua richiesta.",
    "command_ukn": "🤨 Comando sconosciuto.",
    "muted": "⛔ <b>Sei mutato.</b>\n"
             "Un admin ti ha temporaneamente limitato, quindi non puoi scrivere messaggi diretti allo staff.",
    "thanks": [
        "Richiesta effettuata!", "Grazie per la richiesta!", "Grazie dell'aiuto!"
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

    # Change Banggood mobile version to desktop one
    text = text.replace("it-m.banggood.com", "banggood.com")
    text = text.replace("m.banggood.com", "banggood.com")

    ## Messaggio da canale interno
    if chatId == -1001298078411:
        print(msg) # TODO: debug

    ## Messaggio da chat normali
    elif chatId > 0:
        # Genera entry nel database
        if not User.exists(lambda u: u.chatId == chatId):
            isNewUser = True
            user = User(chatId=chatId, name=name)
        else:
            isNewUser = False
            user = User.get(chatId=chatId)
            user.name = name


        # Comandi bot
        if text == "/listmuted" and helpers.isAdmin(chatId):
            mutedUsers = select(u for u in User if u.muted)[:]
            mutedList = ""
            for u in mutedUsers:
                mutedList += "- <a href=\"tg://user?id={}\">{}</a>\n".format(u.chatId, u.name)
            if mutedList:
                bot.sendMessage(chatId, "🔇 <b>Lista utenti mutati:</b>\n"
                                        "{}".format(mutedList), parse_mode="HTML")
            else:
                bot.sendMessage(chatId, "🔇 <b>Nessun utente mutato!</b>", parse_mode="HTML")

        elif text.startswith("/annuncio ") and helpers.isAdmin(chatId):
            bdText = "📢 <b>Annuncio dallo staff</b>\n" + text.split(" ", 1)[1]
            pendingUsers = select(u.chatId for u in User)[:]
            userCount = len(pendingUsers)
            for uid in pendingUsers:
                try:
                    bot.sendMessage(uid, bdText, parse_mode="HTML", disable_web_page_preview=True)
                except (TelegramError, BotWasBlockedError):
                    userCount -= 1
            bot.sendMessage(chatId, "📢 Messaggio inviato correttamente a {0} utenti!".format(userCount))

        elif text == "/start":
            if isNewUser:
                bot.sendMessage(chatId, messages["help"], parse_mode="HTML")
            else:
                bot.sendMessage(chatId, messages["start"].format(msg['from']['first_name']), parse_mode="HTML")

        elif text == "/help":
            bot.sendMessage(chatId, messages["help"], parse_mode="HTML")


        ## Admin ha risposto ad un messaggio di testo
        elif "reply_to_message" in msg and helpers.isAdmin(chatId):
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
                        if not origMsg.fromUser.muted:
                            origMsg.fromUser.muted = True
                            bot.sendMessage(chatId, "🔇 Utente mutato.\n"
                                                    "Usa /unmute per smutarlo.")
                            bot.sendMessage(origMsg.fromUser.chatId, "🔇 Sei stato mutato da un admin.")
                        else:
                            bot.sendMessage(chatId, "⚠️ Utente già mutato.")
                    elif text == "/unmute":
                        if origMsg.fromUser.muted:
                            origMsg.fromUser.muted = False
                            bot.sendMessage(chatId, "🔉 Utente smutato.\n"
                                                    "Usa /mute per mutarlo di nuovo.")
                            bot.sendMessage(origMsg.fromUser.chatId, "🔉 Puoi nuovamente inviare messaggi al bot!")
                        else:
                            bot.sendMessage(chatId, "⚠️ Utente già smutato.")
                    else:
                        bot.sendMessage(chatId, messages["command_ukn"], parse_mode="HTML")

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
                            replyToId = origMsg.sentIds[str(a)] if origMsg else None
                            if replyToId:
                                bot.deleteMessage((a, replyToId))
                            bot.sendMessage(a, "<a href=\"tg://user?id={}\">{}</a> ha risposto a <a href=\"tg://user?id={}\">{}</a>:\n"
                                               "<i>{}</i>".format(chatId, name, userId, userName, text), parse_mode="HTML")
                        except (TelegramError, BotWasBlockedError, KeyError):
                            pass

                    bot.deleteMessage((chatId, quotedMessage['message_id']))
                    bot.deleteMessage((chatId, int(quotedMessage['message_id'])+1))
                    #così elimina anche il messaggio sotto con le risposte rapide (compila e controlla se funzia perchè sto editando da github)

            except Exception as e:
                bot.sendMessage(chatId, "😔 <b>Errore nell'invio.</b>\n\n"
                                        "<i>Debug Info:</i>\n"
                                        "<code>{}</code>".format(e), parse_mode="HTML")
                return


        ## Messaggio non contiene un link: modalità limitatibot
        elif not helpers.getLink(msg):
            if user.muted:
                bot.sendMessage(chatId, messages["muted"], parse_mode="HTML")
                return
            if text.startswith("/"):
                bot.sendMessage(chatId, messages["command_ukn"], parse_mode="HTML")
                return

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
            if user.muted:
                bot.sendMessage(chatId, messages["muted"], parse_mode="HTML")
                return

            link = helpers.getLink(msg)
            sent = bot.sendMessage(forwardChannel, "<b>Nuovo messaggio!</b>\n"
                                                   "<i>Da:</i> <a href=\"tg://user?id={}\">{}</a>\n\n"
                                                   "{}".format(chatId, name, text),
                                   parse_mode="HTML", disable_web_page_preview=True, reply_markup=None)
            Message(fromUser=user, fromMsgId=msgId, sentIds={str(forwardChannel): int(sent['message_id'])})

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
            bot.editMessageReplyMarkup((forwardChannel, message_id), keyboards.open_scontino(linkid, message_id))
        else:
            bot.editMessageReplyMarkup((forwardChannel, message_id), keyboards.error(message_id))

    elif button == "richiesta":
        try:
            prevText = msg['message']['text']
            bot.answerCallbackQuery(query_id, "Richiesta prenotata!")
            sent = bot.sendMessage(chatId, prevText.replace("Nuovo messaggio!\n", "<b>[Richiesta prenotata]</b>\n"), parse_mode="HTML")
            bot.sendMessage(chatId, "ℹ️ <b>Risposte Rapide</b>\n"
                                    "<code>Ciao, purtroppo non ho coupon per questo prodotto</code>", parse_mode="HTML", disable_notification=True)
            bot.deleteMessage((forwardChannel, message_id))
            dbQuery = select(m for m in Message if m.sentIds[str(forwardChannel)] == message_id)[:]
            if len(dbQuery) > 0:
                origMsg = dbQuery[0]
                origMsg.sentIds = {str(chatId): int(sent['message_id'])}
        except e as Exception:
            print(e)


def accept_message(msg):
    Thread(target=reply, args=[msg]).start()

def accept_button(msg):
    Thread(target=button_press, args=[msg]).start()

bot.message_loop({'chat': accept_message, 'callback_query': accept_button})

while True:
    sleep(60)
