import requests
import json
from dotenv import load_dotenv
import os
from http.cookies import SimpleCookie
from Utils import getStringInBetween

class CookieParser:
    COOKIE = None

    def __init__(self) -> None:
        load_dotenv()

        rawCookieData = os.getenv("cookie")
        self.COOKIE = self.parseCookie(rawCookieData = rawCookieData)
    
    def parseCookie(self, rawCookieData: str) -> dict:
        cookieData = SimpleCookie()
        cookieData.load(rawCookieData)
        parsedCookie = {key: value.value  for key, value in cookieData.items()}
        return parsedCookie


class Authenticator(CookieParser):
    MAIN_WEB_ENDPOINT = "https://web.simple-mmo.com"
    WEB_ENDPOINTS = {
        "travel": MAIN_WEB_ENDPOINT + "/travel"
    }
    
    def getLoginCredentials(self):
        humanizedHeaders = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Host": "web.simple-mmo.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0"
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
    
    def getCSRFToken(self, loginResponse: str):
        delimiter1 = '<meta name="csrf-token" content="'
        delimiter2 = '"'

        class InvalidCSRFToken(Exception): pass

        try:
            return getStringInBetween(string=loginResponse, delimiter1=delimiter1, delimiter2=delimiter2)
        except:
            raise InvalidCSRFToken("Cannot find CSRF token!")
    
    def getApiToken(self, loginResponse: str):
        delimiter1 = "web_app=true&api_token="
        delimiter2 = "'"

        class InvalidAPIToken(Exception):
            pass

        try:
            return getStringInBetween(string=loginResponse, delimiter1=delimiter1, delimiter2=delimiter2)
        except:
            raise InvalidAPIToken("Cannot find API Token!")
    
    def getTravelApiEndpoint(self, loginResponse: str):
        delimiter1 = "api_end_point: 'https://api.simple-mmo.com/api/travel/perform/"
        delimiter2 = "'"

        class InvalidTravelApiEndpoint(Exception):
            pass

        try:
            return "https://api.simple-mmo.com/api/travel/perform/" + getStringInBetween(string=loginResponse, delimiter1=delimiter1, delimiter2=delimiter2)
        except:
            raise InvalidTravelApiEndpoint("Cannot find Travel API Endpoint!")
