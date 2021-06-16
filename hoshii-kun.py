import discord
import asyncio
import dateparser
import datetime
import math
import json
import pytz
import apscheduler
import pymongo
import dns
import requests
import arrow
import csv
import random


from difflib import SequenceMatcher
from discord.ext import commands, tasks
from discord.ext.commands.cooldowns import BucketType
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pymongo import MongoClient
from ics import Calendar, Event


#Discord token goes here. It's possible to read the token in from an environment variable or another remote location if required
TOKEN = ""


#Discord client
client = commands.Bot(command_prefix = '/')


#Notification scheduler, used for event hosting notifications
notifier = AsyncIOScheduler(daemon=True)
notifier.start()


#MongoDB initialization, fill in pymongo.MongoClient("") with your mongoDB connection string
mongo_client = pymongo.MongoClient("")
db = mongo_client.events
collection = db.event_data


#12* unit dictionaries, these were used to load in armor data from csv files for quick access back in episode 5.
back_dict = {}   
arms_dict = {}
legs_dict = {}
subs_dict = {}  


#Event calendar, global so we don't need to request it every single time someone calls /uq
cal = None




#************** init_calendar() ****************
#pulls scheduled events from SEGA's event calendar, deserializes the json file,
#adds it into an ics calendar, then converts it into timeline format.
#[It's an adapter so we can use the system we wrote from when SEGA used google calendar for their events]
def init_calendar():
    #Global variable to store the calendar so we don't have to pull the data every time someone calls /uq
    global cal
    
    
    #Create calendar object to store events in
    calendar = Calendar()
    
    
    #SEGA's PSO2 site has an age gate, so in order to get to any other page, we'll need to pretend we passed through the agegate already by changing the cookies
    #Sidenote: In the future, we could read all the cookies and see which ones contain the word 'age' and a T/F value and set them to true for resilience to small name changes
    url = requests.session()
    url = requests.get("https://pso2.com/news/LoadScheduleCampaigns", cookies = {'pso2-age.verification':'true'} )
    
    
    #Make sure the event schedule url is alive before continuing, if it isn't, print to console and exit function.
    if url is None:
        print("Trouble loading json file from SEGA website. Please check their API")
        return
    
    
    #Pulls the json file located at the url and stores it in this variable
    json_file = json.loads(url.content.decode())
    
    
    #For every event in the json file, add Event and its details to the ics calendar.
    for event in json_file:
        id = event["id"]
        title = event["title"]
        events = event["events"]  
        locale = pytz.timezone('US/Pacific')
        
        for event_number in events:
            start = event_number["startDate"]
            end = event_number["endDate"]
            
            new_event = Event()
            
            new_event.name = title
            
            new_event.begin = dateparser.parse(start).replace(tzinfo=locale)
            new_event.end = dateparser.parse(end).replace(tzinfo=locale)
            
            calendar.events.add(new_event)
        
        cal = calendar.timeline


    #Old code for when PSO2 Global used google calendars for their events
    """
    url = "https://calendar.google.com/calendar/ical/rc1af7l1sv3mt995hvjqpi4qb0%40group.calendar.google.com/public/basic.ics"
    cal = Calendar(requests.get(url).text)
    cal = cal.timeline
    """



#************** init_unit_data() ****************    
#This function reads stat information about armors in the game from a CSV file and stores it into a dictionary for quick access    
def init_unit_data():
    with open('backs.csv', newline='') as backs:
        reader = csv.DictReader(backs)
      
        for row in reader:
            back_dict[row['Unit']] = row
    
    with open('arms.csv', newline='') as arms:
        reader = csv.DictReader(arms)
        
        for row in reader:
            arms_dict[row['Unit']] = row
    
    with open('legs.csv', newline='') as legs:
        reader = csv.DictReader(legs)
        
        for row in reader:
            legs_dict[row['Unit']] = row
    
    with open('subs.csv', newline='') as subs:
        reader = csv.DictReader(subs)
        
        for row in reader:
            subs_dict[row['Unit']] = row
            




#This class is used for the event hosting function of hoshii-kun
class GuildEvent:
    
    #Every event will have an id, an associated guild, an event name, a party type, a start time, a host and a list of attendees.
    #Event IDs are just the discord message IDs for when the events are posted, this is so they're 1. Unique and 2. Easily referencable on the discord side of things.
    def __init__(self, guild, eventName, partyType, eventTime, host):
        self.event_ID = None
        self.guild = guild
        self.eventName = eventName
        self.partyType = partyType
        self.eventTime = eventTime
        self.host = host
        self.playerList = []
    
    
    
    
    #************** listEventInfo() ****************    
    #Prints event information to the console
    async def listEventInfo(self):
        print("\n[Alliance] {}\n[Event Name] {}\n[Party Size] {}\n[Event Time] {}\n[Host] {}".format(self.guild.name, self.eventName, self.partyType, self.eventTime, self.host))




    #************** eventToDB() ****************
    #Stores events in mongoDB for data persistence
    def eventToDB(self):
        if self.event_ID and self.guild and self.eventName and self.partyType and self.host:
            j_eventID = self.event_ID
            j_guild = self.guild.id
            j_eventName = self.eventName
            j_partyType = self.partyType
            j_eventTime = str(self.eventTime)
            j_host = self.host
            j_playerList = self.playerList
            
            filter = {"_id": j_eventID}
            event = {"$set": {"_id": j_eventID, "guild": j_guild, "eventName": j_eventName, "partyType": j_partyType, "eventTime": j_eventTime, "host": j_host, "playerList": j_playerList} }
            
            x = collection.update_one(filter ,event, upsert=True)
            '''
            list = [j_eventID, j_guild, j_eventName, j_partyType, j_eventTime, j_host, j_playerList]
            json_string = json.dumps(list)
            
            
            file_name = str(self.event_ID)+".json"
            json_file = open(file_name, 'w+')
            json_file.write(json_string)
            json_file.truncate()
            json_file.close()
            '''




    #************** DBToEvent() ****************
    #Pulls event data from mongoDB using the event ID        
    def DBToEvent(self, event_ID):
        '''
        file_name = str(event_ID)+".json"
        file = open(file_name, 'r')
        json_string = file.read()
        file.close()
        
        list = json.loads(json_string)
        '''
        
        filter = {"_id": event_ID}
        cursor = collection.find_one(filter)
        
        self.event_ID = event_ID
        self.guild = client.get_guild(cursor['guild'])
        self.eventName = cursor['eventName']
        self.partyType = cursor['partyType']
        self.eventTime = dateparser.parse(cursor['eventTime'])
        self.playerList = cursor['playerList']
        self.host = cursor['host']




    #************** shareEvent() ****************
    #Makes a post about the event on the 'event-hosting' guild channel. Creates the channel if it doesn't exist. [In the future, we could let them configure what channel they want it posted in]
    #Allows people to sign up for the event by reacting a heart to the event post
    #Sends people timezone conversions for the event if they react with the clock
    
    #Notes: If the system ever got converted to an embed based rather than message based system, we could just load the start time in the user's local time.
    
    #Unlimited party size hasn't been completed since release, but was left in at request. Unexpected behaviour is expected to occur if the message size for the event ever exceeds the character limit for the message.
    #Patchable by detecting a character limit overflow and adding function to list all the signees by reacting to a list.
    
    #Wishlist: A waitlist function
    async def shareEvent(self):
        #Grabs a list of channels from the event's guild
        channels = self.guild.text_channels
        
        
        #Channel to post event in
        event_channel = None


        #Convert event start time to UTC
        self.eventTime = self.eventTime.astimezone(pytz.utc)
        
        
        #Set the format to print the time out in as Y/M/D @ H:M UTC
        formatted_time = self.eventTime.strftime("%Y/%m/%d @ %H:%M %Z")


        #Scans channels for 'event-hosting' channel, sets event-channel to 'event-hosting' if it's found
        for i in channels:
            if(i.name) == ('event-hosting'):
                event_channel = i
        
        
        #If 'event-hosting' doesn't exist on the server, create the channel        
        if event_channel is None:
            event_channel = await self.guild.create_text_channel('event-hosting', overwrites={self.guild.default_role: discord.PermissionOverwrite(send_messages=False)})

        
        #Post event data with reaction emojis, store event in DB and return event ID
        message = await event_channel.send("**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {} ".format(self.eventName, self.host, self.partyType, formatted_time))
        self.event_ID = message.id
        await message.add_reaction('❤️')
        await message.add_reaction('🕒')
        self.eventToDB()
        return self.event_ID        

#Really disturbing redundant code removed. It must've made sense at one point in time -w-.
'''         
        if self.partyType == '4':
            message = await event_channel.send("**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {} ".format(self.eventName, self.host, self.partyType, formatted_time))
            self.event_ID = message.id
            await message.add_reaction('❤️')
            await message.add_reaction('🕒')
            self.eventToDB()
            return self.event_ID
        elif self.partyType == '8':
            message = await event_channel.send("**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}".format(self.eventName, self.host, self.partyType, formatted_time))  
            self.event_ID = message.id
            await message.add_reaction('❤️')
            await message.add_reaction('🕒')
            self.eventToDB()
            return self.event_ID
        elif self.partyType == '12':
            message = await event_channel.send("**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}".format(self.eventName, self.host, self.partyType, formatted_time))  
            self.event_ID = message.id
            await message.add_reaction('❤️')
            await message.add_reaction('🕒')
            self.eventToDB()
            return self.event_ID            
        elif self.partyType == 'unlimited':
            message = await event_channel.send("**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}".format(self.eventName, self.host, self.partyType, formatted_time))  
            self.event_ID = message.id
            await message.add_reaction('❤️')
            await message.add_reaction('🕒')
            self.eventToDB()
            return self.event_ID     
'''




#************** on_ready() ****************
#Things that need to be run once before the bot can start itself
@client.event
async def on_ready():
    #Loads armor data into their dictionaries from CSV files for the '/back', '/arms', '/legs', '/sub' and '/planunits' commands to have quick access to the data without reading the csvs over and over again.
    init_unit_data()

    
    #Initializes the event calendar by pulling event data from SEGA's website. 
    #Sets the scheduler to update the calendar every 24 hours in case there are unannounced changes to the calendar
    #Note: They retired scheduled events after New Genesis launched.
    init_calendar()
    notifier.add_job(init_calendar, 'interval', minutes=1440)

    
    #Print something to the console so we know we passed the initialization stage
    print(f'{client.user} has connected to Discord!')

    
    #Set the bot's status message to "Playing PHANTASY STAR ONLINE 2"
    await client.change_presence(activity=discord.Game(name="PHANTASY STAR ONLINE 2"))

    
    #Loads all events that haven't started yet into the notification scheduler [the thing that messages event attendees 15 minutes before an event starts]
    await loadAllEventNotifs()



    
#************** loadEvent() ****************
#loads event from database using the event ID, returns GuildEvent object
async def loadEvent(event_ID):
    event = GuildEvent(None, None, None, None, None)
    event.DBToEvent(event_ID)
    #await event.listEventInfo()
    
    return event




#************** notify() ****************
#Pulls event data from event ID, checks if the event is still posted in the guild [in case it got cancelled/deleted], grabs all the signups and notifies them that the event will start soon.
async def notify(event_ID):
    
    event = await loadEvent(event_ID)
    
    if event is None:
        return
    
    channels = event.guild.text_channels
    for i in channels:
            if(i.name) == ('event-hosting'):
                event_channel = i
    
    message = await event_channel.fetch_message(event_ID)               
    if message is None:
        return

    
    for player in event.playerList:
        user = client.get_user(player)
        await user.send("Hey there {}! This is just a reminder that you signed up for {} at {}. It will begin shortly :) ".format(user.display_name, event.eventName, event.guild))





#************** getEventName() ****************
#Prompts user for the event name with a fun dialogue        
async def getEventName(ctx):
    def eventNameCheck(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        eventName = await client.wait_for('message', check=eventNameCheck, timeout=120)
        if eventName is not None:
            eventName.content = eventName.clean_content
            eventName.content = discord.utils.escape_markdown(eventName.content)
    except asyncio.TimeoutError:
        await ctx.author.send("Oh crap, look at the time. I gotta go! Let's talk about this later okay?")
        return "Timeout"
    else:
        if '/host' in eventName.content:
            await ctx.author.send("{}.... More than one '/host' confuses me, I'm just one guy!".format(ctx.author.display_name))
        if '/cancel' == eventName.content:
            await ctx.author.send("What? You want to talk about this another time? Okay {}, I'll be ready for you :> ".format(ctx.author.display_name))
            return None
        if eventName.content is None:
            await ctx.author.send("I completely zoned out {}, could you repeat that again?")
            eventName = await getEventName(ctx)
        if len(eventName.content) > 1500:
            await ctx.author.send("Eeeeeeeeeeeh? Sorry {}! The event name was too long for me to remember. I got most of it down though!".format(ctx.author.display_name))
            eventName.content = eventName.content[0:1500]
        return eventName




#************** getPartyType() ****************
#Prompts user for the party size with a fun dialogue     
async def getPartyType(ctx):
    def partyTypeCheck(m):
        return m.author == ctx.author and m.channel == ctx.channel
        
    try:
        partyType = await client.wait_for('message', check=partyTypeCheck, timeout=120)
    except asyncio.TimeoutError:
        await ctx.author.send("Oh crap! I'm late for class! Let's talk about this another time, okay? Bye {}!".format(ctx.author.display_name) )
        return "Timeout"
    else:
        if '/host' in partyType.content:
            await ctx.author.send("{}.... More than one '/host' confuses me, I'm just one guy!".format(ctx.author.display_name))
        if '/cancel' == partyType.content:
            await ctx.author.send("What? You want to talk about this another time? Okay {}, I'll be ready for you :> ".format(ctx.author.display_name))
            return None
        if partyType.content.lower() == 'four' or partyType.content == '4':
            partyType.content = '4'
            return partyType
        elif partyType.content.lower() == 'eight' or partyType.content == '8':
            partyType.content = '8'
            return partyType
        elif partyType.content.lower() == 'twelve' or partyType.content == '12':
            partyType.content = '12'
            return partyType
        elif partyType.content.lower() == 'unlimited':
            partyType.content = 'unlimited'
            return partyType
        else:
            await ctx.author.send("No can do {}, parties can only be 'four' or '4' and multi-parties can only be 'eight', '8', 'twelve', '12' or 'unlimited'. Try again.".format(ctx.author.display_name))
            partyType = await getPartyType(ctx)
            return partyType




#************** getEventData() ****************
#Prompts user for the event date/time with a fun dialogue, will attempt to infer the date/time without a strict format
async def getEventDate(ctx):
    def dateCheck(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        date = await client.wait_for('message', check=dateCheck, timeout=120)
    except asyncio.TimeoutError:
        await ctx.author.send("Oh snap! My ride's here! See you later {}!".format(ctx.author.display_name))
        return "Timeout"
    else:
        if '/host' in date.content:
            await ctx.author.send("{}.... More than one '/host' confuses me, I'm just one guy!".format(ctx.author.display_name))
        if '/cancel' == date.content:
            await ctx.author.send("What? You want to talk about this another time? Okay {}, I'll be ready for you :> ".format(ctx.author.display_name))
            return None
        date = dateparser.parse(str(date.content))
        if date is None:
            await ctx.author.send("My bad {} 🙁. I couldn't understand the date and time. Can you try again for me? I'll try to do better 😫".format(ctx.author.display_name))
            date = await getEventDate(ctx)
        return date




#************** getMutualGuilds() ****************
#Scans to see what discord servers the bot has in common with the user, if there are no common servers - returns none because they can't host an event without sharing a server with the bot. 
async def getMutualGuilds(ctx):
    mutualGuilds = []
    try:
        for guild in client.guilds:
            if(guild.get_member(ctx.author.id)):
                mutualGuilds.append(guild)
        return mutualGuilds
    except:
        return None
    else:
        return None




#************** getGuildSelection() ****************
#Prompts user for the discord server they'd like to host an event on with a fun dialogue, only activates if the hoshii shares more than one server with the user, will just default to one server if only one server is shared.         
async def getGuildSelection(ctx):
    def guildCheck(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    mutualGuilds = await getMutualGuilds(ctx)
    
    if len(mutualGuilds) < 1:
        await ctx.author.send("You don't share any servers with me {}, it's such a shame :(".format(ctx.author.display_name))
        return None
    elif len(mutualGuilds) == 1:
        guild = mutualGuilds[0]
        return guild
    else:
        try:
            string = "Mmmn {}, can you tell me which alliance we're hosting this event for?".format(ctx.author.display_name)
            for i in mutualGuilds:
                string = string + "\n> *> {}*".format(i.name)
            
            await ctx.author.send(string)
            guild = await client.wait_for('message', check=guildCheck, timeout=120)
            
        except asyncio.TimeoutError:
            await ctx.author.send("What?! The alliance quarters is on fire?! Duty calls {}, we'll discuss this later!".format(ctx.author.display_name))
            return "Timeout"
        else:
            if '/host' in guild.content:
                await ctx.author.send("{}.... More than one '/host' confuses me, I'm just one guy!".format(ctx.author.display_name))
            if '/cancel' == guild.content:
                await ctx.author.send("What? You want to talk about this another time? Okay {}, I'll be ready for you :> ".format(ctx.author.display_name))
                return None
            similarity_ratios = {}
            for i in mutualGuilds:
                similarity_ratio = SequenceMatcher(None, guild.content, i.name).ratio()
                similarity_ratios[i] = similarity_ratio
            
            most_similar = max(similarity_ratios, key=similarity_ratios.get)
            guild = most_similar
            
            if guild is None:
                await ctx.author.send("Sorry {}, I zoned out for a minute. HOSHII TIME TRAVEL MAGIC GO! **poof**".format(ctx.author.display_name))
                guild = await getGuildSelection(ctx)
                
            return guild




#************** updateuq() ****************
#This was a secret command to force a calendar update without rebooting hoshii
@client.command(hidden=True)
async def updateuq(ctx, *args):
    init_calendar()
    
    if ctx:
        await ctx.author.send("Okay {}, I've updated the calendar for you!".format(ctx.author.display_name))
    
    
    
    
#************** back() ****************
#Returns a list of all back armor data currently stored on hoshii's dictionary. If an arg is sent, will scan for the closest match based on similarity ratio and give detailed stats on that armor piece.
@client.command(description='If there\'s no input, this command will return a list of all of the back units currently in Hoshii\'s dictionary. When given input, it will output the back unit\'s stats.\n\nUsage example: /back cleasis')
async def back(ctx, *args):
    if len(args) < 1:
        back_list = ''
        
        for i in back_dict.keys():
            back_list = back_list + i + '\n'
        
        await ctx.send(back_list)    
        return
        
    combined = ""
    for i in args:
       combined = combined + str(i+" ")

    key = combined

    keys = back_dict.keys()
    ratios = {}
    
    for i in keys:
        similarity_ratio = SequenceMatcher(None, key, i).ratio()
        ratios[i] = similarity_ratio
        
    most_similar = max(ratios, key=ratios.get)
    final_key = most_similar
    
    response = "**{}**```\nMEL PWR: {}\nRNG PWR: {}\nTEC PWR: {}\nHP: {}\nPP: {}\n\nMEL DEF: {}\nRNG DEF: {}\nTEC DEF: {}\n\nMEL RES: {}\nRNG RES: {}\nTEC RES: {}\nLight RES: {}\nDark RES: {}\nFire RES: {}\nIce RES: {}\nLightning RES: {}\nWind RES: {}\n\nDEX: {}\n```".format(back_dict[final_key]['Unit'], back_dict[final_key]['MEL pwr'], back_dict[final_key]['RNG pwr'], back_dict[final_key]['TEC pwr'], back_dict[final_key]['HP'], back_dict[final_key]['PP'], back_dict[final_key]['M DEF'], back_dict[final_key]['R DEF'], back_dict[final_key]['T DEF'], back_dict[final_key]['M RES'], back_dict[final_key]['R RES'], back_dict[final_key]['T RES'], back_dict[final_key]['Light RES'], back_dict[final_key]['Dark RES'], back_dict[final_key]['Fire RES'], back_dict[final_key]['Ice RES'], back_dict[final_key]['Lightning RES'], back_dict[final_key]['Wind RES'], back_dict[final_key]['DEX'])
    await ctx.send(response)




#************** arms() ****************
#Returns a list of all arm armor data currently stored on hoshii's dictionary. If an arg is sent, will scan for the closest match based on similarity ratio and give detailed stats on that armor piece.
@client.command(description='If there\'s no input, this command will return a list of all of the arm units currently in Hoshii\'s dictionary. When given input, it will output the arm unit\'s stats. Usage example: /arms cleasis')
async def arms(ctx, *args):
    if len(args) < 1:
        arms_list = ''
        
        for i in arms_dict.keys():
            arms_list = arms_list + i + '\n'
        
        await ctx.send(arms_list)    
        return
        
    combined = ""
    for i in args:
       combined = combined + str(i+" ")

    key = combined

    keys = arms_dict.keys()
    ratios = {}
    
    for i in keys:
        similarity_ratio = SequenceMatcher(None, key, i).ratio()
        ratios[i] = similarity_ratio
        
    most_similar = max(ratios, key=ratios.get)
    final_key = most_similar
    
    response = "**{}**```\nMEL PWR: {}\nRNG PWR: {}\nTEC PWR: {}\nHP: {}\nPP: {}\n\nMEL DEF: {}\nRNG DEF: {}\nTEC DEF: {}\n\nMEL RES: {}\nRNG RES: {}\nTEC RES: {}\nLight RES: {}\nDark RES: {}\nFire RES: {}\nIce RES: {}\nLightning RES: {}\nWind RES: {}\n\nDEX: {}\n```".format(arms_dict[final_key]['Unit'], arms_dict[final_key]['MEL pwr'], arms_dict[final_key]['RNG pwr'], arms_dict[final_key]['TEC pwr'], arms_dict[final_key]['HP'], arms_dict[final_key]['PP'], arms_dict[final_key]['M DEF'], arms_dict[final_key]['R DEF'], arms_dict[final_key]['T DEF'], arms_dict[final_key]['M RES'], arms_dict[final_key]['R RES'], arms_dict[final_key]['T RES'], arms_dict[final_key]['Light RES'], arms_dict[final_key]['Dark RES'], arms_dict[final_key]['Fire RES'], arms_dict[final_key]['Ice RES'], arms_dict[final_key]['Lightning RES'], arms_dict[final_key]['Wind RES'], arms_dict[final_key]['DEX'])
    await ctx.send(response)



#************** legs() ****************
#Returns a list of all leg armor data currently stored on hoshii's dictionary. If an arg is sent, will scan for the closest match based on similarity ratio and give detailed stats on that armor piece.
@client.command(description='If there\'s no input, this command will return a list of all of the leg units currently in Hoshii\'s dictionary. When given input, it will output the leg unit\'s stats. Usage example: /legs cleasis')
async def legs(ctx, *args):
    if len(args) < 1:
        legs_list = ''
        
        for i in legs_dict.keys():
            legs_list = legs_list + i + '\n'
        
        await ctx.send(legs_list)    
        return
        
    combined = ""
    for i in args:
       combined = combined + str(i+" ")

    key = combined

    keys = legs_dict.keys()
    ratios = {}
    
    for i in keys:
        similarity_ratio = SequenceMatcher(None, key, i).ratio()
        ratios[i] = similarity_ratio
        
    most_similar = max(ratios, key=ratios.get)
    final_key = most_similar
    
    response = "**{}**```\nMEL PWR: {}\nRNG PWR: {}\nTEC PWR: {}\nHP: {}\nPP: {}\n\nMEL DEF: {}\nRNG DEF: {}\nTEC DEF: {}\n\nMEL RES: {}\nRNG RES: {}\nTEC RES: {}\nLight RES: {}\nDark RES: {}\nFire RES: {}\nIce RES: {}\nLightning RES: {}\nWind RES: {}\n\nDEX: {}\n```".format(legs_dict[final_key]['Unit'], legs_dict[final_key]['MEL pwr'], legs_dict[final_key]['RNG pwr'], legs_dict[final_key]['TEC pwr'], legs_dict[final_key]['HP'], legs_dict[final_key]['PP'], legs_dict[final_key]['M DEF'], legs_dict[final_key]['R DEF'], legs_dict[final_key]['T DEF'], legs_dict[final_key]['M RES'], legs_dict[final_key]['R RES'], legs_dict[final_key]['T RES'], legs_dict[final_key]['Light RES'], legs_dict[final_key]['Dark RES'], legs_dict[final_key]['Fire RES'], legs_dict[final_key]['Ice RES'], legs_dict[final_key]['Lightning RES'], legs_dict[final_key]['Wind RES'], legs_dict[final_key]['DEX'])
    await ctx.send(response)




#************** sub() ****************
#Returns a list of all sub armor data currently stored on hoshii's dictionary. If an arg is sent, will scan for the closest match based on similarity ratio and give detailed stats on that armor piece.
@client.command(description='If there\'s no input, this command will return a list of all of the sub units currently in Hoshii\'s dictionary. When given input, it will output the sub unit\'s stats. Usage example: /sub stella')
async def sub(ctx, *args):
    if len(args) < 1:
        sub_list = ''
        
        for i in subs_dict.keys():
            sub_list = sub_list + i + '\n'
        
        await ctx.send(sub_list)    
        return
        
    combined = ""
    for i in args:
       combined = combined + str(i+" ")

    key = combined

    keys = subs_dict.keys()
    ratios = {}
    
    for i in keys:
        similarity_ratio = SequenceMatcher(None, key, i).ratio()
        ratios[i] = similarity_ratio
        
    most_similar = max(ratios, key=ratios.get)
    final_key = most_similar
    
    response = "**{}**```\nMEL PWR: {}\nRNG PWR: {}\nTEC PWR: {}\nHP: {}\nPP: {}\n\nMEL DEF: {}\nRNG DEF: {}\nTEC DEF: {}\n\nMEL RES: {}\nRNG RES: {}\nTEC RES: {}\nLight RES: {}\nDark RES: {}\nFire RES: {}\nIce RES: {}\nLightning RES: {}\nWind RES: {}\n\nDEX: {}\n```".format(subs_dict[final_key]['Unit'], subs_dict[final_key]['MEL pwr'], subs_dict[final_key]['RNG pwr'], subs_dict[final_key]['TEC pwr'], subs_dict[final_key]['HP'], subs_dict[final_key]['PP'], subs_dict[final_key]['M DEF'], subs_dict[final_key]['R DEF'], subs_dict[final_key]['T DEF'], subs_dict[final_key]['M RES'], subs_dict[final_key]['R RES'], subs_dict[final_key]['T RES'], subs_dict[final_key]['Light RES'], subs_dict[final_key]['Dark RES'], subs_dict[final_key]['Fire RES'], subs_dict[final_key]['Ice RES'], subs_dict[final_key]['Lightning RES'], subs_dict[final_key]['Wind RES'], subs_dict[final_key]['DEX'])
    await ctx.send(response)
  

 


#************** uq() ****************
#Sends the caller a list of upcoming scheduled urgent quests in the next 12 hours.
@client.command(description='Returns a list of scheduled Urgent Quests within the next 12 hours and their relative start times from now.')
async def uq(ctx, *args):    
    global cal


    #If the calendar somehow didn't load, try to load it, and if that didn't work - abort
    if cal is None:
        init_calendar()
        if cal is None:
            return
    

    now = arrow.utcnow()
    

    #Offsets from current time, hour before allows us to include current events, offset is 12 hours from now
    hour_before = now.shift(hours=-1)
    offset= now.shift(hours=+12)
    

    #Creates a subcalendar between the two offsets, allows us to save compute for larger calendars since we'd only be processing the events within the timeframe rather than all of the events
    upcoming = cal.included(hour_before, offset)
    
    string = "Hi {}! Here are the scheduled urgent quests for the next 12 hours:\n\n".format(ctx.author.display_name)
    

    #Iterates over the subcalendar of events between now-1 and now+12, concatenates a string containing with info about current/upcoming events
    event_counter = 0
    for event in upcoming:
        if now.is_between(event.begin, event.end):
            string = string + "**{} [IN PROGRESS]**```\nEnding {}\n```\n".format(event.name, event.end.humanize(granularity=["hour", "minute"]))
            event_counter +=1
        if event.begin.is_between(now, offset):
            string = string + "**{}**```\nStarting {}\n```\n".format(event.name, event.begin.humanize(granularity=["hour", "minute"]))
            event_counter += 1
    

    #If there's more than zero event from iterating, send the string to the caller - otherwise, send the other message for feedback
    if event_counter > 0:
        await ctx.send(string)
    else:
        await ctx.send("Oh no.... {}, it seems like there's no scheduled events in the next 12 hours. That, or we might be waiting on a calendar update from SEGA. Good luck out there {}!".format(ctx.author.display_name, ctx.author.display_name))
        init_calendar()
    

    #Spices up the command with the ocassional random message to make Hoshii seem more human
    random_message = random.randint(1,250)
    if random_message == 50:
        await ctx.send("Umm, I know this is out of the blue...but I hope you're having a great day {}.".format(ctx.author.display_name))
    elif random_message == 100:
        random_song = random.randint(1,7)
        if random_song == 1:
            await ctx.send("♩ ♪ ♫ ♬ RARE DROP! KOI KOI! ♩ ♪ ♫ ♬")
        elif random_song == 2:
            await ctx.send("♩ ♪ ♫ ♬ ALL I WANT FOR CHRISTMAS IS...♩ ♪ ♫ ♬")
        elif random_song == 3:
            await ctx.send("♩ ♪ ♫ ♬ OPPAN GANGNAM STYLE! ♩ ♪ ♫ ♬")
        elif random_song == 4:
            await ctx.send("♩ ♪ ♫ ♬ Let's dance the night away! du-du-du-dududu dudu-dudu-dudu-du ♩ ♪ ♫ ♬")
        elif random_song == 5:
            await ctx.send("♩ ♪ ♫ ♬ Fighting evil by moonlight! ♩ ♪ ♫ ♬ Winning love by daylight! ♩ ♪ ♫ ♬")
        elif random_song == 6:
            await ctx.send("♩ ♪ ♫ ♬ You teach me and I'll teach you! PO-KE-MON! ♩ ♪ ♫ ♬")
        elif random_song == 7:
            await ctx.send("♩ ♪ ♫ ♬ Hit-cha with that ddu-du ddu-du ♩ ♪ ♫ ♬ ")    
        
        await ctx.send("😱!!! {}, I thought you left already! Eh? Me? singing? I definitely wasn't singing! 😳".format(ctx.author.display_name))
    elif random_message == 150:
        await ctx.send("Me? I'm doing great today! \*stretches\* \*yawwn\*")
    elif random_message == 200:
        await ctx.send("\*Drinks water\* Ahhh, refreshing!")    
        



#************** cancel() ****************
#User command used to escape from commands with dialogue such as /host and /planunits
@client.command(description='Used to escape from commands such as /host and /planunits')
async def cancel(ctx, *args):
    return




#************** getBackSelection() ****************
#Prompts user for back armor selection with a fun dialogue, used for the /planunits command
#Takes user input and matches it with the most similar armor piece found in the dictionary
async def getBackSelection(ctx):
    def Check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        back_unit = await client.wait_for('message', check=Check, timeout=120)
        
    except asyncio.TimeoutError:
        await ctx.author.send("Oh crap, look at the time. I gotta go! Let's talk about this later okay?")
        return "Timeout"
    else:
        if '/host' in back_unit.content:
            await ctx.send("{}.... I thought we were planning units, but okay... lets do this".format(ctx.author.display_name))
            return None
        if '/planunit' in back_unit.content:
            await ctx.send("{}.... That's what we're doing right now! I'll just assume you meant to input that :^)".format(ctx.author.display_name))
        if '/cancel' == back_unit.content:
            await ctx.send("What? You want to talk about this another time? Okay {}, I'll be ready for you :> ".format(ctx.author.display_name))
            return None
        if back_unit.content is None:
            await ctx.send("I completely zoned out {}, could you repeat that again?")
            back_unit = await getBackSelection(ctx)
        if len(back_unit.content) > 1500:
            await ctx.send("Eeeeeeeeeeeh? Sorry {}! The back unit's name was too long for me to remember. I got most of it down though!".format(ctx.author.display_name))
            back_unit.content = back_unit.content[0:1500]
    
        key = back_unit.content

        keys = back_dict.keys()
        ratios = {}
        
        for i in keys:
            similarity_ratio = SequenceMatcher(None, key, i).ratio()
            ratios[i] = similarity_ratio
            
        most_similar = max(ratios, key=ratios.get)
        
        final_key = most_similar        
        
        return final_key
 



#************** getArmsSelection() ****************
#Prompts user for arm armor selection with a fun dialogue, used for the /planunits command
#Takes user input and matches it with the most similar armor piece found in the dictionary
async def getArmsSelection(ctx):
    def Check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        arm_unit = await client.wait_for('message', check=Check, timeout=120)
        
    except asyncio.TimeoutError:
        await ctx.send("Oh crap, look at the time. I gotta go! Let's talk about this later okay?")
        return "Timeout"
    else:
        if '/host' in arm_unit.content:
            await ctx.send("{}.... I thought we were planning units, but okay... lets do this".format(ctx.author.display_name))
            return None
        if '/planunit' in arm_unit.content:
            await ctx.send("{}.... That's what we're doing right now! I'll just assume you meant to input that :^)".format(ctx.author.display_name))
        if '/cancel' == arm_unit.content:
            await ctx.send("What? You want to talk about this another time? Okay {}, I'll be ready for you :> ".format(ctx.author.display_name))
            return None
        if arm_unit.content is None:
            await ctx.send("I completely zoned out {}, could you repeat that again?")
            arm_unit = await getArmsSelection(ctx)
        if len(arm_unit.content) > 1500:
            await ctx.send("Eeeeeeeeeeeh? Sorry {}! The arm unit's name was too long for me to remember. I got most of it down though!".format(ctx.author.display_name))
            arm_unit.content = arm_unit.content[0:1500]
    
        key = arm_unit.content

        keys = arms_dict.keys()
        ratios = {}
        
        for i in keys:
            similarity_ratio = SequenceMatcher(None, key, i).ratio()
            ratios[i] = similarity_ratio
            
        most_similar = max(ratios, key=ratios.get)
        
        final_key = most_similar        
        
        return final_key




#************** getLegsSelection() ****************
#Prompts user for leg armor selection with a fun dialogue, used for the /planunits command
#Takes user input and matches it with the most similar armor piece found in the dictionary
async def getLegsSelection(ctx):
    def Check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        leg_unit = await client.wait_for('message', check=Check, timeout=120)
        
    except asyncio.TimeoutError:
        await ctx.send("Oh crap, look at the time. I gotta go! Let's talk about this later okay?")
        return "Timeout"
    else:
        if '/host' in leg_unit.content:
            await ctx.send("{}.... I thought we were planning units, but okay... lets do this".format(ctx.author.display_name))
            return None
        if '/planunit' in leg_unit.content:
            await ctx.send("{}.... That's what we're doing right now! I'll just assume you meant to input that :^)".format(ctx.author.display_name))
        if '/cancel' == leg_unit.content:
            await ctx.send("What? You want to talk about this another time? Okay {}, I'll be ready for you :> ".format(ctx.author.display_name))
            return None
        if leg_unit.content is None:
            await ctx.send("I completely zoned out {}, could you repeat that again?")
            arm_unit = await getLegsSelection(ctx)
        if len(leg_unit.content) > 1500:
            await ctx.send("Eeeeeeeeeeeh? Sorry {}! The leg unit's name was too long for me to remember. I got most of it down though!".format(ctx.author.display_name))
            leg_unit.content = leg_unit.content[0:1500]
    
        key = leg_unit.content

        keys = legs_dict.keys()
        ratios = {}
        
        for i in keys:
            similarity_ratio = SequenceMatcher(None, key, i).ratio()
            ratios[i] = similarity_ratio
            
        most_similar = max(ratios, key=ratios.get)
        
        final_key = most_similar        
        
        return final_key
 
 
 

#************** AustereCheck() ****************
#Back in episode 5 of Phantasy Star Online 2, there was an armor set called Austere (ofzeterious in the official translated version)
#This was the only 12* unit set that had significant set bonuses, however had a portion of the set bonus matched with the austere weapon series
#This function asks the user if they are using an austere weapon if they tell hoshii they're using austere legs so it can calculate the set bonus properly.
async def AustereCheck(ctx):
    def Check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        austere = await client.wait_for('message', check=Check, timeout=120)
    
    except asyncio.TimeoutError:
        await ctx.send("Oh crap, look at the time. I gotta go! Let's talk about this later okay?")
        return "Timeout"
    
    else:
        if '/host' in austere.content:
            await ctx.send("{}.... I thought we were planning units, but okay... lets do this".format(ctx.author.display_name))
            return None
        if '/planunit' in austere.content:
            await ctx.send("{}.... That's what we're doing right now! I'll just assume you meant to input that :^)".format(ctx.author.display_name))
        if '/cancel' == austere.content:
            await ctx.send("What? You want to talk about this another time? Okay {}, I'll be ready for you :> ".format(ctx.author.display_name))
            return None
        if austere.content is None:
            await ctx.send("I completely zoned out {}, could you repeat that again?")
            austere = await AustereCheck(ctx)
        if len(austere.content) > 1500:
            await ctx.send("Eeeeeeeeeeeh? Sorry {}! I'm asking you a yes or no question. I'll just try to guess what you meant by that.".format(ctx.author.display_name))
            austere.content = austere.content[0:1500]        
        
        key = austere.content
        
        keys = ['yes', 'no']
        
        ratios = {}
        
        for i in keys:
            similarity_ratio = SequenceMatcher(None, key, i).ratio()
            ratios[i] = similarity_ratio
            
        most_similar = max(ratios, key=ratios.get)
        
        final_key = most_similar        
        
        return final_key




#************** planunits() ****************
#Prompts the user for a selection of back/arm/leg units using a fun dialogue and returns the stat total of their selections as a message
@client.command(description='Asks you for a combination of 13 star Back, Arms and Legs units from PSO2 Global - will calculate the stat totals of each combination (experimental)')
@commands.max_concurrency(1, per=BucketType.user, wait=False)
async def planunits(ctx, *args):
    await ctx.send("Hi {}! You wanted some help planning your units?".format(ctx.author.display_name))
    await ctx.send("Okay, but only because it's you who asked ♡")

    
    #Back
    await ctx.send("So tell me {}, which back unit you were you planning on using?".format(ctx.author.display_name))
    back = await getBackSelection(ctx)
    if back == "Timeout" or back is None:
        return
    
    #response = ">>> **{}**```MEL PWR: {}\nRNG PWR: {}\nTEC PWR: {}\nHP: {}\nPP: {}\n\nMEL DEF: {}\nRNG DEF: {}\nTEC DEF: {}\n\nMEL RES: {}\nRNG RES: {}\nTEC RES: {}\nLight RES: {}\nDark RES: {}\nFire RES: {}\nIce RES: {}\nLightning RES: {}\nWind RES: {}\n\nDEX: {}```".format(back_dict[back]['Unit'], back_dict[back]['MEL pwr'], back_dict[back]['RNG pwr'], back_dict[back]['TEC pwr'], back_dict[back]['HP'], back_dict[back]['PP'], back_dict[back]['M DEF'], back_dict[back]['R DEF'], back_dict[back]['T DEF'], back_dict[back]['M RES'], back_dict[back]['R RES'], back_dict[back]['T RES'], back_dict[back]['Light RES'], back_dict[back]['Dark RES'], back_dict[back]['Fire RES'], back_dict[back]['Ice RES'], back_dict[back]['Lightning RES'], back_dict[back]['Wind RES'], back_dict[back]['DEX'])
    #await ctx.send(response)    

    
    #Arms
    await ctx.send("{}, got it! Now onto the arms! Tell me which arms you're planning on using.".format(back))
    arms = await getArmsSelection(ctx)
    if arms == "Timeout" or arms is None:
        return
    
    #response = ">>> **{}**```MEL PWR: {}\nRNG PWR: {}\nTEC PWR: {}\nHP: {}\nPP: {}\n\nMEL DEF: {}\nRNG DEF: {}\nTEC DEF: {}\n\nMEL RES: {}\nRNG RES: {}\nTEC RES: {}\nLight RES: {}\nDark RES: {}\nFire RES: {}\nIce RES: {}\nLightning RES: {}\nWind RES: {}\n\nDEX: {}```".format(arms_dict[arms]['Unit'], arms_dict[arms]['MEL pwr'], arms_dict[arms]['RNG pwr'], arms_dict[arms]['TEC pwr'], arms_dict[arms]['HP'], arms_dict[arms]['PP'], arms_dict[arms]['M DEF'], arms_dict[arms]['R DEF'], arms_dict[arms]['T DEF'], arms_dict[arms]['M RES'], arms_dict[arms]['R RES'], arms_dict[arms]['T RES'], arms_dict[arms]['Light RES'], arms_dict[arms]['Dark RES'], arms_dict[arms]['Fire RES'], arms_dict[arms]['Ice RES'], arms_dict[arms]['Lightning RES'], arms_dict[arms]['Wind RES'], arms_dict[arms]['DEX'])
    #await ctx.send(response)
    
    random_message = random.randint(1,10)
    if random_message == 10:
        await ctx.send("Like my father Hoshii always says - it's all in the arms.\n*(flexes)*\n...I wish I was as strong as he is.... :^)")

    
    #Legs
    await ctx.send("{}, nice choice! Now we just have leg units left! Which leg unit were you planning on using?".format(arms))
    legs = await getLegsSelection(ctx)
    if legs == "Timeout" or legs is None:
        return
    await ctx.send("{}. Man, I want a pair too!".format(legs))
    #response = ">>> **{}**```MEL PWR: {}\nRNG PWR: {}\nTEC PWR: {}\nHP: {}\nPP: {}\n\nMEL DEF: {}\nRNG DEF: {}\nTEC DEF: {}\n\nMEL RES: {}\nRNG RES: {}\nTEC RES: {}\nLight RES: {}\nDark RES: {}\nFire RES: {}\nIce RES: {}\nLightning RES: {}\nWind RES: {}\n\nDEX: {}```".format(legs_dict[legs]['Unit'], legs_dict[legs]['MEL pwr'], legs_dict[legs]['RNG pwr'], legs_dict[legs]['TEC pwr'], legs_dict[legs]['HP'], legs_dict[legs]['PP'], legs_dict[legs]['M DEF'], legs_dict[legs]['R DEF'], legs_dict[legs]['T DEF'], legs_dict[legs]['M RES'], legs_dict[legs]['R RES'], legs_dict[legs]['T RES'], legs_dict[legs]['Light RES'], legs_dict[legs]['Dark RES'], legs_dict[legs]['Fire RES'], legs_dict[legs]['Ice RES'], legs_dict[legs]['Lightning RES'], legs_dict[legs]['Wind RES'], legs_dict[legs]['DEX'])
    #await ctx.send(response)

    
    #Stat total counters
    melee_power = 0
    range_power = 0
    tec_power = 0
    hp = 0
    pp = 0
    melee_defense = 0
    range_defense = 0
    tec_defense = 0
    melee_resist = 0
    range_resist = 0
    tec_resist = 0
    light_resist = 0
    dark_resist = 0
    fire_resist = 0
    ice_resist = 0
    lightning_resist = 0
    wind_resist = 0
    dexterity = 0

    
    #Set effects
    
    #Ray set
    #Conditions: Back, Arms, Legs	Boost: 60 DEX
    if( (back == "Back / Circuray" or back == "Back / Circunion") and (arms == 'Arms / Circaray' or arms == 'Arms / Circaunion') and (legs == 'Legs / Circuray' or legs == 'Legs / Circunion') ):
        dexterity += 60


    #Ophistia Set 1 [Austere set]
    #Conditions: Back and Arms, Boost: All atk 80, 50 dex, 3 ice res, 3 wind res, 3 light res, 50 HP, 20PP
    if (back == 'Back / Ofzeterious' and arms == 'Arms / Ofzende'):
        melee_power += 80
        range_power += 80
        tec_power += 80
        melee_defense += 100
        range_defense += 100
        tec_defense += 100
        hp += 50
        pp += 20
        ice_resist += 3
        wind_resist += 3
        light_resist += 3


    #Ophistia Set 2 [Austere set]
    #Conditions: Legs and Weapon, Boost: All Def + 100, 50 dex, 3 ice res, 3 wind res, 3 light res 
    if(legs == 'Legs / Ofzetrogie'):
        await ctx.send("You said you were using 'Legs / Ofzetrogie'. Do you plan on using an Austere weapon too? Yes or No")
        austere = await AustereCheck(ctx)
        
        if austere == 'yes':
            dexterity += 50
            melee_defense += 100
            range_defense += 100
            tec_defense += 100
            ice_resist += 3
            wind_resist += 3
            light_resist +=3

#Adds all the stats from stored in the unit dictionaries based on the user's unit selections, casts data as an int
    melee_power += int(back_dict[back]['MEL pwr']) + int(arms_dict[arms]['MEL pwr']) + int(legs_dict[legs]['MEL pwr'])
    range_power += int(back_dict[back]['RNG pwr']) + int(arms_dict[arms]['RNG pwr']) + int(legs_dict[legs]['RNG pwr'])
    tec_power += int(back_dict[back]['TEC pwr']) + int(arms_dict[arms]['TEC pwr']) + int(legs_dict[legs]['TEC pwr'])
    hp += int(back_dict[back]['HP']) + int(arms_dict[arms]['HP']) + int(legs_dict[legs]['HP'])
    pp += int(back_dict[back]['PP']) + int(arms_dict[arms]['PP']) + int(legs_dict[legs]['PP'])
    melee_defense += int(back_dict[back]['M DEF']) + int(arms_dict[arms]['M DEF']) + int(legs_dict[legs]['M DEF'])
    range_defense += int(back_dict[back]['R DEF']) + int(arms_dict[arms]['R DEF']) + int(legs_dict[legs]['R DEF'])
    tec_defense += int(back_dict[back]['T DEF']) + int(arms_dict[arms]['T DEF']) + int(legs_dict[legs]['T DEF'])
    melee_resist += int(back_dict[back]['M RES']) + int(arms_dict[arms]['M RES']) + int(legs_dict[legs]['M RES'])
    range_resist += int(back_dict[back]['R RES']) + int(arms_dict[arms]['R RES']) + int(legs_dict[legs]['R RES'])
    tec_resist += int(back_dict[back]['T RES']) + int(arms_dict[arms]['T RES']) + int(legs_dict[legs]['T RES'])
    light_resist += int(back_dict[back]['Light RES']) + int(arms_dict[arms]['Light RES']) + int(legs_dict[legs]['Light RES'])
    dark_resist += int(back_dict[back]['Dark RES']) + int(arms_dict[arms]['Dark RES']) + int(legs_dict[legs]['Dark RES'])
    fire_resist += int(back_dict[back]['Fire RES']) + int(arms_dict[arms]['Fire RES']) + int(legs_dict[legs]['Fire RES'])
    ice_resist += int(back_dict[back]['Ice RES']) + int(arms_dict[arms]['Ice RES']) + int(legs_dict[legs]['Ice RES'])
    lightning_resist += int(back_dict[back]['Lightning RES']) + int(arms_dict[arms]['Lightning RES']) + int(legs_dict[legs]['Lightning RES'])
    wind_resist += int(back_dict[back]['Wind RES']) + int(arms_dict[arms]['Wind RES']) + int(legs_dict[legs]['Wind RES'])
    dexterity += int(back_dict[back]['DEX']) + int(arms_dict[arms]['DEX']) + int(legs_dict[legs]['DEX'])

    await ctx.send("Alright {}! I've finally added up all the numbers!".format(ctx.author.display_name))
    
    response = "**({}) ({}) ({})**```\nMEL PWR: {}\nRNG PWR: {}\nTEC PWR: {}\nHP: {}\nPP: {}\n\nMEL DEF: {}\nRNG DEF: {}\nTEC DEF: {}\n\nMEL RES: {}\nRNG RES: {}\nTEC RES: {}\nLight RES: {}\nDark RES: {}\nFire RES: {}\nIce RES: {}\nLightning RES: {}\nWind RES: {}\n\nDEX: {}\n```".format(back_dict[back]['Unit'], arms_dict[arms]['Unit'], legs_dict[legs]['Unit'], melee_power, range_power, tec_power, hp, pp, melee_defense, range_defense, tec_defense, melee_resist, range_resist, tec_resist, light_resist, dark_resist, fire_resist, ice_resist, lightning_resist, wind_resist, dexterity)
    await ctx.send(response)




#************** host() ****************
#User command to organize/gather signups for guild events
#Prompts the user for the guild, event name, party type and event start time with fun dialogue.
#This command is can only be used in private messages to avoid clutter on guild chat channels

#Notes: This command was the reason this bot was created. The public PSO2 bot that was offered [Matoi-chan] also had a signup system
#The usage of that bot's event hosting command was very rigid/unforgiving to mistakes and did not give good feedback/recovery. So Hoshii was orignally made to supplement what Matoi lacked for event hosting
@client.command(description='Host an alliance event using Hoshii-kun\'s built in signup system. You will be prompted via DMs for the event\'s name, party size and time/timezone. Event signup will be posted on the alliance events channel. For event times, you may use relative times such as "in 20 minutes or tomorrow at 12 EDT" or alternatively, a full date such as "December 25th at 1:00PM EDT"')
@commands.max_concurrency(1, per=BucketType.user, wait=False)
async def host(ctx, *args):
    if not isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.author.send("Hi {}! Hosting is only done from DMs, so feel free to type /host again here to get started".format(ctx.author.display_name))
        return
                
    await ctx.author.send("Hi {}! So I hear you wanted to run an event huh?".format(ctx.author.display_name))
    await ctx.author.send("...What? You wanted my help organizing it?!? Well okay, but only because it's you who asked ♡")

    
    #Guild
    guild = await getGuildSelection(ctx)
    if guild == "Timeout" or guild is None:
        return
        
    await ctx.author.send("Wow! The folks at {} sure are lucky to have you {}. Organizing events is hard work ya'know?".format(guild.name, ctx.author.display_name))
    
    
    #Event Name
    await ctx.author.send("\nNow then, let's get started! What would you like the event to be named?")
    eventName = await getEventName(ctx)
    if eventName == "Timeout" or eventName is None:
        return
    await ctx.author.send("{}? {}! That's a nice name!".format(eventName.content, ctx.author.display_name))
    
    
    #Party Type
    await ctx.author.send("Now, is this for a party of 4, a multiparty of 8, a multiparty of 12 or an unlimited party?")
    partyType = await getPartyType(ctx)
    if partyType == "Timeout" or partyType is None:
        return
    await ctx.author.send("{} people, got it {}!".format(partyType.content, ctx.author.display_name))        


    #Date 
    await ctx.author.send("Now, can you tell me when your event will be? You can tell me the date, time and timezone.")        
    date = await getEventDate(ctx)
    if date == "Timeout" or date is None:
        return

            
    await ctx.author.send("Got it {}! Your event's time will be {}".format(ctx.author.display_name, date))

                
    host = guild.get_member(ctx.author.id).nick
    if host is None:
        host = guild.get_member(ctx.author.id).display_name
        
    await ctx.author.send("Here's what I have:```\n[Event Name] {}\n[Hosted by] {}\n[Party size] {}\n[Date/Time] {}\n```".format(eventName.content, host, partyType.content, date))    
    await ctx.author.send("I'll go tell the others now! You can count on me {} ❤️".format(ctx.author.display_name))
                
    event = GuildEvent(guild, eventName.content, partyType.content, date, host)

    await event.listEventInfo()
    event_ID = await event.shareEvent()
    
    reminder_time = event.eventTime.astimezone(pytz.utc) - timedelta(minutes = 15)
    notifier.add_job(notify, 'date', run_date=reminder_time, args = [event_ID])




#************** loadAllEventNotifs() ****************
#When Hoshii boots up, Hoshii goes through the servers he is a member of and looks for recent posts he made in 'event-hosting'
#For posts he created, he grabs the message ID and tries to see if it's associated with an event ID [event IDs are stored as the event post's message ID]
#If there is an event post and event match inside the DB, we assume the event is still going on because the event post was not deleted.
#We then add the event to the notifier scheduler so we can notify signups when the event is about to start.
async def loadAllEventNotifs():
    for guild in client.guilds:
        channels = guild.text_channels
        for i in channels:
            if(i.name) == ('event-hosting'):
                event_channel = i
        async for message in event_channel.history(limit = 100):
            if message.author == client.user:
                event = await loadEvent(message.id)

                reminder_time = event.eventTime.astimezone(pytz.utc) - timedelta(minutes = 15)
                notifier.add_job(notify, 'date', run_date=reminder_time, args = [event.event_ID])
                #notifier.print_jobs()




#************** on_raw_reaction_add ****************
#This function handles reactions to event posts
#Reacting with the heart emoji signs the reacting person up for the event
#Reacting with the clock emoji sends the reacting person with a list of timezone conversions for the event start time
@client.event
async def on_raw_reaction_add(payload):
    #Initializes fn with reaction information
    message_id = payload.message_id
    emoji = payload.emoji
    channel = client.get_channel(payload.channel_id)
    guild = client.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)


    #If reaction is from a bot, exit
    if member.bot:
        return
    
    
    #If channel doesn't register, exit
    if channel is None:
        return
    
    
    #Grabs the message id from the reacted message
    message = await channel.fetch_message(message_id)
    
    
    #Checks if the message ID being reacted to is associated with an event, if it isn't, exit
    event = await loadEvent(message_id)
    if event is None:
        return
    
    #If the reaction is this clock emoji, send event's timezone conversions to the user reacting
    if str(emoji) == '🕒':
        timezones = ['US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific', 'US/Hawaii', 'US/Alaska', 'Brazil/East', 'Europe/Brussels', 'Europe/Madrid', 'Europe/London', 'Europe/Paris', 'Europe/Rome', 'Europe/Berlin', 'Europe/Budapest', 'Europe/Bucharest', 'Europe/Moscow', 'Europe/Kiev', 'Asia/Ho_Chi_Minh', 'Asia/Jakarta', 'Asia/Manila', 'Asia/Seoul', 'Asia/Shanghai', 'Australia/Queensland', 'Australia/Broken_Hill', 'Australia/West']
        await member.send("Hi {}! I heard that you were interested in some of {}'s timezones. I have prepared a list of some common timezones just for you ️❤️".format(member.display_name, event.eventName))
        time_list = "**[Timezone Conversions]**"
        tz_string = ""
        format = "%Y/%m/%d @ %H:%M %Z"
        for i in timezones:
            timezone = pytz.timezone(i)
            time = event.eventTime.astimezone(timezone)
            tz_string = tz_string + "```\n" + "[{}] ".format(i) + time.strftime(format) + "\n```"
        await member.send(time_list + tz_string)        
    
    
    #If the reaction is not this heart emoji, we can exit
    if str(emoji) != '❤️':
        #print("not heart")
        return
    
    
    #Prepares the time format string since we update the post as people register/unregister for events
    event.eventTime = event.eventTime.astimezone(pytz.utc)
    formatted_time = event.eventTime.strftime("%Y/%m/%d @ %H:%M %Z")
    
    #This branch updates the event post and database list when a user signs up. It will block a signup if the party limit has been reached.
    if event.partyType == '4':
        if len(event.playerList) < 4:
            if payload.user_id not in event.playerList:
                event.playerList.append(payload.user_id)
            
            print(event.playerList)
            event.eventToDB()
            base_string = "**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}\n\n**PARTY MEMBERS**".format(event.eventName, event.host, event.partyType, formatted_time)
            addon_string = ""
            for i in event.playerList:
                addon_string = addon_string + "```\n" +guild.get_member(i).display_name + "\n```"
                #print (i)
                
            spots_left = int(event.partyType) - len(event.playerList)
            if spots_left > 0:
                str_spots_Left = "\nThere are **{}** spots left!".format(spots_left)
            elif spots_left == 0:
                str_spots_Left = "\nThe party is currently **FULL**"
            await message.edit(content = base_string + addon_string + str_spots_Left)
        else:
            await member.send("Sorry {}! The party is full!".format(member.display_name))
            await message.remove_reaction(emoji, client.get_user(payload.user_id))
    elif event.partyType == '8':
        if len(event.playerList) < 8:
            if payload.user_id not in event.playerList:
                event.playerList.append(payload.user_id)
            
            print(event.playerList)
            event.eventToDB()
        
            base_string = "**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}\n\n**PARTY MEMBERS**".format(event.eventName, event.host, event.partyType, formatted_time)
            addon_string = ""
            for i in event.playerList:
                addon_string = addon_string + "```\n" +guild.get_member(i).display_name + "\n```"
                #print (i)
            spots_left = int(event.partyType) - len(event.playerList)
            if spots_left > 0:
                str_spots_Left = "\nThere are **{}** spots left!".format(spots_left)
            elif spots_left == 0:
                str_spots_Left = "\nThe party is currently **FULL**"
            await message.edit(content = base_string + addon_string + str_spots_Left)
        else:
            await member.send("Sorry {}! The party is full!".format(member.display_name))
            await message.remove_reaction(emoji, client.get_user(payload.user_id))
    elif event.partyType == '12':
        if len(event.playerList) < 12:
            if payload.user_id not in event.playerList:
                event.playerList.append(payload.user_id)
            
            print(event.playerList)
            event.eventToDB()
        
            base_string = "**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}\n\n**PARTY MEMBERS**".format(event.eventName, event.host, event.partyType, formatted_time)
            addon_string = ""
            for i in event.playerList:
                addon_string = addon_string + "```\n" +guild.get_member(i).display_name + "\n```"
                #print (i)
            spots_left = int(event.partyType) - len(event.playerList)
            if spots_left > 0:
                str_spots_Left = "\nThere are **{}** spots left!".format(spots_left)
            elif spots_left == 0:
                str_spots_Left = "\nThe party is currently **FULL**"
            await message.edit(content = base_string + addon_string + str_spots_Left)
        else:
            await member.send("Sorry {}! The party is full!".format(member.display_name))
            await message.remove_reaction(emoji, client.get_user(payload.user_id))
    elif event.partyType == 'unlimited':
        if payload.user_id not in event.playerList:
            event.playerList.append(payload.user_id)
            
        print(event.playerList)
        event.eventToDB()
        
        base_string = "**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}\n\n**PARTY MEMBERS**".format(event.eventName, event.host, event.partyType, formatted_time)
        addon_string = ""
        for i in event.playerList:
            addon_string = addon_string + "```\n" +guild.get_member(i).display_name + "\n```"
            #print (i)
            
        await message.edit(content = base_string + addon_string)
        
    #await channel.send("{} reacted with {} to {}".format(member.nick, emoji, message.content))





#************** on_raw_reaction_remove ****************
#This function handles reactions to event posts
#Unreacting to the heart emoji deregisters the reactor from the event
@client.event       
async def on_raw_reaction_remove(payload):
    #Initialize message data from unreacted message
    message_id = payload.message_id
    emoji = payload.emoji
    channel = client.get_channel(payload.channel_id)
    guild = client.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    
    
    #Ignores unreacts from bots
    if member.bot:
        return
    

    #Exits if channel doesn't register in initialization
    if channel is None:
        return
   
    
    #Grabs message ID from the unreacted message    
    message = await channel.fetch_message(message_id)
    
    
    #Checks to see if the message being unreacted to is associated with an event, if it isn't, exits
    event = await loadEvent(message_id)
    if event is None:
        return

    #If the unreacted emoji isn't this heart emoji, exit
    if str(emoji) != '❤️':
        #print("not heart")
        return
    
    
    #Prepares time format string for when event post gets updated
    event.eventTime = event.eventTime.astimezone(pytz.utc)
    formatted_time = event.eventTime.strftime("%Y/%m/%d @ %H:%M %Z")


    if event.partyType == 'unlimited':
            if payload.user_id in event.playerList:
                event.playerList.remove(payload.user_id)
           
            print(event.playerList)
            event.eventToDB()
            base_string = "**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}\n\n**PARTY MEMBERS**".format(event.eventName, event.host, event.partyType, formatted_time)
            addon_string = ""
            for i in event.playerList:
                addon_string = addon_string + "```\n" +guild.get_member(i).display_name + "\n```"
                #print (i)
                
            await message.edit(content = base_string + addon_string)
    else:        
        if payload.user_id in event.playerList:
            event.playerList.remove(payload.user_id)
            
        print(event.playerList)
        event.eventToDB()
        base_string = "**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}\n\n**PARTY MEMBERS**".format(event.eventName, event.host, event.partyType, formatted_time)
        addon_string = ""
        for i in event.playerList:
            addon_string = addon_string + "```\n" +guild.get_member(i).display_name + "\n```"
            #print (i)
        spots_left = int(event.partyType) - len(event.playerList)
        if spots_left > 0:
            str_spots_Left = "\nThere are **{}** spots left!".format(spots_left)
        elif spots_left == 0:
            str_spots_Left = "\nThe party is currently **FULL**"
        await message.edit(content = base_string + addon_string + str_spots_Left)

#Shameful redundant code oops -w-        
'''       
    if event.partyType == '4':
        if payload.user_id in event.playerList:
            event.playerList.remove(payload.user_id)
        
        print(event.playerList)
        event.eventToDB()
        base_string = "**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}\n\n**PARTY MEMBERS**".format(event.eventName, event.host, event.partyType, formatted_time)
        addon_string = ""
        for i in event.playerList:
            addon_string = addon_string + "```\n" +guild.get_member(i).display_name + "\n```"
            #print (i)
        spots_left = int(event.partyType) - len(event.playerList)
        if spots_left > 0:
            str_spots_Left = "\nThere are **{}** spots left!".format(spots_left)
        elif spots_left == 0:
            str_spots_Left = "\nThe party is currently **FULL**"
        await message.edit(content = base_string + addon_string + str_spots_Left)
    elif event.partyType == '8':
        if payload.user_id in event.playerList:
            event.playerList.remove(payload.user_id)
       
        print(event.playerList)
        event.eventToDB()
        base_string = "**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}\n\n**PARTY MEMBERS**".format(event.eventName, event.host, event.partyType, formatted_time)
        addon_string = ""
        for i in event.playerList:
            addon_string = addon_string + "```\n" +guild.get_member(i).display_name + "\n```"
            #print (i)
        spots_left = int(event.partyType) - len(event.playerList)
        if spots_left > 0:
            str_spots_Left = "\nThere are **{}** spots left!".format(spots_left)
        elif spots_left == 0:
            str_spots_Left = "\nThe party is currently **FULL**"
        await message.edit(content = base_string + addon_string + str_spots_Left)    
    elif event.partyType == '12':
        if payload.user_id in event.playerList:
            event.playerList.remove(payload.user_id)
       
        print(event.playerList)
        event.eventToDB()
        base_string = "**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}\n\n**PARTY MEMBERS**".format(event.eventName, event.host, event.partyType, formatted_time)
        addon_string = ""
        for i in event.playerList:
            addon_string = addon_string + "```\n" +guild.get_member(i).display_name + "\n```"
            #print (i)
        spots_left = int(event.partyType) - len(event.playerList)
        if spots_left > 0:
            str_spots_Left = "\nThere are **{}** spots left!".format(spots_left)
        elif spots_left == 0:
            str_spots_Left = "\nThe party is currently **FULL**"
        await message.edit(content = base_string + addon_string + str_spots_Left)
    elif event.partyType == 'unlimited':
        if payload.user_id in event.playerList:
            event.playerList.remove(payload.user_id)
       
        print(event.playerList)
        event.eventToDB()
        base_string = "**[Event Name]** {}\n**[Hosted by]** {}\n**[Party size]** {}\n**[Date/Time]** {}\n\n**PARTY MEMBERS**".format(event.eventName, event.host, event.partyType, formatted_time)
        addon_string = ""
        for i in event.playerList:
            addon_string = addon_string + "```\n" +guild.get_member(i).display_name + "\n```"
            #print (i)
            
        await message.edit(content = base_string + addon_string)
    #await channel.send("{} unreacted their {} to {}".format(member.nick, emoji, message.content))        
'''

client.run(TOKEN)
