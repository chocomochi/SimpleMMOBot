import requests
import dotenv
import os
from http.cookies import SimpleCookie
from Utils import getStringInBetween
import random
import numpy

class CookieParser:
    COOKIE = None

    def __init__(self) -> None:
        dotenv.load_dotenv()

        rawCookieData = os.getenv("cookie")
        self.COOKIE = self.parseCookieString(rawCookieData = rawCookieData)
    
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


class Authenticator(CookieParser):
    MAIN_WEB_ENDPOINT = "https://web.simple-mmo.com"
    WEB_ENDPOINTS = {
        "travel": MAIN_WEB_ENDPOINT + "/travel",
        "session": MAIN_WEB_ENDPOINT + "/api/session-hash"
    }
    userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0"
    host = "web.simple-mmo.com"
    
    def getLoginCredentials(self) -> tuple[str, str, str]:
        self.generateNewSessionCookie()

        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": self.host,
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "User-Agent": self.userAgent
        }

        response = requests.get(
            url = self.WEB_ENDPOINTS["travel"],
            cookies = self.COOKIE,
            headers = humanizedHeaders
        )

        csrfToken = self.getCSRFToken(response.text)
        apiToken = self.getApiToken(response.text)
        travelApiEndpoint = self.getTravelApiEndpoint(response.text)

        return (csrfToken, apiToken, travelApiEndpoint)
    
    def generateNewSessionCookie(self) -> dict:
        humanizedHeaders = {
            "Accept": "*/*",
            "Host": self.host,
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "Origin": self.MAIN_WEB_ENDPOINT,
            "Referer": self.WEB_ENDPOINTS["travel"],
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

        response = requests.post(
            url = self.WEB_ENDPOINTS["session"],
            cookies = self.COOKIE,
            data = humanizedData,
            headers = humanizedHeaders
        )

        newCookie = self.COOKIE
        newCookie["XSRF-TOKEN"] = response.cookies["XSRF-TOKEN"]
        newCookie["laravelsession"] = response.cookies["laravelsession"]

        newCookieInString = self.parseCookieDictionary(cookieData = newCookie)
        self.saveCookie(newCookieInString)

        self.COOKIE = newCookie
        return newCookie
        
    def generateHash(self) -> str:
        newHash = f"{random.random():.17f}"[2:]
        isOver13 = len(newHash) > 13
        if isOver13:
            newHash = newHash[1:]
        newHash = numpy.base_repr(int(newHash, 20))
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
