#TECH 120 Group 3 Final Project (Purdue Event Data Scraper) (IU's SAPB Group)

from bs4 import BeautifulSoup
import requests
from datetime import datetime as dt

#Searches The Spot & SAPB's OrgID for their events 'published'
sapb_events_api = ("https://thespot.indianapolis.iu.edu/api/discovery/event/search")
response = requests.get(sapb_events_api, params={"status": "Approved","organizationId": 132339, "take": 8,"skip": 0,},)

events = response.json()["value"]

filtered_data = [
    [
        event["organizationName"],
        event["name"],
        BeautifulSoup(event["description"] or "", "html.parser").get_text(" ", strip=True),
        event["location"],
        event["startsOn"],
        event["endsOn"],
        event["imagePath"],
        event["theme"],
    ]
    for event in events
]

# Collects script-days time and compares against event time. if it's after, then it's published to the JSON.
#The reason why this filter exists is that The Spot accounts for previous events in its event listing.
now = dt.now()
date_str = now.strftime("%Y-%m-%d")
print (date_str)

futureevents = []

for item in filtered_data:
    #strip older events
    #print (f"Filtered: {item[1]}")
    if item[4][0:10] < date_str:
        print ("Earlier Date Detected")
        #print (item[1])
    else:
        print ("\nFuture Date Detected!")
        futureevents.append(item)


print("The Following is a list of upcoming SAPB events:")
print(f"{futureevents}")
