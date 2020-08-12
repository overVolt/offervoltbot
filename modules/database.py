from pony.orm import Database, Required, Json, Set

db = Database("sqlite", "../offervoltbot.db", create_db=True)


class User(db.Entity):
    chatId = Required(int)
    name = Required(str)
    status = Required(str, default="normal")
    muted = Required(bool, default=False)
    messages = Set(lambda: Message, reverse='user')


class Message(db.Entity):
    fromUser = Required(User)
    fromMsgId = Required(int)
    sentIds = Required(Json)


db.generate_mapping(create_tables=True)
