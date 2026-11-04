#TECH 120 Group 3 Final Project (Purdue Event Data Scraper) (Boiler Link)

#Pull from Purdue Student Centre Website Calendar
import requests
import bs4

Pstudentctr = "https://events.purdue.edu/group/purdue-in-indianapolis/calendar"
#No requirement of JSON decoder :)

pullinfoPSC = requests.get(Pstudentctr)

evdata = bs4.BeautifulSoup(pullinfoPSC.content, "html.parser")
#print (evdata)

#Original Information is too much for Terminal to handle.
PSCevents = []
PSCdetails = []


for event in evdata.find_all("h3", class_="em-card_title"):
    print(event.get_text(strip=True))
    print("\n")
    PSCevents.append(event.get_text(strip=True))
#---------------------------------------------------------------#
#NOTE: ONLY GRABS: Event Names. Other Attributes TBD..
#---------------------------------------------------------------#

#Removes Duplicate Events
PSCevents = list(set(PSCevents))
print (PSCevents)

