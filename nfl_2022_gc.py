from __future__ import print_function

import datetime, time
import pandas as pd
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ['https://www.googleapis.com/auth/calendar']



class NFL():

    def __init__(self,teams, year):
        self.teams = teams
        self.year = year

    def access_google_calendar(self):
        """
        From Google Calendar API Documentation
        Shows basic usage of the Google Calendar API.
        Prints the start and name of the next 10 events on the user's calendar.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        self.creds = creds

    def return_events(self):
        '''
        From Google Calendar API Documentation
        '''
        try:
            service = build('calendar', 'v3', credentials=self.creds)
            
            # Call the Calendar API
            now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            print('Getting the upcoming 10 events')
            events_result = service.events().list(calendarId='suv4b53lnm77ihtphq6vhdt65s@group.calendar.google.com', timeMin=now,
                                                maxResults=10, singleEvents=True,
                                                orderBy='startTime').execute()
            events = events_result.get('items', [])
            if not events:
                print('No upcoming events found.')
                return
            # Prints the start and name of the next 10 events
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(start, event['summary'])
        except HttpError as error:
            print('An error occurred: %s' % error)

    def event_color_options(self):
        '''
        Print color options for each event
        '''
        service = build('calendar', 'v3', credentials=self.creds)
        colors = service.colors().get().execute()
        for id, color in colors['event'].items():
            print(f'colorID: {id} {color}')

    def get_schedule(self):
        '''
        Read in csv, append new column 'Datetime' to format to UTC for google calendar use
        '''
        self.df = pd.read_csv('nfl_schedule.csv')
        self.df['Datetime'] = self.df[['Day', 'Date','Time']].agg(' '.join, axis=1)
        for i in range(len(self.df['Datetime'])):
            year = self.get_year(self.df['Date'][i])
            tmp_time = f'{self.df["Datetime"][i]} {year} EST' # Run from Eastern Standard Time
            tmp = datetime.datetime.strptime(tmp_time,'%a %B %d %I:%M %p %Y %Z')
            self.df.loc[i,'Datetime'] = self.df.loc[i,'Datetime'].replace(self.df.loc[i,'Datetime'], tmp.isoformat() + 'Z')

    def get_year(self, month_str):
        '''
        Last ~2 weeks of the season fall into a new year, must be accounted for
        '''
        month = month_str.split(' ')[0]
        nfl_years = {
            'September': self.year,
            'October': self.year,
            'November':self.year,
            'December':self.year,
            'January':self.year + 1 
        }
        if month in nfl_years:
            year = nfl_years[month]
            return year

    def add_event(self, summary, dt, color):
        '''
        Create an event with the title (summary) the VisTm @ HomeTm and default offset being 3 hours
        New York Time Zone by default
        '''

        try:
            start = self.add_offset(dt,4)
            end = self.add_offset(start,3)
            event = {
                'summary': summary,
                'start': {
                    'dateTime': start,
                    'timeZone':'America/New_York'
                },
                'end':{
                    'dateTime': end,
                    'timeZone':'America/New_York'
                },
                'colorId':color
            }
            service = build('calendar', 'v3', credentials=self.creds)
            event = service.events().insert(calendarId='suv4b53lnm77ihtphq6vhdt65s@group.calendar.google.com', body=event).execute()
            print(f"Event created: {event['summary']} {event['start']}")
        except HttpError as error:
            print('An error occurred trying to add an event: %s' % error)


    def add_offset(self, dt, delay):
        '''
        Convert to datetime object and use timedelta to adjust end time to 3 hours from start (Won't cross midnight to avoid errors)
        '''
        tmp = datetime.datetime.fromisoformat(dt[:-1])
        user_delay = datetime.timedelta(hours=delay)
        res = tmp + user_delay
        end = datetime.datetime.isoformat(res) +'Z'
        return end

    def create_calendar(self):
        '''
        Main loop of dataframe, time.sleep(1) to avoid spamming api
        '''
        for game in range(len(self.df)):
            color = self.find_team_color(self.df['HomeTm'][game])
            self.add_event(f"{self.df['VisTm'][game]} @ {self.df['HomeTm'][game]}",self.df['Datetime'][game], color)
            time.sleep(1)

    def find_team_color(self, home_team):
        '''
        Return colorId from team dictionary
        '''
        return self.teams[home_team]

    def delete_all_events(self):
        '''
        Delete all events on a calendar
        '''
        page_token = None
        service = build('calendar', 'v3', credentials=self.creds)
        while True: 
            events = service.events().list(calendarId='suv4b53lnm77ihtphq6vhdt65s@group.calendar.google.com', pageToken=page_token).execute()
            for event in events['items']:
                service.events().delete(calendarId='suv4b53lnm77ihtphq6vhdt65s@group.calendar.google.com', eventId=str(event['id'])).execute()
            page_token = events.get('nextPageToken')
            if not page_token:
                break



# nfl = NFL(teams,2022)
# nfl.access_google_calendar()
# # nfl.event_color_options()
# nfl.return_events()
# nfl.get_schedule()
# nfl.create_calendar()
# # nfl.delete_all_events()

def main():
    teams = {
        'Los Angeles Rams': 9,
        'Atlanta Falcons': 11,
        'Carolina Panthers': 7,
        'Chicago Bears': 6,
        'Cincinnati Bengals': 6,
        'Detroit Lions': 7,
        'Houston Texans': 9,
        'Miami Dolphins': 2,
        'New York Jets': 2,
        'Washington Commanders': 11,
        'Arizona Cardinals': 11,
        'Minnesota Vikings': 3,
        'Tennessee Titans': 7,
        'Los Angeles Chargers': 7,
        'Dallas Cowboys': 9,
        'Seattle Seahawks': 9,
        'Buffalo Bills': 9,
        'New Orleans Saints': 5,
        'Cleveland Browns': 6,
        'San Francisco 49ers': 11,
        'Pittsburgh Steelers': 5,
        'Philadelphia Eagles': 10,
        'Indianapolis Colts': 9,
        'New England Patriots': 9,
        'Baltimore Ravens': 3,
        'Jacksonville Jaguars': 5,
        'Kansas City Chiefs': 11,
        'Green Bay Packers': 10,
        'New York Giants': 7,
        'Las Vegas Raiders': 8,
        'Tampa Bay Buccaneers': 11,
        'Denver Broncos': 5,
    }
    nfl = NFL(teams,2022)
    nfl.access_google_calendar()
    # nfl.event_color_options()
    # nfl.return_events()
    nfl.get_schedule()
    nfl.create_calendar()
    # nfl.delete_all_events()


if __name__ == '__main__':
    main()

