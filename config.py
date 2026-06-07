import datetime
class Settings():
    def __init__(self):
        self.start_date = datetime.date.today() - datetime.timedelta(days=365)
        self.end_date = datetime.date.today() + datetime.timedelta(1)
