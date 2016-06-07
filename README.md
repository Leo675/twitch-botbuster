# botbuster.py
Automated banning of twitch chat bots based on account creation date.

#Installation

Requires python. I know it will work with 3.5 and 3.4. I think some of the dictionary handling is incompatible with 2.7.
Tested on Windows, should work on *NIX environments too.

https://www.python.org/downloads/

Modules used: socket, time, re, requests, json

If some of these don't come standard in your python installation, they can be installed by opening cmd or terminal and typing:

```pip install requests json```

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

###punishment
This value sets if the bot bans or times users out. The value 'ban' will cause permanent bans, any other value will cause timeouts. 

#Usage

run botbuster.py

In your twitch channel you should see your bot user say 'Reporting for duty!'

###Commands
All commands are accessible to anyone in the channel that are moderators.

#####!blacklist <username>
This will automatically look up the creation date of a user and blacklist it. This is the recommended method so you don't have to worry about time zones. BTTV uses your local time zone and my bot just uses the GMT value twitch provides.

#####!startbans
This command will start the ban loops. It loops through each user in the room checking their creation date. It DOES make an http request to twitch's kraken API for EVERY user unless they have been banned or whitelisted. I will probably implement a cache dictionary of users already looked up in the near future. After finishing the loop, it pauses for 15 seconds.

#####!stopbans
This stops banning users and clears the blacklisted date list

#####!whitelist <username>
This command will prevent a user from being banned by the bot and also send the unban command for convenience. 

#####!bld YYYY-MM-DD
Blacklists a date manually. IMPORTANT: This date is in GMT. BTTV shows the date based on your LOCAL time zone.

#####!unlist YYYY-MM-DD
Manually unlists a blacklisted date
