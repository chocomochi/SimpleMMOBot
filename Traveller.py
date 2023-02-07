import requests
import json
from TelegramVerifier import TelegramVerifier
from Authenticator import getStringInBetween, CookieParser
from random import randint, uniform
from Utils import removeHtmlTags
import enum
import time
from WindowsNotifier import WindowsNotifier

class Traveller:
    stepCount = 0
    userLevel = None
    WEB_ENDPOINT = "https://web.simple-mmo.com"

    class StepTypes(enum.Enum):
        Material = 1
        Text = 2
        Item = 3
        Npc = 4
        Player = 5

    def __init__(self, csrfToken: str, apiToken: str, apiEndpoint: str, runMode: int = 1) -> None:
        cookie = CookieParser()
        self.runMode = runMode
        if runMode == 1:
            self.WINDOWS_NOTIFIER = WindowsNotifier(tag = "SimpleMMO")
        self.COOKIE = cookie.COOKIE
        self.CSRF_TOKEN = csrfToken
        self.API_TOKEN = apiToken
        self.API_ENDPOINT = apiEndpoint
    
    def takeStep(self):
        x, y = self.humanizeMouseClick()

        humanizedData = {
            "_token": self.CSRF_TOKEN,
            "api_token": self.API_TOKEN,
            "d_1": x,
            "d_2": y,
            "s": "false",
            "travel_id": 0
        }

        response = requests.post(
            url = self.API_ENDPOINT,
            data = humanizedData
        )

        try:
            shouldPerformVerification = response.text.count("Perform Verification") > 0 or response.text.count("I'm not a pesky machine") > 0
            if shouldPerformVerification:
                self.stepCount += 1
                print(f"[STEP #{self.stepCount}] ALERT: Perform Verification!")
                if self.runMode == 1:
                    self.WINDOWS_NOTIFIER.showSnackbar(
                        title = "❗❗ VERIFICATION ALERT ❗❗",
                        message = "Please verify as soon as possible!",
                        duration = 'long',
                        icon = r"F:\dont_touch\pythons\simple-mmo-bot\res\alert.png"
                    )
                else:
                    input("> Please verify asap and press enter here to continue travelling...")
                
                return 0

            stepResult = json.loads(response.text)
            timeToWaitForAnotherStep = stepResult["wait_length"]

            stepHeadlineMessage = stepResult["heading"]
            stepType = self.getStepType(stepResult["step_type"])
            stepMessage = stepResult["text"]

            isUserCurrentlyOnAJob = stepMessage == "You cannot travel while you are working!"
            if isUserCurrentlyOnAJob:
                class UserOnJob(Exception): pass
                raise UserOnJob("User is on a job!")

            currentLevel = stepResult["level"]
            currentExp = stepResult["currentEXP"]
            currentGold = stepResult["currentGold"]
            if self.userLevel != None and currentLevel > self.userLevel:
                print(f"> User levelled up! Level: {currentLevel}")
            
            self.userLevel = currentLevel
            goldEarned = stepResult["gold_amount"]
            expEarned = stepResult["exp_amount"]
        except:
            print(stepResult)
            class CannotTakeStep(Exception): pass
            raise CannotTakeStep()
        else:
            self.stepCount += 1

            if stepType == self.StepTypes.Material:
                materialLevelAndRarity, nextAction = self.parseMaterialFound(materialDetails = stepMessage)
                print(f"[STEP #{self.stepCount}] You've found: {stepHeadlineMessage} [{materialLevelAndRarity}]")

                canBeGathered = stepMessage.count("Your skill level isn't high enough") < 1
                
                if canBeGathered:
                    self.obtainMaterials(actionLink = nextAction)

            elif stepType == self.StepTypes.Item:
                itemName = self.parseItemFound(stepMessage)
                print(f"[STEP #{self.stepCount}] You've found: {itemName}")
                
            elif stepType == self.StepTypes.Text:
                print(f"[STEP #{self.stepCount}] {stepHeadlineMessage}")
                
            elif stepType == self.StepTypes.Npc:
                npcLevel, nextAction = self.parseNpcFound(npcDetails = stepMessage)
                print(f"[STEP #{self.stepCount}] You've encountered: {stepHeadlineMessage} [{npcLevel}]")
                self.attackNpc(actionLink = nextAction)
                
            elif stepType == self.StepTypes.Player:
                print(f"[STEP #{self.stepCount}] You've encountered: {stepHeadlineMessage}")
            
            print(f"> Step Rewards [gold/exp]: {goldEarned}/{expEarned} | Current [gold/exp/level]: {currentGold}/{currentExp}/{currentLevel}")

            stepCountIsEven = self.stepCount % 2
            if stepCountIsEven:
                time.sleep(uniform(1.4, 6.2))

            return timeToWaitForAnotherStep
    
    def parseMaterialFound(self, materialDetails: str) -> str:
        try:
            materialLevelAndRarity = removeHtmlTags(
                rawHtml = getStringInBetween(
                    string = materialDetails,
                    delimiter1 = "<br/>",
                    delimiter2 = "</span>"
                )
            ).strip()

            actionLink = self.WEB_ENDPOINT + getStringInBetween(
                string = materialDetails,
                delimiter1 = "document.location='",
                delimiter2 = "'"
            )

            return (materialLevelAndRarity, actionLink)
        except:
            class InvalidMaterial(Exception): pass
            raise InvalidMaterial("Can't parse material!")
    
    def parseItemFound(self, itemDetails: str) -> str:
        try:
            return removeHtmlTags(itemDetails).strip()
        except:
            class InvalidItem(Exception): pass
            raise InvalidItem("Can't parse item!")

    def parseNpcFound(self, npcDetails: str) -> str:
        try:
            npcLevel = "Level " + removeHtmlTags(
                rawHtml = getStringInBetween(
                    string = npcDetails,
                    delimiter1 = "Level ",
                    delimiter2 = "<"
                )
            )

            actionLink = self.WEB_ENDPOINT + getStringInBetween(
                string = npcDetails,
                delimiter1 = "href='",
                delimiter2 = "'"
            )

            return (npcLevel, actionLink)
        except:
            class InvalidNpc(Exception): pass
            raise InvalidNpc("Can't parse NPC!")

    def parseBattleRewards(self, battleDetails: str) -> str:
        battleResults = removeHtmlTags(battleDetails).replace('You have won: ', '')
        return battleResults

    def attackNpc(self, actionLink: str):
        class CannotAttackNpc(Exception): pass
        
        isOpponentDefeated = False
        try:
            response = requests.get(
                url = actionLink,
                cookies = self.COOKIE
            )
            
            attackApiEndpoint = getStringInBetween(
                string = response.text,
                delimiter1 = "api_end_point: '",
                delimiter2 = "'"
            )
        except:
            raise CannotAttackNpc()
        else:
            while isOpponentDefeated == False:
                try:
                    humanizedData = {
                        "_token": self.CSRF_TOKEN,
                        "api_token": self.API_TOKEN,
                        "special_attack": "false"
                    }

                    battleResults = requests.post(
                        url = attackApiEndpoint,
                        data = humanizedData
                    )

                    battleResults = json.loads(battleResults.text)
                except:
                    raise CannotAttackNpc()
                else:
                    isOpponentDefeated = battleResults["opponent_hp"] == 0
                    isUserDefeated = battleResults["player_hp"] == 0

                    if isUserDefeated:
                        class UserNoHealth(Exception): pass
                        raise UserNoHealth("Can't fight without HP!")

                    if isOpponentDefeated:
                        battleRewards = battleResults["result"]
                        battleMessage = self.parseBattleRewards(battleRewards).strip()
                        
                        shouldVerify = battleMessage.count("verify") > 0
                        if shouldVerify:
                            print(f"> ALERT: Perform Verification")
                            break
                        
                        print(f"> You've won! Rewards: {battleMessage}")
                    
                    humanizedSeconds = randint(1, 5)
                    time.sleep(humanizedSeconds)

    def obtainMaterials(self, actionLink: str):
        class CannotObtainMaterials(Exception): pass
        
        isMaterialDoneGathering = False
        try:
            response = requests.get(
                url = actionLink,
                cookies = self.COOKIE
            )
            
            gatherApiEndpoint = self.WEB_ENDPOINT + "/api/crafting/material/gather/" + getStringInBetween(
                string = response.text,
                delimiter1 = "fetch('/api/crafting/material/gather/",
                delimiter2 = "'"
            )
        except:
            raise CannotObtainMaterials()
        else:
            while isMaterialDoneGathering == False:
                try:
                    humanizedData = {"_token": self.CSRF_TOKEN}
                    gatherResults = requests.post(
                        url = gatherApiEndpoint,
                        cookies = self.COOKIE,
                        data = humanizedData
                    )
                    
                    gatherResults = json.loads(gatherResults.text)
                except:
                    raise CannotObtainMaterials()
                else:
                    isMaterialDoneGathering = gatherResults["gatherEnd"]
                    expGained = gatherResults["playerExpGained"]
                    craftingExpGained = gatherResults["craftingExpGained"]

                    if isMaterialDoneGathering:
                        print(f"> Done gathering! Rewards: {expGained} EXP | {craftingExpGained} Crafting EXP")
                    else:
                        print(f"> Gathering! Rewards: {expGained} EXP | {craftingExpGained} Crafting EXP")
                        
                    humanizedSeconds = randint(1, 5)
                    time.sleep(humanizedSeconds)

    def humanizeMouseClick(self):
        xPosition = randint(291, 389)
        yPosition = randint(381, 418)

        return (xPosition, yPosition)
    
    def getStepType(self, stepType: str) -> StepTypes:
        if stepType == "material":
            return self.StepTypes.Material
        if stepType == "item":
            return self.StepTypes.Item
        if stepType == "npc":
            return self.StepTypes.Npc
        if stepType == "text":
            return self.StepTypes.Text
        if stepType == "player":
            return self.StepTypes.Player
        
        class InvalidStepType(Exception): pass
        raise InvalidStepType(f"No step type found for: {stepType}") 