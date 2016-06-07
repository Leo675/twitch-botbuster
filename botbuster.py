#! python3
# -*- coding: utf-8 -*-
# Author: daytona_675 aka IDSninja
# https://www.twitch.tv/daytona_675

from __future__ import print_function
import socket
import time
import re
import requests
import json

# The twitch user which will be acting as your bot
chat_user = ''

# The oauth password for the twitch user which will be operating
# Obtain this value by visiting this page while logged in
# as your bot user: http://www.twitchapps.com/tmi/
# example:
chat_pass = 'oauth:abcdefghijklmnopqrst123456789z'

# The channel the bot will be operating in (your channel's name)
chat_chan = 'daytona_675'

# punishment method; change to timeout (or any word other than ban)
# to make it timeout instead of ban
punishment = 'ban'

# Twitch IRC server info: the host and port should not need to be changed
chat_host = "irc.chat.twitch.tv"
chat_port = 6667

# List of commands which use regular expressions.
# Only change the left side and make sure to leave the ^
commands = {
    '^!startbans': 'start_banning',
    '^!blacklist': 'blacklist_user',
    '^!bld': 'blacklist_date',
    '^!unlist': 'unlist_date',
    '^!whitelist': 'whitelist_user',
    '^!stopbans': 'stop_banning',
    }

# initialize variables
banned_users = []
whitelisted_users = []
mitigation_active = False
banned_dates = []

# Initial IRC socket connection and authentication
s = socket.socket()
s.connect((chat_host, chat_port))
s.send("PASS {}\r\n".format(chat_pass).encode("utf-8"))
s.send("NICK {}\r\n".format(chat_user).encode("utf-8"))
s.send("CAP REQ :twitch.tv/membership\r\n".encode("utf-8"))
s.send("JOIN #{}\r\n".format(chat_chan).encode("utf-8"))


# Function for threaded asynchronous functions decorator @async
def async(func):
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        from threading import Thread
        f = Thread(target=func, args=args, kwargs=kwargs)
        f.start()
        return
    return async_func


# For sending messages to chat
def chat(sock, msg):
    sock.send(bytes('PRIVMSG #%s :%s\r\n' % (chat_chan, msg), 'UTF-8'))


# For permabanning users
def ban(sock, user):
    chat(sock, "/ban {}".format(user))


def unban(sock, user):
    chat(sock, "/unban {}".format(user))


# For timeout (seems to do 10 minutes)
def timeout(sock, user, secs=60):
    chat(sock, "/timeout {}".format(user, secs))


def get_chatters():
    # Loop ends when a value is returned
    global admin_list
    while 1:
        chatter_list = ()
        admins = ()
        # uses try because sometimes the connection times out
        try:
            url_fmt = 'https://tmi.twitch.tv/group/user/{}/chatters'
            r = requests.get(url_fmt.format(chat_chan))
        except:
            time.sleep(1)
            continue
        if r.status_code == 200:
            r = json.loads(r.text)

            # builds the list of chatters
            for chatter in r['chatters']['viewers']:
                chatter_list += (chatter,)

            # Dynamic moderators list, kinda hackish but if you unmod
            # someone they will be removed on the next loop
            for moderator in r['chatters']['moderators']:
                admins += (moderator,)
            admin_list = admins
            return chatter_list
        time.sleep(1)


# Function for returning the user's creation date
def creation_date(user):
    # Loop ends when a value is returned
    while 1:
        # Uses try in case of request timeout
        try:
            url_fmt = 'https://api.twitch.tv/kraken/users/{}'
            r = requests.get(url_fmt.format(user))
        except:
            time.sleep(1)
            continue
        if r.status_code == 200:
            # Captures only YYYY-MM-DD
            date = re.match(
                '([\d]{4}-[\d]{2}-[\d]{2})',
                json.loads(r.text)['created_at']
             )
            return date.group(1)


# Thread for watching and banning chatters
@async
def watch_chatters():
    global chatter_list

    def punish(chatter):
        if punishment == 'ban':
            ban(s, chatter)
            banned_users.append(chatter)
            print('Banning {}'.format(chatter))

        if punishment == 'timeout':
            timeout(s, chatter)
            print('TimingOut {}'.format(chatter))

    while 1:
        if mitigation_active:
            # Gets the list of chatters in the room
            chatter_list = get_chatters()
            for chatter in chatter_list:
                if chatter in whitelisted_users:
                    continue

                if chatter in banned_users:
                    continue

                if creation_date(chatter) in banned_dates:
                    punish(chatter)

                msg_fmt = 'Current number of banned users: {!s}'
                print(msg_fmt.format(len(banned_users)))
        time.sleep(15)


# Thread for reading chat and watching for user commands
@async
def read_chat():
    # Starts infinite loop listening to the IRC server
    while True:
        response = s.recv(1024).decode("utf-8")

        # PONG replies to keep the connection alive
        if response == "PING :tmi.twitch.tv\r\n":
            s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            continue

        # separates user and message.
        chat_object = re.search(r'^:(\w+)![^:]+:(.*)$', response)
        if chat_object:
            handle_chat(chat_object)


def handle_chat(chat_object):
    user = chat_object.group(1)
    msg = chat_object.group(2)
    global banned_dates, mitigation_active

    if user not in admin_list:
        return

    # Processes possible commands from the command dictionary
    for command, action in commands.items():
        if not re.search(command, msg):
            continue

        method = 'cmd_{}'.format(action)
        if callable(method):
            method(command, msg)


def cmd_blacklist_date(command, msg):
    """adds date to the banned list
    """
    input = re.search('^'+command+'\s+([\d]{4}-[\d]{2}-[\d]{2})', msg)
    if input:
        banned_dates.append(input.group(1))
    else:
        chat(s, 'Error: invalid format. Use !bld YYYY-MM-DD')


def cmd_unlist_date(command, msg):
    """Manual unlisting of a date, can also !stopbans to clear the list
    """
    input = re.search('^'+command+'\s+([\d]{4}-[\d]{2}-[\d]{2})', msg)
    if input:
        banned_dates.remove(input.group(1))
    else:
        chat(s, 'Error: invalid format. !unlist YYYY-MM-DD')


def cmd_blacklist_user(command, msg):
    """Automatic lookup of a user's creation date blacklisting it.
    """
    global banned_dates, mitigation_active
    target = re.search('^'+command+'\s*@?([\w\-]+)', msg)
    if target:
        # Makes sure the user is actually in
        # the room to prevent erroneous bans.
        if target.group(1).lower() in chatter_list:
            user_date = creation_date(target.group(1).lower())
            chat(s, 'Blacklisted: {}'.format(user_date))
            banned_dates.append(user_date)
        else:
            msg_fmt = 'User {} not found in the room. ' + \
                'Check spelling or try again in 15 seconds.'
            chat(s, msg_fmt.format(target.group(1)))


def cmd_stop_banning(command, msg):
    """Stops bans and clears blacklist
    """
    global mitigation_active, banned_dates
    mitigation_active = False
    banned_dates = []
    chat(s, 'Turning off chat mitigation.')


def cmd_start_banning(command, msg):
    """Starts banning users
    """
    global mitigation_active
    mitigation_active = True
    chat(s, 'Turning on chat mitigation ═══█❚')


def cmd_whitelist_user(command, msg):
    """unbans and prevents future banning of the user
    """
    target = re.search('^'+command+'\s*@?([\w\-]+)', msg)
    if target:
        chat(s, 'Whitelisting user: {}'.format(target.group(1)))
        whitelisted_users.append(target.group(1).lower())
        unban(s, target.group(1).lower())


if __name__ == '__main__':
    chat(s, 'Reporting for duty!')
    watch_chatters()
    read_chat()
