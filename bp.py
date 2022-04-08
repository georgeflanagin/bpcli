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
    bp 130 70 60 R # The fourth term gives the arm, L or R. Default is L.

That's it.

The records are written with the time stamp when the data are recorded,
and the user name of the person running the program. 
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
# This program executes three SQL statements, and rather
# than spread them around, let's put the text literals here
# and give them names.
###
SQL = {
    'createtable':"""CREATE TABLE facts (
        user VARCHAR(20), 
        systolic INTEGER,
        diastolic INTEGER,
        pulse INTEGER,
        arm CHAR(1),
        t DATETIME DEFAULT CURRENT_TIMESTAMP)""",

    'insertreading':"""INSERT INTO facts 
        (user, systolic, diastolic, pulse, arm) 
        VALUES (?, ?, ?, ?, ?)""",

    'getallreadings':"SELECT * FROM facts"
    }

###
# Installed libraries
###

###
# From hpclib
###

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

verbose = False


def create_or_open_db(name:str) -> tuple:
    """
    As this is a single table database, it is not much trouble to 
    embed all the needed SQL (two statements) into the Python code.

    This function returns two "handles," one to the database 
    connection for commit and close, and one to the cursor to 
    manipulate the data.
    """
    global SQL

    if not os.path.isfile(name):

        db = sqlite3.connect(name)
        cursor = db.cursor()
        cursor.execute(SQL['createtable'])
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
    global verbose
    myid = getpass.getuser()

    # Some default values. The zeros will be easy to filter out
    # or impute in a pandas.DataFrame
    systolic = 0
    diastolic = 0
    pulse = 0
    arm = 'L'

    nargs=len(data)
    using_slash = '/' in data[0]
    verbose and print(f"{using_slash=}")

    if not using_slash and nargs < 2:
        print(f"I do not understand {data}")
        sys.exit(os.EX_NOINPUT)

    elif using_slash:
        data = data[0].split('/') + data[1:]

    else:
        pass

    verbose and print(f"{data=}")

    # Note that the number of things in data may have changed.
    nargs = len(data)
    if nargs == 2:
        systolic, diastolic = data
    elif nargs == 3:
        systolic, diastolic, pulse = data
    elif nargs == 4:
        systolic, diastolic, pulse, arm = data

    # Check that the numbers are numbers.
    try:
        systolic = int(systolic)
        diastolic = int(diastolic)
        pulse = int(pulse)
    except:
        print(f"Some of your numbers are not numbers: {data}")        
        sys.exit(os.EX_DATAERR)
    else:
        verbose and print(f"{diastolic=} {systolic=} {pulse=}")

    # Silently swap the BP numbers if required.
    if diastolic > systolic:
        systolic, diastolic = diastolic, systolic
        verbose and print(f"{diastolic=} {systolic=}")

    arm = arm.upper()
    if arm not in ('L', 'R'):
        print(f"Most people only have two arms, L and R. You have a '{arm}' arm.")
        sys.exit(os.EX_DATAERR)

    if not systolic * diastolic:
        print(f"You appear to be dead because your BP is {systolic}/{diastolic}.")
        sys.exit(os.EX_DATAERR)

    if diastolic < 0:
        print(f"Outside Transylvania, negative BP is a sign of something bad: {systolic}/{diastolic}.")
        sys.exit(os.EX_DATAERR)


    return myid, systolic, diastolic, pulse, arm


def bp_main(myargs:argparse.Namespace) -> int:
    """
    Do the work.
    """

    global SQL

    db, cursor = create_or_open_db(myargs.db)
    if myargs.data[0].lower() == 'report':
        import pandas
        print(pandas.read_sql(SQL['getallreadings'], db).to_string())
        return os.EX_OK

    data = data_to_tuple(myargs.data)
    
    try:
        cursor.execute(SQL['insertreading'], data)
        db.commit()

    except Exception as e:
        print(f"Exception writing to database: {e}")
        return os.EX_IOERR

    finally:
        # Always close the DB, even there was an error.
        db.close()

    return os.EX_OK


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(prog="bp", 
        description="What bp does, bp does best.")
    parser.add_argument('--db', type=str, 
        default=os.path.join(os.environ.get('HOME'), 'bp.db'),
        help="Name of the database.")
    parser.add_argument('-v', '--verbose', action='store_true',
        help="Be chatty about what is taking place")
    parser.add_argument('data', nargs='+',
        help="You must supply the systolic/diastolic pressures, and *optionally* heart rate and arm.")

    myargs = parser.parse_args()
    verbose = myargs.verbose

    try:
        outfile = sys.stdout
        with contextlib.redirect_stdout(outfile):
            sys.exit(globals()[f"{os.path.basename(__file__)[:-3]}_main"](myargs))

    except Exception as e:
        print(f"Unhandled exception: {e}")


