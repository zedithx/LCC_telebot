import os
import logging
from time import sleep

import telegram
import firebase_admin
from firebase_admin import db

from functools import wraps
from telegram import Update, ReplyKeyboardRemove, ChatAction, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, Updater, CommandHandler, MessageHandler, Filters
import posters

PORT = int(os.environ.get('PORT', '8443'))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

"""initialising variables/bot"""
bot = telegram.Bot(token=os.environ.get("TOKEN"))
luckydraw_no = 1
userid_database = {}
# category --> country (For overseas only) -->

# define no. of variables to be stored
CATEGORY, VOTING, OVERSEAS, CONFIRMATION, SUBMIT = range(5)

""" 
Start: Introduction and PDPA clause
Category: Choose the category (Overseas, UROP, Fifth Row)
Overseas: Choose country of Overseas
Confirmation: Show final details of poster voted before writing to db
Voting: Write to db, return response of their lucky draw number
"""

# Flow 1
""" start --> category --> voting --> confirmation --> submit"""
# Flow 2
"""Overseas has an additional choosing of country before the final poster selection"""
""" start --> category --> voting --> overseas --> confirmation --> submit"""

"""Initialising firebase creds"""
cred_obj = firebase_admin.credentials.Certificate('./creds.json')
default_app = firebase_admin.initialize_app(cred_obj, {
    'databaseURL': os.environ.get("DATABASE_URL")
})
ref = db.reference("/")


def send_typing_action(func):
    """Wrapper to show that bot is typing"""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context, *args, **kwargs)

    return command_func


#TODO - PDPA
@send_typing_action
def start(update: Update, _: CallbackContext):
    """Starts the conversation."""
    user = update.message.from_user
    user_id = str(update.message.chat_id)
    reply_keyboard = [['Yes', 'No']]
    userid_database[user_id] = []
    logger.info(f"{user.first_name} has started the bot")
    update.message.reply_text(
        "Thank you for participating in LCC Voting. You can view all the posters on"
        "our website https://lcc.sutd.edu.sg/. \n\nYou are only allowed to vote for one poster. You will "
        "automatically be entered into a lucky draw when you vote for your"
        "favourite poster.")
    sleep(2)
    update.message.reply_text(
        "Do you consent to the collection, use or disclosure of your personal data only for the purpose of this event?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard)
    )
    return CATEGORY



@send_typing_action
def category(update: Update, _: CallbackContext):
    """Let user choose the category"""
    user_id = str(update.message.chat_id)
    user = update.message.from_user
    reply_keyboard = [['1', '2', '3']]
    if update.message.text.lower() == 'yes':
        logger.info("User %s is choosing a category", user.first_name)
        update.message.reply_text(
        "Which category would you like to vote for \n\n"
                "1: UROP \n"
                "2: Overseas Opportunities \n"
                "3: Fifth Rows \n\n"
                "Send /cancel to stop talking to me.", reply_markup=ReplyKeyboardMarkup(reply_keyboard)
            )
        return VOTING
    else:
        logger.info(f"{user.first_name} has rejected the PDPA clause")
        update.message.reply_text("Please consent to the PDPA clause to proceed with registering!",
                                  reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

@send_typing_action
def voting(update: Update, _: CallbackContext):
    """User to choose the poster"""
    user_id = str(update.message.chat_id)
    user = update.message.from_user
    # UROP
    if update.message.text == '1':
        userid_database[user_id].append('UROP')
        reply_keyboard = [['1', '2', '3', '4']]
        poster_string = ''
        for poster in posters.urop:
            poster_string += f'{poster} \n'
        update.message.reply_text(
            "You have chosen the UROP category. Which poster do you wish to vote for? \n\n"
            f'{poster_string}', reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        logger.info("User %s is choosing an option for UROP", user.first_name)
        return CONFIRMATION

    if update.message.text == '2':
        userid_database[user_id].append('OVERSEAS')
        reply_keyboard = [['1', '2'],
                          ['3', '4'],
                          ['5', '6'],
                          ['7', '8'],
                          ['9', '10'],
                          ['11', '12'],
                          ['13']]
        poster_string = ''
        for poster in posters.overseas:
            poster_string += f'{poster}\n'
        update.message.reply_text(
            "You have chosen the Overseas Opportunities category. Which University would you like to vote for? \n\n"
            f'{poster_string}', reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
        logger.info("User %s is choosing an option for Overseas Opportunities", user.first_name)
        return OVERSEAS

    if update.message.text == '3':
        userid_database[user_id].append('FIFTHROW')
        reply_keyboard = [['1', '2'],
                          ['3', '4'],
                          ['5', '6'],
                          ['7', '8'],
                          ['9', '10'],
                          ['11']]
        poster_string = ''
        for poster in posters.fifth_rows:
            poster_string += f'{poster}\n'
        update.message.reply_text(
            "You have chosen the Fifth Row category. Which Poster would you like to vote for? \n\n"
            f'{poster_string}', reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
        logger.info("User %s is choosing an option for Fifth Row", user.first_name)
        return CONFIRMATION

@send_typing_action
def confirmation(update: Update, _: CallbackContext):
    """Verify confirmation of posters before writing to db and releasing lucky draw number"""
    reply_keyboard = [["Yes", "No"]]
    user = update.message.from_user
    user_id = str(update.message.chat_id)
    if user_id in userid_database.keys():
        userid_database[user_id].append('REVOTE')
        logger.info("User %s is revoting", user.first_name)
        bot.sendPhoto(update.message.chat_id, open("images/Archery-min.jpg", 'rb'), caption={posters.urop[update.message.text]})
        update.message.reply_text(
            "You have already voted. Would like to revote for this poster?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        return SUBMIT
    else:
        userid_database[user_id].append('VOTE')
        logger.info("User %s is voting", user.first_name)
        bot.sendPhoto(update.message.chat_id, open("images/Archery-min.jpg", 'rb'),
                      caption=posters.urop[update.message.text])
        update.message.reply_text(
            "Would you like to vote for this poster?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        return SUBMIT


# @send_typing_action
# def fifthrow(update: Update, _: CallbackContext):
#     """Verify confirmation of fifth row poster before writing to db and releasing lucky draw number"""
#     reply_keyboard = [["Yes", "No"]]
#     user = update.message.from_user
#     user_id = str(update.message.chat_id)
#     all_keys = set().union(*(d.keys() for d in ref.child("voting").get().values() if type(d) == dict))
#     if user_id in all_keys:
#         logger.info("User %s is revoting", user.first_name)
#         bot.sendPhoto(update.message.chat_id, open("images/Archery-min.jpg", 'rb'),
#                       caption={posters.fifth_rows[update.message.text]})
#         update.message.reply_text(
#             "You have already voted. Would like to revote for this poster?",
#             reply_markup=ReplyKeyboardMarkup(reply_keyboard))
#         return REVOTE_FIFTHROW
#     else:
#         logger.info("User %s is voting", user.first_name)
#         bot.sendPhoto(update.message.chat_id, open("images/Archery-min.jpg", 'rb'),
#                       caption=posters.fifth_rows[update.message.text])
#         update.message.reply_text(
#             "Would you like to vote for this poster?",
#             reply_markup=ReplyKeyboardMarkup(reply_keyboard))
#         return VOTING_FIFTHROW
#
# @send_typing_action
# def voting_urop(update: Update, _: CallbackContext):
#     user_id = str(update.message.chat_id)
#     global luckydraw_no
#     user = update.message.from_user
#     ref.child("voting").child("urop").child(update({f"{userID}": f"{str(luckydraw_no)}"})
#     update.message.reply_text(
#         f"Your vote was {voting_dict[update.message.text]}.\n"
#         f"Your lucky draw number is {'0' * (4 - len(str(luckydraw_no))) + str(luckydraw_no)}. \n\n"
#         f"We will be announcing the winner at 6:00pm."
#         f" Do check back for the results!", reply_markup=ReplyKeyboardRemove()
#     )
#     luckydraw_no += 1
#     logger.info("User %s has voted", user.first_name)
#     return ConversationHandler.END

@send_typing_action
def submit(update: Update, _: CallbackContext):
    user_id = str(update.message.chat_id)
    global luckydraw_no
    user = update.message.from_user
    userid_category = userid_database[user_id][0]
    if userid_category.lower() == "urop" or userid_category.lower() == "fifthrow":
        userid_poster = userid_database[user_id][1]
    else:
        userid_country = userid_database[user_id][1]
        userid_poster = userid_database[user_id][2]
    ref.child("voting").child(f"{update.message.text}").update({f"{userID}": f"{str(luckydraw_no)}"})
    update.message.reply_text(
        f"Your vote was {voting_dict[update.message.text]}.\n"
        f"Your lucky draw number is {'0' * (4 - len(str(luckydraw_no))) + str(luckydraw_no)}. \n\n"
        f"We will be announcing the winner at 6:00pm."
        f" Do check back for the results!", reply_markup=ReplyKeyboardRemove()
    )
    luckydraw_no += 1
    logger.info("User %s has voted", user.first_name)
    return ConversationHandler.END

@send_typing_action
def revote(update: Update, _: CallbackContext):
    userID = str(update.message.chat_id)
    user = update.message.from_user
    reply_keyboard = [['1', '2', '3', '4']]
    all_keys = set().union(*(d.keys() for d in ref.child("voting").get().values() if type(d) == dict))
    if userID in all_keys:
        update.message.reply_text(
        "You have chosen to revote for your favourite poster. "
        "Which poster would you like to vote for? \n\n"
        "1: Poster 1\n"
        "2: Poster 2\n"
        "3: Poster 3\n"
        "4: Poster 4\n\n"
        "Send /cancel to stop talking to me.", reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        logger.info("User %s is revoting ", user.first_name)
        return REVOTING
    else:
        logger.info("User %s tried to revote without even voting", user.first_name)
        update.message.reply_text(
            f"You have not voted for any poster yet. Please do /start to"
            f"vote for your favourite poster", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
@send_typing_action
def revoting(update: Update, _: CallbackContext):
    user = update.message.from_user
    userID = str(update.message.chat_id)
    nodes = ref.child("voting").get().items()
    for node_key, node_value in nodes:
        if isinstance(node_value, dict) and userID in node_value:
            ref.child("voting").child(node_key).child(userID).delete()
            ref.child("voting").child(f"poster {update.message.text}").update({f"{userID}": f"{str(node_value.get(userID))}"})
            update.message.reply_text(
                f"You have revoted for poster {update.message.text}.\n"
                f"Your lucky draw number is still {'0' * (4 - len(str(node_value.get(userID)))) + str((node_value.get(userID)))}."
                f" All the best for the lucky draw!",
                reply_markup=ReplyKeyboardRemove())
            logger.info("User %s has revoted ", user.first_name)
            return ConversationHandler.END
    return ConversationHandler.END

@send_typing_action
def cancel(update: Update, _: CallbackContext):
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        "We hope that you will eventually participate in the LCC Voting!", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


if __name__ == '__main__':
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # register for ECHO
    start_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CATEGORY: [MessageHandler(Filters.regex('(?i)^(yes|no)$'), category)],
            VOTING: [MessageHandler(Filters.regex('^[1-3]$'), voting)],
            OVERSEAS: [MessageHandler(Filters.regex('[1-11]'), overseas)],
            CONFIRMATION: [MessageHandler(Filters.regex('^[1-13]$'), confirmation)],
            SUBMIT: [MessageHandler(Filters.regex('(?i)^(yes|no)$'), submit)]

        },
        fallbacks=[CommandHandler("cancel", cancel)],
        run_async=True
    )


    dispatcher.add_handler(start_conv_handler)
    updater.start_polling()
    # test = updater.start_webhook(listen="0.0.0.0",
    #                              port=PORT,
    #                              url_path=TOKEN,
    #                              webhook_url='' + TOKEN)
    updater.idle()
