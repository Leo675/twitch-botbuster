#! python3
# -*- coding: utf-8 -*-
# Author: Daytona_675

import socket
import time
import re
import requests
import json
import sqlite3
import datetime
from threading import Thread
import configparser


# Function for threaded asynchronous functions decorator @async
def async(func):
    from functools import wraps
    
    @wraps(func)
    def async_func(*args, **kwargs):
        f = Thread(target = func, args = args, kwargs = kwargs)
        f.start()
        return
    return async_func

class BotBuster():
    # Gets config.ini settings
    config = configparser.ConfigParser()
    config.read('config.ini')
    p_threshold = int(config['DEFAULT']['p_threshold'])
    chat_user = config['DEFAULT']['chat_user']
    chat_pass = config['DEFAULT']['chat_pass']
    chat_chan = config['DEFAULT']['chat_chan']
    client_id = config['DEFAULT']['client_id']
    punishment = config['DEFAULT']['punishment']
    timeout_duration = int(config['DEFAULT']['timeout_duration'])
    chat_host = config['DEFAULT']['chat_host']
    chat_port = int(config['DEFAULT']['chat_port'])
    
    # Persistent database file. Makes file name based on chat channel. Only change to make a combined database for multiple channels.
    database_name = '{}_database.sqlite'.format(chat_chan)
    banned_users = []
    whitelisted_users = []
    banned_dates = []
    timedout_users = {}
    #Maps indexes to names, QoL, don't touch unless changing data structure of database
    user_name = 0
    creation_date = 1
    user_status = 2 # None = not banned, 1 = timed out, 2 = banned, 3 = whitelisted
    time_stamp = 3
    last_message = int(time.time())
    
    # List of commands which use regular expressions. Only change the left side and make sure to leave the ^
    commands = {
        '^!startbans': 'start_banning',
        '^!blacklist': 'blacklist_user',
        '^!bld': 'blacklist_date',
        '^!unlist' : 'unlist_date',
        '^!whitelist': 'whitelist_user',
        '^!stopbans': 'stop_banning',
        '^!wlshow': 'show_whitelist',
        }

    mitigation_active = 0
    
    def __init__(self):
        return
    
    def init_database(self):
        try:
            self.load_database()
            print('loading db')
        except:
            print('creating db')
            # Maps indexes to names
            self.user_name = 0
            self.creation_date = 1
            self.user_status = 2 # None = not banned, 1 = timed out, 2 = banned, 3 = whitelisted
            self.time_stamp = 3

            create_table = 'create table if not exists {} ( {}, {}, {}, {} )'
            epoch_time_stamp = "time_stamp integer"

            create_user_table = create_table.format('user_table', 'user_name id text primary key', 'creation_date text', 'user_status integer', epoch_time_stamp)

            conn = sqlite3.connect(self.database_name)
            c = conn.cursor()
            c.execute(create_user_table)

            # insert_row = 'insert into {} ({}) values (?)'
            # insert_user = insert_row.format('user_table', 'user_name')
            # c.execute(insert_user, ('test_user',))
            # c.execute("select * from 'user_table'")
            conn.commit()
            conn.close()

    # Gets list of chatters and updates admin list
    def get_chatters(self):
        # Loop ends when a value is returned
        while 1:
            self.chatter_list = ()
            admins = ()
            # Uses try because sometimes the connection times out
            try:
                r = requests.get('https://tmi.twitch.tv/group/user/{}/chatters'.format(self.chat_chan))
            except:
                time.sleep(1)
                continue
            
            if r.status_code == 200:
                r = json.loads(r.text)
                # Builds the list of chatters
                for chatter in r['chatters']['viewers']:
                    self.chatter_list += (chatter,)
                
                # Dynamic moderators list, kinda hackish but if you unmod someone they will be removed on the next loop
                for moderator in r['chatters']['moderators']:
                    admins += (moderator,)
                
                self.admin_list = admins
                return self.chatter_list
            time.sleep(3)
            
    def load_database(self):
        self.buster_database = {}
        conn = sqlite3.connect(self.database_name)
        c = conn.cursor()
        select_all = 'select * from user_table;'
        c.execute(select_all)
        rows = c.fetchall()
        print(rows)
        for row in rows:
            self.buster_database.update({row[self.user_name] : [row[self.creation_date], row[self.user_status], row[self.time_stamp]]})
            if row[self.user_status] == 2: #whitelisted
                print('adding {} to whitelist'.format(row[self.user_name]))
                self.whitelisted_users.append(row[self.user_name])
            if row[self.user_status] == 1: #blacklisted
                if row[self.creation_date] not in self.banned_dates:
                    self.banned_dates.append(row[self.creation_date])
        conn.close()
        return self.buster_database

    def update_db(self, user, status):
        if status == 'whitelisted':
            status = 2
        elif status == 'blacklisted':
            status = 1
        else:
            status = 0
        ctime = int(time.time())
        print('checking date created')
        date_created = get_creation_date(user)
        print('date check finished')
        try:
            self.buster_database.update({user : [date_created, status, ctime]})
        except:
            return
        sql_query = "insert or replace into user_table (user_name, creation_date, user_status, time_stamp) values ('{}','{}',{},{})".format(user, date_created, status, ctime)
        #sql_query = "update user_table set user_name = '{}', creation_date = '{}', user_status = {}, time_stamp = {};".format(user, date_created, status, ctime)
        print('executing query: {}'.format(sql_query))
        conn = sqlite3.connect(self.database_name)
        c = conn.cursor()
        c.execute(sql_query)
        conn.commit()
        conn.close()
    
    
    # Thread for watching and banning chatters
    @async
    def watch_chatters(self):
        while 1:
            # Gets the list of chatters in the room, needs to run while mitigation is off
            self.chatter_list = self.get_chatters()
            if self.mitigation_active:
                for chatter in self.chatter_list:
                    if chatter in self.banned_users:
                        continue
                    
                    elif chatter in self.whitelisted_users:
                        continue
                    elif chatter in self.timedout_users:
                        if int(time.time) >= self.timedout_users[chatter]:
                            self.punish(chatter)
                        continue
                    
                    try:
                        user_date = get_creation_date(chatter)
                    except:
                        continue
                    
                    if get_creation_date(chatter) in self.banned_dates:
                        self.punish(chatter)

                        print('Current number of banned users: {!s}'.format(len(self.banned_users)))
            time.sleep(15)

    # Thread for reading chat and watching for user commands
    @async
    def read_chat(self):    
        # Starts infinite loop listening to the IRC server
        self.connect_chat()
        while True:
            response = self.s.recv(1024).decode("utf-8")
            if len(response) == 0:
                self.connect_chat()
                continue
            
            # PONG replies to keep the connection alive
            if response == "PING :tmi.twitch.tv\r\n":
                self.s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                continue

            # Separates user and message.
            chat_object = re.search(r'^:(\w+)![^:]+:(.*)$', response)
            if chat_object:
                self.process_chat(chat_object)

    @async
    def process_chat(self, chat_object):
        user = chat_object.group(1)
        msg = chat_object.group(2)
        # Processes possible commands from the command dictionary
        for command,action in self.commands.items():
            if re.search(command, msg):
                # Manual blacklisting of dates, uses GMT always
                if action == 'blacklist_date' and user in self.admin_list:
                    input = re.search('^'+command+'\s+([\d]{4}-[\d]{2}-[\d]{2})', msg)
                    if input:
                        # Adds date to the banned list
                        self.chat(self.s, 'Blacklisting {}'.format(input.group(1)))
                        self.banned_dates.append(input.group(1))
                    else:
                        print('failed bld')
                        self.chat(self.s, 'Error: invalid format. Use !bld YYYY-MM-DD')
                    return
                
                # Manual unlisting of a date, can also !stopbans to clear the list 
                elif action == 'unlist_date' and user in self.admin_list:
                    input = re.search('^'+command+'\s+([\d]{4}-[\d]{2}-[\d]{2})', msg)
                    if input:
                        self.banned_dates.remove(input.group(1))
                    else:
                        self.chat(self.s, 'Error: invalid format. !unlist YYYY-MM-DD')
                    return

                # Automatic lookup of a user's creation date blacklisting it.
                elif action == 'blacklist_user':
                    if user not in self.admin_list:
                        self.chat(self.s, 'Boop beep ur not a mod bruh {}'.format(user))
                        return
                    target = re.search('^'+command+'\s*@?([\w\-]+)', msg)
                    try:
                        target_user = target.group(1).lower()
                    except:
                        return

                    # Makes sure the user is actually in the room to prevent erroneous bans.
                    
                    user_date = get_creation_date(target_user)
                    self.punish(target_user)
                    self.chat(self.s, 'Blacklisted: {}'.format(user_date))
                    if user_date not in self.banned_dates:
                        self.banned_dates.append(user_date)
                    for i in range(1,self.p_threshold + 1):
                        future = user_date + i
                        past = user_date - i
                        if future not in self.banned_dates:
                            self.banned_dates.append(future)
                        if past not in self.banned_dates:
                            self.banned_dates.append(past)    
                    try:
                        self.whitelisted_users.remove(target_user)
                    except:
                        pass
                    return
                # Stops bans and clears blacklist
                elif action == 'stop_banning' and user in self.admin_list:
                    self.mitigation_active = 0
                    self.banned_dates = []
                    self.chat(self.s, 'Turning off chat mitigation.')
                    return

                # Starts banning users
                elif action == 'start_banning' and user in self.admin_list:
                    self.mitigation_active = 1
                    self.chat(self.s, 'Turning on chat mitigation ═══█❚')
                    return

                # Unbans and prevents future banning of the user
                elif action == 'whitelist_user' and user in self.admin_list:
                    target = re.search('^'+command+'\s*@?([\w\-]+)', msg)
                    try:
                        target_user = target.group(1).lower()
                    except:
                        return
                    if target_user == 'all':
                        for target_user in self.chatter_list:
                            self.whitelist(target_user)
                        return
                    self.whitelist_user(target_user)
                    return
                elif action == 'show_whitelist' and user in self.admin_list:
                    self.chat(self.s, repr(self.whitelisted_users))
                    return
                    
    def whitelist_user(self, target_user):
        if target_user in self.whitelisted_users:
            self.chat(self.s, 'User {} is already whitelisted'.format(target_user))
            return
        self.chat(self.s, 'Whitelisting user: {}'.format(target_user))
        self.update_db(target_user, 'whitelisted')
        self.whitelisted_users.append(target_user)
        self.unban(self.s, target_user)
        try:
            del self.timedout_users[target_user]
        except:
            pass
        try:
            self.banned_users.remove(target_user)
        except:
            pass
        return
        
    # Punishes chatter with specified method
    def punish(self, chatter):
        if self.punishment == 'ban':
            self.ban(self.s, chatter)
            self.banned_users.append(chatter)
            print('Banning {}'.format(chatter))
        else:
            to_time = int(time.time())
            self.timedout_users.update({chatter : to_time + self.timeout_duration})
            self.timeout(self.s, chatter, self.timeout_duration)
            print('Timing Out {}'.format(chatter))    
    # Initial IRC socket connection and authentication
    def connect_chat(self):
        s = socket.socket()
        s.connect((self.chat_host, self.chat_port))
        s.send("PASS {}\r\n".format(self.chat_pass).encode("utf-8"))
        s.send("NICK {}\r\n".format(self.chat_user).encode("utf-8"))
        s.send("CAP REQ :twitch.tv/membership\r\n".encode("utf-8"))
        s.send("JOIN #{}\r\n".format(self.chat_chan).encode("utf-8"))
        self.s = s
        
    # Sends messages to chat
    def chat(self, sock, msg):
        while int(time.time()) - self.last_message  < 2:
            time.sleep(1)
        sock.send(bytes('PRIVMSG #%s :%s\r\n' % (self.chat_chan, msg), 'UTF-8'))
        self.last_message = int(time.time())

    
    # Permabans users
    def ban(self, sock, user):
        self.chat(sock, "/ban {}".format(user))


    # Unbans users
    def unban(self, sock, user):
        self.chat(sock, "/unban {}".format(user))

        
    # Times users out
    def timeout(self, sock, user, secs):
        self.chat(sock, "/timeout {} {}".format(user, secs))
        
# Function for returning the user's creation date
def get_creation_date(user):
    client_id = 'jzkbprff40iqj646a697cyrvl0zt2m6'
    headers = { 'Client-ID' : client_id }
    # Loop ends when a value is returned
    while 1:
        # Uses try in case of request timeout
        try:
            r = requests.get('https://api.twitch.tv/kraken/users/{}'.format(user), headers = headers)
        except:
            time.sleep(1)
            continue

        if r.status_code == 200:
            # Captures only YYYY-MM-DD
            date = re.match(
                '([\d]{4}-[\d]{2}-[\d]{2})',
                json.loads(r.text)['created_at']
            )
            epoch = datetime.datetime.strptime("{}".format(date.group(1)) , "%Y-%m-%d")
            epoch = int(time.mktime(epoch.timetuple()) / 3600)
            # except:
                # print('Failed to get time')
                # return
            return epoch

       
if __name__ == '__main__':
    bot = BotBuster()
    bot.init_database()
    print('database initilized')
    bot.watch_chatters()
    print('watching chatters')
    bot.read_chat()
    print('reading chat')
    time.sleep(7)
    bot.chat(bot.s, 'Reporting for duty!')
    print('looping')
