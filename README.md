# SimpleMMO Bot

An auto-traveller script with captcha verification using Telegram's API.

The script currently requires the user's cookie in order for it to run; the cookie can be obtainable from a web browser. Additionally, if you're using the script with telegram integrations, both **chat id** and **bot token** must be provided. All these essential requirements should be imported inside the **.env** file (see the .env template).

A type *(int)* must be provided in order for the script to run. The type serves as the modality of how the script would like to run itself.

Types | Description |
--- | --- |
1 | Windows w/ Telegram integration
2 | Android (via Termux) w/ Telegram intergration
3 | Just the plain script without any integrations (used on any environment/devices)

### Guide to installation 
* Download/clone this repository to your environment and install the requirements
```
pip install -r requirements.txt
```
* Run the script
```
python main.py --type 3
```

#
*This project serves as an educational tool **ONLY** and not meant to be abused by the players of the game*