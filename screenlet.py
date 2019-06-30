from tkinter import Tk, Frame, Label, Entry, Button, Message, Menu, StringVar
from tkinter.ttk import Combobox
from threading import Thread, Timer
from asyncio import get_event_loop, wait, sleep
from functools import partial
from platform import system
from aiohttp_requests import requests
from PIL import Image, ImageTk
from requests import get


class MainFrame(Tk):
    """
        Frame for screenlet
    """

    def __init__(self):
        super().__init__()
        # Window without frame
        self.overrideredirect(1)
        # Set window transparency
        if system() == 'Linux':
            self.attributes('-type', 'normal')
        self.attributes('-alpha', 0.5)

        self.city = StringVar()
        try:
            # Read data from file
            with open('settings.ini', 'r') as file:
                data = file.readlines()
            # Window geometry and position
            geometry = data[0].strip()
            self.city.set(data[1].strip())
            self.t_unit = data[2].strip()
        except:
            geometry = ''
            self.city.set('Kiev, UA')
            self.t_unit = 'metric'

        self.condition = StringVar()
        self.temperature = StringVar()
        self.currency = StringVar()

        self.start_x = 0
        self.start_y = 0

        # Set data for weather and currency exchange
        thread = Thread(target=self.get_data())
        thread.start()

        if geometry == '':
            # Get screen size and calculate window position
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = screen_width - 320 - 20
            y = screen_height - (screen_height - 100 - 100)
            # Set new position
            self.geometry(f'320x100+{x}+{y}')
        else:
            self.geometry(geometry)

        self.resizable(width=False, height=False)

        # Pressed over the window
        self.bind('<Button-1>', self.on_mouse_press)
        # Mouse is moved while being held down
        self.bind('<B1-Motion>', self.on_drag)

        # Context menu
        self.popup_menu = Menu(self, tearoff=0)
        self.popup_menu.add_command(label="Settings", command=self.settings)
        self.popup_menu.add_command(label="Exit", command=self.close)
        self.bind("<Button-3>", self.popup)

        self.init_widgets()

    def init_widgets(self):
        """
            Set widgets position
        """
        # Set widget for weather image
        self.image_label = Label(self, image=self.image)
        self.image_label.image = self.image
        self.image_label.pack(side='left')
        self.image_label.configure(image=self.image)

        # Show current weather and currency rate
        Label(self, textvariable=self.condition, fg='Teal',
              font=("Helvetica", 9, 'italic', 'bold')).pack(side='left')

        Label(self, textvariable=self.temperature,
              font=('Helvetica', 20, 'bold'),
              fg='orange').pack(expand=True)

        Label(self, textvariable=self.city,
              font=("Helvetica", 15, 'bold'), padx=10, fg='green').pack()

        Label(self, textvariable=self.currency, fg='Navy',
              font=("Helvetica", 10, 'bold')).pack()

        # Start timer for updating information about
        # weather and currency rate
        self.update_thread = Timer(20 * 60, self.get_data())
        self.update_thread.start()

    def get_data(self):
        """
            Set data for weather and currency exchange
        """
        # Get information about current weather
        # and currency rate
        loop = get_event_loop()
        done, _ = loop.run_until_complete(wait([
            get_weather(self.city.get(), self.t_unit),
            get_currency()
        ]))

        for item in done:
            if isinstance(item.result(), dict):
                weather = item.result()
            else:
                currency = item.result()

        # Update weather image
        img = Image.open(weather['icon']).resize(
            (110, 110), Image.ANTIALIAS)

        self.image = ImageTk.PhotoImage(img)

        # Set current weather
        self.condition.set(weather['humidity'] + '\n\n' + weather['wind'] +
                           '  \n\n' + weather['description'].capitalize())

        self.temperature.set('{:.1f}'.format(
            weather['temperature']) + ('° C' if weather['temperature_unit'] == 'metric' else '° F'))

        self.city.set(value=weather['city'])

        # Set currency rate (USD)
        self.currency.set('\n' + currency[0])

    def popup(self, event):
        # Show context menu
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    def on_mouse_press(self, event):
        # Get mouse coordinates
        self.start_x = event.x
        self.start_y = event.y

    def on_drag(self, event):
        # Get current window position
        _, x, y = self.geometry().split('+')
        # Calculate new position
        x = int(x) + (event.x - self.start_x)
        y = int(y) + (event.y - self.start_y)
        # Move window
        self.geometry(f'+{x}+{y}')

    def settings(self):
        # Open program settings and disable current window
        settings_window = SettingsFrame(self)
        if system() == 'Windows':
            self.wm_attributes("-disabled", True)
        settings_window.mainloop()

    def close(self):
        # Save window geometry, position,
        # city and temperature unit
        with open('settings.ini', 'w') as file:
            print(self.geometry(), file=file)
            print(self.city.get(), file=file)
            print(self.t_unit, file=file)
        # Stop timer for updating information and exit
        self.update_thread.cancel()
        exit()


class SettingsFrame(Tk):
    """
        Frame for screenlet settings.

        :param parent: parent window.
    """

    def __init__(self, parent: Tk):
        super().__init__()
        # Program settings
        self.title('Settings')
        self.geometry('230x90')
        self.resizable(width=False, height=False)
        # Close button only
        if system() == 'Windows':
            self.attributes("-toolwindow", 1)

        frame = Frame(self)
        frame.pack(expand=True, side='top')
        left_frame = Frame(frame)
        left_frame.pack(side='left')
        right_frame = Frame(frame)
        right_frame.pack(side='right')

        # Display city name and country from parent window
        Label(left_frame, text='City, Country: ', pady=3).pack(side='top')
        self.city_entry = Entry(right_frame, width=20)
        self.city_entry.insert('end', parent.city.get())
        self.city_entry.pack(side='top', pady=3)

        # Display temperature unit from parent window
        Label(left_frame, text='Units: ', pady=3).pack(side='left')
        self.unit_combo = Combobox(
            right_frame, values=['° C, meter/sec', '° F, miles/hour'], width=17)
        # Units: metric or imperial
        if parent.t_unit == 'metric':
            self.unit_combo.current(0)
        else:
            self.unit_combo.current(1)
        self.unit_combo.pack(side='right', pady=3)

        # Submit button
        bottom_frame = Frame(self)
        bottom_frame.pack(side='bottom')
        Button(bottom_frame, text='Cancel', width=10,
               command=partial(self.on_close, parent)).pack(side='left', pady=3, padx=10)
        Button(bottom_frame, text="OK", width=10,
               command=partial(self.get_settings, parent)).pack(side='right', pady=3, padx=10)

        self.protocol("WM_DELETE_WINDOW", partial(self.on_close, parent))

    def on_close(self, parent: Tk):
        # Close settings window and enable parent window
        if system() == 'Windows':
            parent.wm_attributes("-disabled", False)
        self.destroy()

    def get_settings(self, parent: Tk):
        # Save data
        parent.city.set(self.city_entry.get())
        # Get units
        if self.unit_combo.current() == 0:
            parent.t_unit = 'metric'
        else:
            parent.t_unit = 'imperial'
        # Update information
        thread = Thread(target=parent.get_data())
        thread.start()
        self.on_close(parent)


async def get_weather(city: str, unit: str):
    """
        Get current weather from OpenWeatherMap.

        :param city: city name and country code. Example: London, GB;

        :param unit: temperature unit (metric, imperial).
        metric: temperature in '° C', wind speed in 'meter/sec';
        imperial: temperature in '° F', wind speed in 'miles/hour'.

        :return: {
            'city': str,
            'temperature_unit': str,
            'temperature': float,
            'humidity': int in %,
            'wind: float,
            'description': str,
            'icon': 'url'
        }.
    """
    url = 'http://api.openweathermap.org/data/2.5/weather?q={}' + \
        '&units={}&id=524901&appid=19973c652198e53d12c0f820dd3fcb34'

    # Send request and get responce in json
    resp = await requests.get(url.format(city, unit))
    resp = await resp.json()

    icon = get('http://openweathermap.org/img/w/{}.png'.format(
        resp['weather'][0]['icon']), stream=True).raw
    await sleep(0.001)

    city_weather = {
        'city': '{}, {}'.format(resp['name'], resp['sys']['country']),
        'temperature_unit': unit,
        'temperature': resp['main']['temp'],
        'humidity': '{} %'.format(resp['main']['humidity']),
        'wind': str(resp['wind']['speed']) + (' m/sec' if unit == 'metric' else ' mph'),
        'description': resp['weather'][0]['description'],
        'icon': icon
    }

    return city_weather


async def get_currency():
    """
        Get currency rate from PrivatBank
        (USD, EUR, RUB, BTC).

        :return: list. Example: ['USD: 00.00 UAH', ...]
    """
    api_url = 'https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5'

    try:
        response = await requests.get(api_url)

        if response.raise_for_status() is None:
            response_json = await response.json()
    except Exception as e:
        Message(e)

    result = list()

    # format: USD: 00.00 UAH
    for cur in response_json:
        result.append("{}: {:.2f} {}".format(
            cur["ccy"], float(cur["sale"]), cur["base_ccy"]))

    return result


if __name__ == '__main__':
    # Main window
    window = MainFrame()
    window.mainloop()
