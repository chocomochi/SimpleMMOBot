#!/usr/bin/python
from Authenticator import Authenticator
from Traveller import Traveller
from TelegramVerifier import TelegramVerifier
import asyncio
import Utils
import logging
import argparse
import nest_asyncio
import time
import threading

nest_asyncio.apply()

parser = argparse.ArgumentParser(description = "Traveller")
parser.add_argument("-t", "--type", type=int, help="Type of Bot to run. (1: windows w/ telegram), (2: phone w/ telegram), (3: plain script, no integrations or whatsoever)")
args = parser.parse_args()

def takeSteps(
    traveller: Traveller,
    authenticator: Authenticator,
    runMode: int,
    telegramVerifierBot: TelegramVerifier = None
):
    while True:
        msToSleep = traveller.takeStep()
        if msToSleep == 0 and runMode == 1 or msToSleep == 0 and runMode == 2:
            telegramVerifierBot.run(authenticator)
            continue
        
        secondsToSleep = Utils.millisecondsToSeconds(msToSleep)
        time.sleep(secondsToSleep)

def main() -> None:
    authenticator = Authenticator()
    (CSRF_TOKEN, API_TOKEN, API_ENDPOINT) = authenticator.getLoginCredentials()
    
    if args.type == 1 or args.type == 2:
        traveller = Traveller(CSRF_TOKEN, API_TOKEN, API_ENDPOINT, runMode=args.type)
        telegramVerifierBot = TelegramVerifier(traveller.COOKIE)
        telegramVerifierBot.logger = logging.getLogger(__name__)
        takeSteps(traveller, authenticator, args.type, telegramVerifierBot=telegramVerifierBot)
    elif args.type == 3:
        takeSteps(traveller, authenticator, args.type)
    else:
        class NoTypeFoundException(Exception): pass
        raise NoTypeFoundException("Please provide a type number with -t or --type")

if __name__ == "__main__":
    main()
