#pickleball weather forecast shiny app

import requests
import json
import shiny
import pandas
import time

def get_time(x):
    return time.strptime(x, '%H:%M:%S')

class weather: #define weather class, which stores and operates on one weather entry (i.e. weather in one 3-h time window)
    def __init__(self, json_data): #construct weather object on each weather entry in the weather json; store temperature, wind speed, precipitation, and datetime data as attributes
        self.temp = int(json_data["main"]["temp"])
        self.speed = int(json_data["wind"]["speed"])
        self.precip = int(json_data["pop"]*100)
        self.date, self.time = json_data['dt_txt'].split(' ')
    
    def check_day(self): #check whether the weather entry is for a relevant time of day (6:00 am to 12:00 am)
        self.day = self.time > "05:59:00" and self.time < "22:59:00"
        return self.day

#define state input options
states = ["AL", "AK", "AZ", "AR", "AS", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "GU", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", 
          "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "MP", "OH", "OK", "OR", "PA", 
          "PR", "RI", "SC", "SD", "TN", "TX", "TT", "UT", "VT", "VA", "VI", "WA", "WV", "WI", "WY"]

#create the shiny ui
app_ui = shiny.ui.page_fluid(
    shiny.ui.panel_title("Find a time to play outdoor pickleball"),
    shiny.ui.layout_sidebar( #create two-panel layout
        shiny.ui.panel_sidebar( #place inputs in the sidebar
            shiny.ui.input_text("city", "City:", placeholder="Enter city name"),
            shiny.ui.input_selectize("state", "State:", states),
            shiny.ui.input_action_button("compute", "Generate Calendar", class_="btn-primary"),
            shiny.ui.input_slider("temp_range", "Temperature range (F):", value = (40, 90), min = 30, max = 110),
            shiny.ui.input_slider("max_precip", "Max chance of precipitation (%):", value = 30, min = 0, max = 100),
            shiny.ui.input_numeric("max_speed", "Max wind speed (mph):", 15)
        ),
        shiny.ui.panel_main( #place outputs in the main panel
            shiny.ui.output_text("geo_API_test"),
            shiny.ui.output_text("weather_test"),
            shiny.ui.output_table("make_table"),
            shiny.ui.output_text("make_legend")
            )
    )
)

#create the server function
def server(input, output, session):
    @shiny.reactive.Calc
    def geo_params(): #return a dictionary with parameters for the geo API request, including user-specified city and state
        return {
            "q": input.city() + "," + input.state() +  ",US",
            "appid": "b0fb1574b0176f4025a21cfea6f99005",
            "limit": 1
            }
    
    @shiny.reactive.Calc
    def geo_request(): #return geo location data from API request
        input.compute() #reexecute this function in response to input button press
        with shiny.reactive.isolate(): #do NOT reexecute this function in response to changes in its dependencies (city or state inputs) to avoid excess API requests
            return requests.get("http://api.openweathermap.org/geo/1.0/direct?", params = geo_params())
    
    @output
    @shiny.render.text
    def geo_API_test(): #print error message if geo API request was unsuccessful (usually happens because city is misspelled or city and state are mismatched)
        if geo_request().status_code != 200 or len(geo_request().json()) != 1:
            return  "Error: Please check that the location information is accurate."
    
    @shiny.reactive.Calc
    def weather_params(): #create dictionary parameters for weather API request, including lat and lon from geo data
        return {
            "lat": geo_request().json()[0]['lat'],
            "lon": geo_request().json()[0]['lon'],
            "appid": "b0fb1574b0176f4025a21cfea6f99005",
            "exclude": "current,minutely,hourly",
            "units": "imperial"
            }
    
    @shiny.reactive.Calc
    def weather_request(): #return weather data for the chosen location
        input.compute() #reexecute this function in response to input button press
        with shiny.reactive.isolate(): #do NOT reexecute this function in response to changes in its dependencies (city or state inputs) to avoid excess API requests
            return requests.get("http://api.openweathermap.org/data/2.5/forecast?id=524901", params = weather_params())
    
    @output
    @shiny.render.text
    def weather_test(): #print error message if weather API request was unsuccessful
        if weather_request().status_code != 200 or len(weather_request().json()) == 0:
            return "Error: weather data is not currently available for this location. Please try again later."
    
    def weather_list(): #create list of weather objects, one for each entry in the weather dictionary
        return [weather(i) for i in weather_request().json()['list']]
    
    def day_index(): #create list of booleans for whether the weather object at each position is during the day (6:00 am to 12:00 pm)
        return [j.check_day() for j in weather_list()]
    
    def filtered_list(): #filter the list of weather objects to include only those for daytime entries
        return [weather_list()[k] for k in range(len(weather_list())) if day_index()[k]]
    
    @shiny.reactive.Calc
    def min_temp(): #get the user-specified minimum temperature
        return input.temp_range()[0]
    
    @shiny.reactive.Calc
    def max_temp(): #get the user-specified maximum temperature
        return input.temp_range()[1]
    
    @shiny.reactive.Calc
    def max_speed(): #get the user-specified maximum wind speed
        return input.max_speed()
    
    @shiny.reactive.Calc
    def max_precip(): #get the user-specified maximum precipitation
        return input.max_precip()
    
    @shiny.reactive.Calc
    def day_sorting(): #create a list of lists, where each of the sublists contains the weather objects for a given day
        list_of_days = []
        list_of_days.append([])
        prev_date = filtered_list()[0].date
        day_index = 0
        for m in range(len(filtered_list())):
            if filtered_list()[m].date == prev_date: #place all weather objects with the same data in the same sublist
                list_of_days[day_index].append(filtered_list()[m])
            else: #each time the weather object has a different date than the weather object before it, place it in a new sublist
                list_of_days.append([])
                day_index = day_index + 1
                list_of_days[day_index].append(filtered_list()[m])
                prev_date = filtered_list()[m].date
        return list_of_days
    
    def time_windows(): #create list of time windows, to be used as the row names in the output table
        return ["6:00 am - 9:00 am", "9:00 am - 12:00 pm", "12:00 pm - 3:00 pm", "3:00 pm - 6:00 pm", "6:00 pm - 9:00 pm", "9:00 pm - 12:00 am"]

    def day_dictionary(): #return a dictionary where each key is a column heading for the output table, and each value is the corresponding list of entires (time windows or weather objects)
        day_dictionary = {}
        day_dictionary["Time of day"] = time_windows() #create the dictionary entry for the row names
        for day in day_sorting(): #for each day, create a list of weather reports describing whether the conditions are suitable for pickleball
            day_report = []
            for time_point in ("06:00:00", "09:00:00", "12:00:00", "15:00:00", "18:00:00"): #create a blank report for each time window on the first day that preceeds the first weather entry
                if get_time(day[0].time) > get_time(time_point):
                    day_report.append(f"")
            for o in day:
                if o.temp >= min_temp() and o.temp <= max_temp() and o.speed <= max_speed() and o.precip <= max_precip(): #if conditions are suitable, create a report describing the conditions
                    day_report.append(f"\U0001f600 <br> {o.temp}" + u'\N{DEGREE SIGN}' + f"F <br>Wind: {o.speed} mph <br>Precipitation: {o.precip}% <br>")
                else: #if conditions are not suitable, create a report stating why
                    bad_report = ""
                    if o.temp < min_temp():
                        bad_report = bad_report + f"\U0001F976"
                    if o.temp > max_temp():
                        bad_report = bad_report + f"\U0001F975"
                    if o.speed > max_speed():
                        bad_report = bad_report + f"\U0001f32a\uFE0F"
                    if o.precip > max_precip():
                        bad_report = bad_report + f"\U0001f327\uFE0F"
                    day_report.append(bad_report)
            for time_point in ("21:00:00", "18:00:00", "15:00:00", "12:00:00", "09:00:00"): #for every time window on the last day that's after the last weather entry, create a blank report
                if get_time(day[-1].time) < get_time(time_point):
                    day_report.append(f"")
            day_dictionary[day[0].date] = day_report
        return day_dictionary
    
    @output
    @shiny.render.table
    def make_table(): #convert the dictionary of weather reports into a pandas data frame
        weather_df = pandas.DataFrame(data = day_dictionary())
        return weather_df.style.set_table_attributes(
                'class="dataframe shiny-table table w-auto "'
        ).hide(axis="index").set_table_styles([dict(selector="th", props=[("text-align", "center"), ("white-space", "pre-wrap")])]) #make <br> get interpreted as a line break in the table text
    
    @output
    @shiny.render.text
    def make_legend(): #create a legend explaining what each emoji means
        if geo_request().status_code != 200 or len(geo_request().json()) != 1:
            return ""
        else:
            return "\U0001f600 = good conditions; \U0001F976 = too cold; \U0001F975 = too hot; \U0001f32a\uFE0F = too windy; \U0001f327\uFE0F = high chance of precipitation"

app = shiny.App(ui=app_ui, server=server) 

#Indicate in readme somewhere that it's (currently) limited to cities in the US?

#change the column titles to days of the week? - might need to access a calender to do this