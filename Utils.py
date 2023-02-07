import re

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

