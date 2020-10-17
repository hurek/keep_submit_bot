from pony.orm import *
import telebot
from datetime import datetime
from config import initialize
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pprint import pprint
from polog.flog import flog

bot = initialize()
# logger = telebot.logger
# telebot.logger.setLevel(logging.DEBUG)

scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

db = Database('sqlite', 'test.sqlite', create_db=True)


class Telega(db.Entity):
    telegram_id = Required(int, size=64, unique=True)
    username = Required(str, unique=True)
    status = Required(str, default='new')
    solved = Required(int, default=0)
    path1 = Required(int, default=1)
    path2 = Required(int, default=2)
    path3 = Required(int, default=4)


class One(db.Entity):
    solvedtime = Required(str)
    discord = Optional(str, unique=True)
    telegram_id = Required(int, size=64, unique=True)
    username = Required(str, unique=True)
    feedback = Optional(LongStr, sql_default='empty')
    step = Required(str, sql_default='new')


class Two(db.Entity):
    solvedtime = Required(str)
    discord = Optional(str, unique=True)
    telegram_id = Required(int, size=64, unique=True)
    username = Required(str, unique=True)
    feedback = Optional(LongStr, sql_default='empty')
    step = Required(str, sql_default='new')


class Three(db.Entity):
    solvedtime = Required(str)
    discord = Optional(str, unique=True)
    telegram_id = Required(int, size=64, unique=True)
    username = Required(str, unique=True)
    feedback = Optional(LongStr, sql_default='empty')
    step = Required(str, sql_default='new')


db.generate_mapping(create_tables=True)


def submit_tables(model, message):
    currenttime = datetime.strftime(datetime.now(), "%H:%M:%S %d.%m.%Y")
    if not select(p.telegram_id for p in model if p.telegram_id == message.from_user.id):
        p = model(solvedtime=currenttime, telegram_id=message.from_user.id, username=message.from_user.username,
                  step='discordname')


def submit(model, message):
    user = model.get(telegram_id=message.from_user.id)
    if user.step == 'discordname':
        user.step = 'discordsubmit'
        user.discord = message.text
        commit()
        bot.send_message(message.chat.id,
                         "Your nickname is " + message.text + ", isn't it? Write me Yes if nickname is correct, else write me No.")
    elif user.step == 'discordsubmit':
        if message.text.lower() == 'yes':
            user.step = 'feedback'
            commit()
            bot.send_message(message.chat.id,
                             "Tell us in a few sentences about your impressions of the puzzle.\n▪What did you like the most?\n▪What was the most difficult part?\n▪Would you like more similar events?\nIf you don't want to leave feedback, write me PASS.")
        else:
            user.step = 'discordname'
            commit()
            bot.send_message(message.chat.id, "Enter your Discord nickname in the format nickname#number📝")
    elif user.step == 'feedback':
        if message.text.lower() == 'pass':
            user.step = 'submited'
            user.feedback = 'pass'
            commit()
        else:
            user.step = 'submited'
            user.feedback = message.text
            commit()


def migrate_row(model, status, message):
    if status == 'MK-774d314a2ffa262a089a875b4a2e6be59843de9e1752c0c2ce1e9c17851f299f':
        sheet = client.open("submit_sheet").sheet1
    elif status == 'MK-1f1602e05a1052f9d3398a8476b74b8834cd9e473f79099a93720fce3534976a':
        sheet = client.open("submit_sheet").get_worksheet(1)
    elif status == 'MK-5df4138f1e0e85d606cac6e2f3574e1af5f0182a7555fd9174380847b5d8c35b':
        sheet = client.open("submit_sheet").get_worksheet(2)
    user = model.get(telegram_id=message.from_user.id)
    row = [user.id, user.solvedtime, user.discord, user.telegram_id, user.username, user.feedback]
    pprint(row)
    sheet.append_row(row)


@bot.message_handler(commands=['start'])
@flog
def welcome(message):
    if message.chat.type == 'private':
        with db_session:
            if not select(p.telegram_id for p in Telega if p.telegram_id == message.from_user.id):
                p = Telega(telegram_id=message.from_user.id, username=message.from_user.username)
                commit()
        StartKB = telebot.types.ReplyKeyboardMarkup(True)
        StartKB.row("Fill")
        bot.send_message(message.chat.id,
                         "Congratulations, you've come a long way!\nThe last step is to fill the form📝",
                         reply_markup=StartKB)


@bot.message_handler(content_types=['text'])
@flog
@db_session
def verify_key(message):
    if message.chat.type == 'private':
        user_id = message.from_user.id
        username = message.from_user.username
        if not select(p.telegram_id for p in Telega if p.telegram_id == message.from_user.id):
            return
        user = Telega.get(telegram_id=user_id)
        if message.text == 'Fill' and user.solved < 7:
            user.status = 'inputkey'
            commit()
            bot.send_message(message.chat.id, "Enter the key", reply_markup=telebot.types.ReplyKeyboardRemove())
            return
        key_status = {'MK-774d314a2ffa262a089a875b4a2e6be59843de9e1752c0c2ce1e9c17851f299f': 1,
                      'MK-1f1602e05a1052f9d3398a8476b74b8834cd9e473f79099a93720fce3534976a': 2,
                      'MK-5df4138f1e0e85d606cac6e2f3574e1af5f0182a7555fd9174380847b5d8c35b': 4}
        if user.status == 'inputkey':
            if message.text in key_status and not user.solved & key_status[message.text]:
                user.set(status=message.text, solved=(user.solved | key_status[message.text]))
                commit()
            elif message.text in key_status:
                bot.send_message(message.chat.id, "Already solved✅")
                return
            else:
                bot.send_message(message.chat.id, "Wrong key⚠")
                return
            bot.send_message(message.chat.id, "Enter your Discord nickname in the format nickname#number📝")
            return
        tables = {'MK-774d314a2ffa262a089a875b4a2e6be59843de9e1752c0c2ce1e9c17851f299f': One,
                  'MK-1f1602e05a1052f9d3398a8476b74b8834cd9e473f79099a93720fce3534976a': Two,
                  'MK-5df4138f1e0e85d606cac6e2f3574e1af5f0182a7555fd9174380847b5d8c35b': Three}
        if user.status in tables:
            table = tables[user.status]
            submit_tables(table, message)
            submit(table, message)
            k = table.get(telegram_id=user_id)
            if k.step == 'submited':
                migrate_row(table, user.status, message)
                if user.solved < 7:
                    restartKB = telebot.types.ReplyKeyboardMarkup(True)
                    restartKB.row("Fill")
                    bot.send_message(message.chat.id,
                                     "Thank you for filling out the form!✅\nThe team will announce the results soon! If you want to solve another branch of the puzzle click on the button.",
                                     reply_markup=restartKB)
                else:
                    bot.send_message(message.chat.id,
                                     "Thank you for filling out the form!✅\nThe team will announce the results soon!")


bot.polling(none_stop=True)
