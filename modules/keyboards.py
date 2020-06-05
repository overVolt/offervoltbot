from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton


def open_scontino(link_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="➡️ Apri con Scontino",
                                     url="tg://resolve?domain=Scontino_bot&start={}".format(link_id))
            ]])


def link_prenota(link_id, msg_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➡️ Apri con Scontino",
                             url="tg://resolve?domain=Scontino_bot&start={}".format(link_id)),
        InlineKeyboardButton(text="📩 Prenota",
                             callback_data="prenotato#{}#{}".format(msg_id, link_id))
    ]])


def error_prenota(msg_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Errore col link.",
                             callback_data="error#{}".format(msg_id)),
        InlineKeyboardButton(text="📩 Prenota",
                             callback_data="prenotato#{}#-1".format(msg_id))
    ]])


def error(msg_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Errore col link.",
                             callback_data="error#{}".format(msg_id))
            ]])
