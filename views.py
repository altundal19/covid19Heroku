from __future__ import print_function
import sys
from os import error
from werkzeug.utils import redirect
import config
from flask import Flask, render_template, request, session, flash
from datetime import date, datetime
import psycopg2 as dbapi
import numpy as np

    
def checkIsAdmin():
    isadmin = False
    if('loggedin' in session and session["loggedin"] == True):
        isadmin = True if (
            'isadmin' in session and session["isadmin"] == True) else False

    return isadmin

def getCountries(curr):
    st = "SELECT name FROM country;"
    curr.execute(st)
    countries = curr.fetchall()
    return countries


def getCountryId(country_name, cur):
    get_country_st = f"SELECT id FROM country where name='{country_name}';"
    cur.execute(get_country_st)
    fetched_country_id = cur.fetchone()
    return fetched_country_id

def global_page():
    if not session.get('loggedin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    pageNumber =request.args.get("pageNumber") if request.args.get("pageNumber") is not None else "1"
    startDate = request.args.get("startDate")  if request.args.get("startDate") is not None else "2020-01-01" 
    endDate = request.args.get("endDate")  if request.args.get("endDate") is not None else "2023-01-01"
    countryName = request.args.get("countryName") if request.args.get("countryName") is not None else "Turkey"
    order = request.args.get("order") if request.args.get("order") is not None else "ASC"
    pageNumber = int(pageNumber)
    offset = (pageNumber-1)*50
    paginationValues = (pageNumber,pageNumber+1,pageNumber+2) if (pageNumber)>0 else (0,1,2)
    result = None
    header = ("Date", "Country Name", "total_cases", "new_cases", "total_deaths", "new_deaths", "total_tests", "new_tests", "total_vaccinations", "new_vaccinations")
    try:
        curr = conn.cursor()
        fetched_country = getCountries(curr)

        format = "%Y-%m-%d"

        try:
            datetime.strptime(startDate, format)
            datetime.strptime(endDate, format)
        except ValueError:
            flash("Please enter a valid date in the format YYYY-MM-DD")
            print(request.path)
            return render_template("global.html",result=result,header= header,paginationValues=paginationValues,fetched_country=fetched_country)
        

        select = f"SELECT covid19.datetime, country.name,total_cases, new_cases, total_deaths, new_deaths, total_tests, new_tests, total_vaccinations, new_vaccinations "
        fr = f" FROM covid19 LEFT JOIN country ON covid19.country_id = country.id INNER JOIN cases ON cases_id = cases.id INNER JOIN death ON death_id = death.id  INNER JOIN test ON test_id = test.id INNER JOIN vaccination ON vaccination_id = vaccination.id "
        where = f" WHERE country.name = '{countryName}' and datetime >= '{startDate}' AND datetime <= '{endDate}' "
        orderby = f" ORDER BY datetime {order} OFFSET {offset} ROWS FETCH NEXT 50 ROWS ONLY"
        
        statement = select + fr + where + orderby
        curr.execute(statement)
        result = curr.fetchall()
        curr.close()
        conn.commit()
        return render_template("global.html",result=result,header= header,paginationValues=paginationValues,fetched_country=fetched_country)
    except ValueError:
        flash("Date Format is not proper")
        return render_template("global.html",result=result,header= header,paginationValues= paginationValues,fetched_country=fetched_country)
    except dbapi.Error:
        flash("Error")
        return render_template("global.html",result=result,header= header,paginationValues= paginationValues,fetched_country=fetched_country)
    finally:
        conn.close()
        return render_template("global.html",result=result,header= header,paginationValues= paginationValues,fetched_country=fetched_country)


def countries_page():
    if not session.get('loggedin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    countries = None
    isadmin = False
    country_id = None
    try:
        isadmin = checkIsAdmin()
        curr = conn.cursor()
        statement = "SELECT * FROM country;"
        curr.execute(statement)
        result = curr.fetchall()
        countries = np.zeros([1, 8], dtype='str')
        for row in result:
            newRow = np.array(row)
            countries = np.vstack([countries, newRow])

        countries = np.delete(countries, 0, 0)
        curr.close()
        conn.commit()
    except dbapi.DatabaseError:
        conn.rollback()
    finally:
        conn.close()
        return render_template("countries/countries.html", isadmin=isadmin, countries=countries)

def country_page(country_id):
    if not session.get('loggedin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    countryInfo = {}
    isadmin = False
    try:
        isadmin = checkIsAdmin()
        curr = conn.cursor()
        statement = f"select * from country where country.id='{country_id}'"
        curr.execute(statement)
        result = curr.fetchone()
        countryInfo['id'] = result[0]
        countryInfo['name'] = result[1]

        countryInfo['population'] = result[2]
        countryInfo['age_65_older'] = result[3]
        countryInfo['age_70_older'] = result[4]
        countryInfo['median_age'] = result[5]
        countryInfo['handwashing_facilities'] = result[6]
        countryInfo['hospital_beds_per_thousand'] = result[7]

        curr.close()
        conn.commit()
        conn.close()
    except:
        conn.rollback()
    finally:
        conn.close()
    return render_template('countries/country.html', country_id=country_id, countryInfo=countryInfo, isadmin=isadmin)

# cases
def cases_page():
    if not session.get('loggedin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)

    #pagination
    countryName = request.args.get("countryName")
    pageNumber =request.args.get("pageNumber") if request.args.get("pageNumber") is not None else "1"
    pageNumber = int(pageNumber)
    offset = (pageNumber-1)*50
    paginationValues = (pageNumber,pageNumber+1,pageNumber+2) if (pageNumber)>0 else (0,1,2)

    countries = None
    cases = None
    isadmin = False
    headings = ("total_cases", "new_cases", "total_cases_per_million", "new_cases_per_million", "new_cases_smoothed", "new_cases_smoothed_per_million")
    try:
        isadmin = checkIsAdmin()
        curr = conn.cursor()
        
        countries = getCountries(curr)

        select = """SELECT covid19.datetime, country.name, total_cases, new_cases, total_cases_per_million, new_cases_per_million, new_cases_smoothed, new_cases_smoothed_per_million"""
        fr = f" FROM covid19 LEFT JOIN country ON covid19.country_id = country.id INNER JOIN cases ON cases_id = cases.id"
        where = " "
        if countryName is not None:
            where = f" WHERE country.name = '{countryName}'"
        orderby = f" ORDER BY datetime desc OFFSET {offset} ROWS FETCH NEXT 50 ROWS ONLY"

        statement = select + fr + where + orderby
        curr.execute(statement)
        result = curr.fetchall()
        cases = np.zeros([1, 8], dtype='str')
        for row in result:
            newRow = np.array(row)
            cases = np.vstack([cases, newRow])

        cases = np.delete(cases, 0, 0)
        curr.close()
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()
        return render_template("cases/cases.html", paginationValues=paginationValues, headings=headings, isadmin=isadmin, cases=cases, countries=countries)

def edit_cases_page():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    #pagination
    countryName = request.args.get("countryName")
    pageNumber =request.args.get("pageNumber") if request.args.get("pageNumber") is not None else "1"
    pageNumber = int(pageNumber)
    offset = (pageNumber-1)*50
    paginationValues = (pageNumber,pageNumber+1,pageNumber+2) if (pageNumber)>0 else (0,1,2)

    countries = None
    cases = None
    isadmin = False
    headings = ("total_cases", "new_cases", "total_cases_per_million", "new_cases_per_million", "new_cases_smoothed", "new_cases_smoothed_per_million")
    try:
        isadmin = checkIsAdmin()
        if isadmin == False:
            redirect('/access-denied')
        curr = conn.cursor()
        countries = getCountries(curr)
        
        select = """SELECT covid19.datetime, country.name, total_cases, new_cases, total_cases_per_million, new_cases_per_million, new_cases_smoothed, new_cases_smoothed_per_million"""
        fr = f" FROM covid19 LEFT JOIN country ON covid19.country_id = country.id INNER JOIN cases ON cases_id = cases.id"
        where = " "
        if countryName is not None:
            where = f" WHERE country.name = '{countryName}'"
        orderby = f" ORDER BY datetime desc OFFSET {offset} ROWS FETCH NEXT 50 ROWS ONLY"

        statement = select + fr + where + orderby

        curr.execute(statement)
        result = curr.fetchall()

        cases = np.zeros([1, 8], dtype='str')
        for row in result:
            newRow = np.array(row)
            cases = np.vstack([cases, newRow])

        cases = np.delete(cases, 0, 0)
        curr.close()
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()
        return render_template('cases/edit-cases.html', paginationValues=paginationValues, headings=headings, isadmin=isadmin, cases=cases, countries=countries)

def add_case_data():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        countries = getCountries(cur)
        
        if request.method == "POST":
            country_name = request.form["country"]
            date_time = request.form["date"]
            total_cases = request.form["total_cases"]
            new_cases = request.form["new_cases"]
            total_cases_per_million = request.form["total_cases_per_million"] if request.form["total_cases_per_million"] !="" else "NULL"
            new_cases_per_million = request.form["new_cases_per_million"] if request.form["new_cases_per_million"] !="" else "NULL"
            new_cases_smoothed = request.form["new_cases_smoothed"] if request.form["new_cases_smoothed"] !="" else "NULL"
            new_cases_smoothed_per_million = request.form["new_cases_smoothed_per_million"] if request.form["new_cases_smoothed_per_million"] !="" else "NULL"
            
            country_id_fetched  = getCountryId(country_name, cur)

            if country_id_fetched is None:
                flash("Please enter a valid country")
                return render_template("cases/add.html", countries=countries)
            
            (country_id,) = country_id_fetched

            format = "%Y-%m-%d"
            try:  
                datetime.strptime(date_time, format)
            except ValueError:
                flash("Please enter a valid date in the format YYYY-MM-DD")
                return render_template("cases/add.html", countries=countries)

            check_q = f"select id, cases_id from covid19 where datetime = '{date_time}' and country_id = {country_id};"
            cur.execute(check_q)
            case_special = cur.fetchone()
            cases_id = None
            id = None
            if case_special is not None:
                id,cases_id = case_special
            
            if(case_special is not None and cases_id is not None):
                flash("You can not add a new record into an already existing record.")
                return render_template("cases/add.html", countries=countries)

            if(total_cases =="" and new_cases ==""):
                flash("Please provide total case and new case values.")
                return render_template("cases/add.html", countries=countries)
            
            q = f"INSERT INTO cases (total_cases, new_cases, total_cases_per_million, new_cases_per_million, new_cases_smoothed, new_cases_smoothed_per_million, country_id)\
                  VALUES ({total_cases}, {new_cases}, {total_cases_per_million}, {new_cases_per_million}, {new_cases_smoothed}, {new_cases_smoothed_per_million}, {country_id}) RETURNING id;"
            
            cur.execute(q)
            cases_created_id = cur.fetchone()[0]
            
            s=""
            if(id is None):
                s =  f"INSERT INTO covid19 (death_id, test_id, vaccination_id, cases_id, country_id,datetime)\
                  VALUES (NULL, NULL, NULL, {cases_created_id},{country_id},'{date_time}');" 
            else:
                s = f"UPDATE covid19 SET cases_id={cases_created_id} where id = {id};"   
            cur.execute(s)            
            conn.commit()

            flash("Successfully created")
            return render_template("cases/add.html", countries=countries)
        else:
            return render_template("cases/add.html", countries=countries)
    except dbapi.Error: 
        print(dbapi.Error)
        return render_template("cases/add.html", countries=countries)
    finally:
        cur.close()
        conn.commit()
        conn.close()

def update_last_case():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        country_statement2 = "SELECT name FROM country;"
        cur.execute(country_statement2)
        fetched_country =cur.fetchall()

        if request.method == "POST":
            country_name = request.form["country"]
            date_time = request.form["date"]
            total_cases = request.form["total_cases"]
            new_cases = request.form["new_cases"] if request.form["new_cases"] !="" else "NULL"
            total_cases_per_million = request.form["total_cases_per_million"]
            new_cases_per_million = request.form["new_cases_per_million"]  if request.form["new_cases_per_million"] !="" else "NULL"
            new_cases_smoothed = request.form["new_cases_smoothed"] if request.form["new_cases_smoothed"] !="" else "NULL"
            new_cases_smoothed_per_million = request.form["new_cases_smoothed_per_million"] if request.form["new_cases_smoothed_per_million"] !="" else "NULL"
            
            


            q = f"select distinct on(covid19.datetime) covid19.id,cases_id,datetime,country.name from covid19 LEFT JOIN country ON covid19.country_id = country.id  \
                where country.name='{country_name}' order by covid19.datetime DESC"
            
            cur.execute(q)
            last_id,last_cases_id,last_date,country_name_last =cur.fetchone()
           
            if(date_time != str(last_date)):
                flash(f"You can only update last day ({last_date}) case informations of relevant country ({country_name_last})")
                return render_template("cases/update.html", fetched_country=fetched_country)
            if(last_cases_id is None):
                flash(f"Case information could not find, please first add.")
                return render_template("cases/update.html", fetched_country=fetched_country)
            q = " total_cases='" + total_cases + "' ," if total_cases != "" else ""
            q = q + (" new_cases='" + new_cases + "' ," if new_cases != "" else "")
            q = q + (" total_cases_per_million='" + total_cases_per_million + "' ," if total_cases_per_million != "" else "")
            q = q + (" new_cases_per_million='" + new_cases_per_million + "' ," if new_cases_per_million != "" else "")
            q = q + (" new_cases_smoothed='" + new_cases_smoothed + "' ," if new_cases_smoothed != "" else "")
            q = q + (" new_cases_smoothed_per_million='" + new_cases_smoothed_per_million + "' ," if new_cases_smoothed_per_million != "" else "")
            

            if q == "":
                flash("Couldn't updated")
                return redirect("/update-case")
            else:
                if q[len(q) - 1] == ",":
                    q = q[:-1]
                q = q + f" where id= {last_cases_id}"
                q = "UPDATE cases SET " + q
                
            cur.execute(q)     
            flash("Updated succesfully")
            return redirect("/update-case")
        else:
            return render_template("cases/update.html", fetched_country=fetched_country)

               
        conn.commit()
        cur.close()
    except dbapi.Error: 
        flash("error")
        print(dbapi.Error)
        return render_template("cases/update.html", fetched_country=fetched_country)
    finally:
        conn.close()

def delete_last_case(country_name):
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        country_statement2 = f"SELECT id FROM country WHERE name='{country_name}';"
        cur.execute(country_statement2)
        fetched = cur.fetchone()
        (c_id,) = fetched
        if(c_id is None):
            flash("Could not find such an country")
            return redirect("/edit-case")
        q = f"SELECT max(datetime) FROM covid19 WHERE country_id = {c_id};"
        cur.execute(q)
        fetched = cur.fetchone()
        (max_date,)= fetched
        if(max_date is None):
            flash("Could not find such a data")
            return redirect("/edit-case")
        q = f"SELECT cases_id FROM covid19 WHERE country_id = {c_id} and datetime='{str(max_date)}';"
        cur.execute(q)
        fetched = cur.fetchone()
        (cases_id,)= fetched
        if(cases_id is None):
            flash(str(max_date)+"--Could not find any case data at "+str(max_date)+". It has already been deleted.")
            return redirect("/edit-case")
        q = f"DELETE FROM cases WHERE id = {cases_id}"
        cur.execute(q)
        q = f"DELETE FROM covid19 WHERE datetime = '{str(max_date)}'  and country_id = {c_id} \
                                                                    and death_id is NULL\
                                                                    and cases_id is NULL\
                                                                    and vaccination_id is NULL\
                                                                    and test_id is NULL"
        cur.execute(q)
        conn.commit()
        flash(f"Deleted case data belonging to date({max_date}) and country({country_name})...")
        return redirect("/edit-case")

    except dbapi.Error: 
        flash("error")
        print(dbapi.Error)
        return redirect("/edit-case")

# test
def tests_page():
    if not session.get('loggedin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    tests = None
    isadmin = False
    headings = ("total_tests", "new_tests", "total_tests_per_thousand", "new_tests_per_thousand", "new_tests_smoothed", "positive_rate")
    
    #pagination
    countryName = request.args.get("countryName")
    pageNumber =request.args.get("pageNumber") if request.args.get("pageNumber") is not None else "1"
    pageNumber = int(pageNumber)
    offset = (pageNumber-1)*50
    paginationValues = (pageNumber,pageNumber+1,pageNumber+2) if (pageNumber)>0 else (0,1,2)
    countries = None

    try:
        isadmin = checkIsAdmin()
        curr = conn.cursor()
        
        countries = getCountries(curr)
        select = """SELECT covid19.datetime, country.name, total_tests, new_tests, total_tests_per_thousand, new_tests_per_thousand, new_tests_smoothed, positive_rate"""
        fr = f" FROM covid19 LEFT JOIN country ON covid19.country_id = country.id INNER JOIN test ON covid19.test_id = test.id"
        where = " "
        if countryName is not None:
            where = f" WHERE country.name = '{countryName}'"
        orderby = f" ORDER BY datetime desc OFFSET {offset} ROWS FETCH NEXT 50 ROWS ONLY"
        statement = select + fr + where + orderby
        curr.execute(statement)

        result = curr.fetchall()
        tests = np.zeros([1, 8], dtype='str')
        for row in result:
            newRow = np.array(row)
            tests = np.vstack([tests, newRow])

        tests = np.delete(tests, 0, 0)
        curr.close()
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()
        return render_template("tests/tests.html", headings=headings, isadmin=isadmin, tests=tests, countries=countries, paginationValues=paginationValues)

def edit_tests_page():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    tests = None
    isadmin = False
    headings = ("total_tests", "new_tests", "total_tests_per_thousand", "new_tests_per_thousand", "new_tests_smoothed", "positive_rate")
    
    #pagination
    countryName = request.args.get("countryName")
    pageNumber =request.args.get("pageNumber") if request.args.get("pageNumber") is not None else "1"
    pageNumber = int(pageNumber)
    offset = (pageNumber-1)*50
    paginationValues = (pageNumber,pageNumber+1,pageNumber+2) if (pageNumber)>0 else (0,1,2)
    countries = None
    try:
        isadmin = checkIsAdmin()
        if isadmin == False:
            redirect('/access-denied')
        
        curr = conn.cursor()
        countries = getCountries(curr)
        select = """SELECT covid19.datetime, country.name, total_tests, new_tests, total_tests_per_thousand, new_tests_per_thousand, new_tests_smoothed, positive_rate"""
        fr = f" FROM covid19 LEFT JOIN country ON covid19.country_id = country.id INNER JOIN test ON covid19.test_id = test.id"
        where = " "
        if countryName is not None:
            where = f" WHERE country.name = '{countryName}'"
        orderby = f" ORDER BY datetime desc OFFSET {offset} ROWS FETCH NEXT 50 ROWS ONLY"
        statement = select + fr + where + orderby

        curr.execute(statement)

        result = curr.fetchall()
        tests = np.zeros([1, 8], dtype='str')
        for row in result:
            newRow = np.array(row)
            tests = np.vstack([tests, newRow])

        tests = np.delete(tests, 0, 0)
        curr.close()
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()
        return render_template("tests/edit-tests.html", headings=headings, isadmin=isadmin, tests=tests, countries=countries, paginationValues=paginationValues)


def add_test_data():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        countries = getCountries(cur)
        headings = ("total_tests", "new_tests", "total_tests_per_thousand", "new_tests_per_thousand", "new_tests_smoothed", "positive_rate")
    
        if request.method == "POST":
            country_name = request.form["country"]
            date_time = request.form["date"]
            total_tests = request.form["total_tests"]
            new_tests = request.form["new_tests"]
            total_tests_per_thousand = request.form["total_tests_per_thousand"] if request.form["total_tests_per_thousand"] !="" else "NULL"
            new_tests_per_thousand = request.form["new_tests_per_thousand"] if request.form["new_tests_per_thousand"] !="" else "NULL"
            new_tests_smoothed = request.form["new_tests_smoothed"] if request.form["new_tests_smoothed"] !="" else "NULL"
            positive_rate = request.form["positive_rate"] if request.form["positive_rate"] !="" else "NULL"
            
            country_id_fetched  = getCountryId(country_name, cur)

            if country_id_fetched is None:
                flash("Please enter a valid country")
                return render_template("tests/add.html", headings=headings, countries=countries)
            
            (country_id,) = country_id_fetched

            format = "%Y-%m-%d"

            
            try:
                
                datetime.strptime(date_time, format)
            except ValueError:
                flash("Please enter a valid date in the format YYYY-MM-DD")
                return render_template("tests/add.html", headings=headings,countries=countries)

            check_q = f"select id, test_id from covid19 where datetime = '{date_time}' and country_id = {country_id};"
            cur.execute(check_q)
            case_special = cur.fetchone()
            test_id = None
            id = None
            if case_special is not None:
                id,test_id = case_special
            
            if(case_special is not None and test_id is not None):
                flash("You can not add a new record into an already existing record")
                return render_template("tests/add.html",headings=headings,  countries=countries)

            if(total_tests =="" and new_tests ==""):
                flash("Please provide total test and new case values")
                return render_template("tests/add.html", headings=headings, countries=countries)
    
            q = f"INSERT INTO test (total_tests, new_tests, total_tests_per_thousand, new_tests_per_thousand, new_tests_smoothed, positive_rate, country_id)\
                  VALUES ({total_tests}, {new_tests}, {total_tests_per_thousand}, {new_tests_per_thousand}, {new_tests_smoothed}, {positive_rate}, {country_id}) RETURNING id;"
            cur.execute(q)
            tests_created_id = cur.fetchone()[0]
            
            s=""
            if(id is None):
                s =  f"INSERT INTO covid19 (death_id, test_id, vaccination_id, cases_id, country_id,datetime)\
                  VALUES (NULL, {tests_created_id}, NULL, NULL,{country_id},'{date_time}');" 
            else:
                s = f"UPDATE covid19 SET test_id={tests_created_id} where id = {id};"   
            print(s)
            cur.execute(s) 
            cur.close()   
            conn.commit()
            flash("Successfully created")
            return render_template("tests/add.html", headings=headings, countries=countries)
        else:
            return render_template("tests/add.html", headings=headings, countries=countries)
    except dbapi.Error: 
        print(dbapi.Error)
        conn.rollback()
        return render_template("tests/add.html", headings=headings, countries=countries)
    finally:        
        conn.close()

def update_last_test():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    headings = ("total_tests", "new_tests", "total_tests_per_thousand", "new_tests_per_thousand", "new_tests_smoothed", "positive_rate")
    try:
        
        cur = conn.cursor()
        country_statement2 = "SELECT name FROM country;"
        
        cur.execute(country_statement2)
        fetched_country =cur.fetchall()

        if request.method == "POST":
            country_name = request.form["country"]
            date_time = request.form["date"]
            total_tests = request.form["total_tests"]
            new_tests = request.form["new_tests"]
            total_tests_per_thousand = request.form["total_tests_per_thousand"]
            new_tests_per_thousand = request.form["new_tests_per_thousand"] 
            new_tests_smoothed = request.form["new_tests_smoothed"]
            positive_rate = request.form["positive_rate"]
            
            format = "%Y-%m-%d"

            
            try:               
                datetime.strptime(date_time, format)
            except ValueError:
                flash("Please enter a valid date in the format YYYY-MM-DD")
                return render_template("tests/update.html" ,headings=headings,fetched_country=fetched_country)

            q = f"select distinct on(covid19.datetime) covid19.id,test_id,datetime,country.name from covid19 LEFT JOIN country ON covid19.country_id = country.id  \
                where country.name='{country_name}' order by covid19.datetime DESC"
            
            cur.execute(q)
            last_id,last_test_id,last_date,country_name_last =cur.fetchone()
           
            if(date_time != str(last_date)):
                flash(f"You can only update last day ({last_date}) test informations of relevant country ({country_name_last})")
                return render_template("tests/update.html" ,headings=headings,fetched_country=fetched_country)
            if(last_test_id is None):
                flash(f"Vaccination information could not find, please first add.")
                return render_template("tests/update.html", headings=headings, fetched_country=fetched_country)

            q = " total_tests='" + total_tests + "' ," if total_tests != "" else ""
            q = q + (" new_tests='" + new_tests + "' ," if new_tests != "" else "")
            q = q + (" total_tests_per_thousand='" + total_tests_per_thousand + "' ," if total_tests_per_thousand != "" else "")
            q = q + (" new_tests_per_thousand='" + new_tests_per_thousand + "' ," if new_tests_per_thousand != "" else "")
            q = q + (" new_tests_smoothed='" + new_tests_smoothed + "' ," if new_tests_smoothed != "" else "")
            q = q + (" positive_rate='" + positive_rate + "' ," if positive_rate != "" else "")
            

            if q == "":
                flash("Couldn't updated")
                return redirect("/update-test")
            else:
                if q[len(q) - 1] == ",":
                    q = q[:-1]
                q = q + f" where id= {last_test_id}"
                q = "UPDATE test SET " + q
                
            cur.execute(q)            
            conn.commit()
            flash("Updated succesfully")
            return redirect("/update-test")
        else:
            return render_template("tests/update.html", headings=headings,fetched_country=fetched_country)
    except dbapi.Error: 
        flash("error")
        print(dbapi.Error)
        return render_template("tests/update.html", headings=headings,fetched_country=fetched_country)
    finally:
        cur.close()
        conn.commit()
        conn.close()

def delete_last_test(country_name):
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        country_statement2 = f"SELECT id FROM country WHERE name='{country_name}';"
        cur.execute(country_statement2)
        fetched = cur.fetchone()
        (c_id,) = fetched

        if(c_id is None):
            flash("Could not find such an country")
            return redirect("/edit-test")
        q = f"SELECT max(datetime) FROM covid19 WHERE country_id = {c_id};"
        cur.execute(q)
        fetched = cur.fetchone()
        (max_date,)= fetched
        if(max_date is None):
            flash("Could not find such a data")
            return redirect("/edit-test")
        
        q = f"SELECT test_id FROM covid19 WHERE country_id = {c_id} and datetime='{str(max_date)}';"
        cur.execute(q)
        fetched = cur.fetchone()
        (test_id,)= fetched
        if(test_id is None):
            flash(str(max_date)+"--Could not find any test data at "+str(max_date)+". It has already been deleted.")
            return redirect("/edit-test")
        
        q = f"DELETE FROM test WHERE id = {test_id}"
        cur.execute(q)
        q = f"DELETE FROM covid19 WHERE datetime = '{str(max_date)}'  and country_id = {c_id} \
                                                                    and death_id is NULL\
                                                                    and cases_id is NULL\
                                                                    and vaccination_id is NULL\
                                                                    and test_id is NULL"
        cur.execute(q)
        conn.commit()
        flash(f"Deleted test data belonging to date({max_date}) and country({country_name})...")
        return redirect("/edit-test")

    except dbapi.Error: 
        flash("error")
        print(dbapi.Error)
        return redirect("/edit-test")


# vaccination
def vaccinations_page():
    if not session.get('loggedin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    vaccinations = None
    isadmin = False
    headings = ("total_vaccinations", "people_vaccinated", "people_fully_vaccinated", "total_boosters", "new_vaccinations", "new_vaccinations_smoothed")
        
    #pagination
    countryName = request.args.get("countryName")
    pageNumber =request.args.get("pageNumber") if request.args.get("pageNumber") is not None else "1"
    pageNumber = int(pageNumber)
    offset = (pageNumber-1)*50
    paginationValues = (pageNumber,pageNumber+1,pageNumber+2) if (pageNumber)>0 else (0,1,2)
    countries = None
    
    try:
        isadmin = checkIsAdmin()
        curr = conn.cursor()
        
        countries = getCountries(curr)
        select = """SELECT covid19.datetime, country.name, total_vaccinations, people_vaccinated, people_fully_vaccinated, total_boosters, new_vaccinations, new_vaccinations_smoothed"""
        fr = f" FROM covid19 LEFT JOIN country ON covid19.country_id = country.id INNER JOIN vaccination ON covid19.vaccination_id = vaccination.id"
        where = " "
        if countryName is not None:
            where = f" WHERE country.name = '{countryName}'"
        orderby = f" ORDER BY datetime desc OFFSET {offset} ROWS FETCH NEXT 50 ROWS ONLY"
        statement = select + fr + where + orderby
        
        curr.execute(statement)
        result = curr.fetchall()
        vaccinations = np.zeros([1, 8], dtype='str')
        for row in result:
            newRow = np.array(row)
            vaccinations = np.vstack([vaccinations, newRow])

        vaccinations = np.delete(vaccinations, 0, 0)
        curr.close()
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()
        return render_template("vaccinations/vaccinations.html", headings=headings, isadmin=isadmin, vaccinations=vaccinations, countries=countries, paginationValues=paginationValues)


def edit_vaccinations_page():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    vaccinations = None
    isadmin = False
    headings = ("total_vaccinations", "people_vaccinated", "people_fully_vaccinated", "total_boosters", "new_vaccinations", "new_vaccinations_smoothed")
        
    #pagination
    countryName = request.args.get("countryName")
    pageNumber =request.args.get("pageNumber") if request.args.get("pageNumber") is not None else "1"
    pageNumber = int(pageNumber)
    offset = (pageNumber-1)*50
    paginationValues = (pageNumber,pageNumber+1,pageNumber+2) if (pageNumber)>0 else (0,1,2)
    countries = None
    
    try:
        isadmin = checkIsAdmin()
        if isadmin == False:
            redirect('/access-denied')
        curr = conn.cursor()
        
        countries = getCountries(curr)
        select = """SELECT covid19.datetime, country.name, total_vaccinations, people_vaccinated, people_fully_vaccinated, total_boosters, new_vaccinations, new_vaccinations_smoothed"""
        fr = f" FROM covid19 LEFT JOIN country ON covid19.country_id = country.id INNER JOIN vaccination ON covid19.vaccination_id = vaccination.id"
        where = " "
        if countryName is not None:
            where = f" WHERE country.name = '{countryName}'"
        orderby = f" ORDER BY datetime desc OFFSET {offset} ROWS FETCH NEXT 50 ROWS ONLY"
        statement = select + fr + where + orderby
        print(statement)
        curr.execute(statement)
        result = curr.fetchall()
        vaccinations = np.zeros([1, 8], dtype='str')
        for row in result:
            newRow = np.array(row)
            vaccinations = np.vstack([vaccinations, newRow])

        vaccinations = np.delete(vaccinations, 0, 0)
        curr.close()
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()
        return render_template("vaccinations/edit-vaccinations.html", headings=headings, isadmin=isadmin, vaccinations=vaccinations, countries=countries, paginationValues=paginationValues)

def add_vaccination_data():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    headings = ("total_vaccinations", "people_vaccinated", "people_fully_vaccinated", "total_boosters", "new_vaccinations", "new_vaccinations_smoothed")
    
    try:
        cur = conn.cursor()
        countries = getCountries(cur)
        
        if request.method == "POST":
            country_name = request.form["country"]
            date_time = request.form["date"]
            total_vaccinations = request.form["total_vaccinations"]
            people_vaccinated = request.form["people_vaccinated"]
            total_boosters = request.form["total_boosters"]
            people_fully_vaccinated = request.form["people_fully_vaccinated"]
            new_vaccinations = request.form["new_vaccinations"] if request.form["new_vaccinations"] !="" else "NULL"
            new_vaccinations_smoothed = request.form["new_vaccinations_smoothed"] if request.form["new_vaccinations_smoothed"] !="" else "NULL"
            
            country_id_fetched  = getCountryId(country_name, cur)

            if country_id_fetched is None:
                flash("Please enter a valid country")
                return render_template("vaccinations/add.html", headings=headings, countries=countries)
            
            (country_id,) = country_id_fetched

            format = "%Y-%m-%d"

            
            try:
                
                datetime.strptime(date_time, format)
            except ValueError:
                flash("Please enter a valid date in the format YYYY-MM-DD")
                return render_template("vaccinations/add.html", headings=headings,countries=countries)

            check_q = f"select id, vaccination_id from covid19 where datetime = '{date_time}' and country_id = {country_id};"
            cur.execute(check_q)
            case_special = cur.fetchone()
            vaccination_id = None
            id = None
            if case_special is not None:
                id,vaccination_id = case_special
            
            if(case_special is not None and vaccination_id is not None):
                flash("You can not add a new record into already existing record.")
                return render_template("vaccinations/add.html", headings=headings,  countries=countries)

            if(total_boosters =="" and people_vaccinated =="" and total_vaccinations=="" and people_fully_vaccinated==""):
                flash("Please provide total_boosters, people_vaccinated, total_vaccinations, people_fully_vaccinated fields")
                return render_template("vaccinations/add.html", headings=headings, countries=countries)

            q = f"INSERT INTO vaccination (total_vaccinations, people_vaccinated, people_fully_vaccinated, total_boosters, new_vaccinations, new_vaccinations_smoothed, country_id)\
                  VALUES ({total_vaccinations}, {people_vaccinated}, {people_fully_vaccinated}, {total_boosters}, {new_vaccinations}, {new_vaccinations_smoothed}, {country_id}) RETURNING id;"
            
            cur.execute(q)
            vaccination_created_id = cur.fetchone()[0]
            s=""
            if(id is None):
                s =  f"INSERT INTO covid19 (death_id, test_id, vaccination_id, cases_id, country_id,datetime)\
                  VALUES (NULL, NULL, {vaccination_created_id}, NULL, {country_id},'{date_time}');" 
            else:
                s = f"UPDATE covid19 SET vaccination_id={vaccination_created_id} where id = {id};"   
            
            cur.execute(s) 
            cur.close()   
            conn.commit()
            flash("Successfully created")
            return render_template("vaccinations/add.html", headings=headings, countries=countries)
        else:
            return render_template("vaccinations/add.html", headings=headings, countries=countries)
    except dbapi.Error: 
        print(dbapi.Error)
        conn.rollback()
        return render_template("vaccinations/add.html", headings=headings, countries=countries)
    finally:        
        conn.close()

def update_last_vaccination():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        country_statement2 = "SELECT name FROM country;"
        
        cur.execute(country_statement2)
        fetched_country =cur.fetchall()
        headings = ("total_vaccinations", "people_vaccinated", "people_fully_vaccinated", "total_boosters", "new_vaccinations", "new_vaccinations_smoothed")

        if request.method == "POST":
            country_name = request.form["country"]
            date_time = request.form["date"]
            total_vaccinations = request.form["total_vaccinations"]
            people_vaccinated = request.form["people_vaccinated"]
            people_fully_vaccinated = request.form["people_fully_vaccinated"]
            total_boosters = request.form["total_boosters"] 
            new_vaccinations = request.form["new_vaccinations"]
            new_vaccinations_smoothed = request.form["new_vaccinations_smoothed"]

            format = "%Y-%m-%d"
            try:            
                datetime.strptime(date_time, format)
            except ValueError:
                flash("Please enter a valid date in the format YYYY-MM-DD")
                return render_template("vaccinations/update.html" ,headings=headings,fetched_country=fetched_country)
            
            q = f"select distinct on(covid19.datetime) covid19.id,vaccination_id,datetime,country.name from covid19 LEFT JOIN country ON covid19.country_id = country.id  \
                where country.name='{country_name}' order by covid19.datetime DESC"
            
            cur.execute(q)
            last_id,last_vaccination_id,last_date,country_name_last =cur.fetchone()
           
            if(date_time != str(last_date)):
                flash(f"You can only update last day ({last_date}) vaccination informations of relevant country ({country_name_last})")
                return render_template("vaccinations/update.html" ,headings=headings,fetched_country=fetched_country)
            if(last_vaccination_id is None):
                flash(f"Vaccination information could not find, please first add.")
                return render_template("vaccinations/update.html", headings=headings, fetched_country=fetched_country)

            q = " total_vaccinations='" + total_vaccinations + "' ," if total_vaccinations != "" else ""
            q = q + (" people_vaccinated='" + people_vaccinated + "' ," if people_vaccinated != "" else "")
            q = q + (" people_fully_vaccinated='" + people_fully_vaccinated + "' ," if people_fully_vaccinated != "" else "")
            q = q + (" total_boosters='" + total_boosters + "' ," if total_boosters != "" else "")
            q = q + (" new_vaccinations='" + new_vaccinations + "' ," if new_vaccinations != "" else "")
            q = q + (" new_vaccinations_smoothed='" + new_vaccinations_smoothed + "' ," if new_vaccinations_smoothed != "" else "")
            

            if q == "":
                flash("Couldn't updated")
                return redirect("/update-vaccination")
            else:
                if q[len(q) - 1] == ",":
                    q = q[:-1]
                q = q + f" where id= {last_vaccination_id}"
                q = "UPDATE vaccination SET " + q
                
            cur.execute(q)            
            conn.commit()
            flash("Updated succesfully")
            return redirect("/update-vaccination")
        else:
            return render_template("vaccinations/update.html", headings=headings,fetched_country=fetched_country)
    except dbapi.Error: 
        flash("error")
        print(dbapi.Error)
        return render_template("vaccinations/update.html", headings=headings,fetched_country=fetched_country)
    finally:
        cur.close()
        conn.commit()
        conn.close()




def delete_last_vaccination(country_name):
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        country_statement2 = f"SELECT id FROM country WHERE name='{country_name}';"
        cur.execute(country_statement2)
        fetched = cur.fetchone()
        (c_id,) = fetched

        if(c_id is None):
            flash("Could not find such an country")
            return redirect("/edit-vaccination")
        q = f"SELECT max(datetime) FROM covid19 WHERE country_id = {c_id};"
        cur.execute(q)
        fetched = cur.fetchone()
        (max_date,)= fetched
        if(max_date is None):
            flash("Could not find such a data")
            return redirect("/edit-vaccination")
        

        q = f"SELECT vaccination_id FROM covid19 WHERE country_id = {c_id} and datetime='{str(max_date)}';"
        print(q, "get id statement")
        cur.execute(q)
        fetched = cur.fetchone()
        (vaccination_id,)= fetched
        if(vaccination_id is None):
            flash(str(max_date)+"--Could not find any vaccination data at "+str(max_date)+". It has already been deleted.")
            return redirect("/edit-vaccination")
        
        q = f"DELETE FROM vaccination WHERE id = {vaccination_id};"
        print(q, "st")
        cur.execute(q)
        q = f"DELETE FROM covid19 WHERE datetime = '{str(max_date)}'  and country_id = {c_id} \
                                                                    and death_id is NULL\
                                                                    and cases_id is NULL\
                                                                    and vaccination_id is NULL\
                                                                    and test_id is NULL"
        cur.execute(q)
        conn.commit()
        flash(f"Deleted test data belonging to date({max_date}) and country({country_name})...")
        return redirect("/edit-vaccination")

    except dbapi.Error:
        print('This is error output', file=sys.stderr)
        #flash("error")
        #print(dbapi.Error)
        #return redirect("/edit-vaccination")

# death
def deaths_page():
    if not session.get('loggedin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    
    #pagination
    countryName = request.args.get("countryName")
    pageNumber =request.args.get("pageNumber") if request.args.get("pageNumber") is not None else "1"
    pageNumber = int(pageNumber)
    offset = (pageNumber-1)*50
    paginationValues = (pageNumber,pageNumber+1,pageNumber+2) if (pageNumber)>0 else (0,1,2)

    countries = None
    deaths = None
    isadmin = False
    headings = ("total_deaths", "new_deaths", "total_deaths_per_million", "new_deaths_per_million", "new_deaths_smoothed", "new_deaths_smoothed_per_million")
    try:
        isadmin = checkIsAdmin()
        curr = conn.cursor()
        
        countries = getCountries(curr)

        select = """SELECT covid19.datetime, country.name, total_deaths, new_deaths, total_deaths_per_million, new_deaths_per_million, new_deaths_smoothed, new_deaths_smoothed_per_million"""
        fr = f" FROM covid19 LEFT JOIN country ON covid19.country_id = country.id INNER JOIN death ON covid19.death_id = death.id"
        where = " "
        if countryName is not None:
            where = f" WHERE country.name = '{countryName}'"
        orderby = f" ORDER BY datetime desc OFFSET {offset} ROWS FETCH NEXT 50 ROWS ONLY"

        statement = select + fr + where + orderby
        print(statement)
        curr.execute(statement)
        result = curr.fetchall()
        deaths = np.zeros([1, 8], dtype='str')
        for row in result:
            newRow = np.array(row)
            deaths = np.vstack([deaths, newRow])

        deaths = np.delete(deaths, 0, 0)
        curr.close()
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()
        return render_template("deaths/deaths.html",headings=headings, isadmin=isadmin,  deaths=deaths, countries=countries, paginationValues=paginationValues)

def edit_deaths_page():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    
    #pagination
    countryName = request.args.get("countryName")
    pageNumber =request.args.get("pageNumber") if request.args.get("pageNumber") is not None else "1"
    pageNumber = int(pageNumber)
    offset = (pageNumber-1)*50
    paginationValues = (pageNumber,pageNumber+1,pageNumber+2) if (pageNumber)>0 else (0,1,2)
    countries = None

    deaths = None
    isadmin = False
    headings = ("total_deaths", "new_deaths", "total_deaths_per_million", "new_deaths_per_million", "new_deaths_smoothed", "new_deaths_smoothed_per_million")
    try:
        isadmin = checkIsAdmin()
        if isadmin == False:
            redirect('/access-denied')

        curr = conn.cursor()

        countries = getCountries(curr)
        select = """SELECT covid19.datetime, country.name, total_deaths, new_deaths, total_deaths_per_million, new_deaths_per_million, new_deaths_smoothed, new_deaths_smoothed_per_million"""
        fr = f" FROM covid19 LEFT JOIN country ON covid19.country_id = country.id INNER JOIN death ON covid19.death_id = death.id"
        where = " "
        if countryName is not None:
            where = f" WHERE country.name = '{countryName}'"
        orderby = f" ORDER BY datetime desc OFFSET {offset} ROWS FETCH NEXT 50 ROWS ONLY"
        statement = select + fr + where + orderby

        curr.execute(statement)
        result = curr.fetchall()
        deaths = np.zeros([1, 8], dtype='str')
        for row in result:
            newRow = np.array(row)
            deaths = np.vstack([deaths, newRow])

        deaths = np.delete(deaths, 0, 0)
        curr.close()
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()
        return render_template("deaths/edit-deaths.html",headings=headings, isadmin=isadmin,  deaths=deaths, countries=countries, paginationValues=paginationValues)


def add_death_data():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    headings = ("total_deaths", "new_deaths", "total_deaths_per_million", "new_deaths_per_million", "new_deaths_smoothed", "new_deaths_smoothed_per_million")
    try:
        cur = conn.cursor()
        countries = getCountries(cur)
        if request.method == "POST":
            country_name = request.form["country"]
            date_time = request.form["date"]
            total_deaths = request.form["total_deaths"]
            total_deaths_per_million = request.form["total_deaths_per_million"]
            new_deaths = request.form["new_deaths"] if request.form["new_deaths"] !="" else "NULL"
            new_deaths_per_million = request.form["new_deaths_per_million"] if request.form["new_deaths_per_million"] !="" else "NULL"
            new_deaths_smoothed = request.form["new_deaths_smoothed"] if request.form["new_deaths_smoothed"] !="" else "NULL"
            new_deaths_smoothed_per_million = request.form["new_deaths_smoothed_per_million"] if request.form["new_deaths_smoothed_per_million"] !="" else "NULL"
            
            country_id_fetched  = getCountryId(country_name, cur)

            if country_id_fetched is None:
                flash("Please enter a valid country")
                return render_template("deaths/add.html", headings=headings, countries=countries)
            
            (country_id,) = country_id_fetched

            format = "%Y-%m-%d"

            
            try:
                
                datetime.strptime(date_time, format)
            except ValueError:
                flash("Please enter a valid date in the format YYYY-MM-DD")
                return render_template("deaths/add.html", headings=headings,countries=countries)

            check_q = f"select id, death_id from covid19 where datetime = '{date_time}' and country_id = {country_id};"
            cur.execute(check_q)
            case_special = cur.fetchone()
            death_id = None
            id = None
            if case_special is not None:
                id,death_id = case_special
            
            if(case_special is not None and death_id is not None):
                flash("You can not add a new record into already existing record")
                return render_template("deaths/add.html", headings=headings,  countries=countries)

            if(total_deaths_per_million =="" and total_deaths ==""):
                flash("Please provide total_deaths_per_million, total_deaths fields")
                return render_template("deaths/add.html", headings=headings, countries=countries)

            q = f"INSERT INTO death (total_deaths, new_deaths, total_deaths_per_million, new_deaths_per_million, new_deaths_smoothed, new_deaths_smoothed_per_million, country_id)\
                  VALUES ({total_deaths}, {new_deaths}, {total_deaths_per_million}, {new_deaths_per_million}, {new_deaths_smoothed}, {new_deaths_smoothed_per_million}, {country_id}) RETURNING id;"
            
            
            cur.execute(q)
            death_created_id = cur.fetchone()[0]
            s=""
            
            if(id is None):
                s =  f"INSERT INTO covid19 (death_id, test_id, vaccination_id, cases_id, country_id,datetime)\
                  VALUES ({death_created_id}, NULL, NULL, NULL,{country_id},'{date_time}');" 
            else:
                s = f"UPDATE covid19 SET death_id={death_created_id} where id = {id};"   

            cur.execute(s) 
            cur.close()   
            conn.commit()
            flash("Successfully created")
            return render_template("deaths/add.html", headings=headings, countries=countries)
        else:
            return render_template("deaths/add.html", headings=headings, countries=countries)
    except dbapi.Error: 
        print(dbapi.Error)
        conn.rollback()
        return render_template("deaths/add.html", headings=headings, countries=countries)
    finally:        
        conn.close()

def update_last_death():
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        country_statement2 = "SELECT name FROM country"
        
        cur.execute(country_statement2)
        fetched_country =cur.fetchall()
        headings = ("total_deaths", "new_deaths", "total_deaths_per_million", "new_deaths_per_million", "new_deaths_smoothed", "new_deaths_smoothed_per_million")

        if request.method == "POST":
            country_name = request.form["country"]
            date_time = request.form["date"]
            total_deaths = request.form["total_deaths"]
            new_deaths = request.form["new_deaths"]
            total_deaths_per_million = request.form["total_deaths_per_million"]
            new_deaths_per_million = request.form["new_deaths_per_million"] 
            new_deaths_smoothed = request.form["new_deaths_smoothed"]
            new_deaths_smoothed_per_million = request.form["new_deaths_smoothed_per_million"]
            
            format = "%Y-%m-%d"

            
            try:
                
                datetime.strptime(date_time, format)
            except ValueError:
                flash("Please enter a valid date in the format YYYY-MM-DD")
                return render_template("deaths/update.html", headings=headings, fetched_country=fetched_country)

            q = f"select distinct on(covid19.datetime) covid19.id,death_id,datetime,country.name from covid19 LEFT JOIN country ON covid19.country_id = country.id  \
                where country.name='{country_name}' order by covid19.datetime DESC"
            
            cur.execute(q)
            last_id,last_death_id,last_date,country_name_last =cur.fetchone()

            if(date_time != str(last_date)):
                flash(f"You can only update last day ({last_date}) Death informations of relevant country ({country_name_last})")
                return render_template("deaths/update.html" ,headings=headings,fetched_country=fetched_country)
            if(last_death_id is None):
                flash(f"Death information could not find, please first add.")
                return render_template("deaths/update.html", headings=headings, fetched_country=fetched_country)

            q = " total_deaths='" + total_deaths + "' ," if total_deaths != "" else ""
            q = q + (" new_deaths='" + new_deaths + "' ," if new_deaths != "" else "")
            q = q + (" total_deaths_per_million='" + total_deaths_per_million + "' ," if total_deaths_per_million != "" else "")
            q = q + (" new_deaths_per_million='" + new_deaths_per_million + "' ," if new_deaths_per_million != "" else "")
            q = q + (" new_deaths_smoothed='" + new_deaths_smoothed + "' ," if new_deaths_smoothed != "" else "")
            q = q + (" new_deaths_smoothed_per_million='" + new_deaths_smoothed_per_million + "' ," if new_deaths_smoothed_per_million != "" else "")
            

            if q == "":
                flash("Couldn't updated")
                return redirect("/update-death")
            else:
                if q[len(q) - 1] == ",":
                    q = q[:-1]
                q = q + f" where id= {last_death_id}"
                q = "UPDATE death SET " + q
                
            cur.execute(q)            
            conn.commit()
            flash("Updated succesfully")
            return redirect("/update-death")
        else:
            return render_template("deaths/update.html", headings=headings,fetched_country=fetched_country)
    except dbapi.Error: 
        flash("error")
        print(dbapi.Error)
        return render_template("deaths/update.html", headings=headings,fetched_country=fetched_country)
    finally:
        cur.close()
        conn.commit()
        conn.close()

def delete_last_death(country_name):
    if not session.get('isadmin'):
        return redirect('/access-denied')
    conn = dbapi.connect(config.DSN)
    try:
        cur = conn.cursor()
        country_statement2 = f"SELECT id FROM country WHERE name='{country_name}';"
        cur.execute(country_statement2)
        fetched = cur.fetchone()
        (c_id,) = fetched
        if(c_id is None):
            flash("Could not find such an country")
            return redirect("/edit-death")

        q = f"SELECT max(datetime) FROM covid19 WHERE country_id = {c_id};"
        cur.execute(q)
        fetched = cur.fetchone()
        (max_date,)= fetched
        if(max_date is None):
            flash("Could not find such a data")
            return redirect("/edit-death")
        q = f"SELECT death_id FROM covid19 WHERE country_id = {c_id} and datetime='{str(max_date)}';"
        cur.execute(q)
        fetched = cur.fetchone()
        (death_id,)= fetched
        if(death_id is None):
           flash(str(max_date)+"--Could not find any death data at "+str(max_date)+". It has already been deleted.")
           return redirect("/edit-death")
        q = f"DELETE FROM death WHERE id = {death_id}"
        cur.execute(q)
        q = f"DELETE FROM covid19 WHERE datetime = '{str(max_date)}'  and country_id = {c_id} \
                                                                    and death_id is NULL\
                                                                    and cases_id is NULL\
                                                                    and vaccination_id is NULL\
                                                                    and test_id is NULL"
        cur.execute(q)

        cur.close()
        conn.commit()
        flash(f"Deleted death data belonging to date({max_date}) and country({country_name})...")
        return redirect("/edit-death")

    except dbapi.Error: 
        flash("error")
        print(dbapi.Error)
        return redirect("/edit-death")


# home page
def home_page():
    conn = dbapi.connect(config.DSN)
    totalTests = None
    totalDeaths = None
    totalCases = None
    totalVacs = None
    try:
        curr = conn.cursor()
        
        statement = "SELECT SUM(max) FROM (Select max(total_cases) \
                    from cases left join country on country.id =cases.country_id  \
                    group by country.name) AS S1"
                    
        curr.execute(statement)
        totalCases = float('.'.join(str(ele) for ele in curr.fetchone()))
        

        statement = "SELECT SUM(max) FROM (Select max(total_deaths) \
                    from death left join country on country.id =death.country_id  \
                    group by country.name) AS S1"
        curr.execute(statement)
        totalDeaths = float('.'.join(str(ele) for ele in curr.fetchone()))

        statement = "SELECT SUM(max) FROM (Select max(total_tests) \
                    from test left join country on country.id =test.country_id  \
                    group by country.name) AS S1"
        curr.execute(statement)
        totalTests = float('.'.join(str(ele) for ele in curr.fetchone()))

        statement = "SELECT SUM(max) FROM (Select max(total_vaccinations) \
                    from vaccination left join country on country.id =vaccination.country_id  \
                    group by country.name) AS S1"
        curr.execute(statement)
        totalVacs = float('.'.join(str(ele) for ele in curr.fetchone()))
        curr.close()
        conn.commit()
    except error:
        print(error)
        conn.rollback()
    finally:
        conn.close()
        return render_template("home.html",totalTests=totalTests ,totalVacs=totalVacs,totalCases=totalCases, totalDeaths=totalDeaths)

