import requests
import requests.utils
import dotenv
import os
import json
import random
from http.cookies import SimpleCookie
from Utils import getStringInBetween, int2base, generateRandomUserAgent

class CookieParser:
    def parseCookieString(self, rawCookieData: str) -> dict:
        cookieData = SimpleCookie()
        cookieData.load(rawCookieData)
        parsedCookie = {key: value.value  for key, value in cookieData.items()}
        return parsedCookie
    
    def parseCookieDictionary(self, cookieData: dict) -> str:
        return "; ".join([str(x)+"="+str(y) for x,y in cookieData.items()])
    
    def saveCookie(self, cookie: str):
        os.environ["cookie"] = cookie
        envFile = dotenv.find_dotenv()
        dotenv.set_key(envFile, "cookie", os.environ["cookie"])

class RequestWithSession:
    session: requests.Session = None

    def post(
        self,
        url,
        data = None,
        headers = None
    ) -> requests.Response:
        return self.session.post(
            url = url,
            data = data,
            headers = headers
        )
    
    def get(
        self,
        url,
        headers = None
    ) -> requests.Response:
        return self.session.get(
            url = url,
            headers = headers
        )

class Authenticator(CookieParser, RequestWithSession):
    WEB_ENDPOINT = "https://simple-mmo.com"
    API_ENDPOINT = "https://api.simple-mmo.com"
    ENDPOINTS = {
        "login": WEB_ENDPOINT + "/login",
        "home": WEB_ENDPOINT + "/home",
        "token": WEB_ENDPOINT + "/api/token",
        "session": WEB_ENDPOINT + "/api/session-hash",
        "quests": WEB_ENDPOINT + "/quests/viewall",
        "step": API_ENDPOINT + "/api/travel/perform/f4gl4l3k",
        "travel": WEB_ENDPOINT + "/travel",
        "arena": WEB_ENDPOINT + "/battle/arena",
        "arenaMenu": WEB_ENDPOINT + "/battle/menu",
        "generateNpc": API_ENDPOINT + "/api/battlearena/generate",
        "popup": API_ENDPOINT + "/api/popup",
        "character": WEB_ENDPOINT + "/user/character",
        "verifyPage": WEB_ENDPOINT + "/i-am-not-a-bot?new_page=true",
        "verifyXHR": WEB_ENDPOINT + "/api/bot-verification",
        "verifyImages": WEB_ENDPOINT + "/i-am-not-a-bot/generate_image?uid="
    }
    userAgent = {
        "webView": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
        "okHttp": "okhttp/4.2.1"
    }
    webHost = "simple-mmo.com"
    apiHost = "api.simple-mmo.com"
    packageName = "dawsn.simplemmo"

    session: requests.Session = None

    CSRF_TOKEN: str = None
    API_TOKEN: str = None
    API_ENDPOINT: str = None
    COOKIE: dict = {}

    def __init__(self) -> None:
        dotenv.load_dotenv()
        self.session = requests.Session()

        rawCookieData = os.getenv("cookie")
        isCookieEmpty = rawCookieData == ""
        if isCookieEmpty:
            self.login()
        else:
            self.COOKIE = self.parseCookieString(rawCookieData = rawCookieData)

    def post(self, url, data=None, headers=None) -> requests.Response:
        response = super().post(url, data, headers)
        try :
            self.COOKIE = requests.utils.dict_from_cookiejar(response.cookies)

            newCookieInString = self.parseCookieDictionary(cookieData = response.cookies)
            self.saveCookie(newCookieInString)
        finally:
            return response
    
    def get(self, url, headers=None) -> requests.Response:
        response = super().get(url, headers)
        try:
            self.COOKIE = requests.utils.dict_from_cookiejar(response.cookies)

            newCookieInString = self.parseCookieDictionary(cookieData = self.COOKIE)
            self.saveCookie(newCookieInString)
        finally:
            return response

    def login(self):
        self.getUserAgent()
        email = os.getenv("email")
        password = os.getenv("password")

        # Manipulate first request to obtain cookies
        self.session.get(
            url = self.ENDPOINTS["token"],
            headers = { "User-Agent": self.userAgent["okHttp"] }
        )

        self.generateCSRFToken(isLoggedIn = False)

        humanizedHeaders = {
            "Accept": "*/*",
            "Host": self.webHost,
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": self.WEB_ENDPOINT,
            "Referer": self.ENDPOINTS["login"],
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "x-requested-with": self.packageName,
            "User-Agent": self.userAgent["webView"]
        }

        humanizedData = {
            "_token": self.CSRF_TOKEN,
            "email": email,
            "password": password,
            "dark_mode": "false",
            "remember": "on"
        }

        response = self.post(
            url = self.ENDPOINTS["login"],
            headers = humanizedHeaders,
            data = humanizedData
        )

        isSuccessful = response.url == self.ENDPOINTS["home"]
        if not isSuccessful:
            print(response.text)
            raise Exception("Could not login!")

    def getLoginCredentials(self) -> tuple[str, str, str]:
        if not self.COOKIE:
            self.session.cookies = requests.utils.cookiejar_from_dict(self.COOKIE)

        self.getUserAgent()
        self.generateApiToken()
        self.generateNewSessionCookie()
        self.generateCSRFToken()
        # self.API_ENDPOINT = self.getTravelApiEndpoint(response.text)
    
    def getUserAgent(self):
        userAgent = os.getenv("user_agent")

        isUserAgentEmpty = userAgent == ""
        if isUserAgentEmpty:
            userAgent = generateRandomUserAgent()
            os.environ["user_agent"] = userAgent
            envFile = dotenv.find_dotenv()
            dotenv.set_key(envFile, "user_agent", userAgent)

        self.userAgent["webView"] = userAgent

    def generateNewSessionCookie(self) -> dict:
        humanizedHeaders = {
            "Accept": "*/*",
            "Host": self.webHost,
            "Content-Type": "application/json",
            "Origin": self.WEB_ENDPOINT,
            "Referer": self.ENDPOINTS["travel"],
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": self.userAgent["webView"]
        }

        humanizedData = {
            "data": self.generateHash()
        }

        self.post(
            url = self.ENDPOINTS["session"],
            data = humanizedData,
            headers = humanizedHeaders
        )
    
    def generateHash(self) -> str:
        newHash = f"{random.random():.17f}"[2:]
        newHash = int2base(int(newHash), 20)

        isOver13 = len(newHash) > 13
        if isOver13:
            newHash = newHash[1:]
            
        return newHash.lower()

    def generateCSRFToken(self, isLoggedIn: bool = True):
        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.webHost,
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "x-requested-with": self.packageName,
            "x-simplemmo-token": self.API_TOKEN,
            "User-Agent": self.userAgent["webView"]
        }

        if not isLoggedIn:
            response = self.session.get(
                url = self.ENDPOINTS["login"],
                headers = humanizedHeaders
            )
        else:
            response = self.get(
                url = self.ENDPOINTS["travel"],
                headers = humanizedHeaders
            )
        
        loginResponse = response.text

        delimiter1 = '<meta name="csrf-token" content="'
        delimiter2 = '"'

        class InvalidCSRFToken(Exception): pass
        class BannedUser(Exception): pass

        isUserBanned = loginResponse.count("banned") > 0
        if isUserBanned:
            raise BannedUser(f"Banned for: {loginResponse}")

        try:
            self.CSRF_TOKEN = getStringInBetween(string=loginResponse, delimiter1=delimiter1, delimiter2=delimiter2)
        except:
            raise InvalidCSRFToken("Cannot find CSRF token!")
    
    def generateApiToken(self):
        self.API_TOKEN = os.getenv("api_token")

        isApiTokenEmpty = self.API_TOKEN == ""
        if not isApiTokenEmpty:
            return

        humanizedHeaders = {
            "Host": self.webHost,
            "Connection": "keep-alive",
            "User-Agent": self.userAgent["okHttp"]
        }

        response = self.get(
            url = self.ENDPOINTS["token"],
            headers = humanizedHeaders
        )
        jsonResponse = json.loads(response.text)

        class InvalidAPIToken(Exception): pass

        try:
            self.API_TOKEN = jsonResponse["api_token"]

            os.environ["api_token"] = jsonResponse["api_token"]
            envFile = dotenv.find_dotenv()
            dotenv.set_key(envFile, "api_token", jsonResponse["api_token"])
        except:
            raise InvalidAPIToken("Cannot find API Token!")
    
    # def getTravelApiEndpoint(self, loginResponse: str):
    #     delimiter1 = "api_end_point: 'https://api.simple-mmo.com/api/travel/perform/"
    #     delimiter2 = "'"

    #     class InvalidTravelApiEndpoint(Exception): pass

    #     try:
    #         return "https://api.simple-mmo.com/api/travel/perform/" + getStringInBetween(string=loginResponse, delimiter1=delimiter1, delimiter2=delimiter2)
    #     except:
    #         raise InvalidTravelApiEndpoint("Cannot find Travel API Endpoint!")