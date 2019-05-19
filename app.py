from flask import Flask, render_template, flash
from flask import session as login_session
from flask import make_response
from flask import request, redirect, jsonify

app = Flask(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Category, Item, User, Base 

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests
import random, string
from pprint import pprint

engine = create_engine('sqlite:///ItemCatalog.db', connect_args={'check_same_thread': False})
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()
APPLICATION_NAME = "Item Catalog"
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']


#home
@app.route('/')
def Home(): 
    #session = DBSession()
    all_items = session.query(Item).all()
    all_cats = session.query(Category).all()
    all_users = session.query(User).all()
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template("GoogleSignInHTML.html", 
        STATE=state, CLIENT_ID=CLIENT_ID, cats=all_cats, users=all_users, items=all_items)



# @app.route('/ (logged)')
# def HomeLogged(): 
#     #session = DBSession()
#     all_items = session.query(Item).all()
#     all_cats = session.query(Category).all()

#     return render_template("Home (Logged).html", cats=all_cats, items=all_items)


@app.route('/gconnect', methods=['POST'])
def gconnect():

    # Validate state token
    
    
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return "response"
    # Obtain authorization code
    code = request.data


    try:
        # Upgrade the authorization code into a credentials object

        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)  
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 333   )
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    addUser(login_session)

    # See if a user exists, if it doesn't make a new one

    output = ''
    output += '<span style="font-size:20 margin:80px">Welcome, '
    output += login_session['username']
    output += '!</span>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 70px; height: 70px;border-radius: 35px;-webkit-border-radius: 35px;-moz-border-radius: 35px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect', methods=['POST'])
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    print url
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


def addUser(login_session):
    nameInput=login_session['username'] 
    emailInput=login_session['email']
    pictureInput=login_session['picture']
    #session = DBSession()
    userExists = session.query(User).filter(User.email== emailInput).scalar() is not None
    if(not userExists):
        newUser = User(email=emailInput, name=emailInput, picture=pictureInput)
        session.add(newUser)
        session.commit()
    users = session.query(User).all()
    for user in users:
        print(user.email)
    return Home()

def getUserID(userEmail):
    session = DBSession()
    user = session.query(User).filter(User.email==userEmail).one()
    return user.id

@app.route('/deleteUser/<string:userEmail>')
def deleteUser(userEmail): 
    session = DBSession()
    deleteUser = session.query(User).filter_by(email = userEmail).first()
    session.delete(deleteUser)
    session.commit()
    users = session.query(User).all()
    for user in users:
        print(user.email)
    return Home()

@app.route('/addItem/<string:Cat>/<string:itemName>/<string:userEmail>')
def addItem(Cat, itemName, userEmail):
    session = DBSession()
    newItem = Item(name=itemName, user_id=getUserID(userEmail), category_id=getCategoryID(Cat))
    #newItem = Item(name=itemName)
    session.add(newItem)
    session.commit()
    return Home()


@app.route('/deleteItem/<string:itemName>')
def deleteItem(itemName): 
    session = DBSession()
    deleteItem = session.query(Item).filter(Item.name==itemName).first()
    session.delete(deleteItem)
    session.commit()
    return Home()


def getCategoryID(catName):
    session = DBSession()
    cat = session.query(Category).filter(Category.name==catName).first()
    return cat.id


@app.route('/addCat/<string:Cat>')
def addCat(Cat):
    session = DBSession()
    #     userExists = session.query(User).filter(User.email== emailInput).scalar() is not None
    # if(not userExists):
    #     newUser = User(email=emailInput, name=name)
    #     session.add(newUser)
    #     session.commit()

    newCat = Category(name=Cat)
    session.add(newCat)
    session.commit()
    return Home()   
    

@app.route('/deleteCat/<string:catName>')
def deleteCat(catName): 
    session = DBSession()
    deleteCat = session.query(Category).filter(Category.name==catName).first()
    if deleteCat is not None:
        session.delete(deleteCat)  
        session.commit()
    return Home()

# @app.route('/editItem')
# def editItem():
#     session = DBSession()
#     all_cats = session.query(Category).all()
#     return render_template('EditItem.html', cats = all_cats)

@app.route('/item/<string:catName>/<string:itemName>')
def description(catName,itemName):
    session = DBSession()
    thisItem = session.query(Item).filter(Item.name==itemName and Item.category==catName).first()
    return render_template('Item.html', item=thisItem)


@app.route('/newItem', methods=['POST','GET'])
def newItem():
    #session = DBSession()
    all_cats = session.query(Category).all()
    if request.method == "POST":
        name = request.form['name']
        desc = request.form['description']
        cat = getCategoryID(request.form['category'])
        user = getUserID(login_session['email'])
        #user = 1
        newItem = Item(name=name, description=desc, category_id=cat, user_id=user)
        session.add(newItem)
        session.commit()
        return Home()

    else:
        return render_template('NewItem.html', cats = all_cats)

@app.route('/editItem/<string:catName>/<string:itemName>', methods=['POST','GET'])
def editItem(catName, itemName):
    session = DBSession()
    all_cats = session.query(Category).all()
    if request.method == "POST":        
        thisItem = session.query(Item).filter(Item.name==itemName and Item.category==catName).first()
        thisItem.name = request.form['name']
        thisItem.description = request.form['description']
        thisItem.category_id = getCategoryID(request.form['category'])
        session.commit()
        return Home()
    else:
        thisItem = session.query(Item).filter(Item.name==itemName and Item.category.name==catName).first()
        return render_template('EditItem.html', item = thisItem, cats=all_cats)



if __name__ == '__main__':
    app.secret_key = 'FJH9WUWUG0oAyZNAmkpJGsgt'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)