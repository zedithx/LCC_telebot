import os
import logging
import telegram
import firebase_admin

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
TOKEN = '6397262167:AAF5JUnqD_spZzNeGPWmf-nDX_X2VeUgbiQ'
bot = telegram.Bot(token=TOKEN)
luckydraw_no = 1

# define no. of variables to be stored
VOTING, CATEGORY, UROP, OVERSEAS, FIFTHROW = range(5)

# Flow 1
""" start --> category --> urop --> voting_urop """
# Flow 2
"""Overseas has an additional choosing of country before the final poster selection"""
""" start --> category --> overseas --> overseas_phase2 --> voting_overseas"""
# Flow 3
""" start --> category --> fifthrow --> voting_fifthrow"""

"""Initialising firebase creds"""
cred_obj = firebase_admin.credentials.Certificate('./creds.json')
default_app = firebase_admin.initialize_app(cred_obj, {
    'databaseURL': 'https://lcc-luckydraw-default-rtdb.asia-southeast1.firebasedatabase.app/'
})
ref = firebase_admin.db.reference("/")


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
    reply_keyboard = [['1', '2', '3']]
    update.message.reply_text(
        "Thank you for participating in LCC Voting. You can view all the posters on"
        "our website https://lcc.sutd.edu.sg/. \n\nYou are only allowed to vote for one poster. You will "
        "automatically be entered into a lucky draw when you vote for your"
        "favourite poster.\n\n"
        "Which category would you like to vote for \n\n"
        "1: UROP \n"
        "2: Overseas Opportunities \n"
        "3: Fifth Rows \n\n"
        "Send /cancel to stop talking to me.", reply_markup=ReplyKeyboardMarkup(reply_keyboard)
    )
    logger.info("User %s is choosing a category", user.first_name)
    return CATEGORY

@send_typing_action
def category(update: Update, _: CallbackContext):
    """Let user choose the options based on category"""
    user = update.message.from_user
    # UROP
    if update.message.text == '1':
        reply_keyboard = [['1', '2', '3', '4']]
        poster_string = ''
        for poster in posters.urop:
            poster_string += f'{poster} \n'
        update.message.reply_text(
            "You have chosen the UROP category. Which poster do you wish to vote for? \n\n"
            f'{poster_string}', reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        logger.info("User %s is choosing an option for UROP", user.first_name)
        return UROP
    if update.message.text == '2':
        reply_keyboard = [['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13']]
        poster_string = ''
        for poster in posters.overseas:
            poster_string += f'{poster}\n'
        update.message.reply_text(
            "You have chosen the Overseas Opportunities category. Which University would you like to vote for? \n\n"
            f'{poster_string}', reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        logger.info("User %s is choosing an option for Overseas Opportunities", user.first_name)
        return OVERSEAS
    if update.message.text == '3':
        reply_keyboard = [['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11']]
        poster_string = ''
        for poster in posters.fifth_rows:
            poster_string += f'{poster}\n'
        update.message.reply_text(
            "You have chosen the Fifth Row category. Which Poster would you like to vote for? \n\n"
            f'{poster_string}', reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        logger.info("User %s is choosing an option for Fifth Row", user.first_name)
        return FIFTHROWS

@send_typing_action
def category(update: Update, _: CallbackContext):
    """Let user choose the options based on category"""


@send_typing_action
def voting(update: Update, _: CallbackContext):
    userID = str(update.message.chat_id)
    global luckydraw_no
    user = update.message.from_user
    all_keys = set().union(*(d.keys() for d in ref.child("voting").get().values() if type(d) == dict))
    if userID in all_keys:
        logger.info("User %s tried to vote multiple times", user.first_name)
        update.message.reply_text(
            f"You have already voted. You are only allowed to vote for one poster.\n"
            f"Please do /revote to change your vote", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    else:
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
            CATEGORY: [MessageHandler(Filters.regex('^[1-13]$'), category)],
            VOTING: [MessageHandler(Filters.regex('^[1-4]$'), voting)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        run_async=True
    )

    revote_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("revote", revote)],
        states={
            REVOTING: [MessageHandler(Filters.regex('^[1-4]$'), revoting)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        run_async=True
    )

    dispatcher.add_handler(start_conv_handler)
    dispatcher.add_handler(revote_conv_handler)
    updater.start_polling()
    # test = updater.start_webhook(listen="0.0.0.0",
    #                              port=PORT,
    #                              url_path=TOKEN,
    #                              webhook_url='' + TOKEN)
    updater.idle()
