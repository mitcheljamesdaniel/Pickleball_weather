#pickleball weather shiny

#import api stuff
from optparse import AmbiguousOptionError
from turtle import setundobuffer
import requests
import json
import shiny
import pandas
from htmltools import HTML
import datetime
import time

def get_time(x):
    return time.strptime(x, '%H:%M:%S')

#define weather class
#each weather object encompasses the weather conditions for a given 3h time window
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
        self.day = True #overwritten by check_day method
    
    def check_day(self): #checks whether the time window is during the day (6:00 am to 11:00 pm)
        self.day = self.time > "05:59:00" and self.time < "22:59:00"
        return self.day
    
    def report_time(self):
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
        return time_range
    
    def report_temp(self):
        #report the temperature
        return "Temp: " + str(self.temp) + u'\N{DEGREE SIGN}' + "F (feels like " + str(self.feels_like) + u'\N{DEGREE SIGN}' + "F)"
        
    def report_speed(self):
        #report the wind speed
        return "Wind speed: " + str(self.speed) + "mph"
        
    def report_precip(self):
        #report precipitation
        return "Chance of precipidation: " + str(self.precip) + "%\n"

#define state abbrevation choices
states = ["AL", "AK", "AZ", "AR", "AS", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "GU", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", 
          "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "MP", "OH", "OK", "OR", "PA", 
          "PR", "RI", "SC", "SD", "TN", "TX", "TT", "UT", "VT", "VA", "VI", "WA", "WV", "WI", "WY"]

#set the style of the columns and rows in the output panel
style="border: 1px solid #999;"

#create the shiny app
app_ui = shiny.ui.page_fluid(
    shiny.ui.panel_title("Find a time to play outdoor pickleball"),
    shiny.ui.layout_sidebar(
        shiny.ui.panel_sidebar(
            shiny.ui.input_text("city", "City:", placeholder="Enter city name"),
            shiny.ui.input_selectize("state", "State:", states),
            shiny.ui.input_slider("temp_range", "Temperature range (F):", value = (40, 90), min = 30, max = 110),
            shiny.ui.input_slider("max_precip", "Max chance of precipitation (%):", value = 30, min = 0, max = 100),
            shiny.ui.input_numeric("max_speed", "Max wind speed (mph):", 15),
            shiny.ui.input_action_button("compute", "Generate Calendar", class_="btn-primary")
        ),
        shiny.ui.panel_main(
            shiny.ui.output_text("txt"),
            shiny.ui.output_text("geo_API_test"),
            shiny.ui.output_text("geo_results"),
            shiny.ui.output_text("geo_lat"),
            shiny.ui.output_text("geo_lon"),
            shiny.ui.output_text("weather_test"),
            shiny.ui.output_text("weather_results"),
            shiny.ui.output_text("weather_list_output"),
            shiny.ui.output_text("filtered_list_output"),
            shiny.ui.output_text("list_of_days_output"),
            shiny.ui.output_text("report_conditions"),
            shiny.ui.row( #row of date headings
                shiny.ui.column(6, shiny.ui.output_text_verbatim("day_dictionary_output"), style=style),
                shiny.ui.column(6, "row-1 col-2", style=style),
            shiny.ui.output_table("make_table")
            )
        )
    )
)


def server(input, output, session):
    @shiny.reactive.Calc
    def geo_params(): #return a dictionary with the geo_parameters
        return {
            "q": input.city() + "," + input.state() +  ",US",
            "appid": "b0fb1574b0176f4025a21cfea6f99005",
            "limit": 1
            }
    
    @shiny.reactive.Calc
    def geo_request(): #return geo API request
        input.compute() #creates a dependency on the button (makes this function execute only if the button is pressed)

        with shiny.reactive.isolate(): #eliminates dependencies in this code chunk (i.e. changes to inputs used in this code chunk do NOT cause the chunk to be re-executed (to avoid excessive API requests)
            return requests.get("http://api.openweathermap.org/geo/1.0/direct?", params = geo_params())
    
    @output
    @shiny.render.text
    def geo_API_test(): #tell user whether geo data is available for the location they input
        if geo_request().status_code == 200 and len(geo_request().json()) == 1:
            return "Successfully pulled geographical data." #keep this for debugging, delete afterwards
        else:
            return "Error: data for this location could not be found. Please check that the location information is accurate."
    
    @shiny.reactive.Calc
    def weather_params(): #create dictionary of parameters for weather API request
        return {
            "lat": geo_request().json()[0]['lat'],
            "lon": geo_request().json()[0]['lon'],
            "appid": "b0fb1574b0176f4025a21cfea6f99005",
            "exclude": "current,minutely,hourly",
            "units": "imperial"
            }
    
    @shiny.reactive.Calc
    def weather_request(): #returns weather API request
        input.compute()

        with shiny.reactive.isolate():
            return requests.get("http://api.openweathermap.org/data/2.5/forecast?id=524901", params = weather_params())
    
    @output
    @shiny.render.text
    def weather_test(): #return whether weather API request was successful
        if weather_request().status_code == 200 and len(weather_request().json()) > 0:
            return "Successfully pulled weather data."
        else:
            return "Error: weather data is not currently available for this location. Please try again later."
    
    def weather_list(): #create list of weather objects, one for each entry in the weather dictionary
        return [weather(i) for i in weather_request().json()['list']]
    
    def day_index(): #create index filter based on whether each time window is during the day (6:00 am to 11:00 pm)
        return [j.check_day() for j in weather_list()]
    
    def filtered_list(): #have each weather object determine whether it meets the play conditions
        return [weather_list()[k] for k in range(len(weather_list())) if day_index()[k]]
    
    @shiny.reactive.Calc
    def min_temp():
        return input.temp_range()[0]
    
    @shiny.reactive.Calc
    def max_temp():
        return input.temp_range()[1]
    
    @shiny.reactive.Calc
    def max_speed():
        return input.max_speed()
    
    @shiny.reactive.Calc
    def max_precip():
        return input.max_precip()
    
    @shiny.reactive.Calc
    def day_sorting(): #creates a list of (sub)lists, where each sublist is the weather objects for a given day, in chronological order
        list_of_days = [] #create a list
        list_of_days.append([]) #make the first element in the list an empty list
        prev_date = filtered_list()[0].date #start with the first date as the current date
        day_index = 0 
        for m in range(len(filtered_list())):
            if filtered_list()[m].date == prev_date: #if the weather object's date is the same as the previous object's date, then add it to the current date's list of objects
                list_of_days[day_index].append(filtered_list()[m])
            else: #otherwise, add a new empty list (representing the next day), increment the day index, and add the weather object to the new day
                list_of_days.append([])
                day_index = day_index + 1
                list_of_days[day_index].append(filtered_list()[m])
                prev_date = filtered_list()[m].date
        
        return list_of_days
    
    def time_windows(): #time windows, used for leftmost column in the table
        times = ""
        for window in ("6:00 am - 9:00 am", "9:00 am - 12:00 pm", "12:00 pm - 3:00 pm", "3:00 pm - 6:00 pm", "6:00 pm - 9:00 pm", "9:00 pm - 12:00 am"):
            times = times + window + "\n\n\n\n"
        return times

    def day_dictionary(): #returns a dictionary with the column headings for keys and the daily weather reports for values
        day_dictionary = {}
        day_dictionary["Time of day"] = time_windows().split("\n") #make empty dictionary
        for day in day_sorting(): #for each day (which is a list of weather objects)
            day_report = "" #day_report is a long string containing all of the weather info for that day
            for time_point in ("06:00:00", "09:00:00", "12:00:00", "15:00:00", "18:00:00"): #add a chunk of whitespace to the day's report for each time window missing before the first weather object's time window
                if get_time(day[0].time) > get_time(time_point):
                    day_report = day_report + f"No Data, first time is {day[0].time}, which is after {time_point}\n\n\n\n" #text is for testing, change to just empty lines
            for o in day: #for every time window on the day
                if o.temp > min_temp() and o.temp < max_temp() and o.speed < max_speed() and o.precip < max_precip():
                    day_report = day_report + f"Great conditions! \nTemp: {o.temp}" + u'\N{DEGREE SIGN}' + f"F (feels like {o.feels_like}" + u'\N{DEGREE SIGN}' + f"F) \nWind speed: {o.speed} mph \nChance of precipitation: {o.precip}% \n "
                else:
                    day_report = day_report + "Unsuitable conditions. \n\n\n\n"
            for time_point in ("21:00:00", "18:00:00", "15:00:00", "12:00:00", "09:00:00"):
                if get_time(day[-1].time) < get_time(time_point):
                    day_report = day_report + f"No Data, last time is {day[0].time}, which is after {time_point}\n\n\n\n" #text is for testing, change to just empty lines
            day_dictionary[day[0].date] = day_report.split("\n")
        return day_dictionary
    
    @output
    @shiny.render.table
    def make_table(): #converts dictionary of reports into a data frame
        return pandas.DataFrame(data = day_dictionary()) #if I get an "Error, can't use only scale values", put the dictionary in []

    #consider splitting up each day into multiple elements to that I can use table formatting to highlight / color code the good tmies to play

    #tweak code so that if the city name is empty, it will display something instead of the table of outputs (e.g. "Please enter a city name") to make the output panel less ugly while waiting


    #make output a table with one results row, with the date as the heading for the column, and the time windows in the leftmost column


    

    #get rid of report time and check day functions - no longer used






    #debugging outputs
    @output
    @shiny.render.text
    def geo_results():
        return f"{geo_request().json()}"
    
    @output
    @shiny.render.text
    def geo_lat():
        return f"{geo_request().json()[0]['lat']}"
    
    @output
    @shiny.render.text
    def geo_lon():
        return f"{geo_request().json()[0]['lon']}"
    
    @output
    @shiny.render.text
    def weather_test_output():
        return weather_test()

    @output
    @shiny.render.text
    def weather_results():
        return f"{weather_request().json()}"
    
    @output
    @shiny.render.text
    def weather_list_output():
        return f"{len(weather_list())}"

    @output
    @shiny.render.text
    def filtered_list_output():
        return f"{len(filtered_list())}"
    
    @output
    @shiny.render.text
    def list_of_days_output():
        return day_sorting()
    
    @output
    @shiny.render.text
    def day_dictionary_output():
        return day_dictionary()
    
    @output
    @shiny.render.text
    def report_conditions():
        return str(filtered_list()[0].temp) + str(filtered_list()[0].precip) + str(filtered_list()[0].speed)









    #example output function - delete this and corresponding ui.output
    @output
    @shiny.render.text
    def txt():
        input.compute() #creates a dependency on the button (makes this function execute only if the button is pressed)

        with shiny.reactive.isolate(): #changes to the dependencies (inputs) in this code chunk do NOT cause the function to be re-executed
            return f"The location is {geo_params()['q']}"






app = shiny.App(ui=app_ui, server=server) 



####NOTE: need to tweak code to parse the input from the temp slider into min temp and max temp variables
#do this outside of the weather class to avoid repeating the computation?


#Indicate in UI somewhere that it's (currently) limited to cities in the US?

#use shiny.input.compute() and with shiny.reactive.isolate(): to make it so the code chunks that make API requests only react (i.e. re-execute) in response to 
#   in the functions that make API requests, place the shiny.input.compute() line at the top so that the function has a dependency on the button
#   place the API request part nested inside the with shiny.reactive.isolate(): line to that other inputs DON'T trigger it 


#add something to prevent the calender (or other outputs) from being displayed when the information location is incorrect?