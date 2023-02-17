import re
import string

HTML_PATTERN = re.compile('<.*?>')

def removeHtmlTags(rawHtml: str) -> str:
    return re.sub(HTML_PATTERN, '', rawHtml)

def getStringInBetween(string: str, delimiter1: str, delimiter2: str) -> str:
    return string.split(delimiter1)[1].split(delimiter2)[0]

def millisecondsToSeconds(milliseconds: int) -> float:
    return milliseconds / 1000

def getMultipleStringsInBetween(string: str, delimiter1: str, delimiter2: str) -> list[str]:
    foundOccurences = string.split(delimiter1)

    results = []
    try:
        for occurence in foundOccurences:
            isFoundOccurenceUseless = occurence.count(delimiter2) == 0
            if isFoundOccurenceUseless:
                continue

            parsedOccurence = occurence.split(delimiter2)[0]
            results.append(parsedOccurence)
    finally:
        return results

def int2base(x: int, base: int) -> str:
    """
    Returns a string representation of a given number
    based on a given base system

    from: https://stackoverflow.com/a/2267446/19371763
    """
    digs = string.digits + string.ascii_letters

    if x < 0:
        sign = -1
    elif x == 0:
        return digs[0]
    else:
        sign = 1

    x *= sign
    digits = []

    while x:
        digits.append(digs[x % base])
        x = x // base

    if sign < 0:
        digits.append('-')

    digits.reverse()

    return ''.join(digits)

