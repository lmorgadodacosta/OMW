#!/usr/bin/python3

import sqlite3, sys

# It takes one argument: the name of the db
if (len(sys.argv) < 2):
    sys.stderr.write('You need to give the name of the DB\n')
    sys.exit(1)
else:
    u =  sys.argv[0]
    dbfile = sys.argv[1]

################################################################
# CONNECT TO DB
################################################################
con = sqlite3.connect(dbfile)
c = con.cursor()

################################################################
# INSERT EXAMPLE USERS DATA (CODES AND NAMES)
################################################################

c.execute("""INSERT INTO users (userID, full_name, password, 
             email, access_level, access_group, affiliation, u)
             VALUES (?,?,?,?,?,?,?,?)""",
          ['admin','System Administrator',
           '1fc9b75701d72e2051441d23ee8acc20',
           'changeme@changeme.com', 99, 'admin', 'sys', u])

c.execute("""INSERT INTO users (userID, full_name, password, 
             email, access_level, access_group, affiliation, u)
             VALUES (?,?,?,?,?,?,?,?)""",
          ['user1','System User 1',
           '46bcc2d7eb5723292133857fa95454b9',
           'changeme@changeme.com', 0, 'common', 'sys', u])


c.execute("""INSERT INTO users (userID, full_name, password, 
             email, access_level, access_group, affiliation, u)
             VALUES (?,?,?,?,?,?,?,?)""",
          ['lmc','Luís Morgado da Costa',
           '1fc9b75701d72e2051441d23ee8acc20',
           'lmorgado.dacosta@gmail.com', 99, 'admin', 'pwn|cow|jpwn', u])



# ADD: lmc, fcbond, fellbaum

con.commit()
con.close()
sys.stderr.write('Loaded example user data in (%s)\n' % (dbfile))
