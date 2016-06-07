# botbuster
Automated banning of twitch chat bots based on account creation date.

#Installation

Requires python. I know it will work with 3.5, probably will work with 3.4 too. Probably will work with 2.7 since I import the future print function in an attempt at compatability. Tested on windows, should work on *NIX environments too.
https://www.python.org/downloads/

Modules used: socket, time, re, requests, json

If these don't come standard in your python installation, they can be installed by opening cmd or terminal and typing:
pip install requests

Download the botbuster.py and open with a text editor to configure authentication and channel.

#Configuration

###chat_user 
Set this value to the twitch user name which your bot will use. You CAN use your channel user, but the bot will send messages as you.
This user needs to be a mod in the channel which it will be protecting.

###chat_pass
This is the oauth password for the above user. To obtain this, visist the following website while logged in as the above user:
http://www.twitchapps.com/tmi/

###chat_chan
This is the name of your channel on twitch that the bot will be joining. For example, mine is daytona_675.
