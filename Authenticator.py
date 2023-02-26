import requests
import requests.utils
import dotenv
import os
from http.cookies import SimpleCookie
from Utils import getStringInBetween, int2base
import random

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
    WEB_ENDPOINT = "https://web.simple-mmo.com"
    API_ENDPOINT = "https://api.simple-mmo.com"
    ENDPOINTS = {
        "session": WEB_ENDPOINT + "/api/session-hash",
        "quests": WEB_ENDPOINT + "/quests/viewall",
        "travel": WEB_ENDPOINT + "/travel",
        "arena": WEB_ENDPOINT + "/battle/arena",
        "arenaMenu": WEB_ENDPOINT + "/battle/menu",
        "generateNpc": API_ENDPOINT + "/api/battlearena/generate",
        "character": WEB_ENDPOINT + "/user/character",
        "verifyPage": WEB_ENDPOINT + "/i-am-not-a-bot?new_page=true",
        "verifyXHR": WEB_ENDPOINT + "/api/bot-verification",
        "verifyImages": WEB_ENDPOINT + "/i-am-not-a-bot/generate_image?uid="
    }
    userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0"
    webHost = "web.simple-mmo.com"
    apiHost = "api.simple-mmo.com"
    session: requests.Session = None

    CSRF_TOKEN: str = None
    API_TOKEN: str = None
    API_ENDPOINT: str = None
    COOKIE: dict = None

    def __init__(self) -> None:
        dotenv.load_dotenv()
        self.session = requests.Session()

        rawCookieData = os.getenv("cookie")
        self.COOKIE = self.parseCookieString(rawCookieData = rawCookieData)
    
    def getLoginCredentials(self) -> tuple[str, str, str]:
        self.generateNewSessionCookie()

        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.webHost,
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "User-Agent": self.userAgent
        }

        response = self.get(
            url = self.ENDPOINTS["travel"],
            headers = humanizedHeaders
        )

        self.CSRF_TOKEN = self.getCSRFToken(response.text)
        self.API_TOKEN = self.getApiToken(response.text)
        self.API_ENDPOINT = self.getTravelApiEndpoint(response.text)
    
    def generateNewSessionCookie(self) -> dict:
        self.session.cookies = requests.utils.cookiejar_from_dict(self.COOKIE)

        humanizedHeaders = {
            "Accept": "*/*",
            "Host": self.webHost,
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "Origin": self.WEB_ENDPOINT,
            "Referer": self.ENDPOINTS["travel"],
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "TE": "trailers",
            "User-Agent": self.userAgent
        }

        humanizedData = {
            "data": self.generateHash()
        }

        self.post(
            url = self.ENDPOINTS["session"],
            data = humanizedData,
            headers = humanizedHeaders
        )
    
    def post(self, url, data=None, headers=None) -> requests.Response:
        response = super().post(url, data, headers)
        try :
            self.COOKIE["XSRF-TOKEN"] = response.cookies["XSRF-TOKEN"]
            self.COOKIE["laravelsession"] = response.cookies["laravelsession"]

            newCookieInString = self.parseCookieDictionary(cookieData = self.COOKIE)
            self.saveCookie(newCookieInString)
        finally:
            return response
    
    def get(self, url, headers=None) -> requests.Response:
        response = super().get(url, headers)
        try :
            self.COOKIE["XSRF-TOKEN"] = response.cookies["XSRF-TOKEN"]
            self.COOKIE["laravelsession"] = response.cookies["laravelsession"]

            newCookieInString = self.parseCookieDictionary(cookieData = self.COOKIE)
            self.saveCookie(newCookieInString)
        finally:
            return response
        
    def generateHash(self) -> str:
        newHash = f"{random.random():.17f}"[2:]
        newHash = int2base(int(newHash), 20)

        isOver13 = len(newHash) > 13
        if isOver13:
            newHash = newHash[1:]
            
        return newHash.lower()

    def getCSRFToken(self, loginResponse: str):
        delimiter1 = '<meta name="csrf-token" content="'
        delimiter2 = '"'

        class InvalidCSRFToken(Exception): pass
        class BannedUser(Exception): pass

        isUserBanned = loginResponse.count("banned") > 0
        if isUserBanned:
            raise BannedUser(f"Banned for: {loginResponse}")

        try:
            return getStringInBetween(string=loginResponse, delimiter1=delimiter1, delimiter2=delimiter2)
        except:
            raise InvalidCSRFToken("Cannot find CSRF token!")
    
    def getApiToken(self, loginResponse: str):
        delimiter1 = "web_app=true&api_token="
        delimiter2 = "'"

        class InvalidAPIToken(Exception): pass

        try:
            return getStringInBetween(string=loginResponse, delimiter1=delimiter1, delimiter2=delimiter2)
        except:
            raise InvalidAPIToken("Cannot find API Token!")
    
    def getTravelApiEndpoint(self, loginResponse: str):
        delimiter1 = "api_end_point: 'https://api.simple-mmo.com/api/travel/perform/"
        delimiter2 = "'"

        class InvalidTravelApiEndpoint(Exception): pass

        try:
            return "https://api.simple-mmo.com/api/travel/perform/" + getStringInBetween(string=loginResponse, delimiter1=delimiter1, delimiter2=delimiter2)
        except:
            raise InvalidTravelApiEndpoint("Cannot find Travel API Endpoint!")