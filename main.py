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
parser.add_argument(
    "-n", 
    "--no-telegram",
    help="Run bot without telegram integrations",
    required = False,
    action="store_true"
)
parser.add_argument(
    "-i", 
    "--ignore-npc",
    help="Auto-stepping without attacking NPCs (good for low levels!)",
    required = False,
    action="store_true"
)
parser.add_argument(
    "-s", 
    "--no-auto-equip",
    help="Auto-stepping without auto-equipping newly found items",
    required = False,
    action="store_true"
)
args = parser.parse_args()

def takeSteps(traveller: Traveller, authenticator: Authenticator):
    while True:
        currentTime = traveller.getTimeInSeconds()
        if currentTime >= traveller.energyTimer:
            msToSleep = 0
            traveller.upgradeSkill()
            msToSleep += traveller.doQuests()
            msToSleep += traveller.doArena()
            traveller.upgradeSkill()
            traveller.resetEnergyTimer()
            authenticator.generateCSRFToken()
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
    verifyCallback = None
    
    if not args.no_telegram:
        telegramVerifierBot = TelegramVerifier()
        telegramVerifierBot.logger = logging.getLogger(__name__)
        verifyCallback = telegramVerifierBot.run
    
    traveller = Traveller(
        verifyCallback = verifyCallback,
        isRunningWithTelegram = not args.no_telegram,
        shouldAttackNPCs = not args.ignore_npc,
        shouldAutoEquipItems = not args.no_auto_equip
    )
    while True:
        try:
            authenticator = Authenticator()
            authenticator.getLoginCredentials()

            traveller.auth = authenticator
            if not args.no_telegram:
                telegramVerifierBot.auth = authenticator
            
            traveller.getUser()
            takeSteps(traveller, authenticator)
        except (KeyboardInterrupt, SystemExit):
            print(f"> Exiting...")
            break
        except (ConnectionError, Timeout):
            print(f"=======!! [ERR: No Internet Connection] !!=======")
        except Exception as e:
            print(f"=======!! [ERR: Unknown error] !!=======")
            print(f"> Error details: {str(e)}")
            # raise e # Uncomment this to see whole error
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

if __name__ == "__main__":
    main()
