#!/usr/bin/python
from Authenticator import Authenticator, RequestWithSession
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

def takeSteps(traveller: Traveller):
    while True:
        currentTime = traveller.getTimeInSeconds()
        if currentTime >= traveller.energyTimer:
            traveller.upgradeSkill()
            traveller.doQuests()
            msToSleep = traveller.doArena()
            traveller.upgradeSkill()
            traveller.resetEnergyTimer()
        else:
            msToSleep = traveller.takeStep()
        
        secondsToSleep = Utils.millisecondsToSeconds(msToSleep)
        time.sleep(secondsToSleep)

def main() -> None:
    authenticator = Authenticator()
    authenticator.getLoginCredentials()
    
    if args.type == 1 or args.type == 2:
        telegramVerifierBot = TelegramVerifier(authenticator = authenticator)
        telegramVerifierBot.logger = logging.getLogger(__name__)
        traveller = Traveller(
            authenticator = authenticator,
            verifyCallback = telegramVerifierBot.run,
            runMode = args.type
        )
    elif args.type == 3:
        traveller = Traveller(
            authenticator = authenticator,
            runMode = args.type
        )
    else:
        class NoTypeFoundException(Exception): pass
        raise NoTypeFoundException("Please provide a type number with -t or --type")
    
    takeSteps(traveller)

if __name__ == "__main__":
    main()
