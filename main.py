from Authenticator import Authenticator
from Traveller import Traveller
from TelegramVerifier import TelegramVerifier
import random
import asyncio
import threading
import Utils
import logging
import argparse

parser = argparse.ArgumentParser(description = "Traveller")
parser.add_argument("-t", "--type", type=int, help="Type of Bot to run. (1: windows w/ telegram), (2: phone w/ telegram), (3: plain script, no integrations or whatsoever)")
args = parser.parse_args()

async def takeSteps(traveller: Traveller, telegramBot: TelegramVerifier, runMode: int):
    while True:
        msToSleep = traveller.takeStep()
        if msToSleep == 0 and runMode == 1 or msToSleep == 0 and runMode == 2:
            isDone = await telegramBot.verify()
            if isDone:
                while telegramBot.isUserCorrect == False:
                    continue

            continue
        secondsToSleep = Utils.millisecondsToSeconds(msToSleep)
        additionalHumanizedSeconds = random.uniform(0.4, 1.6)
        await asyncio.sleep(secondsToSleep + additionalHumanizedSeconds)

def asyncStepperFunctionWrapper(traveller: Traveller, telegramBot: TelegramVerifier, runMode: int):
    asyncio.run(takeSteps(traveller, telegramBot, runMode))

def main() -> None:
    authenticator = Authenticator()
    (CSRF_TOKEN, API_TOKEN, API_ENDPOINT) = authenticator.getLoginCredentials()

    if args.type == 1 or args.type == 2:
        traveller = Traveller(CSRF_TOKEN, API_TOKEN, API_ENDPOINT, runMode=args.type)
        telegramBot = TelegramVerifier(traveller.COOKIE)
        telegramBot.logger = logging.getLogger(__name__)
        
        travellerThread = threading.Thread(
            target = asyncStepperFunctionWrapper,
            args = (traveller, telegramBot, args.type)
        )
        travellerThread.start()
        telegramBot.startPolling()
    elif args.type == 3:
        traveller = Traveller(CSRF_TOKEN, API_TOKEN, API_ENDPOINT, runMode=args.type)
        travellerThread = threading.Thread(
            target = asyncStepperFunctionWrapper,
            args = (traveller, telegramBot, args.type)
        )
        travellerThread.start()
        travellerThread.join()
    else:
        class NoTypeFoundException(Exception): pass
        raise NoTypeFoundException("Please provide a type number with -t or --type")

if __name__ == "__main__":
    main()
