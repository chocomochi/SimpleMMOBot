from telegram import *
from telegram.ext import *
import requests
import Utils
from dotenv import load_dotenv
import os
from random import randint
import json

class TelegramVerifier:
    WEB_VERIFICATION_ENDPOINT = "https://web.simple-mmo.com/i-am-not-a-bot"
    API_VERIFICATION_ENDPOINT = "https://web.simple-mmo.com/api/bot-verification"
    IMAGES_ENDPOINT = "https://web.simple-mmo.com/i-am-not-a-bot/generate_image?uid="
    isUserCorrect: bool = False
    itemKeys = []

    class CannotVerify(Exception):
        pass

    def __init__(self, cookie: dict) -> None:
        load_dotenv()
        self.COOKIE = cookie
        
        token = os.getenv("bot_token")
        self.chatId = os.getenv("chat_id")
        self.application = Application.builder().token(token = token).build()
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.onItemClick))

    def startPolling(self):
        self.application.run_polling()
    
    async def verify(self):
        self.isUserCorrect = False
        response = requests.get(
            url = self.WEB_VERIFICATION_ENDPOINT,
            cookies = self.COOKIE
        )

        try:
            objectToFind = Utils.removeHtmlTags(
                rawHtml = Utils.getStringInBetween(
                    string = response.text,
                    delimiter1 = 'Please press on the following item:',
                    delimiter2 = '</div>'
                )
            )

            self.itemKeys = self.getItemKeys(response.text)
            self.itemKeys.pop(0)
            itemImages = self.getItemImages()

            await self.sendItemImages(
                updater = self.application.updater,
                text = f"🔍 Find: {objectToFind.strip()}",
                media = itemImages
            )
        except:
            raise self.CannotVerify("Please verify it manually, ASAP!")
    
    def getItemKeys(self, verificationDetails: str) -> list[str]:
        return Utils.getMultipleStringsInBetween(
            string = verificationDetails,
            delimiter1 = "chooseItem('",
            delimiter2 = '\');"'
        )
    
    def getItemImages(self) -> list[InputMediaPhoto]:
        contents = []

        for i in range(0, 4):
            item = requests.get(
                url = self.IMAGES_ENDPOINT + str(i),
                cookies = self.COOKIE
            ).content

            contents.append(InputMediaPhoto(item, caption = str(i + 1)))
            print("> Obtained item image #" + str(i + 1))
        
        return contents

    async def sendItemImages(
        self,
        updater: Updater,
        text: str,
        media: list[InputMediaPhoto],
    ):
        await updater.bot.sendMediaGroup(
            chat_id = self.chatId,
            media = media
        )

        buttons = [
            [InlineKeyboardButton("1", callback_data="1")],
            [InlineKeyboardButton("2", callback_data="2")],
            [InlineKeyboardButton("3", callback_data="3")],
            [InlineKeyboardButton("4", callback_data="4")]
        ]
        await updater.bot.send_message(
            chat_id = self.chatId,
            text = text,
            reply_markup = InlineKeyboardMarkup(buttons)
        )
    
    async def onItemClick(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query

        isSuccess: bool = False
        if "1" == query.data:
            isSuccess = self.getVerificationResults(itemPosition=0)

        elif "2" == query.data:
            isSuccess = self.getVerificationResults(itemPosition=1)

        elif "3" == query.data:
            isSuccess = self.getVerificationResults(itemPosition=2)

        elif "4" == query.data:
            isSuccess = self.getVerificationResults(itemPosition=3)
        
        status = "INCORRECT"
        if isSuccess:
            status = "CORRECT"
            self.isUserCorrect = True

        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)
        await query.edit_message_text(text = f"❗❗ VERIFICATION [{query.data}] is {status} ❗❗")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Sends a message with three inline buttons attached."""
        keyboard = [
            [
                InlineKeyboardButton("Option 1", callback_data="Testing 1"),
                InlineKeyboardButton("Option 2", callback_data="Testing 2"),
            ],
            [InlineKeyboardButton("Option 3", callback_data="Testing 3")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Please choose:", reply_markup=reply_markup)

    def getVerificationResults(self, itemPosition: int) -> bool:
        x, y = self.humanizeMouseClick()
        humanizedData = {
            "data": None,
            "x": x,
            "y": y
        }

        humanizedData["data"] = self.itemKeys[itemPosition]
        result = requests.post(
            url = self.API_VERIFICATION_ENDPOINT,
            cookies = self.COOKIE,
            data = humanizedData
        )

        try:
            parsedResult = json.loads(result.text)
            isSuccess = parsedResult["type"] == "success"
            if isSuccess:
                return True
            else:
                return False
        except:
            raise self.CannotVerify("Please verify it manually, ASAP!")
    
    def humanizeMouseClick(self):
        xPosition = randint(291, 410)
        yPosition = randint(381, 398)

        return (xPosition, yPosition)