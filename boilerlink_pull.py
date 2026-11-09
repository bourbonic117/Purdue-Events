#TECH 120 Group 3 Final Project (Purdue Event Data Scraper)
import requests

#BoilerLink pulls their events from the following website JSON API.
events2 = 10
boilerlink = "https://boilerlink.purdue.edu/api/discovery/event/search"
pullinfoBL = requests.get(boilerlink,params={"status": "Approved", "take": events2, "skip": 0}) #take: # of events pulled | skip: # of events skipped before pulling
data = pullinfoBL.json()

#cuts everything before 'value' phrase in original JSON
events = data["value"]

#filters out all unnecessary fields from filtered list.
filtereddata = [
    [
        event["organizationName"],
        event["name"],
        event["description"],
        event["location"],
        event["startsOn"],
        event["endsOn"],
        event["imagePath"],
        event["theme"]
    ]
    for event in events #repeats to find all qualified 'events'
]

#Removing HTML tags from description field
for event in filtereddata:
    for i in range(len(event)):
        if i == 2 and event[i] is not None:
            event[i] = event[i].strip("<p>")
            event[i] = event[i].strip("&ndash;")
            event[i] = event[i].strip("div>")
            event[i] = event[i].strip("class=")
            event[i] = event[i].strip("&nbsp;")
            event[i] = event[i].strip("</p>")
            event[i] = event[i].strip("*")
            event[i] = event[i].strip("</p>\r\n<p>&nbsp;")
            event[i] = event[i].strip("</p>\r\n<p>&nbsp;</p>\r\n<p>")
            event[i] = event[i].strip("</p>\r\n<p>")
            event[i] = event[i].strip("&nbsp;<br />")


print ("The Following is a list of the next {events2} events from BoilerLink:")

for event in filtereddata:
    #Beautification & Ease of Reading
    print (event)
    print ("\n")

#---------------------Troubleshooting & Development----------------
#print (data)
#print ("\n \n \n")
#print (filtereddata)
