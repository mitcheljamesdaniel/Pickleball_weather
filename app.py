#pickleball weather forecast shiny app

from doctest import OutputChecker
import json
import shiny
import pandas
import time
import pyodide.http

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

current_data = shiny.reactive.Value(None)

#create the shiny ui
app_ui = shiny.ui.page_fluid(
    shiny.ui.panel_title("When to play outdoor pickleball"),
    shiny.ui.layout_sidebar( #create two-panel layout
        shiny.ui.panel_sidebar( #place inputs in the sidebar
            shiny.ui.output_text("instructions_a"),
            shiny.ui.input_text("city", "City:", placeholder="Enter city name"),
            shiny.ui.input_selectize("state", "State:", states),
            shiny.ui.input_action_button("compute", "Generate Calendar", class_="btn-primary"),
            shiny.ui.output_text("instructions_b"),
            shiny.ui.input_slider("temp_range", "Temperature range (F):", value = (40, 90), min = 30, max = 110),
            shiny.ui.input_slider("max_precip", "Max chance of precipitation (%):", value = 30, min = 0, max = 100),
            shiny.ui.input_numeric("max_speed", "Max wind speed (mph):", 15)
        ),
        shiny.ui.panel_main( #place outputs in the main panel
            shiny.ui.output_text("weather_test"),
            shiny.ui.output_text("make_legend"),
            shiny.ui.output_table("make_table")
            )
    )
)

#create the server function
def server(input, output, session):
    @output
    @shiny.render.text
    def instructions_a():
        return "Find times in the 5-day weather forecast that are suitable for outdoor Pickleball! Type in your city and select your state (US locations only). Then, click 'Generate Calendar' to see when conditions will be suitable in your location."
    
    @output
    @shiny.render.text
    def instructions_b():
        return "You can customize the range of weather conditions that are considered suitable to fit your preferences. Drag the sliders to temperature range and max chance of precipitation. Type or use the scroller to set the max wind speed. The calendar will automatically update to reflect these changes."

    @shiny.reactive.Calc
    async def geo_request(): #return geo location data from API request
        API = "b0fb1574b0176f4025a21cfea6f99005"
        input.compute() #reexecute this function in response to input button press
        with shiny.reactive.isolate(): #do NOT reexecute this function in response to changes in its dependencies (city or state inputs) to avoid excess API requests
            geo_response = await pyodide.http.pyfetch(f"https://api.openweathermap.org/geo/1.0/direct?q={input.city()},{input.state()},US&limit=1&appid={API}")
            geo_data = await geo_response.json()
            if geo_response.status != 200 or len(geo_data) != 1: #return string error message if geo API request was unsuccessful (usually happens because city is misspelled or city and state are mismatched)
                output_string.set("Error: Please check that the location information is accurate. Bad geolocation request. Check your city name spelling.")
                return None
            geo_data = geo_data[0]
            return [geo_data['lat'], geo_data['lon']]

    @output
    @shiny.render.text
    async def geo_test(): #if the request failed (and returned a string), print an error message
        geo_data = await geo_request()
        if geo_data == None:
            return "Error: Please check that the location information is accurate."
        return ""
    
    @shiny.reactive.Effect
    @shiny.reactive.event(input.compute)
    async def weather_request(): #return weather data for the chosen location
        weather_ID = "b0fb1574b0176f4025a21cfea6f99005"
        geo_data = await geo_request()
        if geo_data == None:
            return
        weather_response = await pyodide.http.pyfetch(f"https://api.openweathermap.org/data/2.5/forecast?id=524901&units=imperial&lat={geo_data[0]}&lon={geo_data[1]}&exclude=current,minutely,hourly&appid={weather_ID}")
        weather_data = await weather_response.json()
        if weather_response.status != 200 or len(weather_data) == 0:
            output_string.set("Weather API request failed. Try again.")
            return
        output_string.set(f"{input.city()}, {input.state()}")
        process_the_weather_data(weather_data)
    
    def process_the_weather_data(data):
        weather_list = [weather(i) for i in data['list']]
        filtered_list = [day for day in weather_list if day.check_day()]
        
        list_of_days = day_sorting(filtered_list)
        current_data.set(list_of_days)

    output_string = shiny.reactive.Value("")
    
    @output
    @shiny.render.text
    def weather_test(): #print error message if weather API request returned a string (i.e. failed)
        return output_string()
    
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
    
    def day_sorting(filtered_list): #create a list of lists, where each of the sublists contains the weather objects for a given day
        list_of_days = []
        list_of_days.append([])
        prev_date = filtered_list[0].date
        day_index = 0
        for m in range(len(filtered_list)):
            if filtered_list[m].date == prev_date: #place all weather objects with the same data in the same sublist
                list_of_days[day_index].append(filtered_list[m])
            else: #each time the weather object has a different date than the weather object before it, place it in a new sublist
                list_of_days.append([])
                day_index = day_index + 1
                list_of_days[day_index].append(filtered_list[m])
                prev_date = filtered_list[m].date
        return list_of_days
    
    def time_windows(): #create list of time windows, to be used as the row names in the output table
        return ["6:00 am - 9:00 am", "9:00 am - 12:00 pm", "12:00 pm - 3:00 pm", "3:00 pm - 6:00 pm", "6:00 pm - 9:00 pm", "9:00 pm - 12:00 am"]

    def day_dictionary(): #return a dictionary where each key is a column heading for the output table, and each value is the corresponding list of entires (time windows or weather objects)
        day_dictionary = {}
        day_dictionary["Time of day"] = time_windows() #create the dictionary entry for the row names
        if current_data() == None:
            return day_dictionary
        for day in current_data(): #for each day, create a list of weather reports describing whether the conditions are suitable for pickleball
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
                        bad_report = bad_report + f"\U0001F976 " + str(o.temp) + u'\N{DEGREE SIGN}' + "F<br>"
                    if o.temp > max_temp():
                        bad_report = bad_report + f"\U0001F975 " + str(o.temp) + u'\N{DEGREE SIGN}' + "F<br>"
                    if o.speed > max_speed():
                        bad_report = bad_report + f"\U0001f32a\uFE0F " + str(o.speed) + " mph<br>"
                    if o.precip > max_precip():
                        bad_report = bad_report + f"\U0001f327\uFE0F " + str(o.precip) + "%"
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
        if current_data() == None: #don't make legend unless there is data in the table
            return ""
        else:
            return "\U0001f600 = good conditions; \U0001F976 = too cold; \U0001F975 = too hot; \U0001f32a\uFE0F = too windy; \U0001f327\uFE0F = high chance of precipitation"

app = shiny.App(ui=app_ui, server=server) 
