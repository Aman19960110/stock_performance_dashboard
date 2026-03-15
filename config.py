import datetime
class Settings():
    def __init__(self):
        self.start_date = '2025-12-31'
        self.end_date = datetime.date.today() + datetime.timedelta(1)

        