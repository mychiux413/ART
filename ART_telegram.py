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
VERSION = 20180228
tiny = Tiny_referrals(db_path='referrals.sqlite', REFERRAL_SZIE=1000000, REFFERAL_LENGTH=8, overwrite=False,
                      field_names_text=['eth', 'lang', 'email'], field_names_num=['token'], CLAIMED_KEYS=['eth', 'email'])

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

GUIDE_ETH, GUIDE_EMAIL, GUIDE_REFERRAL = range(3)

# reply_keyboard = [['go', 'cancel']]
# markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

def start(bot, update, args):
    if len(args) > 0:
        update.message.reply_text('The referral code is {}'.format(args[0]))
    tiny.connect()
    user = update.message.from_user
    lang = get_lang(tiny, user)

    #if not tiny.user_claimed(user.id):
    if True:
        reply_keyboard = [['Set Profile', 'Maybe Later']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update = show_infos(update, 'start_new', lang, replacer={}, reply_markup=markup)
        return GUIDE_ETH
    else:
        profiles = tiny.get_user_profiles(user.id, ['eth', 'email', 'lang', 'referral', 'token'])
        show_infos(update, 'start_old', lang,
                {'\$username': user.username,
                '\$eth': profiles['eth'],
                '\$email': profiles['email'],
                '\$lang': profiles['lang'],
                '\$referral': profiles['referral'],
                '\$token': profiles['token']
                }
                )


        return None
        
def guide_eth(bot, update):
    print('we are in guide_eth')
    tiny.connect()
    user = update.message.from_user
    lang = get_lang(tiny, user)
    
    if update.message.text == 'Maybe Later':
        return None
    elif update.message.text == 'Set Profile':
        show_infos(update, 'guide_eth',
        lang)
        return GUIDE_EMAIL

def guide_email(bot, update):
    tiny.connect()
    user = update.message.from_user
    lang = get_lang(tiny, user)
    
    eth_address = update.message.text
    if is_eth_valid(eth_address):
        tiny.set_user_profiles(user.id, {'eth': eth_address})
        show_infos(update, 'guide_email', lang,
            {'\$eth':eth_address}
            )
        return GUIDE_REFERRAL
    else:
        show_infos(update, 'guide_eth_invalid', lang,
            {'\$eth':eth_address}
            )
        return GUIDE_EMAIL
        
    
def guide_referral(bot, update):
    tiny.connect()
    user = update.message.from_user
    lang = get_lang(tiny, user)
    
    email_address = update.message.text
    if is_email_valid(email_address):
        tiny.set_user_profiles(user.id, {'email': email_address, 'token':100})
        get_referral(bot, update)
    else:
        show_infos(update, 'guide_email_invalid', lang,
            {'\$email':email_address}
            )
        return GUIDE_REFERRAL
    
def is_eth_valid(eth_address):
    if eth_address[:2] == '0x':
        return True
    else:
        return False
        
def is_email_valid(email_address):
    if email_address.find('@') > -1:
        return True
    else:
        return False
    
def show_infos(update, topic, lang, replacer={}, reply_markup=None):
    try:
        reply = INFOS[INFOS['topic'] == topic][lang.lower()].iloc[0]
    except:
        reply = INFOS[INFOS['topic'] == topic]['en'].iloc[0]
    
    for k, v in replacer.items():
        if v is None:
            replacer[k] = 'null'
        elif not isinstance(v, str):
            replacer[k] = str(v)
    
    if pd.isnull(reply):
        reply = INFOS[INFOS['topic'] == topic]['en'].iloc[0]
        if pd.isnull(reply):
            return None
    for place_holder, rep in replacer.items():
        reply = re.sub(place_holder, rep, reply)
    print('=== reply ===')
    print(reply)
    if reply_markup:
        update.message.reply_text(reply, reply_markup=reply_markup)
    else:
        update.message.reply_text(reply)
    return update

def get_lang(tiny, user):
    try:
        lang = tiny.get_user_profiles(user.id, ['lang'])['lang']
        if lang is None:
            lang = user.language_code
            tiny.set_user_profiles(user.id, {'lang':lang})
        return lang
    except:
        return 'en'
    
def help(bot, update):
    tiny.connect()
    user = update.message.from_user
    
    lang = get_lang(tiny, user)
    show_infos(update, 'help', lang)
    
def set_lang(bot, update, args):
    tiny.connect()
    user = update.message.from_user
    
    # check user exist or not
    if not tiny.user_exist(user.id):
        show_infos(update, 'not_claimed', user.language_code, replacer = {'\$username': user.username})
        return None
    
    current_lang = get_lang(tiny, user)
    if len(args) > 0:
        lang = str(args[0])
        if lang not in LANG_TAGS:
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
        show_infos(update, 'set_lang', current_lang,
            {'\$username': user.username,
            '\$current_lang':current_lang}
            )

def set_eth(bot, update, args):
    tiny.connect()
    user = update.message.from_user
    
    # check user exist or not
    if not tiny.user_exist(user.id):
        show_infos(update, 'not_claimed', user.language_code, replacer = {'\$username': user.username})
        return None
    
    lang = get_lang(tiny, user)
    if len(args) > 0:
        eth_address = str(args[0])
        if is_eth_valid(eth_address):
            tiny.set_user_profiles(user.id, {'eth':eth_address})
            show_infos(update, 'set_eth_done', lang,
            {'\$username': user.username,
            '\$current_eth':eth_address}
            )
        else:
            current_eth_address = tiny.get_user_profiles(user.id, ['eth'])['eth']
            current_eth_address = 'none' if current_eth_address is None else current_eth_address
            show_infos(update, 'wrong_eth', lang,
            {'\$username': user.username,
            '\$eth':eth_address,
            '\$current_eth':current_eth_address}
            )
            return None
    else:
        
               
        current_eth_address = tiny.get_user_profiles(user.id, ['eth'])['eth']
        current_eth_address = 'none' if current_eth_address is None else current_eth_address
        show_infos(update, 'set_eth', lang,
            {'\$username': user.username,
            '\$current_eth':current_eth_address}
            )

def set_email(bot, update, args):
    tiny.connect()
    user = update.message.from_user
    
    # check user exist or not
    if not tiny.user_exist(user.id):
        show_infos(update, 'not_claimed', user.language_code, replacer = {'\$username': user.username})
        return None
    
    lang = get_lang(tiny, user)
        
    if len(args) > 0:
        email_address = str(args[0])
        if is_email_valid(email_address):
            tiny.set_user_profiles(user.id, {'email':email_address})
            show_infos(update, 'set_email_done', lang,
            {'\$username': user.username,
            '\$current_email':email_address}
            )
        else:
            current_email_address = tiny.get_user_profiles(user.id, ['email'])['email']
            current_email_address = 'none' if current_email_address is None else current_email_address
            show_infos(update, 'wrong_email', lang,
            {'\$username': user.username,
            '\$email':email_address,
            '\$current_email':current_email_address}
            )
            return None
    else:
        
               
        current_email_address = tiny.get_user_profiles(user.id, ['email'])['email']
        current_email_address = 'none' if current_email_address is None else current_email_address
        show_infos(update, 'set_email', lang,
            {'\$username': user.username,
            '\$current_email':current_email_address}
            )
            
def get_version(bot, update):
    update.message.reply_text(VERSION)

def get_profile(bot, update):
    tiny.connect()
    user = update.message.from_user
    # check user exist or not
    if not tiny.user_claimed(user.id):
        show_infos(update, 'not_claimed', user.language_code, replacer = {'\$username': user.username})
        return None
    lang = get_lang(tiny, user)
    
    profiles = tiny.get_user_profiles(user.id, ['eth', 'email', 'lang', 'referral', 'token'])
    show_infos(update, 'profile', lang,
            {'\$username': user.username,
            '\$eth': profiles['eth'],
            '\$email': profiles['email'],
            '\$lang': profiles['lang'],
            '\$referral': profiles['referral'],
            '\$token': profiles['token']
            }
            )
def get_token(bot, update):
    tiny.connect()
    user = update.message.from_user
    # check user exist or not
    if not tiny.user_claimed(user.id):
        show_infos(update, 'not_claimed', user.language_code, replacer = {'\$username': user.username})
        return None
    lang = get_lang(tiny, user)
    
    profiles = tiny.get_user_profiles(user.id, ['token', 'referral'])
    show_infos(update, 'claim', lang,
            {'\$username': user.username,
            '\$token': profiles['token'],
            '\$referral': profiles['referral']
            }
            )
def get_referral(bot, update):
    tiny.connect()
    user = update.message.from_user
    # check user exist or not
    if not tiny.user_claimed(user.id):
        show_infos(update, 'not_claimed', user.language_code, replacer = {'\$username': user.username})
        return None
    lang = get_lang(tiny, user)
    
    profiles = tiny.get_user_profiles(user.id, ['eth', 'email', 'lang', 'referral', 'token'])
    show_infos(update, 'profile', lang,
            {'\$username': user.username,
            '\$eth': profiles['eth'],
            '\$email': profiles['email'],
            '\$lang': profiles['lang'],
            '\$referral': profiles['referral'],
            '\$token': profiles['token']
            }
            )
            
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
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("profile", get_profile))
    dp.add_handler(CommandHandler("lang", set_lang,
                                  pass_args=True))
    dp.add_handler(CommandHandler("eth", set_eth,
                                  pass_args=True))
    dp.add_handler(CommandHandler("email", set_email,
                                  pass_args=True))
    dp.add_handler(CommandHandler("referral", get_referral)) 
    dp.add_handler(CommandHandler("claim", get_token))
    dp.add_handler(CommandHandler("version", get_version))
                                  
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
    guide_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start,
                                  pass_args=True)],

        states={
            # ETH: [RegexHandler('^(zh-cn|en|kr)$', guide_eth)],
            GUIDE_ETH: [RegexHandler('^(Set Profile|Maybe Later)$', guide_eth)],
            GUIDE_EMAIL: [MessageHandler(Filters.text, guide_email)],
            GUIDE_REFERRAL: [MessageHandler(Filters.text, guide_referral)],

            # PHOTO: [MessageHandler(Filters.photo, photo),
                    # CommandHandler('skip', skip_photo)],

            # LOCATION: [MessageHandler(Filters.location, location),
                       # CommandHandler('skip', skip_location)],

            # BIO: [MessageHandler(Filters.text, bio)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )
    

    dp.add_handler(guide_handler)
    

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
