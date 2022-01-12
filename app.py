from flask import Flask, render_template, request, session, flash
from os import error
from werkzeug.utils import redirect
import config
from datetime import datetime
import psycopg2 as dbapi
import numpy as np
from views import *

app = Flask(__name__)
app.config.from_pyfile("config.py")

def register_page():
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        country_statement2 = "SELECT name FROM country;"
        cur.execute(country_statement2)
        fetched_country = cur.fetchall()
        if request.method == "POST":
            name = request.form["name"]
            surname = request.form["surname"]
            email = request.form["email"]
            password = request.form["password"]
            password_conf = request.form["password_conf"]
            address = request.form["address"]
            country = request.form["country"]

            if (
                not name
                or not surname
                or not email
                or not password
                or not address
                or not country
            ):
                flash("Please fill in all necessary information")
                return render_template("register.html", fetched_country=fetched_country)
            if len(password) < 6:
                flash("Password length should be at least 6")
                return render_template("register.html", fetched_country=fetched_country)
            if password != password_conf:
                flash("Password matching failed")
                return render_template("register.html", fetched_country=fetched_country)
            country_statement = f"SELECT id FROM country WHERE name='{country}'"
            cur.execute(country_statement)
            fetched = cur.fetchone()

            if fetched is None:
                flash("Please enter a valid country")
                return render_template("register.html", fetched_country=fetched_country)
        
            st = f"SELECT * FROM users WHERE email='{email}'"
            cur.execute(st)
            fetchedUser = cur.fetchone()
            st = f"SELECT * FROM admin WHERE email='{email}'"
            cur.execute(st)
            fetchedAdmin = cur.fetchone()
            if not ((fetchedAdmin is None) and (fetchedUser is None)):
                flash("There is already an existing account with this email")
                return render_template("register.html")

            (country_id,) = fetched
            cur.execute(
                "INSERT INTO users (name, surname, email, \
                            password, address, country_id)\
                            VALUES (%s, %s, %s, %s, %s, %s);",
                (name, surname, email, password, address, int(country_id)),
            )

            flash("Successfully registered please login.")
            return redirect("/login")
        else:

            return render_template("register.html", fetched_country=fetched_country)
    except dbapi.errors.UniqueViolation:
        flash("You are already registered.")
        return render_template("register.html", fetched_country=fetched_country)
    except error:
        return "Something happened"
    finally:
        cur.close()
        conn.commit()
        conn.close()

def login_page():
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        if request.method == "POST":
            if "id" in session.keys():
                flash("You are already logged in")
                return render_template("login.html")
            email = request.form["email"]
            password = request.form["password"]
            st = f"SELECT id, email, password, name,surname FROM users WHERE email='{email}'"
            cur.execute(st)
            fetchedUser = cur.fetchone()
            st = f"SELECT id, email, password, name,surname FROM admin WHERE email='{email}'"
            cur.execute(st)
            fetchedAdmin = cur.fetchone()
            if (fetchedAdmin is None) and (fetchedUser is None):
                flash("Invalid email")
                return render_template("login.html")
            fetched = fetchedUser if fetchedAdmin == None else fetchedAdmin
            id, email, password_t, name, surname = fetched
            if password_t != password:
                flash("Wrong Password")
                return render_template("login.html")

            session["loggedin"] = True
            session["id"] = id
            session["email"] = email
            session["name"] = name
            session["surname"] = surname
            session["isadmin"] = False if fetchedAdmin == None else True

            conn.close()
            return redirect("/")
        else:
            return render_template("login.html")
    except dbapi.errors.UniqueViolation:
        flash("You are already logged in")
        return render_template("login.html")
    except error:
        flash("Something happened")
        return render_template("login.html")

def edit_page():
    if not session.get("loggedin"):
        return redirect("/access-denied")
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        country_statement2 = "SELECT name FROM country;"
        cur.execute(country_statement2)
        fetched_country = cur.fetchall()
        if "id" not in session.keys():
            flash("You must edit ")
            return "Can not go to edit page without logging in"

        infos_query = ""
        if session["isadmin"] is True:
            infos_query = f"Select name,surname,email,country_id,address from admin where id= {session['id']}"
        else:
            infos_query = f"Select name,surname,email,country_id,address from users where id= {session['id']}"

        cur.execute(infos_query)
        infos = cur.fetchone()
        country_statement2 = f"SELECT name FROM country WHERE id='{infos[3]}'"
        cur.execute(country_statement2)
        (infosCountry,) = cur.fetchone()

        if request.method == "POST":
            name = request.form["name"]
            surname = request.form["surname"]
            email = request.form["email"]
            password = request.form["password"]
            password_conf = request.form["password_conf"]
            address = request.form["address"]
            country = request.form["country"]

            if country is not None:
                country_statement = f"SELECT id FROM country WHERE name='{country}'"
                cur.execute(country_statement)
                fetched = cur.fetchone()

                if fetched is None:
                    flash("Please enter a valid country")
                    return render_template("edit.html", infos=infos, infosCountry=infosCountry, fetched_country=fetched_country)
                (country_id,) = fetched
            if (
                name == ""
                and surname == ""
                and email == ""
                and password == ""
                and address == ""
                and country_id == infos[3]
            ):
                flash("Nothing to change")
                return render_template("edit.html", infos=infos, infosCountry=infosCountry, fetched_country=fetched_country)
            if password != "" and len(password) < 6:
                flash("Password length should be at least 6")
                return render_template("edit.html", infos=infos, infosCountry=infosCountry, fetched_country=fetched_country)
            if password != password_conf:
                flash("Password matching failed")
                return render_template("edit.html", infos=infos, infosCountry=infosCountry, fetched_country=fetched_country)

            #check if there already exists an account registered with requested email address
            if not (email == ""):
                print("here")
                fetchedAdminId = 0
                fetchedUserId = 0
                st = f"SELECT id FROM users WHERE email='{email}'"
                cur.execute(st)
                fetchedUser = cur.fetchone()
                if fetchedUser is not None:
                    (fetchedUserId,) = fetchedUser
                    print(fetchedUserId, "fetchedUserId")
                
                st = f"SELECT id FROM admin WHERE email='{email}'"
                cur.execute(st)
                fetchedAdmin = cur.fetchone()
                if fetchedAdmin is not None:
                    (fetchedAdminId,) = fetchedAdmin
                    print(fetchedAdminId, "fetchedAdminId")

                print("session[id] ", session["id"] )
                if not (session["id"] == fetchedAdminId) or (session["id"] == fetchedAdminId):
                    flash("There already exists an account registered with this email address.")
                    return render_template("edit.html", infos=infos, infosCountry=infosCountry, fetched_country=fetched_country)


            q = " name='" + name + "' ," if name != "" else ""
            q = q + (" surname='" + surname + "' ," if surname != "" else "")
            q = q + (" email='" + email + "' ," if email != "" else "")
            q = q + (" address='" + address + "' ," if address != "" else "")
            q = q + (" password='" + password + "' ," if password != "" else "")
            q = q + (
                " country=" + str(country_id) + " ," if country_id != infos[3] else ""
            )
            if q == "":
                flash("Couldn't updated")
                return redirect("/edit")
            else:
                if q[len(q) - 1] == ",":
                    q = q[:-1]
                q = q + f" where id= {session['id']}"
                if session["isadmin"] is True:
                    q = "UPDATE admin SET" + q
                else:
                    q = "UPDATE users SET" + q
                cur.execute(q)
                flash("Successfully updated")
            return redirect("/edit")
        else:
            return render_template("edit.html", infos=infos, infosCountry=infosCountry, fetched_country=fetched_country)

    except error:
        return "Something happened"
    finally:
        cur.close()
        conn.commit()
        conn.close()

def delete_profile():
    if not session.get("loggedin"):
        return redirect("/access-denied")
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        infos_query = ""

        if session is not None:
            if session["isadmin"] is True:
                infos_query = f"delete from admin where id={session['id']};"
            else:
                infos_query = f"delete from users where id={session['id']};"

            cur.execute(infos_query)
            session.clear()

        cur.close()
        conn.commit()
    except error:
        return "Something happened"
    finally:
        conn.close()
        return redirect("/account-deleted")

def logout_page():
    if session is not None:
        session.clear()
    return redirect("/")

def account_deleted():
    return render_template("account-deleted.html")

def access_denied():
    return render_template("access-denied.html")


# home page and global page
app.add_url_rule("/", view_func=home_page, methods=["GET"])
app.add_url_rule("/global", view_func=global_page)

# case table pages
app.add_url_rule("/case", view_func=cases_page, methods=["GET", "POST"])
app.add_url_rule("/edit-case", view_func=edit_cases_page, methods=["GET", "POST"])
app.add_url_rule("/add-case", view_func=add_case_data, methods=["GET", "POST"])
app.add_url_rule("/update-case", view_func=update_last_case, methods=["GET", "POST"])
app.add_url_rule(
    "/delete-case/<country_name>", view_func=delete_last_case, methods=["GET"]
)

# test table pages
app.add_url_rule("/test", view_func=tests_page, methods=["GET", "POST"])
app.add_url_rule("/edit-test", view_func=edit_tests_page, methods=["GET", "POST"])
app.add_url_rule("/add-test", view_func=add_test_data, methods=["GET", "POST"])
app.add_url_rule("/update-test", view_func=update_last_test, methods=["GET", "POST"])
app.add_url_rule(
    "/delete-test/<country_name>", view_func=delete_last_test, methods=["GET"]
)

# death table pages
app.add_url_rule("/death", view_func=deaths_page)
app.add_url_rule("/edit-death", view_func=edit_deaths_page)
app.add_url_rule("/add-death", view_func=add_death_data, methods=["GET", "POST"])
app.add_url_rule("/update-death", view_func=update_last_death, methods=["GET", "POST"])
app.add_url_rule(
    "/delete-death/<country_name>", view_func=delete_last_death, methods=["GET"]
)

# vaccination table pages
app.add_url_rule("/vaccination", view_func=vaccinations_page)
app.add_url_rule("/edit-vaccination", view_func=edit_vaccinations_page)
app.add_url_rule(
    "/add-vaccination", view_func=add_vaccination_data, methods=["GET", "POST"]
)
app.add_url_rule(
    "/update-vaccination", view_func=update_last_vaccination, methods=["GET", "POST"]
)
app.add_url_rule(
    "/delete-vaccination/<country_name>",
    view_func=delete_last_vaccination,
    methods=["GET"],
)

# country table pages
app.add_url_rule("/countries", view_func=countries_page)
app.add_url_rule("/countries/<country_id>", view_func=country_page)

# user pages
app.add_url_rule("/register", view_func=register_page, methods=["GET", "POST"])
app.add_url_rule("/login", view_func=login_page, methods=["GET", "POST"])
app.add_url_rule("/edit", view_func=edit_page, methods=["GET", "POST"])
app.add_url_rule("/delete-profile", view_func=delete_profile, methods=["GET"])
app.add_url_rule("/logout", view_func=logout_page)

# access denied and account deleted page
app.add_url_rule("/access-denied", view_func=access_denied)
app.add_url_rule("/account-deleted", view_func=account_deleted)

app.run(host="0.0.0.0", port=8080, debug=True)
