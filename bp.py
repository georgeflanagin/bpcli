# -*- coding: utf-8 -*-
import typing
from   typing import *

"""
This is a simple commandline program to enter blood pressure readings
without a lot of fuss. It allows flexible formatting of the inputs, and
drops the time stamped records into a fact-table type database for 
later analysis. These analyses are particularly easy with pandas.

Usage:

    bp 140/90      # Just the basics.
    bp 140 80      # You can use a space if that works for you.
    bp 80 140      # bp will swap them for you.
    bp 130/95 75   # The third number is construed to be the pulse.
    bp 130/90 80 some text about the reading  # The text does not need to be quoted.
    bp report      # dump the contents of the database.
    bp report > x  # write the report to a file named 'x'.

That's it.

The records are written with the time stamp when the data are recorded,
and the user name of the person running the program. Do note that the timestamps
are GMT, but the 'bp report' function converts them to localtime.
"""

min_py = (3, 8)

###
# Standard imports, starting with os and sys
###
import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

###
# Other standard distro imports
###
import argparse
import contextlib
import getpass
import sqlite3

###
# From hpclib
###
import parsec4 
from   parsec4 import *

###
# Credits
###
__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2022'
__credits__ = None
__version__ = 0.9
__maintainer__ = 'George Flanagin'
__email__ = ['gflanagin@richmond.edu', 'me@georgeflanagin.com']
__status__ = 'working prototype'
__license__ = 'MIT'

myid = getpass.getuser()
verbose = False

###
# for the bp parser
###
positive_number = lexeme(DIGIT_STR).parsecmap(int)
systolic = positive_number
slash = lexeme(string(SLASH))
diastolic = (slash >> positive_number) ^ positive_number
pulse = positive_number
bp_parser = systolic + diastolic + pulse + everything_else


def create_or_open_db(name:str) -> tuple:
    """
    As this is a single table database, it is not much trouble to 
    embed all the needed SQL (two statements) into the Python code.

    This function returns two "handles," one to the database 
    connection for commit and close, and one to the cursor to 
    manipulate the data.
    """
    if not os.path.isfile(name):

        db = sqlite3.connect(name)
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE facts (
                user VARCHAR(20), 
                systolic INTEGER,
                diastolic INTEGER,
                pulse INTEGER,
                arm CHAR(1),
                t DATETIME DEFAULT CURRENT_TIMESTAMP,
                narrative VARCHAR(100))
        ''')
        cursor.execute('''
            drop view export;
            create view export as 
                select 
                    datetime(t, 'localtime') as time, 
                    systolic, diastolic, pulse, 
                    narrative 
                from facts order by time;
        ''')
        db.close()
        # Now that it is built, just call this function.
        return create_or_open_db(name)

    else:
        db = sqlite3.connect(name,
                timeout=5, 
                isolation_level='EXCLUSIVE')

        return db, db.cursor()


def data_to_tuple(data:list) -> tuple:
    """
    Create the tuple to put in the database.
    """
    global myid, verbose

    try:
        data = bp_parser.parse(" ".join(data))
    except Exception as e:
        print(e)
        sys.exit(os.EX_DATAERR)

    numbers, desc = data
    pressure, pulse = numbers
    s, d = pressure

    return myid, s, d, pulse, 'L', desc


def bp_main(myargs:argparse.Namespace) -> int:

    db, cursor = create_or_open_db(myargs.db)
    if myargs.data[0] == 'report':
        for row in cursor.execute('''SELECT * from export''').fetchall():
            print(row)
        return os.EX_OK

    data = data_to_tuple(myargs.data)
    try:
        cursor.execute('''INSERT INTO facts 
            (user, systolic, diastolic, pulse, arm, narrative) 
            VALUES (?, ?, ?, ?, ?, ?)''', data)
        
        db.commit()

    except Exception as e:
        print(f"Exception writing to database: {e}")
        return os.EX_IOERR

    finally:
        db.close()

    return os.EX_OK


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(prog="bp", 
        description="What bp does, bp does best.")
    parser.add_argument('--db', type=str, 
        default=os.path.join('bp.db'),
        help="Name of the database.")
    parser.add_argument('-v', '--verbose', action='store_true',
        help="Be chatty about what is taking place")
    parser.add_argument('data', nargs='+',
        help="You must supply the systolic/diastolic pressures, heart rate, and optionally a desc. You can also choose to type 'report', and you will get a dump of the previously recorded data.")

    myargs = parser.parse_args()
    verbose = myargs.verbose

    try:
        outfile = sys.stdout
        with contextlib.redirect_stdout(outfile):
            sys.exit(globals()[f"{os.path.basename(__file__)[:-3]}_main"](myargs))

    except Exception as e:
        print(f"Unhandled exception: {e}")


