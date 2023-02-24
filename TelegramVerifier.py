from telegram import *
from telegram.ext import *
from telegram.constants import ParseMode
from dotenv import load_dotenv
from random import randint
from PIL import Image, ImageDraw
from io import BytesIO
from Authenticator import Authenticator
import traceback
import html
import Utils
import os
import json
import asyncio


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

            new.paste(image, (width,height))

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
    WEB_VERIFICATION_ENDPOINT = "https://web.simple-mmo.com/i-am-not-a-bot?new_page=true"
    API_VERIFICATION_ENDPOINT = "https://web.simple-mmo.com/api/bot-verification"
    IMAGES_ENDPOINT = "https://web.simple-mmo.com/i-am-not-a-bot/generate_image?uid="
    isUserCorrect: bool = False
    scopeLoop: asyncio.AbstractEventLoop = None
    itemKeys = []

    class CannotVerify(Exception): pass

    def __init__(self, authenticator: Authenticator) -> None:
        load_dotenv()

        self.auth = authenticator
        self.chatId = os.getenv("chat_id")
        self.token = os.getenv("bot_token")

    def run(self):
        loop = asyncio.get_event_loop()

        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self.application = Application.builder().token(token = self.token).build()
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.onItemClick))
        self.application.add_error_handler(self.errorHandler)

        loop.run_until_complete(self.verify())
        print("> Please answer immediately!")
        self.application.run_polling()
        print("> Stopping telegram bot...")

    async def verify(self) -> bool:
        retries = 3
        objectToFind: str = None

        while retries > 0:
            try:
                if retries < 3:
                    print(f"> Retrying [{retries}]")
                
                self.isUserCorrect = False
                if objectToFind == None:
                    humanizedHeaders = {
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Host": "web.simple-mmo.com",
                        "Pragma": "no-cache",
                        "Referer": "https://web.simple-mmo.com/travel",
                        "Connection": "keep-alive",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "same-origin",
                        "Sec-Fetch-User": "?1",
                        "TE": "trailers",
                        "Upgrade-Insecure-Requests": "1",
                        "User-Agent": self.auth.userAgent
                    }

                    response = self.auth.get(
                        url = self.WEB_VERIFICATION_ENDPOINT,
                        headers = humanizedHeaders
                    )

                    objectToFind = Utils.removeHtmlTags(
                        rawHtml = Utils.getStringInBetween(
                            string = response.text,
                            delimiter1 = 'Please press on the following item:',
                            delimiter2 = '</div>'
                        )
                    )

                self.itemKeys = self.getItemKeys(response.text)
                self.itemKeys.pop(0)
                
                print("> Obtaining images...")
                itemImages = self.getItemImages()

                print("> Collaging images...")
                collageCreator = CollageCreator()
                collagedImages = collageCreator.createCollage(itemImages)

                buttons = [
                    [InlineKeyboardButton("1", callback_data="0")],
                    [InlineKeyboardButton("2", callback_data="1")],
                    [InlineKeyboardButton("3", callback_data="2")],
                    [InlineKeyboardButton("4", callback_data="3")]
                ]

                print("> Sending the images...")
                await self.application.updater.bot.sendPhoto(
                    chat_id = self.chatId,
                    photo = collagedImages,
                    caption = f"🔍 Find: {objectToFind.strip()}",
                    reply_markup = InlineKeyboardMarkup(buttons)
                )
            except:
                retries -= 1
                raise Exception()
            else:
                return
                
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
            delimiter2 = "'"
        )
    
    def getItemImages(self) -> list[bytes]:
        contents = []
        humanizedHeaders = {
            "Accept": "image/avif,image/webp,*/*",
            "Host": "web.simple-mmo.com",
            "Pragma": "no-cache",
            "Referer": self.WEB_VERIFICATION_ENDPOINT,
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "image",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-origin",
            "TE": "trailers",
            "User-Agent": self.auth.userAgent
        }

        for i in range(0, 4):
            item = self.auth.get(
                url = self.IMAGES_ENDPOINT + str(i),
                headers = humanizedHeaders
            ).content

            contents.append(item)
        
        return contents
    
    async def onItemClick(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        
        item = int(query.data)
        self.isUserCorrect = self.getVerificationResults(itemPosition = item)
        
        status = "incorrect ❗"
        if self.isUserCorrect:
            print("> Verification successful!")
            status = "correct ✔️"
        else:
            print("> Verification failed!")

        try:
            await query.edit_message_reply_markup(reply_markup=None)
            await context.bot.sendMessage(
                chat_id = self.chatId,
                text = f"🔒 Verification [{query.data}] is {status}"
            )
        finally:
            asyncio.get_event_loop().stop()
            return
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """A ping function to send a dummy message"""
        await update.message.reply_text("Hi! I'm a bot!")

    def getVerificationResults(self, itemPosition: int) -> bool:
        x, y = self.humanizeMouseClick()

        humanizedData = {
            "data": self.itemKeys[itemPosition],
            "x": x,
            "y": y
        }

        result = self.auth.post(
            url = self.API_VERIFICATION_ENDPOINT,
            data = humanizedData,
            headers = { "User-Agent": self.auth.userAgent }
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