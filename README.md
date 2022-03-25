# bpcli
Command line mini-tool to record blood pressure in a tiny database.

If you are like me (i.e., you work in tech *and* you have hypertension), then you 
might want to keep track of your blood pressure while you work. `bpcli` does this
task for you with a minimum of fuss.

## Requirements

- Python 3.8+
- POSIX compliant OS such as
    - Any flavor of Linux
    - UNIX
    - Mac OSX
    - Windows with the POSIX extension

## Usage

### At a minimum

First, make an alias like this:

```bash
alias bp="python /path/to/bpcli/bp.py"
```

Then enter your blood pressure:

```bash
bp 120/70
```

The record in the database will have your current username and the current timestamp, so you
don't have to keep track of when you are taking your readings (at least not if you enter
the data promptly).

### Optional information

`bpcli` supports several input formats. 

- You can use the "slash" notation: `bp 120/70`
- You can leave out the slash: `bp 120 70`
- You can add your pulse: `bp 120 70 60`
- You can even add your arm on the end (if you have included pulse info): `bp 120/70 60 R`
- You can accidentally reverse your bp numbers, `bp 70 130`, and `bpcli` will fix it.
- `bpcli` checks for a number of errors in your data input and tells you about them.
- Only if the data are correct is the database written to.

## The database

You can put the database anywhere with the `--db` option. The first time you 
run the program, the database will be created, either where you say to do it,
or in `~/bp.db` If the database is in a non-default location, you will have to
tell the program the location with the `--db mybpdb.db` option when you 
enter your data.
