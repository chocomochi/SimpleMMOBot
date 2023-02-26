#!/usr/bin/python
from Authenticator import Authenticator
from Traveller import Traveller
from TelegramVerifier import TelegramVerifier
from requests import ConnectionError, Timeout
import Utils
import logging
import argparse
import time
import multiprocessing

RECONNECTION_TIME_INTERVAL = 4
parser = argparse.ArgumentParser(description = "Traveller")
parser.add_argument("-t", "--type", type=int, help="Type of Bot to run. (1: w/ telegram), (2: w/o telegram)")
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

def animateLoading(message = "Loading..."):
    characters = ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"]
    idx = 0
    while True:
        print(f"\r> {characters[idx % len(characters)]} {message}", end="", flush = True)
        idx += 1
        time.sleep(0.1)

def main() -> None:
    if args.type == 1:
        telegramVerifierBot = TelegramVerifier()
        telegramVerifierBot.logger = logging.getLogger(__name__)
        traveller = Traveller(
            verifyCallback = telegramVerifierBot.run,
            runMode = args.type
        )
    elif args.type == 2:
        traveller = Traveller(runMode = args.type)
    else:
        class NoTypeFoundException(Exception): pass
        raise NoTypeFoundException("Please provide a type number with -t or --type")
    
    while True:
        try:
            authenticator = Authenticator()
            authenticator.getLoginCredentials()

            traveller.auth = authenticator
            if args.type == 1:
                telegramVerifierBot.auth = authenticator
            
            traveller.getUserInfo()
            takeSteps(traveller)
        except (KeyboardInterrupt, SystemExit):
            print(f"> Exiting...")
            break
        except (ConnectionError, Timeout):
            print(f"=======!! [ERR: No Internet Connection] !!=======")
        except Exception as e:
            print(f"=======!! [ERR: Unknown error] !!=======")
            print(f"> Error details: {str(e)}")
            break
        
        p = multiprocessing.Process(
            target = animateLoading,
            args = ("Waiting for internet connection...",),
            daemon = True
        )
        p.start()

        while not Utils.isConnectedToInternet():
            time.sleep(RECONNECTION_TIME_INTERVAL)

        if p.is_alive():
            p.terminate()

        print("\n> Internet resumed!")
        time.sleep(2)

if __name__ == "__main__":
    main()
