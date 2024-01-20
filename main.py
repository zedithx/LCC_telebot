import os
import logging
import telegram
import firebase_admin

from time import sleep
from firebase_admin import db
from functools import wraps
from telegram import Update, ReplyKeyboardRemove, ChatAction, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, Updater, CommandHandler, MessageHandler, Filters
from dotenv import load_dotenv
from posters import urop, overseass, fifth_rows


load_dotenv()

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
deleted_userid_database = {}
# vote/revote --> category --> country(overseas) --> poster title

# define no. of variables to be stored
CATEGORY, VOTING, OVERSEAS, CONFIRMATION, SUBMIT = range(5)

""" 
Start: Introduction and PDPA clause
Category: Choose the category (overseas, UROP, Fifth Row)
overseas: Choose country of overseas
Confirmation: Show final details of poster voted before writing to db
Voting: Write to db, return response of their lucky draw number
"""

# Flow 1
""" start --> category --> voting --> confirmation --> submit"""
# Flow 2
"""overseas has an additional choosing of country before the final poster selection"""
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


@send_typing_action
def start(update: Update, _: CallbackContext):
    """Starts the conversation."""
    user = update.message.from_user
    user_id = str(update.message.chat_id)
    reply_keyboard = [['Yes', 'No']]
    print(f'{deleted_userid_database=}')
    print(f'{userid_database=}')
    if user_id in userid_database:
        deleted_userid_database[user_id] = userid_database[user_id]
        userid_database[user_id] = ['revote']
    else:
        userid_database[user_id] = ['vote']
    logger.info(f"{user.full_name} has started the bot")
    update.message.reply_text(
        "Thank you for participating in LCC Voting. You can view all the posters on "
        "our website. \n\n https://lcc.sutd.edu.sg/ \n\nYou are only allowed to vote for one poster. You will "
        "automatically be entered into a lucky draw when you vote for your "
        "favourite poster.")
    sleep(1)
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
    # "YES" response
    if update.message.text.lower() == 'yes':
        logger.info("User %s is choosing a category", user.full_name)
        update.message.reply_text(
            "Which category would you like to vote for \n\n"
            "1: UROP \n"
            "2: Overseas Opportunities \n"
            "3: Fifth Rows \n\n"
            "Send /cancel to stop talking to me.", reply_markup=ReplyKeyboardMarkup(reply_keyboard)
            )
        return VOTING
    # "NO" response
    else:
        logger.info(f"{user.full_name} has rejected the PDPA clause")
        update.message.reply_text("Please consent to the PDPA clause to proceed with registering!",
                                  reply_markup=ReplyKeyboardRemove())
        # check if user is revoting
        if user_id in deleted_userid_database:
            # This ensures that people don't just cancel or answer no to reset their vote count
            userid_database[user_id] = deleted_userid_database[user_id]  # transfer old data back
            del deleted_userid_database[user_id]  # clear the old database
        # user if voting for first time
        else:
            del userid_database[user_id]
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
        for key, value in urop.items():
            poster_string += f'{key}.) {value[0]} \n'
        update.message.reply_text(
            "You have chosen the UROP category. Which poster do you wish to vote for? \n\n"
            f'{poster_string}', reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        logger.info("User %s is choosing an option for UROP", user.full_name)
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
        for key, value in overseass.items():
            poster_string += f'{key}.) {value[0]} \n'
        update.message.reply_text(
            "You have chosen the Overseas Opportunities category. Which University or Category"
            " is the poster under? \n\n"
            f'{poster_string}', reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
        logger.info("User %s is choosing an option for Overseas Opportunities", user.full_name)
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
        for key, value in fifth_rows.items():
            poster_string += f'{key}.) {value[0]} \n'
        update.message.reply_text(
            "You have chosen the Fifth Row category. Which Poster would you like to vote for? \n\n"
            f'{poster_string}', reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
        logger.info("User %s is choosing an option for Fifth Row", user.full_name)
        return CONFIRMATION

@send_typing_action
def overseas(update: Update, _: CallbackContext):
    """Choose overseas poster after choosing country"""
    user_id = str(update.message.chat_id)
    user = update.message.from_user
    userid_database[user_id].append(overseass[update.message.text][0])
    userid_database[user_id].append(overseass[update.message.text][1])
    overseas_dict = overseass[update.message.text][1]
    input_range = len(overseas_dict.keys())
    reply_keyboard = []
    for i in range(1, input_range+1, 2):
        if i+1 < input_range + 1:
            reply_keyboard.append([str(i), str(i + 1)])
        else:
            reply_keyboard.append([str(i)])
    poster_string = ''
    for key, value in overseas_dict.items():
        poster_string += f'{key}.) {value[0]} \n'
    update.message.reply_text(
        f"You have chosen {overseass[update.message.text][0]}. Which Poster would you like to vote for? \n\n"
        f'{poster_string}', reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
    return CONFIRMATION
@send_typing_action
def confirmation(update: Update, _: CallbackContext):
    """Verify confirmation of posters before writing to db and releasing lucky draw number"""
    reply_keyboard = [["Yes", "No"]]
    user = update.message.from_user
    user_id = str(update.message.chat_id)

    if userid_database[user_id][1].lower() == 'urop':
        userid_database[user_id].append(urop[update.message.text][0])
        poster_picture = urop[update.message.text][1]
        poster_name = urop[update.message.text][0]
    elif userid_database[user_id][1].lower() == 'overseas':
        # get the dict
        overseas_dict = userid_database[user_id][3]
        userid_database[user_id].append(overseas_dict[update.message.text][0])
        poster_picture = overseas_dict[update.message.text][1]
        poster_name = overseas_dict[update.message.text][0]
    else:
        userid_database[user_id].append(fifth_rows[update.message.text][0])
        poster_picture = fifth_rows[update.message.text][1]
        poster_name = fifth_rows[update.message.text][0]

    if userid_database[user_id][0].lower() == 'revote':
        logger.info("User %s is revoting", user.full_name)
        bot.sendPhoto(update.message.chat_id, open(poster_picture, 'rb'),
                      caption=poster_name)
        sleep(1)
        update.message.reply_text(
            "You have already voted. Would you like to revote for this poster?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    else:
        logger.info("User %s is voting", user.full_name)
        bot.sendPhoto(update.message.chat_id, open(poster_picture, 'rb'),
                      caption=poster_name)
        sleep(1)
        update.message.reply_text(
            "Would you like to vote for this poster?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    return SUBMIT


@send_typing_action
def submit(update: Update, _: CallbackContext):
    user_id = str(update.message.chat_id)
    user = update.message.from_user
    if update.message.text.lower() == 'yes':
        userid_action = userid_database[user_id][0]
        userid_category = userid_database[user_id][1]
        # vote
        update.message.reply_text(
            "Please wait while we save your response..."
        )
        if userid_action.lower() == "vote":
            global luckydraw_no
            # not overseas
            if len(userid_database[user_id]) == 3:
                userid_poster = userid_database[user_id][2]
                ref.child(userid_category).child(userid_poster).child(user_id).update({user.full_name: str(luckydraw_no)})
                userid_database[user_id].append(str(luckydraw_no))
            # overseas
            else:
                userid_country = userid_database[user_id][2]
                userid_poster = userid_database[user_id][4]
                ref.child(userid_category).child(userid_country).child(userid_poster).child(user_id)\
                    .update({user.full_name: str(luckydraw_no)})
                userid_database[user_id].append(str(luckydraw_no))

            # Response for voting
            update.message.reply_text(
                f"Your vote was {userid_poster}.\n\n"
                f"Your lucky draw number is {'0' * (4 - len(str(luckydraw_no))) + str(luckydraw_no)}. \n\n"
                f"The lucky draw reveal will be at 5.30pm @ Campus Centre. "
                f"Please be reminded that you will have to be present physically to "
                f"receive the prize", reply_markup=ReplyKeyboardRemove()
            )
            luckydraw_no += 1
            logger.info("User %s has voted", user.full_name)
        # revote
        else:
            # delete all old info
            deleted_user_info = deleted_userid_database[user_id]
            # Means not overseas
            if len(deleted_user_info) == 4:
                deleted_userid_category, deleted_userid_poster, deleted_userid_luckydraw = deleted_user_info[1], \
                    deleted_user_info[2], deleted_user_info[3]
                ref.child(deleted_userid_category).child(deleted_userid_poster).child(user_id).delete()

            # overseas since additional country
            else:
                deleted_userid_category, deleted_userid_country, deleted_userid_poster, deleted_userid_luckydraw = \
                    deleted_user_info[1], deleted_user_info[2], deleted_user_info[4], deleted_user_info[5]
                ref.child(deleted_userid_category).child(deleted_userid_country) \
                    .child(deleted_userid_poster).child(user_id).delete()

            # Add new info
            # not overseas
            if len(userid_database[user_id]) == 3:
                userid_poster = userid_database[user_id][2]
                ref.child(userid_category).child(userid_poster).child(user_id).\
                    update({user.full_name: str(deleted_userid_luckydraw)})
                userid_database[user_id].append(str(deleted_userid_luckydraw))
            # overseas
            else:
                userid_country = userid_database[user_id][2]
                userid_poster = userid_database[user_id][4]
                ref.child(userid_category).child(userid_country).child(userid_poster).child(user_id).update(
                    {user.full_name: str(deleted_userid_luckydraw)})
                userid_database[user_id].append(str(deleted_userid_luckydraw))

                # Response for revote
            update.message.reply_text(
                f"Your vote has been changed to {userid_poster}.\n\n"
                f"Your lucky draw number is still "
                f"{'0' * (4 - len(str(deleted_userid_luckydraw))) + str(deleted_userid_luckydraw)}. \n\n"
                f"The lucky draw reveal will be at 5.30pm @ Campus Centre. "
                f"Please be reminded that you will have to be present physically to "
                f"receive the prize", reply_markup=ReplyKeyboardRemove()
            )
            logger.info("User %s has revoted", user.full_name)
            del deleted_userid_database[user_id]

    else:
        logger.info("User %s has answered no to voting.", user.full_name)
        update.message.reply_text(
            "You have answered no to the confirmation. Please vote again by doing /start",
            reply_markup=ReplyKeyboardRemove()
        )
        # check if user is revoting
        if user_id in deleted_userid_database:
            # This ensures that people don't just cancel or answer no to reset their vote count
            userid_database[user_id] = deleted_userid_database[user_id]  # transfer old data back
            del deleted_userid_database[user_id]  # clear the old database
        # user if voting for first time
        else:
            del userid_database[user_id]  # delete userid from database
    return ConversationHandler.END


# Error handler function
def error(update: Update, context: CallbackContext):
    """Log errors and handle them gracefully"""
    user = update.message.from_user
    logger.error(f"Error: {user} entered {context.error} as input")
    update.message.reply_text(
        "That was an invalid response. Please try entering a valid response.")

@send_typing_action
def cancel(update: Update, _: CallbackContext):
    """Cancels and ends the conversation."""
    user = update.message.from_user
    user_id = str(update.message.chat_id)
    logger.info("User %s canceled the conversation.", user.full_name)
    update.message.reply_text(
        "We hope that you will eventually participate in the LCC Voting!", reply_markup=ReplyKeyboardRemove()
    )
    # check if user is revoting
    if user_id in deleted_userid_database:
        # This ensures that people don't just cancel or answer no to reset their vote count
        userid_database[user_id] = deleted_userid_database[user_id]  # transfer old data back
        del deleted_userid_database[user_id]  # clear the old database
    # user if voting for first time
    else:
        del userid_database[user_id]  # delete userid from database
    return ConversationHandler.END


if __name__ == '__main__':
    updater = Updater(os.environ.get('TOKEN'), use_context=True)
    dispatcher = updater.dispatcher

    # register for ECHO
    start_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CATEGORY: [MessageHandler(Filters.regex('(?i)^(yes|no)$'), category)],
            VOTING: [MessageHandler(Filters.regex('^[1-3]$'), voting)],
            OVERSEAS: [MessageHandler(Filters.regex('[1-9]|1[0-3]?'), overseas)],
            CONFIRMATION: [MessageHandler(Filters.regex('[1-9]|1[0-1]?'), confirmation)],
            SUBMIT: [MessageHandler(Filters.regex('(?i)^(yes|no)$'), submit)]

        },
        fallbacks=[CommandHandler("cancel", cancel)],
        run_async=True
    )

    dispatcher.add_handler(start_conv_handler)
    dispatcher.add_error_handler(error)
    updater.start_polling()
    # test = updater.start_webhook(listen="0.0.0.0",
    #                              port=PORT,
    #                              url_path=TOKEN,
    #                              webhook_url='' + TOKEN)
    updater.idle()
