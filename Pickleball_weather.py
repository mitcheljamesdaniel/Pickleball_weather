#Pickleball_weather.py

from optparse import AmbiguousOptionError
from turtle import setundobuffer
import requests
import json

#take user inputs
location = input("Enter the name of your city: ")

customize = input("Do you want to customize the search? 'y' = customize, 'n' = use defaults: ") #add option to see the defaults, and then go back to this decison? or have defaults shown when the app starts up?

        #make defaults always, then override with user specs

if customize.startswith("y"): #get custom play conditions
    min_temp = input("What is the lowest temperature (in Fahrenheit) you will play in? ")
    max_temp = input("What is the highest temperature (in Fahrenheit) you will play in? ")
    max_speed = input("What is the highest windspeed (in mph) that you're okay with? ")
    max_precip = input("What is the highest risk of precipitation (on a scale of 0% to 100%) that you're okay with? ")
else: #set default play conditions
    min_temp = 40
    max_temp = 90
    max_speed = 15
    max_precip = 30

geo_parameters = {
    "q": "Terre Haute,IN,US",
    "appid": "b0fb1574b0176f4025a21cfea6f99005",
    "limit": 1
}

#use the geocoder to automate gettings the lat and lon for the user's city name
geo_response = requests.get("http://api.openweathermap.org/geo/1.0/direct?", params = geo_parameters)

if geo_response.status_code != 200:
    print("Error: data for this location could not be found. Please check the spelling of the location, or try again later.")

#create dictionary with the parameters
weather_parameters = {
    "lat": geo_response.json()[0]['lat'],
    "lon": geo_response.json()[0]['lon'],
    "appid": "b0fb1574b0176f4025a21cfea6f99005",
    "exclude": "current,minutely,hourly",
    "units": "imperial"
}

#use parameters dictionary to get data for specific location
weather_response = requests.get("http://api.openweathermap.org/data/2.5/forecast?id=524901", params = weather_parameters)

if weather_response.status_code != 200:
    print("Error: weather data is not currently available for this location. Please try again later.")

class weather: #class of objects that consist of a single entry (i.e. time window) returned by the API request
    def __init__(self, json_data):
        self.temp = int(json_data["main"]["temp"])
        self.speed = int(json_data["wind"]["speed"])
        self.precip = int(json_data["pop"]*100)
        self.feels_like = int(json_data["main"]["feels_like"])
        #self.datetime = json_data['dt_txt']
        self.date, self.time = json_data['dt_txt'].split(' ')
        self.print_date = True #true by default, but gets overwritten by the check_dates method before getting used
        self.filtered_index = 0 #overwritten by check_dates method before getting used
        self.suitable = False #false by default, but gets overwritten by the check_conditions method before getting used
        self.day = True #overwritten by check_day method
    
    def check_conditions(self): #checks whether the conditions are suitable
        if self.temp > min_temp and self.temp < max_temp and self.speed < max_speed and self.precip < max_precip:
            self.suitable = True
    
    def check_day(self): #checks whether the time window is during the day (6:00 am to 11:00 pm)
        self.day = self.time > "05:59:00" and self.time < "22:59:00"
        return self.day
    
    def report_conditions(self):
        if self.filtered_index == 0:
            print("Suitable times to play outdoor pickleball in " + geo_response.json()[0]['name'] + ", " + geo_response.json()[0]['state'] + ", " + geo_response.json()[0]['country'] + "\n")
        if self.print_date:
            print(self.date)
        #get the hour that the time window starts, and convert to int
        h_mil = int(self.time[:-6])
        #convert h from military time to standard time
        if h_mil == 12 or h_mil == 24:
            h = 12
        else:
            h = h_mil % 12
        if h_mil < 12:
            h_period = " am"
        else:
            h_period = " pm"
        #get the end of the time window
        h_t_mil = (h_mil + 3)
        if h_t_mil == 12 or h_t_mil == 24:
            h_t = 12
        else:
            h_t = h_t_mil % 12
        if h_t_mil < 12 or h_t_mil == 24:
            h_t_period = " am"
        else:
            h_t_period = " pm"
        time_range = str(h) + ":00" + h_period + " to " + str(h_t) + ":00" + h_t_period
        print(time_range)
        #report the temperature
        print("Temp: " + str(self.temp) + u'\N{DEGREE SIGN}' + "F (feels like " + str(self.feels_like) + u'\N{DEGREE SIGN}' + "F)")
        #report the wind speed
        print("Wind speed: " + str(self.speed) + "mph")
        #report precipitation
        print("Chance of precipidation: " + str(self.precip) + "%\n")
    
    def check_dates(self, filtered_index):
        self.filtered_index = filtered_index
        if filtered_index > 0:
            self.print_date = self.date != filtered_list[filtered_index-1].date
    
#create list of weather objects, one for each entry in the json dictionary
weather_list = [weather(i) for i in weather_response.json()['list']]

#create index filter based on whether each time window is during the day (6:00 am to 11:00 pm)
day_index = [j.check_day() for j in weather_list]

#filter to only keep time day time windows
filtered_list = [weather_list[k] for k in range(len(weather_list)) if day_index[k]]

#have each weather object determine whether it meets the play conditions
for j in filtered_list:
    j.check_conditions()

#get each object to determine whether it's the first object on that date
for l in range(len(filtered_list)):
    filtered_list[l].check_dates(l)

#report the conditions from the filtered weather objects
for m in filtered_list:
    m.report_conditions()





#in shiny (or some other Python library), find a way to create a graphical grid with on column per day, and one row per time window
#have the weather for each time window displayed inside its box
#graphically indicate which times are suitable (e.g. color coding and/or pickleball symbol)
#maybe highlight or put a star beside which condition(s) make a given time slot unsuitable







#include statement about when sun rises or sets?

#check whether the request was successful
print(weather_response.status_code)

#see the data
print(weather_response.json())

#define function that creates a formatted string of the Python JSON object
def jprint(obj):
    text = json.dumps(obj, sort_keys = True, indent = 4)
    print(text)

jprint(weather_response.json())

#to see the keys of the dictionary that is returned
list(weather_response.json())[0] #change the index to see different keys
#see the value associated with a given key
weather_response.json()['cod']

#to see the weather forecast part of the response
weather_response.json()['list'] #each weather entry is a different element in the list dictionary, and each corresponds to a 3-h time window, with the earliest being at 0:00 AM the day after the request was made
#latest entry is midnight 5 days from the day of the request

#access a specific entry
weather_response.json()['list'][0]

#access temperature for a specific entry
weather_response.json()['list'][0]["main"]["temp"]

#define a class of object that represents a time window, with the different variables as attributes
#place all the objects in a list
#define a function that loops through the list to remove any objects that don't meet the inclusion criteria (temp, precip, wind, etc.)
#present the user with the relevant info from the objects remaining in the list


