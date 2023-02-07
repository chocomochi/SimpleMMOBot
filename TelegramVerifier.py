from telegram import *
from telegram.ext import *
from telegram.constants import ParseMode
from dotenv import load_dotenv
from random import randint
from PIL import Image, ImageDraw
from io import BytesIO
import requests
import logging
import traceback
import html
import Utils
import os
import json


class CollageCreator:
    def createCollage(self, imagesBytesList: list[bytes]) -> BytesIO:
        new = Image.new("RGBA", (100,100))
        memory = BytesIO()

        for i in range(len(imagesBytesList)):
            imageBytes = imagesBytesList[i]
            image = Image.open(BytesIO(imageBytes))
            image = image.resize((50, 50))
            draw = ImageDraw.Draw(image)
            draw.text((0, 0), str(i + 1), (87, 0, 3))

            height = 0
            width = 0
            if i == 1:
                width = 50
            elif i == 2:
                height = 50
            elif i == 3:
                height = 50
                width = 50

            new.paste(image, (height,width))

        memory.name = "image.png"
        new.save(
            memory, 
            "PNG", 
            optimize = True, 
            quality = 10
        )
        memory.seek(0)
        return memory
        
        

class TelegramVerifier:
    WEB_VERIFICATION_ENDPOINT = "https://web.simple-mmo.com/i-am-not-a-bot"
    API_VERIFICATION_ENDPOINT = "https://web.simple-mmo.com/api/bot-verification"
    IMAGES_ENDPOINT = "https://web.simple-mmo.com/i-am-not-a-bot/generate_image?uid="
    isUserCorrect: bool = False
    logger: logging.Logger = None
    itemKeys = []

    class CannotVerify(Exception):
        pass

    def __init__(self, cookie: dict) -> None:
        load_dotenv()
        token = os.getenv("bot_token")

        self.COOKIE = cookie
        self.chatId = os.getenv("chat_id")
        self.application = Application.builder().token(token = token).build()
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.onItemClick))
        self.application.add_error_handler()

    def startPolling(self):
        self.application.run_polling()
    
    async def verify(self) -> bool:
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
            collageCreator = CollageCreator()
            collagedImages = collageCreator.createCollage(itemImages)

            buttons = [
                [InlineKeyboardButton("1", callback_data="1")],
                [InlineKeyboardButton("2", callback_data="2")],
                [InlineKeyboardButton("3", callback_data="3")],
                [InlineKeyboardButton("4", callback_data="4")]
            ]

            print("> Sending the images...")
            await self.application.updater.bot.sendPhoto(
                chat_id = self.chatId,
                photo = collagedImages,
                caption = f"🔍 Find: {objectToFind.strip()}",
                reply_markup = InlineKeyboardMarkup(buttons)
            )
            
            print("> Images have been sent! Please answer immediately!")
            return True
        except:
            raise self.CannotVerify("Please verify it manually, ASAP!")
    
    async def errorHandler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a telegram message to notify the developer."""
        # Log the error before we do anything else, so we can see it even if something breaks.
        self.logger.error(msg="Exception while handling an update:", exc_info=context.error)

        # traceback.format_exception returns the usual python message about an exception, but as a
        # list of strings rather than a single string, so we have to join them together.
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = "".join(tb_list)

        # Build the message with some markup and additional information about what happened.
        # You might need to add some logic to deal with messages longer than the 4096 character limit.
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f"An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            "</pre>\n\n"
            f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
            f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )

        # Finally, send the message
        await context.bot.send_message(
            chat_id=self.chatId, text=message, parse_mode=ParseMode.HTML
        )

    def getItemKeys(self, verificationDetails: str) -> list[str]:
        return Utils.getMultipleStringsInBetween(
            string = verificationDetails,
            delimiter1 = "chooseItem('",
            delimiter2 = '\');"'
        )
    
    def getItemImages(self) -> list[bytes]:
        contents = []

        for i in range(0, 4):
            item = requests.get(
                url = self.IMAGES_ENDPOINT + str(i),
                cookies = self.COOKIE
            ).content

            contents.append(item)
            print("> Obtained item image #" + str(i + 1))
        
        return contents
    
    async def onItemClick(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()

        isSuccess: bool = False
        if "1" == query.data:
            isSuccess = self.getVerificationResults(itemPosition=0)

        elif "2" == query.data:
            isSuccess = self.getVerificationResults(itemPosition=1)

        elif "3" == query.data:
            isSuccess = self.getVerificationResults(itemPosition=2)

        elif "4" == query.data:
            isSuccess = self.getVerificationResults(itemPosition=3)
        
        status = "incorrect ❗"
        if isSuccess:
            print("> Verification successful!")
            status = "correct ✔️"
            self.isUserCorrect = True
        else:
            print("> Verification failed!")

        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.sendMessage(
            chat_id = self.chatId,
            text = f"🔒 Verification [{query.data}] is {status}"
        )
    
    # Ping function
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