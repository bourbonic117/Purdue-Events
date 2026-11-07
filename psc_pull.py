#TECH 120 Group 3 Final Project (Purdue Event Data Scraper) (Boiler Link)

#Pull from Purdue Student Center Website Calendar
import requests
import bs4

Pstudentctr = "https://events.purdue.edu/group/purdue-in-indianapolis/calendar"
#No requirement of JSON decoder :)

pullinfoPSC = requests.get(Pstudentctr)

evdata = bs4.BeautifulSoup(pullinfoPSC.content, "html.parser")
#print (evdata)

#Original Information is too much for Terminal to display in VSCode.
PSCevents = []
PSCdetails = []
PSClinks = []
PSClocate = []

titles = evdata.find_all("h3", class_="em-card_title")
print (titles)
#Check through the 'Network' Section and digest the event cards??
#Review 'titles', as it has titles & their links.

for event in evdata.find_all("h3", class_="em-card_title"):
    #print(event.get_text(strip=True))
    #print("\n")
    PSCevents.append(event.get_text(strip=True))

#Marks Time AND Location. Format = <Time> , <Location>
for event in evdata.find_all("p", class_="em-card_event-text"):
    #print(event.get_text(strip=True))
    PSClocate.append(event.get_text(strip=True))

PSCcombined = set(zip(PSCevents, PSClocate[1::2], PSClocate[::2]))

#--------Troubleshooting_Problems---------------------------------

#filterevents =evdata.find_all("p", class_="em-card_event-text")
#print (PSCevents)
#print (PSClinks)
#print (PSClocate)
#print (PSCcombined)


for event in PSCcombined:
    #Display Friendly
    print("\n")
    print(event)
