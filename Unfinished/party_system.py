import math



class Player:

    def __init__(self, name, roles):
        self.name = name
        self.roles = roles
    
    
    #Checks if a player has a role
    def hasRole(self, roleName):
        if roleName.lower() in map(str.lower, self.roles):
            return True
        else:
            return False




class Party:
    numMembers = 0
    
    #Doing it like this since party size is fixed anyways
    def __init__(self, leader, member2, member3, member4):
        self.leader = leader
        self.member2 = member2
        self.member3 = member3
        self.member4 = member4
        Party.numMembers = 0
        
    
    def listMembers(self):
        if self.leader:
            print ("\n1: ", self.leader.name, " (leader)")
        else:
            print ("\n1: None")
        
        if self.member2:
            print ("2: ", self.member2.name)
        else:
            print ("2: None")

        if self.member3:
            print ("3: ", self.member3.name)
        else:
            print ("3: None")
            
        if self.member4:
            print ("4: ", self.member4.name)
        else:
            print ("4: None")
    
    
    #Fun fact about python, empty strings are considered false in boolean context so this works ^^
    def isFull(self):
        if self.leader and self.member2 and self.member3 and self.member4:
            return True
        else:
            return False


    def addMember(self, member):
        if self.leader is None:
            self.leader = member
        elif self.member2 is None:
            self.member2 = member
        elif self.member3 is None:
            self.member3 = member
        elif self.member4 is None:
            self.member4 = member
         
         
         
         
class MultiParty:

    def __init__(self, party1, party2, party3):
        self.party1 = party1
        self.party2 = party2
        self.party3 = party3

    def listMultiParty(self):
        print("\nParty 1:")
        self.party1.listMembers()
        print("\nParty 2:")
        self.party2.listMembers()
        print("\nParty 3:")
        self.party3.listMembers()



        
    
#Create a 4 person hosted party  
def makeParty(host, players):
    leader = None
    player2 = None
    player3 = None
    player4 = None
    
    #This loop makes sure the host is the party leader while assigning the rest of the members in a First-Come first served basis if there's more than 4 signups
    for i in players:
        if i.name.lower() == host.lower() and leader is None:
            leader = i
        else:
            if player2 is None:
                player2 = i
            elif player3 is None:
                player3 = i
            elif player4 is None:
                player4 = i
                    
    party = Party(leader, player2, player3, player4)
    return party



#Create a 12 person multi party
def makeMultiPartyArea(players):
    numParties = 0 #The number of parties we need to make
    
    
    playerCount = len(players) #Number of players in signup
    remainder = playerCount % 4 #Number of players who cannot fit into a full party
    
    
    officers = [] #This is the list of officers we'll divide up to lead the multiparties
    members = [] #This is the list of players who aren't officers

    #Empty party objects
    party1 = Party(None, None, None, None)
    party2 = Party(None, None, None, None)
    party3 = Party(None, None, None, None)
    
    #If we can't perfectly divide parties into 4s, then we need one more party for the remaining players
    if remainder != 0:
        numParties = math.floor(playerCount/4)+1
    else:
        numParties = int(playerCount/4)
    
    
    #Maximum size for a multiparty is 3 parties, this is here for redundancy in case there are somehow more than 12 players on signup
    if numParties > 3:
        numParties = 3
    
    #Creates lists of players with officer tags and a player tags
    for i in players:
        if(i.hasRole("Officer")):
            officers.append(i)
        else:
            members.append(i)
    
    #This asigns each party a leader with officers taking priority
    for m in range(numParties):
        if m == 0:
            if officers[0]:
                party1.leader = officers[0]
                officers.pop(0)
            else:
                party1.leader = members[0]
                members.pop(0)
        if m == 1:
            if officers[0]:
                party2.leader = officers[0]
                officers.pop(0)
            else:
                party2.leader = members[0]
                members.pop(0)
        if m == 2:
            if officers[0]:
                party3.leader = officers[0]
                officers.pop(0)
            else:
                party3.leader = members[0]
                members.pop(0)
    
    #If there are leftover officers, add them to a party and pop them
    while officers:
        if party1.isFull() == False:
            party1.addMember(officers[0])
            officers.pop(0)
        elif party2.isFull() == False:
            party2.addMember(officers[0])
            officers.pop(0)
        elif party3.isFull() == False:
            party3.addMember(officers[0])
            officers.pop(0)
        if party3.isFull():
            break
            
    #If there are members that need a party still, add them to an empty party and pop them        
    while members:
        if party1.isFull() == False:
            party1.addMember(members[0])
            members.pop(0)
        elif party2.isFull() == False:
            party2.addMember(members[0])
            members.pop(0)
        elif party3.isFull() == False:
            party3.addMember(members[0])
            members.pop(0)
        if party3.isFull():
            break
    multiparty = MultiParty(party1, party2, party3)
    
    return multiparty

def main():
    player1 = Player("Selphine", ["Guest", "Rappy"])
    player2 = Player("Mina", ["Officer", "Kat"])
    player3 = Player("Rath", ["Officer", "Pirate"])
    player4 = Player("Emily", ["GRAPE", "Cutie"])
    player5 = Player("Delamora", ["GRAPE", "Elf"])
    player6 = Player("Heffie", ["Officer", "Leader"])
    player7 = Player("Shah", ["GRAPE", "RED"])
    player8 = Player("Akane", ["GRAPE", "Akane"])
    player9 = Player("Elendiel", ["FKO", "Leader"])
    player10 = Player("Kae", ["FKO", "Best Force"])
    player11 = Player("Stumb", ["Member", "Coding"])
    player12 = Player("CloudStrife", ["Member", "Coding"])
    player13 = Player("Ren", ["Gremlin Inc", "Slammed"])
    
    players = [player1, player2, player3, player4, player5, player6, player7, player8, player9, player10, player11, player12, player13]
    multiparty = makeMultiPartyArea(players)
    multiparty.listMultiParty()
    
    #party = makeParty("Mina", players)
    #party.listMembers()
    
    #party = Party(player1, player2, player3, player4)
    #party.listMembers()
main()