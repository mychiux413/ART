#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.

First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from pyreferrals import Tiny_referrals
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

import logging, os, pprint
import pandas as pd
import re

with open('lang_list', 'r') as thefile:
    LANG_TAGS = thefile.read().split('\n')
    
INFOS = pd.read_excel('infos.xlsx')

tiny = Tiny_referrals(db_path='referrals.sqlite', REFERRAL_SZIE=1000000, REFFERAL_LENGTH=8, overwrite=False,
                      field_names_text=['eth','lang','email'])

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

LANG, SET_LANG, ETH, REFERRAL, EMAIL, SCORE, PROFILE = range(7)


def start(bot, update):

    reply_keyboard = [['zh-cn', 'en', 'kr']]

    update.message.reply_text(
        'Set your Language.',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return LANG

def show_infos(update, topic, lang, replacer={}):
    reply = INFOS[INFOS['topic'] == topic][lang.lower()].iloc[0]
    if pd.isnull(reply):
        reply = INFOS[INFOS['topic'] == topic]['en'].iloc[0]
        if pd.isnull(reply):
            return None
    for place_holder, rep in replacer.items():
        reply = re.sub(place_holder, rep, reply)
    print('=== reply ===')
    print(reply)
    update.message.reply_text(reply)

def set_lang(bot, update, args):
    tiny.connect()
    user = update.message.from_user
    
    # check user exist or not
    if not tiny.user_exist(user.id):
        show_infos(update, 'not_claimed', user.language_code, replacer = {'\$username': user.username})
        return None
    
    if len(args) > 0:
        lang = str(args[0])
        if lang not in LANG_TAGS:
            current_lang = tiny.get_user_profiles(user.id, ['lang'])['lang']
            if current_lang is None:
                current_lang = user.language_code
                tiny.set_user_profiles(user.id, {'lang':current_lang})
            show_infos(update, 'wrong_lang', current_lang,
            {'\$username': user.username,
            '\$lang':lang,
            '\$current_lang':current_lang}
            )
            return None
            
        
        tiny.set_user_profiles(user.id, {'lang':lang})
        show_infos(update, 'set_lang_done', lang,
            {'\$username': user.username,
            '\$lang':lang}
            )
    else:
        show_infos(update, 'set_lang', user.language_code)

def eth(bot, update):
    tiny = Tiny_referrals(db_path='referrals.sqlite')
    user = update.message.from_user
    tiny.set_user_profiles(user.id, {'eth':update.message.text})
    logger.info("ETH of %s: %s", user.first_name, update.message.text)
    update.message.reply_text('set email.',
                              reply_markup=ReplyKeyboardRemove())

    return EMAIL

def email(bot, update):
    tiny = Tiny_referrals(db_path='referrals.sqlite')
    user = update.message.from_user
    tiny.set_user_profiles(user.id, {'email':update.message.text})
    referral = tiny.request_referral(user_id=user.id)
    logger.info("EMAIL of %s: %s", user.first_name, update.message.text)
    update.message.reply_text('Thanks, your referral is %s, send /profile to check your profile.' %
    (referral.decode('utf8'),))

    return REFERRAL

def referral(bot, update):
    user = update.message.from_user
    logger.info("User %s did not send a photo.", user.id)
    update.message.reply_text('I bet you look great! Now, send me your location please, '
                              'or send /skip.')

    return LOCATION

def profile(bot, update):
    tiny = Tiny_referrals(db_path='referrals.sqlite')
    user = update.message.from_user
    
    referral = tiny.request_referral(user_id=user.id)
    profile = tiny.get_user_profiles(user.id, ['email', 'lang', 'eth', 'referral'])

    update.message.reply_text('your profile: email: %s, language: %s, ETH address: %s, referral: %s' %
    (profile.get('email'), profile.get('lang'), profile.get('eth'), profile.get('referral')))

    return None

def location(bot, update):
    user = update.message.from_user
    user_location = update.message.location
    logger.info("Location of %s: %f / %f", user.first_name, user_location.latitude,
                user_location.longitude)
    update.message.reply_text('Maybe I can visit you sometime! '
                              'At last, tell me something about yourself.')

    return BIO

    
def skip_location(bot, update):
    user = update.message.from_user
    logger.info("User %s did not send a location.", user.first_name)
    update.message.reply_text('You seem a bit paranoid! '
                              'At last, tell me something about yourself.')

    return BIO


def bio(bot, update):
    user = update.message.from_user
    logger.info("Bio of %s: %s", user.first_name, update.message.text)
    update.message.reply_text('Thank you! I hope we can talk again some day.')

    return ConversationHandler.END


def cancel(bot, update):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Bye! I hope we can talk again some day.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(os.environ['TELEGRAM_BOT'])

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("lang", set_lang,
                                  pass_args=True))
    # dp.add_handler(CommandHandler("lang", set_lang,
                                  # pass_args=True))

    # lang_handler = ConversationHandler(
        # entry_points=[CommandHandler("lang", set_lang,
                                  # pass_args=True)],
        # states={
            # LANG: [MessageHandler(Filters.text, lang)]
        # },
        # fallbacks=[CommandHandler('cancel', cancel)]
    # )
    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    # conv_handler = ConversationHandler(
        # entry_points=[CommandHandler('start', start)],

        # states={
            # LANG: [RegexHandler('^(zh-cn|en|kr)$', lang)],
            # ETH: [MessageHandler(Filters.text, eth)],
            # EMAIL: [MessageHandler(Filters.text, email)]

            # # PHOTO: [MessageHandler(Filters.photo, photo),
                    # # CommandHandler('skip', skip_photo)],

            # # LOCATION: [MessageHandler(Filters.location, location),
                       # # CommandHandler('skip', skip_location)],

            # # BIO: [MessageHandler(Filters.text, bio)]
        # },

        # fallbacks=[CommandHandler('cancel', cancel)]
    # )
    
    profile_handler = ConversationHandler(
        entry_points=[CommandHandler('profile', profile)],
        states={},
        fallbacks=[]
    )

    # dp.add_handler(conv_handler)
    
    dp.add_handler(profile_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
