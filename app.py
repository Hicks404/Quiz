from datetime import datetime
from functools import wraps
from hashlib import md5

import sys
import sqlite3
import os
import re
import random

from flask import Flask, redirect, render_template, request, session
# from flask_session import Session
from sqlalchemy import create_engine, text

# Configure application
app = Flask(__name__)
app.secret_key = "Shiaverse"
# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

# Set up the database
engine = create_engine("sqlite:///QuizData.db")
connection = engine.connect()

# helper functions
def apology(message, code=400):
    """Render message as an apology to user."""
    #send user to apology / error page
    return render_template("apology.html", top=code, bottom=message), code


def login_required(f):
    """Decorate routes to require login."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        #checks if user_id is set
        if session.get("user_id") is None:
            #no User_id so sent back to login screen
            return redirect("/login")
        #User_Id exists so bring to homepage instead
        return f(*args, **kwargs)

    return decorated_function

class Hash:
    def __init__(self, password):
        self.salt = "shia"
        self.password = password

    def pwd(self):
        #hashes password and adds salt before the hashing
        pwd = self.password + self.salt
        return md5(pwd.encode()).hexdigest()

class filechildstealer:
    def __init__(self, parent):
        #steals all children under folder or file
        self.children = [f for f in os.listdir(parent)]
    def returner(self):
        return self.children
    def scrambler(self):
        random.shuffle(self.children)

def getAverage(connection, category):
    #get the average score
    query = text("SELECT Result FROM records WHERE Quiz = :category")
    values = connection.execute(query, [{"category": category}]).fetchall()
    total = 0
    num = 0
    #adds all scores and divides it by amount of scores to get average
    try:
        for i in values:
            add = str(i)
            add = re.sub(r'[^\w\.]+', '', add)
            total += float(add)
            num += 1
        average = round(total/num, 2)
    except:
        #activates when average couldn't be found. Most likely zero division error
        average = 50
        print("######################## average failed ########################")
    return average

def getPast(Uid, name):
    #get past score of user if they did quiz
    score = 404 #404 will mark the quiz as incomplete. It will remain 404 if no result is found
    query = text("SELECT Quiz, Result FROM records WHERE UserID = :user_id") #
    values = connection.execute(query, [{"user_id": Uid}]).fetchall()
    for i in values:
        if str(i[0]) == name:
            score = i[1]
    return score

@app.route("/")
@login_required
def index():
    #opening home page with list of Quizzes and results
    Uid = session.get("user_id")
    #getting old results to display
    query = text("SELECT Quiz, Result FROM records") #WHERE UserID = :user_id
    values = connection.execute(query, [{"user_id": Uid}]).fetchall()
    #getting file in random order
    filesclass = filechildstealer("Quizzes")
    filesclass.scrambler()
    files = filesclass.returner()
    #adding score to names
    try:
        
        for i in values:
            for l in files:
                if i[0] == l:
                    files.remove(i[0])
                    iName = i[0]
                    iPast = getPast(Uid, str(iName))
                    iAverage = getAverage(connection, iName)
                    files.append(f"{iName}, {iPast}, {iAverage}")

    except:
        print("score failed")
    return render_template("index.html", files=files, values=values)

def removal(Uid, category):
    #deleting previous score as users should only have one of each
    query = text("DELETE FROM records WHERE UserID = :user_id AND Quiz = :category")
    connection.execute(query, {"user_id": Uid, "category": category})
    connection.commit()

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    #retreiving information of which Quiz and where the result info is
    category = request.args.get('category')
    result = request.form.get('result')
    if not result:
        #If result not found, it means that the quiz wasn't done yet so it opens up the Quiz files for the info
        with open(f"Quizzes/{category}/Questions.txt") as questions, open(f"Quizzes/{category}/Info.txt") as info:
            try:
                #if the txt files are fond, it reads them and sends them to the quiz page
                quests = questions.readlines()
                information = info.readlines()
                #questnum is the amount of questions listed by the Info txt file
                questnum = int(information[1])
                return render_template("quiz.html", quests=quests, questnum=questnum, category=category)
            except:
                return redirect("/")
    else:
        #activates when entering result page
        result = round(float(result))
        Uid = session.get("user_id")

        removal(Uid, category)

        #adding new score the user just got
        insert_qry = text(
            "INSERT INTO records (UserID, Quiz, Result) values(:Uid, :category, :result)"
        )
        connection.execute(insert_qry, [{"Uid": Uid, "category": category, "result": result}])
        connection.commit()

        #get the average score
        average = getAverage(connection, category)

        #result detail
        typ = "error"
        with open(f"Quizzes/{category}/Info.txt") as info:
            information = info.readlines()
            typ = str(information[0])
        
        return render_template("results.html", result=result, average=average, category=category, typ=typ)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method != "POST":
        return render_template("login.html")
    # Get the variables from the submitted form
    usern = request.form.get("username")
    passw = request.form.get("password")
    # Ensure username and passwordwas submitted
    if usern and passw:
        #stops login if username below 4 characters to block test accounts
        if len(usern) >= 4:
            # Query database for username
            query = text("SELECT * FROM users WHERE username = :usern")
            result = connection.execute(query, [{"usern": usern}]).fetchone()
            #print(result)
            # Ensure username exists and password is corret
            if result:
                hasher = Hash(passw)
                passw = hasher.pwd()
                if result[2] == passw:
                # Remember which user has logged in
                    session['user_id'] = result[0]
                else:
                    return apology("password incorrect", 403)
            else:
                return apology("account not found", 403)
            # Redirect user to home page
            return redirect("/")
        else:
            return apology("username doesn't meet required length", 403)
    else:
        return apology("no username or password detected", 403)
        


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        uname = request.form.get("username")
        pwd = request.form.get("password")
        cpwd = request.form.get("confirmpassword")
        email = request.form.get("email")
        # Ensure username was submitted
        if not uname:
            return apology("must provide username", 403)
        # Ensure password was submitted
        elif not pwd:
            return apology("must provide password", 403)
        #ensure email is submitted
        elif not email:
            return apology("must have an email", 403)
        #ensure username is 4 or more characters
        elif len(uname) < 4:
            return apology("username must have 4 or more characters", 403)
        #ensure password is 4 or more characters
        elif len(pwd) < 4:
            return apology("password must have 4 or more characters", 403)
        #ensure password and confirm password are the same
        elif pwd != cpwd:
            return apology("Confirm password isn't same to passwoerd", 403)
        #ensure password has a number
        num = False
        for i in pwd:
            if i.isdigit():
                num = True
        if not num:
            return apology("password must have atleast one number", 403)

        #pwd = (f"o{pwd}ely")
        #pwd = hash(pwd)

        #stop already used usernames or emails
        query = text("SELECT username, email FROM users")
        values = connection.execute(query).fetchall()
        for i in values:
            if i[0] == uname:
                return apology("username already used", 403)
            elif i[1] == email:
                return apology("email already used", 403)

        # Query database for username
        hasher = Hash(pwd)
        pwd = hasher.pwd()
        insert_qry = text(
            "INSERT INTO users (username, password, email) values(:uname,:pwd, :email)"
        )
        connection.execute(insert_qry, [{"uname": uname, "pwd": pwd, "email": email}])
        connection.commit()

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html", display_RL=True)

if __name__ == "__main__":
    app.run(debug=True)
