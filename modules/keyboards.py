from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton


def link_error(msg_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="❌ Prenota ed elimina", callback_data="error#{}".format(msg_id))
            ]])

def open_scontino(link_id, msg_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="➡️ Apri con Scontino",
                                     #url="tg://resolve?domain=Scontino_bot&start={}".format(link_id),
                                     callback_data="error#{}".format(msg_id))
            ]])
