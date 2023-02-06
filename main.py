from Authenticator import Authenticator
from Traveller import Traveller
from TelegramVerifier import TelegramVerifier
import random
import asyncio
import threading

def millisecondsToSeconds(milliseconds: int) -> float:
    return milliseconds / 1000

async def takeSteps(traveller: Traveller, telegramBot: TelegramVerifier):
    while True:
        msToSleep = traveller.takeStep()
        if msToSleep == 0:
            await telegramBot.verify()
            while telegramBot.isUserCorrect == False:
                continue
            continue
        secondsToSleep = millisecondsToSeconds(msToSleep)
        additionalHumanizedSeconds = random.uniform(0.4, 1.6)
        await asyncio.sleep(secondsToSleep + additionalHumanizedSeconds)

def asyncStepperFunctionWrapper(traveller: Traveller, telegramBot: TelegramVerifier):
    asyncio.run(takeSteps(traveller, telegramBot))

def main() -> None:
    authenticator = Authenticator()
    (CSRF_TOKEN, API_TOKEN, API_ENDPOINT) = authenticator.getLoginCredentials()

    traveller = Traveller(CSRF_TOKEN, API_TOKEN, API_ENDPOINT)

    telegramBot = TelegramVerifier(traveller.COOKIE)
    travellerThread = threading.Thread(
        target = asyncStepperFunctionWrapper,
        args = (traveller, telegramBot)
    )
    travellerThread.start()
    telegramBot.startPolling()

if __name__ == "__main__":
    main()
