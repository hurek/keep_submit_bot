import telebot

def initialize():
	bot = telebot.TeleBot('YOUR TOKEN HERE', skip_pending=True)
	return bot