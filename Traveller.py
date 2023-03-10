from Authenticator import Authenticator
from random import randint, uniform
from Utils import *
import time
import json
import enum
import time
import typing
import base64

class User:
    auth: Authenticator = None
    
    userName: str = None
    userId: str = None
    guildId: str = None
    userLevel: int = 0
    totalSteps: int = 0
    stepCount: int = -1 # daily steps
    
    energyTimer: int = 0
    maxQuestPoints: int = 0
    currentQuestPoints: int = 0
    maxEnergy: int = 0
    currentEnergy: int = 0

    def getUser(self):
        if self.userId == None:
            self.getUserInfo()
            print(f"[USER] {self.userName} ({self.userId}) : Level {self.userLevel}")
            
        if self.guildId == None:
            self.getGuildId()
            print(f"[GUILD ID] {self.guildId}")

        if self.stepCount == -1:
            self.getDailyStepCount()
            print(f"[STEPS] Today: {self.stepCount} | Overall: {self.totalSteps}") 
    
    def getUserInfo(self):
        humanizedHeaders = {
            "Accept": "*/*",
            "Host": self.auth.apiHost,
            "Origin": self.auth.WEB_ENDPOINT,
            "Referer": self.auth.ENDPOINTS["home"],
            "x-requested-with": self.auth.packageName,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Connection": "keep-alive",
            "User-Agent": self.auth.userAgent["webView"]
        }
        
        humanizedData = { "api_token": self.auth.API_TOKEN }
        
        response = self.auth.post(
            url = self.auth.ENDPOINTS["popup"],
            headers = humanizedHeaders,
            data = humanizedData
        )

        try:
            jsonResponse = json.loads(response.text)
            self.userId = str(jsonResponse["id"])
            self.userName = jsonResponse["username"]
            self.userLevel = int(jsonResponse["level"])
            self.totalSteps = int(jsonResponse["total_steps"].replace(",", ""))
            return jsonResponse
        except:
            print(response.text)
            class CannotFindUserId(Exception): pass
            raise CannotFindUserId("No UID Found!")

    def getQuestAndEnergyPoints(self):
        otherInfos = self.getUserInfo()

        self.currentQuestPoints = int(otherInfos["quest_points"])
        self.maxQuestPoints = int(otherInfos["max_quest_points"])
        self.currentEnergy = int(otherInfos["energy"])
        self.maxEnergy = int(otherInfos["max_energy"])

    def getGuildId(self):
        if self.userLevel < 10:
            self.guildId = None
            return

        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.auth.webHost,
            "Referer": self.auth.ENDPOINTS["character"],
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
            "x-requested-with": self.auth.packageName,
            "Sec-Fetch-User": "?1",
            "User-Agent": self.auth.userAgent["webView"]
        }
        
        response = self.auth.get(
            url = self.auth.WEB_ENDPOINT + "/user/view/" + self.userId,
            headers = humanizedHeaders
        )

        try:
            self.guildId = getStringInBetween(response.text, "/guilds/view/", '&')
        except:
            isUserGuildless = response.text.count("/guilds/view/") <= 0
            if isUserGuildless:
                return
            
            class CannotFindGuildId(Exception): pass
            raise CannotFindGuildId("No Guild ID Found!")

    def getDailyStepCount(self):
        isUserGuildless = self.guildId == None
        if self.userLevel < 10 or isUserGuildless:
            self.stepCount = 0
            return
        
        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.auth.webHost,
            "Referer": self.auth.WEB_ENDPOINT + f"/leaderboards?guild={self.guildId}&new_page=true",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
            "x-requested-with": self.auth.packageName,
            "x-simplemmo-token": self.auth.API_TOKEN,
            "Sec-Fetch-User": "?1",
            "User-Agent": self.auth.userAgent["webView"]
        }
        
        response = self.auth.get(
            url = self.auth.WEB_ENDPOINT + f"/leaderboards/view/steps/daily?guild={self.guildId}&tier=all",
            headers = humanizedHeaders
        )

        try:
            extracted = getStringInBetween(response.text, f"/user/view/{self.userId}'>", " steps")
            extracted = getStringInBetween(extracted + " steps", "whitespace-nowrap\">", " steps")
            self.stepCount = int(removeHtmlTags(extracted.replace(",", "")))
        except:
            self.stepCount = 0

class Traveller(User):
    equippableItemsStack = []

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
    
    class RarityType(enum.Enum):
        Common = 1
        Uncommon = 2
        Rare = 3
        Elite = 4
        Epic = 5
        Legendary = 6
        Celestial = 7
        Exotic = 8

    class UserNoHealth(Exception): pass

    def __init__(
        self, 
        verifyCallback: typing.Callable[[], None] = None, 
        isRunningWithTelegram: bool = True,
        shouldAutoEquipItems: bool = True,
        shouldAttackNPCs: bool = True
    ) -> None:
        self.isRunningWithTelegram = isRunningWithTelegram
        self.shouldAttackNPCs = shouldAttackNPCs
        self.shouldAutoEquipItems = shouldAutoEquipItems
        self.verifyCallback = verifyCallback

    def takeStep(self):
        x, y = self.humanizeMouseClick()

        humanizedHeaders = {
            "Accept": "*/*",
            "Host": self.auth.apiHost,
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": self.auth.WEB_ENDPOINT,
            "Referer": self.auth.ENDPOINTS["travel"],
            "x-requested-with": self.auth.packageName,
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": self.auth.userAgent["webView"]
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
            url = self.auth.ENDPOINTS["step"],
            data = humanizedData,
            headers = humanizedHeaders
        )

        try:
            shouldPerformVerification = response.text.count("Perform Verification") > 0 or response.text.count("I'm not a pesky machine") > 0
            if shouldPerformVerification:
                self.stepCount += 1
                print(f"[STEP #{self.stepCount}] ALERT: Perform Verification!")
                
                if not self.isRunningWithTelegram:
                    input("> Please verify asap and press enter here to continue travelling...")
                    return 0
                
                self.startVerification()
                return 0
            
            isUserOnNewLocation = response.text.count("You have reached") > 0
            if isUserOnNewLocation:
                self.stepCount += 1
                print(f"[STEP #{self.stepCount}] Reached new location!")
                return 0
            
            stepResult = json.loads(response.text)
            timeToWaitForAnotherStep = stepResult["wait_length"]

            shouldWaitMore = response.text.count("Hold your horses!") > 0 or response.text.count("gPlayReview();") > 0
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
            didUserLevelledUp = self.userLevel > 0 and currentLevel > self.userLevel
            if didUserLevelledUp:
                print(f"=======!! [LEVEL UP -> {currentLevel}] !!=======")
            
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
                print(f"[STEP #{self.stepCount}] You've found (Material): {stepHeadlineMessage} [{materialLevelAndRarity}]")

                canBeGathered = stepMessage.count("Your skill level isn't high enough") < 1
                
                if canBeGathered:
                    self.obtainMaterials(actionLink = nextAction)

            elif stepType == self.StepTypes.Item:
                itemName, itemId = self.parseItemFound(stepMessage)
                self.equippableItemsStack.append(itemId)
                
                print(f"[STEP #{self.stepCount}] You've found (Item): {itemName}")

                print("> Checking if there's previous items found...")
                for id in reversed(self.equippableItemsStack):
                    if self.shouldAutoEquipItems and self.shouldEquipItem(itemId = id):
                        self.equipItem(itemId = id)
                
            elif stepType == self.StepTypes.Text:
                print(f"[STEP #{self.stepCount}] {stepHeadlineMessage}")
                
            elif stepType == self.StepTypes.Npc:
                npcLevel, nextAction = self.parseNpcFound(npcDetails = stepMessage)
                print(f"[STEP #{self.stepCount}] You've encountered (NPC): {stepHeadlineMessage} [{npcLevel}]")
                if self.shouldAttackNPCs:
                    self.attackNpc(actionLink = nextAction)
                
            elif stepType == self.StepTypes.Player:
                print(f"[STEP #{self.stepCount}] You've encountered (Player): {stepHeadlineMessage}")
            
            print(f"> Step Rewards [gold/exp]: {goldEarned}/{expEarned} | Current [gold/exp/level]: {currentGold}/{currentExp}/{currentLevel}")

            shouldHumanizeStepping = self.stepCount % randint(8, 16)
            if shouldHumanizeStepping:
                timeToWaitForAnotherStep += randint(1000, 3000)

            return timeToWaitForAnotherStep
    
    def startVerification(self):
        if self.isRunningWithTelegram:
            self.verifyCallback()

    def doQuests(self) -> int:
        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.auth.webHost,
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "x-requested-with": self.auth.packageName,
            "x-simplemmo-token": self.auth.API_TOKEN,
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-User": "?1",
            "User-Agent": self.auth.userAgent["webView"]
        }
        
        response = self.auth.get(
            url = self.auth.ENDPOINTS["quests"],
            headers = humanizedHeaders
        )

        questActionLink = self.parseHighestAvailableQuest(questResponse = response.text)
        self.getQuestAndEnergyPoints()

        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.auth.webHost,
            "Referer": self.auth.ENDPOINTS["quests"],
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
            "x-requested-with": self.auth.packageName,
            "Sec-Fetch-User": "?1",
            "User-Agent": self.auth.userAgent["webView"]
        }

        questActionLinkResponse = self.auth.get(
            url = questActionLink,
            headers = humanizedHeaders
        )

        questApiLink = self.auth.WEB_ENDPOINT + "/api/quest/" + getStringInBetween(
            string = questActionLinkResponse.text,
            delimiter1 = "fetch('/api/quest/",
            delimiter2 = "'"
        )
        
        isUserOutOfEnergy = self.currentQuestPoints == 0
        if isUserOutOfEnergy:
            return randint(4000, 5000) # Random milliseconds

        print(f"[QUEST] Energy: {self.currentQuestPoints}/{self.maxQuestPoints}")
        while self.currentQuestPoints > 0:
            humanizedHeaders = {
                "Accept": "*/*",
                "Host": self.auth.webHost,
                "Origin": self.auth.WEB_ENDPOINT,
                "Referer": questActionLink,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "x-requested-with": self.auth.packageName,
                "User-Agent": self.auth.userAgent["webView"]
            }

            x, y = self.humanizeMouseClick()
            humanizedData = {
                "api_token": self.auth.API_TOKEN,
                "x": x,
                "y": y,
                "s": 0
            }

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
                print(f"> Failed Quest Point #{self.currentQuestPoints}/{self.maxQuestPoints}: {result}")
            else:
                goldEarned = questResponseOnJson["gold"]
                expEarned = questResponseOnJson["exp"]
                print(f"> Quest Point #{self.currentQuestPoints}/{self.maxQuestPoints}: {status} -> {goldEarned} gold and {expEarned} exp")

            self.currentQuestPoints = questResponseOnJson["quest_points"]
            humanizedSeconds = uniform(2.0, 4.0)
            time.sleep(humanizedSeconds)

        return randint(4000, 5000) # Random milliseconds
    
    def doArena(self) -> int:
        if not self.shouldAttackNPCs:
            return randint(4000, 5000)
        
        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.auth.webHost,
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "x-requested-with": self.auth.packageName,
            "x-simplemmo-token": self.auth.API_TOKEN,
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-User": "?1",
            "User-Agent": self.auth.userAgent["webView"]
        }
        
        self.auth.get(
            url = self.auth.ENDPOINTS["arenaMenu"],
            headers = humanizedHeaders
        )

        self.getQuestAndEnergyPoints()

        isUserOutOfEnergy = self.currentEnergy == 0
        if isUserOutOfEnergy:
            return randint(800, 1500) # Random milliseconds
        
        print(f"[ARENA] Energy: {self.currentEnergy}/{self.maxEnergy}")
        while self.currentEnergy > 0:
            npcInfo = self.generateNpc()
            if not npcInfo:
                raise Exception("Cannot generate NPC!")
            
            npcId = npcInfo["id"]
            npcName = npcInfo["name"]
            level = npcInfo["level"]
            print(f"> Fighting: {npcName} (lv. {level}) at Energy #{self.currentEnergy}/{self.maxEnergy}...")
            self.attackNpc(
                actionLink = "https://web.simple-mmo.com/npcs/attack/" + str(npcId),
                isUserTravelling = False
            )
            self.currentEnergy -= 1
            humanizedSeconds = uniform(2.0, 3.5)
            time.sleep(humanizedSeconds)
        
        return randint(800, 1500) # Random milliseconds
    
    def upgradeSkill(self, skillToUpgrade: SkillType = SkillType.Dexterity):
        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.auth.webHost,
            "Connection": "keep-alive",
            "Referer": self.auth.ENDPOINTS["travel"],
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "x-requested-with": self.auth.packageName,
            "x-simplemmo-token": self.auth.API_TOKEN,
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-User": "?1",
            "User-Agent": self.auth.userAgent["webView"]
        }
        
        response = self.auth.get(
            url = self.auth.ENDPOINTS["character"],
            headers = humanizedHeaders
        )
        
        isRemainingSkillPointsEmpty = response.text.count("available_points") > 1
        if not isRemainingSkillPointsEmpty:
            time.sleep(randint(1, 3))
            return

        remainingSkillPoints = self.parseRemainingSkillPoints(response = response.text)

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
            url = self.auth.WEB_ENDPOINT + "/api/user/upgrade/" + skill,
            data = data,
            headers = {
                "User-Agent": self.auth.userAgent["webView"],
                "x-requested-with": self.auth.packageName
            }
        )

        skillUpgradeResponseInJson = json.loads(skillUpgradeResponse.text)

        isSuccess = skillUpgradeResponseInJson["type"] == "success"
        if isSuccess:
            print(f"> Skill {skill.upper()} is upgraded by {remainingSkillPoints}!")
            time.sleep(randint(1, 3))
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
            "Host": self.auth.apiHost,
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Connection": "keep-alive",
            "Origin": self.auth.WEB_ENDPOINT,
            "Referer": self.auth.ENDPOINTS["arena"],
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "x-requested-with": self.auth.packageName,
            "User-Agent": self.auth.userAgent["webView"]
        }

        data = {
            "api_token": self.auth.API_TOKEN
        }

        response = self.auth.post(
            url = self.auth.ENDPOINTS["generateNpc"],
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
        highestAvailableQuestActionLink = self.auth.WEB_ENDPOINT + "/quests/view/" + getStringInBetween(
            string = questResponse,
            delimiter1 = "if (!window.__cfRLUnblockHandlers) return false; window.location='/quests/view/",
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

    def parseMaterialFound(self, materialDetails: str) -> tuple[str, str]:
        try:
            materialLevelAndRarity = removeHtmlTags(
                rawHtml = getStringInBetween(
                    string = materialDetails,
                    delimiter1 = "<br/>",
                    delimiter2 = "</span>"
                )
            ).strip()

            actionLink = self.auth.WEB_ENDPOINT + getStringInBetween(
                string = materialDetails,
                delimiter1 = "document.location='",
                delimiter2 = "'"
            )

            return (materialLevelAndRarity, actionLink)
        except:
            class InvalidMaterial(Exception): pass
            raise InvalidMaterial("Can't parse material!")
    
    def parseItemFound(self, itemDetails: str, isFromNpc: bool = False) -> tuple[str, str]:
        try:
            if isFromNpc:
                itemId = getStringInBetween(itemDetails, "retrieveItem(", ")")
                return ("", itemId)
            
            itemName = removeHtmlTags(itemDetails).strip()
            itemId = getStringInBetween(itemDetails, "retrieveItem(", ",")
            return (itemName, itemId)
        except:
            class InvalidItem(Exception): pass
            raise InvalidItem("Can't parse item!")

    def parseNpcFound(self, npcDetails: str) -> tuple[str, str]:
        try:
            npcLevel = "Level " + removeHtmlTags(
                rawHtml = getStringInBetween(
                    string = npcDetails,
                    delimiter1 = "Level ",
                    delimiter2 = "<"
                )
            )

            actionLink = self.auth.WEB_ENDPOINT + getStringInBetween(
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
        
        referer = self.auth.ENDPOINTS["travel"] if isUserTravelling else self.auth.ENDPOINTS["arena"]
        isOpponentDefeated = False
        try:
            humanizedHeaders = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Host": self.auth.webHost,
                "Referer": referer,
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Upgrade-Insecure-Requests": "1",
                "x-requested-with": self.auth.packageName,
                "Sec-Fetch-User": "?1",
                "User-Agent": self.auth.userAgent["webView"]
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
                        "Host": self.auth.apiHost,
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                        "Origin": self.auth.WEB_ENDPOINT,
                        "Referer": actionLink,
                        "Connection": "keep-alive",
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-site",
                        "x-requested-with": self.auth.packageName,
                        "User-Agent": self.auth.userAgent["webView"]
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

                        isItemAReward = battleRewards.count("retrieveItem") > 0
                        if isItemAReward:
                            _, itemId = self.parseItemFound(battleRewards, isFromNpc = True)
                            self.equippableItemsStack.append(itemId)

                            print("> Checking if there's previous items found...")
                            for id in reversed(self.equippableItemsStack):
                                if self.shouldAutoEquipItems and self.shouldEquipItem(itemId = id):
                                    self.equipItem(itemId = id)
                    
                    humanizedSeconds = uniform(2.0, 4.0)
                    time.sleep(humanizedSeconds)

    def obtainMaterials(self, actionLink: str):
        class CannotObtainMaterials(Exception): pass
        
        isMaterialDoneGathering = False
        try:
            humanizedHeaders = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Host": self.auth.webHost,
                "Referer": self.auth.ENDPOINTS["travel"],
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Upgrade-Insecure-Requests": "1",
                "x-requested-with": self.auth.packageName,
                "Sec-Fetch-User": "?1",
                "User-Agent": self.auth.userAgent["webView"]
            }

            response = self.auth.get(
                url = actionLink,
                headers = humanizedHeaders
            )
            
            gatherApiEndpoint = self.auth.WEB_ENDPOINT + "/api/crafting/material/gather/" + getStringInBetween(
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
                        "Host": self.auth.webHost,
                        "Content-Type": "application/json",
                        "Origin": self.auth.WEB_ENDPOINT,
                        "Referer": actionLink,
                        "Connection": "keep-alive",
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-origin",
                        "User-Agent": self.auth.userAgent["webView"]
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
                        
                    humanizedSeconds = uniform(1.0, 2.5)
                    time.sleep(humanizedSeconds)

    def equipItem(self, itemId: str):
        humanizedHeaders = {
            "Accept": "*/*",
            "Host": self.auth.webHost,
            "Origin": self.auth.WEB_ENDPOINT,
            "Referer": self.auth.ENDPOINTS["travel"],
            "x-requested-with": self.auth.packageName,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Connection": "keep-alive",
            "User-Agent": self.auth.userAgent["webView"]
        }

        itemEquippedResponse = self.auth.get(
            url = f"{self.auth.ENDPOINTS['itemEquip']}/{itemId}?api=true",
            headers = humanizedHeaders
        )

        isItemEquipped = itemEquippedResponse.status_code == 200

        if not isItemEquipped:
            class CannotEquipItem(Exception): pass
            raise CannotEquipItem(f"Failed to equip item: {itemId}")
        
        print(f"> Item [{itemId}] has been equipped!")

    def shouldEquipItem(self, itemId: str):
        humanizedHeaders = {
            "Accept": "*/*",
            "Host": self.auth.webHost,
            "Origin": self.auth.WEB_ENDPOINT,
            "Referer": self.auth.ENDPOINTS["travel"],
            "x-requested-with": self.auth.packageName,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Connection": "keep-alive",
            "User-Agent": self.auth.userAgent["webView"]
        }

        checkItemResponse = self.auth.post(
            url = f"{self.auth.ENDPOINTS['itemStats']}/{itemId}",
            headers = humanizedHeaders
        )

        checkItemResponseJson = json.loads(checkItemResponse.text)

        try:
            itemName = base64.b64decode(checkItemResponseJson["name"])
            itemLevel = checkItemResponseJson["level"]
            itemRarity = self.getRarityType(checkItemResponseJson["rarity"])
            itemType = checkItemResponseJson["type"]

            isItemCelestialOrExotic = itemRarity.value >= self.RarityType.Celestial.value
            isItemEpicOrAbove = itemRarity.value >= self.RarityType.Epic.value

            if isItemCelestialOrExotic:
                print(f"=======!! [FOUND A {itemRarity.name.upper()} -> {itemName} ({itemType})] !!=======")
            
            print(f"> Item Stats: {itemName} ({itemId}) [{itemType} Level {itemLevel} {itemRarity.name}]")

            isItemATool = self.isItemATool(itemType = itemType)
            isItemEquippable = checkItemResponseJson["equipable"] == 1
            isItemCurrentlyEquipped = checkItemResponseJson["currently_equipped"] == True
            isItemLevelGreaterThanUserLevel = itemLevel > self.userLevel
            isFoundItemWorse = checkItemResponseJson["stats_string"].count("caret-down") > 0
            
            if not isItemEquippable or isFoundItemWorse or isItemCurrentlyEquipped or isItemATool and not isItemEpicOrAbove:
                self.equippableItemsStack.remove(itemId)
                return False

            if isItemLevelGreaterThanUserLevel:
                return False
            
            if isItemATool and isItemEpicOrAbove:
                self.equippableItemsStack.remove(itemId)
                return True

            isEquipSlotEmpty = checkItemResponseJson["currently_equipped_string"] == ""
            isFoundItemBetter = checkItemResponseJson["stats_string"].count("caret-up") > 0
            if isFoundItemBetter or isEquipSlotEmpty:
                self.equippableItemsStack.remove(itemId)
                return True
            
        except:
            class CannotCheckItemStats(Exception): pass
            raise CannotCheckItemStats("Failed getting item stats!")

    def isItemATool(self, itemType: str) -> bool:
        try:
            validTools = [
                "Fishing Rod",
                "Wood Axe",
                "Pickaxe",
                "Shovel"
            ]
            validTools.index(itemType)
            return True
        except:
            return False

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

    def getRarityType(self, itemRarity: str) -> RarityType:
        if itemRarity == "Common":
            return self.RarityType.Common
        if itemRarity == "Uncommon":
            return self.RarityType.Uncommon
        if itemRarity == "Rare":
            return self.RarityType.Rare
        if itemRarity == "Elite":
            return self.RarityType.Elite
        if itemRarity == "Epic":
            return self.RarityType.Epic
        if itemRarity == "Legendary":
            return self.RarityType.Legendary
        if itemRarity == "Celestial":
            return self.RarityType.Celestial
        if itemRarity == "Exotic":
            return self.RarityType.Exotic

    def getTimeInSeconds(self) -> int:
        return round(time.time())

    def resetEnergyTimer(self):
        self.energyTimer = self.getTimeInSeconds() + randint(300, 1050) # Add 5.5 minutes