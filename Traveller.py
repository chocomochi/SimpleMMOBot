from Authenticator import Authenticator
from random import randint, uniform
from Utils import removeHtmlTags, getStringInBetween
import time
import requests
import json
import enum
import time
import typing
try:
    from WindowsNotifier import WindowsNotifier
except:
    pass

class Traveller:
    WEB_ENDPOINT = "https://web.simple-mmo.com"
    API_ENDPOINT = "https://api.simple-mmo.com"
    ENDPOINTS = {
        "quests": WEB_ENDPOINT + "/quests/viewall",
        "travel": WEB_ENDPOINT + "/travel",
        "arena": WEB_ENDPOINT + "/battle/arena",
        "arenaMenu": WEB_ENDPOINT + "/battle/menu",
        "generateNpc": API_ENDPOINT + "/api/battlearena/generate",
        "character": WEB_ENDPOINT + "/user/character"
    }
    webHost = "web.simple-mmo.com"
    apiHost = "api.simple-mmo.com"
    
    stepCount = 0
    userLevel = None
    energyTimer = 0

    class StepTypes(enum.Enum):
        Material = 1
        Text = 2
        Item = 3
        Npc = 4
        Player = 5
    
    class SkillType(enum.Enum):
        Strength = 1
        Defense = 2
        Dexterity = 3
    
    class UserNoHealth(Exception): pass

    def __init__(self, authenticator: Authenticator, verifyCallback: typing.Callable[[], None] = None, runMode: int = 1) -> None:
        self.runMode = runMode
        self.auth = authenticator
        self.verifyCallback = verifyCallback
        if runMode == 1:
            self.WINDOWS_NOTIFIER = WindowsNotifier(tag = "SimpleMMO")
    
    def takeStep(self):
        x, y = self.humanizeMouseClick()

        humanizedHeaders = {
            "Accept": "*/*",
            "Host": self.apiHost,
            "Pragma": "no-cache",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": self.WEB_ENDPOINT,
            "Referer": self.ENDPOINTS["travel"],
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": self.auth.userAgent
        }

        humanizedData = {
            "_token": self.auth.CSRF_TOKEN,
            "api_token": self.auth.API_TOKEN,
            "d_1": x,
            "d_2": y,
            "s": "false",
            "travel_id": 0
        }

        response = self.auth.post(
            url = self.auth.API_ENDPOINT,
            data = humanizedData,
            headers = humanizedHeaders
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
                elif self.runMode == 3:
                    input("> Please verify asap and press enter here to continue travelling...")
                
                if self.runMode != 3:
                    self.startVerification()

                return 0
            
            isUserOnNewLocation = response.text.count("You have reached") > 0
            if isUserOnNewLocation:
                self.stepCount += 1
                print(f"[STEP #{self.stepCount}] Reached new location!")
                return 0
            
            stepResult = json.loads(response.text)
            timeToWaitForAnotherStep = stepResult["wait_length"]

            shouldWaitMore = stepResult["heading"].count("Hold your horses!") > 0
            if shouldWaitMore:
                return timeToWaitForAnotherStep

            stepHeadlineMessage = stepResult["heading"]
            stepMessage = stepResult["text"]

            isUserDead = stepHeadlineMessage == "You're dead."
            if isUserDead:
                raise self.UserNoHealth("Can't fight without HP!")

            isUserCurrentlyOnAJob = stepMessage == "You cannot travel while you are working!"
            if isUserCurrentlyOnAJob:
                class UserOnJob(Exception): pass
                raise UserOnJob("User is on a job!")

            stepType = self.getStepType(stepResult["step_type"])
            
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

            shouldHumanizeStepping = self.stepCount % randint(8, 16)
            if shouldHumanizeStepping:
                time.sleep(uniform(1.4, 4.2))

            return timeToWaitForAnotherStep
    
    def startVerification(self):
        if self.runMode != 3:
            self.verifyCallback()

    def doQuests(self) -> int:
        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.webHost,
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "TE": "trailers",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-User": "?1",
            "User-Agent": self.auth.userAgent
        }
        
        response = self.auth.get(
            url = self.ENDPOINTS["quests"],
            headers = humanizedHeaders
        )

        questActionLink = self.parseHighestAvailableQuest(questResponse = response.text)
        currentEnergy, highestEnergy = self.parseEnergyPoints(response = response.text)

        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.webHost,
            "Pragma": "no-cache",
            "Referer": self.ENDPOINTS["quests"],
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-User": "?1",
            "User-Agent": self.auth.userAgent
        }

        questActionLinkResponse = self.auth.get(
            url = questActionLink,
            headers = humanizedHeaders
        )

        questApiLink = self.WEB_ENDPOINT + "/api/quest/" + getStringInBetween(
            string = questActionLinkResponse.text,
            delimiter1 = "fetch('/api/quest/",
            delimiter2 = "'"
        )
        
        isUserOutOfEnergy = currentEnergy == 0
        if isUserOutOfEnergy:
            return randint(4000, 5000) # Random milliseconds

        print(f"[QUEST] Energy: {currentEnergy}/{highestEnergy}")
        while currentEnergy > 0:
            humanizedHeaders = {
                "Accept": "*/*",
                "Host": self.webHost,
                "Pragma": "no-cache",
                "Origin": self.WEB_ENDPOINT,
                "Referer": questActionLink,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "TE": "trailers",
                "User-Agent": self.auth.userAgent
            }

            x, y = self.humanizeMouseClick()
            humanizedData = {
                "api_token": self.auth.API_TOKEN,
                "x": x,
                "y": y,
                "s": 0
            }

            try:
                questResponse = self.auth.post(
                    url = questApiLink,
                    headers = humanizedHeaders,
                    data = humanizedData
                )

                shouldVerify = questResponse.text.count("Press here to verify") > 0
                if shouldVerify:
                    self.startVerification()
                    continue

                questResponseOnJson = json.loads(questResponse.text)
                isUserOutOfEnergy = questResponseOnJson["resultText"] == "You have no more quest points."
                if isUserOutOfEnergy:
                    break

                isUserFailed = questResponseOnJson["fail"] == True
                status = questResponseOnJson["status"]
                result = questResponseOnJson["resultText"]
                if isUserFailed:
                    print(f"> Failed Quest Point #{currentEnergy}/{highestEnergy}: {result}")
                else:
                    goldEarned = questResponseOnJson["gold"]
                    expEarned = questResponseOnJson["exp"]
                    print(f"> Quest Point #{currentEnergy}/{highestEnergy}: {status} -> {goldEarned} gold and {expEarned} exp")

                currentEnergy = questResponseOnJson["quest_points"]
                time.sleep(randint(3, 6))
            except:
                print("> Error quest! ====> " + questResponse.text)
                currentEnergy -= 1

        return randint(4000, 5000) # Random milliseconds
    
    def doArena(self) -> int:
        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.webHost,
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Referer": self.ENDPOINTS["travel"],
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "TE": "trailers",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-User": "?1",
            "User-Agent": self.auth.userAgent
        }
        
        response = self.auth.get(
            url = self.ENDPOINTS["arenaMenu"],
            headers = humanizedHeaders
        )
        
        currentEnergy, highestEnergy = self.parseEnergyPoints(response = response.text)
        
        isUserOutOfEnergy = currentEnergy == 0
        if isUserOutOfEnergy:
            return randint(4000, 5000) # Random milliseconds
        
        print(f"[ARENA] Energy: {currentEnergy}/{highestEnergy}")
        while currentEnergy > 0:
            npcInfo = self.generateNpc()
            if not npcInfo:
                raise Exception("Cannot generate NPC!")
            
            npcId = npcInfo["id"]
            npcName = npcInfo["name"]
            level = npcInfo["level"]
            print(f"> Fighting: {npcName} (lv. {level}) at Energy #{currentEnergy}/{highestEnergy}...")
            self.attackNpc(
                actionLink = "https://web.simple-mmo.com/npcs/attack/" + str(npcId),
                isUserTravelling = False
            )
            currentEnergy -= 1
            time.sleep(randint(3, 6))
        
        return randint(4000, 5000) # Random milliseconds
    
    def upgradeSkill(self, skillToUpgrade: SkillType = SkillType.Dexterity):
        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.webHost,
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Referer": self.ENDPOINTS["travel"],
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "TE": "trailers",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-User": "?1",
            "User-Agent": self.auth.userAgent
        }
        

        response = self.auth.get(
            url = self.ENDPOINTS["character"],
            headers = humanizedHeaders
        )

        remainingSkillPoints = self.parseRemainingSkillPoints(response = response.text)

        isRemainingSkillPointsEmpty = remainingSkillPoints == "0" or remainingSkillPoints == "undefined" 
        if isRemainingSkillPointsEmpty:
            return

        print(f"[SKILL UPGRADE] {remainingSkillPoints} SP remaining")

        data = {
            "_token": self.auth.CSRF_TOKEN,
            "amount": remainingSkillPoints
        }

        if skillToUpgrade == self.SkillType.Strength:
            skill = "str"
        elif skillToUpgrade == self.SkillType.Defense:
            skill = "def"
        else:
            skill = "dex"
        
        skillUpgradeResponse = self.auth.post(
            url = self.WEB_ENDPOINT + "/api/user/upgrade/" + skill,
            data = data,
            headers = {
                "User-Agent": self.auth.userAgent
            }
        )

        skillUpgradeResponseInJson = json.loads(skillUpgradeResponse.text)

        isSuccess = skillUpgradeResponseInJson["type"] == "success"
        if isSuccess:
            print(f"> Skill {skill.upper()} is upgraded by {remainingSkillPoints}!")
            return
        
        print(skillUpgradeResponseInJson)
        raise Exception(f"Cannot upgrade skill {skill}")
    
    def parseRemainingSkillPoints(self, response: str) -> str:
        return getStringInBetween(
            string = response,
            delimiter1 = 'id="available_points">',
            delimiter2 = '</span>'
        )

    def generateNpc(self):
        humanizedHeaders = {
            "Accept": "*/*",
            "Host": self.apiHost,
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Origin": self.WEB_ENDPOINT,
            "Referer": self.ENDPOINTS["arena"],
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": self.auth.userAgent
        }

        data = {
            "api_token": self.auth.API_TOKEN
        }

        response = self.auth.post(
            url = self.ENDPOINTS["generateNpc"],
            headers = humanizedHeaders,
            data = data
        )

        try:
            jsonResponse = json.loads(response.text)

            jsonResponse["id"]
            jsonResponse["name"]
            return jsonResponse
        except:
            isUserOutOfEnergy = jsonResponse["result"] == "You do not have enough energy to do this."
            if isUserOutOfEnergy:
                return []

            print(jsonResponse)
            raise Exception("Error generating NPC")

    def parseHighestAvailableQuest(self, questResponse: str) -> str:
        highestAvailableQuestActionLink = self.WEB_ENDPOINT + getStringInBetween(
            string = questResponse,
            delimiter1 = "onclick=\"if (!window.__cfRLUnblockHandlers) return false; window.location='",
            delimiter2 = "'"
        )

        return highestAvailableQuestActionLink

    def parseEnergyPoints(self, response: str) -> list[int]:
        result = getStringInBetween(
            string = response,
            delimiter1 = 'id="questPoints">',
            delimiter2 = "</div>"
        ).split("</span>/")
        return [eval(i) for i in result]

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

    def attackNpc(self, actionLink: str, isUserTravelling: bool = True):
        class CannotAttackNpc(Exception): pass
        
        referer = self.ENDPOINTS["travel"] if isUserTravelling else self.ENDPOINTS["arena"]
        isOpponentDefeated = False
        try:
            humanizedHeaders = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Host": self.webHost,
                "Pragma": "no-cache",
                "Referer": referer,
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "TE": "trailers",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-User": "?1",
                "User-Agent": self.auth.userAgent
            }

            response = self.auth.get(
                url = actionLink,
                headers = humanizedHeaders
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
                    humanizedHeaders = {
                        "Accept": "*/*",
                        "Host": self.apiHost,
                        "Pragma": "no-cache",
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                        "Origin": self.WEB_ENDPOINT,
                        "Referer": actionLink,
                        "Connection": "keep-alive",
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-site",
                        "TE": "trailers",
                        "User-Agent": self.auth.userAgent
                    }

                    humanizedData = {
                        "_token": self.auth.CSRF_TOKEN,
                        "api_token": self.auth.API_TOKEN,
                        "special_attack": "false"
                    }

                    battleResults = self.auth.post(
                        url = attackApiEndpoint,
                        data = humanizedData,
                        headers = humanizedHeaders
                    )

                    battleResults = json.loads(battleResults.text)
                except:
                    raise CannotAttackNpc()
                else:
                    isOpponentDefeated = battleResults["opponent_hp"] == 0
                    isUserDefeated = battleResults["player_hp"] == 0

                    if isUserDefeated:
                        raise self.UserNoHealth("Can't fight without HP!")

                    if isOpponentDefeated:
                        battleRewards = battleResults["result"]
                        battleMessage = self.parseBattleRewards(battleRewards).strip()
                        
                        shouldVerify = battleMessage.count("verify") > 0
                        if shouldVerify:
                            print(f"> ALERT: Perform Verification")
                            isOpponentDefeated = False
                            self.startVerification()
                            continue
                        
                        print(f"> You've won! Rewards: {battleMessage}")
                    
                    humanizedSeconds = randint(1, 5)
                    time.sleep(humanizedSeconds)

    def obtainMaterials(self, actionLink: str):
        class CannotObtainMaterials(Exception): pass
        
        isMaterialDoneGathering = False
        try:
            humanizedHeaders = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Host": self.webHost,
                "Pragma": "no-cache",
                "Referer": self.WEB_ENDPOINT + "/travel",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "TE": "trailers",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-User": "?1",
                "User-Agent": self.auth.userAgent
            }

            response = self.auth.get(
                url = actionLink,
                headers = humanizedHeaders
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
                    humanizedHeaders = {
                        "Accept": "application/json",
                        "Host": self.webHost,
                        "Pragma": "no-cache",
                        "Content-Type": "application/json",
                        "Origin": self.WEB_ENDPOINT,
                        "Referer": actionLink,
                        "Connection": "keep-alive",
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-origin",
                        "TE": "trailers",
                        "User-Agent": self.auth.userAgent
                    }

                    humanizedData = {"_token": self.auth.CSRF_TOKEN}
                    gatherResults = self.auth.post(
                        url = gatherApiEndpoint,
                        data = humanizedData,
                        headers = humanizedHeaders
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

    def getTimeInSeconds(self) -> int:
        return round(time.time())

    def resetEnergyTimer(self):
        self.energyTimer = self.getTimeInSeconds() + 350 # Add 5.5 minutes