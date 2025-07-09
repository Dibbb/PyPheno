pip install babel

import locale
import datetime
import sys

dob_str = "1980-10-10T00:00:00Z"
print(dob_str)
try:
    dob = datetime.datetime.strptime(dob_str, "%Y-%m-%dT%H:%M:%SZ").date()
except Exception:
    dob = None

print(dob)

# Try to get locale-aware format, fallback to ISO if unavailable
if dob:
    try:
        if hasattr(locale, 'nl_langinfo'):
            locale.setlocale(locale.LC_TIME, '')
            date_format = locale.nl_langinfo(locale.D_FMT)
        else:
            # Fallback for platforms without nl_langinfo (e.g., Windows)
            import platform
            if platform.system() == 'Windows':
                # Use locale date format from locale module
                date_format = '%x'
            else:
                date_format = '%Y-%m-%d'
        formatted = dob.strftime(date_format)
    except Exception:
        formatted = dob.strftime("%Y-%m-%d")
else:
    formatted = ''

print(formatted)

from babel.dates import format_date
import datetime

dob = datetime.date(1980, 10, 10)
formatted = format_date(dob, locale='your-locale-code') 

print(formatted)