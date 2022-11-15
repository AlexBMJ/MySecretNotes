import sqlite3, functools, os, time, random, sys, subprocess
from flask import Flask, session, redirect, render_template, url_for, request, jsonify


PREFIX = "/mysecretnotes"

### DATABASE FUNCTIONS ###

def connect_db():
    return sqlite3.connect(app.database)

def init_db():
    """Initializes the database with our great SQL schema"""
    conn = connect_db()
    db = conn.cursor()
    db.executescript("""

DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS notes;
DROP TABLE IF EXISTS dateformat;

CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assocUser INTEGER NOT NULL,
    dateWritten DATETIME NOT NULL,
    note TEXT NOT NULL,
    publicID INTEGER NOT NULL
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE dateformat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    format TEXT NOT NULL
);

INSERT INTO users VALUES(null,"admin", "password");
INSERT INTO users VALUES(null,"bernardo", "omgMPC");
INSERT INTO notes VALUES(null,2,"1993-09-23 10:10:10","hello my friend",1234567890);
INSERT INTO notes VALUES(null,2,"1993-09-23 12:10:10","i want lunch pls",1234567891);

INSERT INTO dateformat VALUES(0,"%m/%d/%Y");
""")



### APPLICATION SETUP ###
app = Flask(__name__)
app.database = "db.sqlite3"
app.secret_key = os.urandom(32)

### ADMINISTRATOR'S PANEL ###
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route(f"{PREFIX}/")
def index():
    if not session.get('logged_in'):
        return render_template('index.html')
    else:
        return redirect(url_for('notes'))


@app.route(f"{PREFIX}/notes/", methods=('GET', 'POST'))
@login_required
def notes():
    importerror=""
    #Posting a new note:
    if request.method == 'POST':
        if request.form['submit_button'] == 'add note':
            note = request.form['noteinput']
            db = connect_db()
            c = db.cursor()
            c.execute("INSERT INTO notes(id,assocUser,dateWritten,note,publicID) VALUES(null,?,?,?,?);", (session['userid'],time.strftime('%Y-%m-%d %H:%M:%S'),note,random.randrange(1000000000, 9999999999)))
            db.commit()
            db.close()
        elif request.form['submit_button'] == 'import note':
            noteid = request.form['noteid']
            db = connect_db()
            c = db.cursor()
            c.execute("SELECT * from NOTES where publicID = ?", (noteid, ))
            result = c.fetchall()
            if(len(result)>0):
                row = result[0]
                c.execute("INSERT INTO notes(id,assocUser,dateWritten,note,publicID) VALUES(null,?,?,?,?);", (session['userid'],row[2],row[3],row[4]))
            else:
                importerror="No such note with that ID!"
            db.commit()
            db.close()
    
    db = connect_db()
    c = db.cursor()
    c.execute("SELECT * FROM notes WHERE assocUser = ?;", (session['userid'], ))
    notes = c.fetchall()


    success, dateformat = get_dateformat()
    
    return render_template('notes.html',notes=notes,importerror=importerror, dateformat=dateformat)


@app.route(f"{PREFIX}/login/", methods=('GET', 'POST'))
def login():
    error = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = connect_db()
        c = db.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?;", (username, password))
        result = c.fetchall()

        if len(result) > 0:
            session.clear()
            session['logged_in'] = True
            session['userid'] = result[0][0]
            session['username']=result[0][1]
            return redirect(url_for('index'))
        else:
            error = "Wrong username or password!"
    return render_template('login.html',error=error)


@app.route(f"{PREFIX}/register/", methods=('GET', 'POST'))
def register():
    errored = False
    usererror = ""
    passworderror = ""
    if request.method == 'POST':
        

        username = request.form['username']
        password = request.form['password']
        db = connect_db()
        c = db.cursor()

        c.execute("SELECT * FROM users WHERE password = ?;", (password,))
        if(len(c.fetchall())>0):
            errored = True
            passworderror = "That password is already in use by someone else!"

        c.execute("SELECT * FROM users WHERE username = ?;", (username,))
        if(len(c.fetchall())>0):
            errored = True
            usererror = "That username is already in use by someone else!"

        if(not errored):
            c.execute("INSERT INTO users(id,username,password) VALUES(null,?,?);", (username, password))
            db.commit()
            db.close()

            return f"""<html>
                        <head>
                            <meta http-equiv="refresh" content="2;url=/" />
                        </head>
                        <body>
                            <h1>SUCCESS!!! Redirecting in 2 seconds...</h1>
                        </body>
                        </html>
                        """
        
        db.commit()
        db.close()
    return render_template('register.html',usererror=usererror,passworderror=passworderror)


@app.route(f"{PREFIX}/admin/", methods=('GET', 'POST'))
@login_required
def admin():
    if request.method != 'GET':
        db = connect_db()
        c = db.cursor()
        c.execute("UPDATE dateformat SET format = ? WHERE id = 0;", (request.form['dateformat'],))
        db.commit()
        db.close()

        return redirect(url_for('notes'))

    success, dateformat = get_dateformat()
    return render_template('admin.html', dateformat=dateformat)

def get_dateformat():
    db = connect_db()
    
    c = db.cursor()
    c.execute("SELECT * FROM dateformat WHERE id = 0;")
    
    dateformat = c.fetchone()[1]

    db.commit()
    db.close()

    try:
        d =  subprocess.run([f"date +{dateformat}"], shell=True, capture_output=True, text=True)

        if not d.returncode == 0:
            raise Exception("Invalid date format!") 
    
        return True, d.stdout
    except Exception as e:
        return False, "Error: " + str(e)

@app.route(f"{PREFIX}/admin/date/")
@login_required
def get_date():
    success, date = get_dateformat()

    if success:
        return jsonify({"date": date, success: True})
    else:
        return jsonify({success: False, "error": date})


@app.route(f"{PREFIX}/logout/")
@login_required
def logout():
    """Logout: clears the session"""
    session.clear()
    return redirect(url_for('index'))



if __name__ == "__main__":
    #create database if it doesn't exist yet
    if not os.path.exists(app.database):
        init_db()
    runport = 5000
    if(len(sys.argv)==2):
        runport = sys.argv[1]
    try:
        app.run(host='0.0.0.0', port=runport) # runs on machine ip address to make it visible on netowrk
    except:
        print("Something went wrong. the usage of the server is either")
        print("'python3 app.py' (to start on port 5000)")
        print("or")
        print("'sudo python3 app.py 80' (to run on any other port)")