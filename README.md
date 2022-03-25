# bpcli
Command line mini-tool to record blood pressure in a tiny database.

If you are like me (i.e., you work in tech, and you have hypertension), then you 
might want to keep track of your blood pressure while you work. `bpcli` does this
task for you with a minimum of fuss.

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

### Optional information

`bp` supports several input formats. 

- You can use the "slash" notation: `bp 120/70`
- You can leave out the slash: `bp 120 70`
- You can add your pulse: `bp 120 70 60`
- You can even add your arm on the end (if you have included pulse info): `bp 120/70 60 R`


 

## The database

You can put the database anywhere with the `--db` option. The first time you 
run the program, the database will be created, either where you say to do it,
or in `~/bp.db`
