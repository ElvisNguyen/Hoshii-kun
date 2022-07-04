# Hoshii-kun [My retired PSO2 discord bot]
Hoshii-kun is a discord bot created for my former alliance in Phantasy Star Online 2. 

## Story
Hoshii-kun was originally a passion project created to supplement [Matoi-Chan](https://matoi.ngrok.io/), a public PSO2 bot with an event hosting feature that is more forgiving to mistakes, walks the user through event hosting step by step with feedback and offers recovery when inputs are not understood.

![Matoi bot rigid commands](https://i.imgur.com/hne09g4.png)

**Image:** *Matoi-Chan's event hosting feature was very rigid in how it took inputs to host an event. It offered poor feedback on what errors a user may have inputted incorrectly and did not offer a way to recover from these mistakes*

![Matoi bot event post](https://i.imgur.com/rZk8fQB.png)

**Image:** *Matoi-Chan's event hosting feature lacked a way for users from other timezones to find out when an event was in their time.*

![Example dialogue from hoshii-bot](https://i.imgur.com/olqi1S1.png)

**Image:** *Example dialogue from Hoshii-kun walks you through the process of entering event information with fun dialogue, it is able to accept multiple forms of input with the option of recovery if an input is not accepted*

![Signup sheet from hoshii bot](https://i.imgur.com/u8JpwSv.png)

**Image:** *Event signup interface from Hoshii-bot*

![Notifications from hoshii bot](https://i.imgur.com/plyOkGU.png)

**Image:** *Hoshii-kun will send you a private message 15 minutes before an event starts if you've signed up for it*

Hoshii eventually evolved to help people plan their gears and give useful information on upcoming scheduled urgent quests while roleplaying as a helpful friend through fun dialogues. 


## Commands

### /host
Guides you step by step through a fun dialogue to host an event on their discord server.
Will prompt the user for:

1. The discord server you'd like to host the event for [if you share more than one server with Hoshii-kun]
2. The name of the event
3. The size of the party [In PSO2, quest parties/multiparties came in sizes of 4, 8 and 12]
4. The date and time of the event


![/host usage](https://i.imgur.com/8RsPQPh.png)
![/host usage2](https://i.imgur.com/AEOQdPO.png)
** Usable through DMs only

### /uq [Retired Feature]
This command used to display upcoming scheduled urgent quests in the next 12 hours. The release of PSO2 New Genesis has put base PSO2 on life support and as a result, scheduled urgent quests have been discontinued.

![Urgent quest schedule](https://i.imgur.com/0PmA2z1.png)

### /planunits
This command walks you through the process of selecting 13* armor units in the game and calculates the stat total for all three units. 

![Unit planner](https://i.imgur.com/tafmxnB.png)

It is compatible with 12* units as well, however would require the CSVs to include them. 12* units were no longer viable armors as of Episode 6 and the bot was updated accordingly.

### /arms /legs /back /sub
Outputs a list of all the armor units inside hoshii's dictionary for that category of armor.
If an argument is given in addition to the command, Hoshii will display the unit's stats instead.

![example usage](https://i.imgur.com/tfUMrrr.png)


### Acknowledgements / Special Thanks
I would like to thank the entire Yume R&D Ops team for helping me test/intentionally break the bot's features while the bot was still in development.
Special thanks to [@alairon](https://github.com/alairon) for collaborating/coordinating with me on age gate updates and urgent quest schedule scraping.

