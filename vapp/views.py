from flask import render_template, flash, redirect, session, url_for, request, g
from vapp import app, lm
from peewee import *
from models import Market, Seller, Number, SMS, List, ListRelationship, Outbox, User
from config import SPAM, KEYWORDS, SELLER_KEYWORDS, HELP_KEYWORDS, MARKETLISTS, POST_LOAD, GET_LOAD, STATUS, ROLE_USER, ROLE_ADMIN, PASSWORD
from flask.ext.login import LoginManager, login_user, logout_user, current_user, login_required
import requests
import sys, datetime, json, pprint, ast, math

# SPAM = [0, 180, 727272, 456, 24273, 40404]

# KEYWORDS = ['join', 'okuyunga', 'me', 'nze']

# SELLER_KEYWORDS = ['join', 'okuyunga', 'start', 'tandikawo', 'okutandikawo', 'kuvawo', 'leave', 'me', 'nze']

# HELP_KEYWORDS = ['join', 'okuyunga', 'start', 'tandikawo', 'okutandikawo', 'help', 'obuyambi', 'me', 'nze', 'who', 'ani', 'yongerako', 'add']

# MARKETLISTS = ['bugolobi market', 'monachello market', 'wind tunnel market']

# POST_LOAD = [{'user' : 'phone', 'pw' : 'Bug0l0b1'}]

#GET_LOAD = [{'user' : 'phone', 'pw' : 's3cr3t'}]

# STATUS = ['confirmed', 'processing', 'initiated']

# ROLE_USER = 0
# ROLE_ADMIN = 1

# PASSWORD = 'secret'


# simple utility function to create tables
def create_tables():
    Number.create_table(True)
    SMS.create_table(True)
    Seller.create_table(True)
    Market.create_table(True)
    List.create_table(True)
    ListRelationship.create_table(True)
    Outbox.create_table(True)
    User.create_table(True)
    
# create SMS message 
# returns in unicode
def create_SMS(read, body, id, date, address):
    bodyList = body.split()
    body = ' '.join(str(n) for n in bodyList) # strips extra whitespace
    read = unicode(str(read), 'utf_8')
    body = unicode(str(body).lower(), 'utf_8') # ensures all messages are in lower case
    id = unicode(str(id), 'utf_8')
    date = unicode(str(date), 'utf_8')
    address = unicode(str(address), 'utf_8')
    message = {u'read' : read, u'body' : body, u'_id': id, u'date': date, u'address': address}
    return message

# pass list of messages
# return messageDict   
def create_Message_Dict(messages):
    print >> sys.stderr, "within create_Message_Dict()"
    messageDict = {}
    messageString = str(messages)
    messageDict["messages"] = messageString
    messageDict["auth"] = str(GET_LOAD)
    # print messageDict
    return messageDict

# create list of ALL numbers from database
def create_Number_List():
    numberList = []
    for number in Number.select():
        numberList.append(number.number)
    return numberList

# get number from incoming SMS message
# return number as integer
def create_Number(message):
    try:
        number = int(message['address'])
        return number
    except ValueError, Argument:
        print >> sys.stderr, "The argument does not contain numbers\n", Argument

# pass number
# return validated number
def validate_Number(number):
    number = str(number)
    if (number[0] == '0') and (len(number) == 10):
        number = number[1:]
        number = '256' + number
        number = int(number)
    elif (number[0:3] == '256') and (len(number) == 12):
        number = int(number)
    elif (number[0] == '1') and (len(number) == 11):
        number = int(number)
    elif (len(number) == 10):
        number = '1' + number
        number = int(number)
    else:
        number = number + " Ennamba eno tesobodde kuterekebwa kubanga ebadde tewera. Wandiika ng'eno 256784820672 oba 0784820672" # incorrect number format
    return number


# pass number integer, store or find
# return Number.id
def store_Number(number):
    numberList = create_Number_List()
    if number not in numberList:
        newNumber = Number(number = number)
        newNumber.save()
        numberID = newNumber.id
        print 'new number saved!'
    else:
        oldNumber = Number.get(Number.number == number)
        numberID = oldNumber.id
        print 'number found!'
    return numberID

# pass number integer
# return Number object
def get_Number_Object(number):
    numberObject = Number.get(Number.number == number)
    return numberObject

# pass Market object
# return List object associated with that Market
def get_List_Object(market):
    listObject = List.get(List.market == market)
    return listObject
    
        
def cut_SMS(message):
    print >> sys.stderr, "within cut_SMS"
    texts = []
    count = 0
    x = 0
    current_text = []
    cutSMSList = message.split()
    lenList = len(cutSMSList)
    print 'LEN LIST: ' + str(lenList)
    indexList = lenList - 1
    print 'INDEX LIST: ' + str(indexList)
    if len(message) > 130:
        print >> sys.stderr, "message > 130"
        for word in cutSMSList:
            print word
            print 'INDEX OF WORD: ' + str(cutSMSList.index(word))
            if (count + len(word) < 130) and (x == indexList):
                current_text.append(word)
                print 'CURRENT TEXT LIST: ' + str(current_text)
                count += (len(word) + 1)
                print 'CURRENT COUNT: ' + str(count)
                texts.append(" ".join(current_text))
                print 'CURRENT TEXTS COMBINED LIST: ' + str(texts)
                x += 1
            elif (count + len(word) < 130) and (x < indexList):
                current_text.append(word)
                print 'CURRENT TEXT LIST: ' + str(current_text)
                count += (len(word) + 1)
                print 'CURRENT COUNT: ' + str(count)
                x += 1
            else:
                texts.append(" ".join(current_text))
                print 'CURRENT TEXTS COMBINED LIST: ' + str(texts)
                count = 0
                current_text = []
                current_text.append(word)
                print 'CURRENT TEXT LIST: ' + str(current_text)
                count += (len(word) + 1)
                print 'CURRENT COUNT: ' + str(count)
                x += 1
    else:
        print >> sys.stderr, "message < 130"
        texts.append(message)
        print texts
    return texts

# receive incoming SMS message and store
# return SMS object
def store_SMS(message):
    print >> sys.stderr, "within store SMS"
    number = create_Number(message) # gets number from incoming SMS
    numberID = store_Number(number) # creates and stores number as Number object
    newSMS = SMS(sms_id = message['_id'], body = message['body'].lower(), date = message['date'], number = numberID)
    newSMS.save()
    return newSMS

# create Market object
# update Number object to include correct Market foreign key
# returns Market object
def create_Market(name, nickname, neighborhood, city, number):
    newMarket = Market(name = name.lower(), nickname = nickname.lower(), neighborhood = neighborhood.lower(), city = city.lower())
    newMarket.save()
    update_query = Number.update(market=newMarket).where(Number.number == number)
    update_query.execute()
    return newMarket

# pass SMS object
# check to see if number associated with SMS object is already associated with a Seller
# if so, return warning
# if not, store new Seller object
# update Number object to include correct Seller foreign key
# create List Relationship, placing Seller's Number on its appropriate Market mailing list
# return Seller object or String
def store_Seller(newSMS):
    print >> sys.stderr, "within store seller"
    if check_Seller_Exists(newSMS.number):
        print >> sys.stderr, "within store seller if"
        statement = "Okimanyi nti e nnamba eno wagiwaandiisa dda ku lukalala?"
        # Do you know you've already registered this number for the mailing list?
        create_Outbox_Message(newSMS.number, statement)
    else:
        try:
            print >> sys.stderr, "within store seller else try"
            bodyList = split_Body(newSMS)
            if len(bodyList) > 3:
                print >> sys.stderr, "within store seller else if"
                newSeller = Seller(givenName = bodyList[1], familyName = bodyList[2], product = bodyList[3], market = 1)
                newSeller.save()
                update_query = Number.update(seller=newSeller).where(Number.number == newSMS.number.number)
                update_query.execute()
                numberObject = get_Number_Object(newSMS.number.number)
                listObject = get_List_Object(newSeller.market)
                newListRelationship = create_ListRelationship(listObject, numberObject, numberObject, numberObject)
                statement = newSeller
            else:
                print >> sys.stderr, "within store seller else else"
                statement = "Okutwegattako Goberera enkola eno 'okuyunga Erinnya Eppaatiike Erinnya Ery'ekika Byotunda'" #explanation of how to join
                create_Outbox_Message(newSMS.number, statement)
        except:
            print >> sys.stderr, "within except"
            print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
            print >> sys.stderr, str(sys.exc_info()[1])
            statement = 'An exception has Occurred'+ str(sys.exc_type) + '[' + str(sys.exc_value) + ']'
            return statement
    return statement

# pass Number Object
# check if Number exists AND Number is associated with foreign key Seller
# return True if Number is already associated with a Seller
def check_Seller_Exists(numberObject):
    print >> sys.stderr, "within check_Seller_Exists"
    for number in Number.select():
        if number == numberObject and number.seller:
            print 'a seller is already associated with the number of this incoming sms!'
            return True

# pass listName
# check if List exists
# return True if List already exists
def check_List_Exists(listName):
    for l in List.select():
        if listName == List.name:
            print 'this list exists!'
            return True

# get an already registered Seller based on a stored Number Object 
# return Seller object           
def get_Seller(numberObject):
    smsNumber = numberObject.number
    sellerNumber = Number.get(Number.number == smsNumber)
    seller = sellerNumber.seller
    return seller

# creates a list out of the SMS body
# returns list in unicode
def split_Body(newSMS):
    body = newSMS.body
    bodyList = body.split()
    return bodyList 

# pass Number object and message body
# return saved Outbox Message
def create_Outbox_Message(number, body): # parameters I could add to function, make a test case just with outbox just to focus on this problem
    # print >> sys.stderr, "within create outbox message"
    outboxMessage = Outbox(number=number.id, body=body)
    outboxMessage.save()
    return True

# pass a stored SMS object
# create a new mini List from information contained in stored SMS, or add numbers to a pre-existing mini List
# return confirmation statement
def create_Mini_Seller_List(newSMS):
    print >> sys.stderr, "inside create_Mini_Seller_List()"
    seller = get_Seller(newSMS.number)
    bodyList = split_Body(newSMS)
    bodyList.pop(0) # remove create keyword
    name = bodyList[0]
    bodyList.pop(0) # remove name so that it is just a list of numbers
    numberList = bodyList
    print numberList 
    if check_Mini_Sellers_ListName_Exists(seller, name):
        newList = get_Mini_Sellers_List(seller, name)
        message = "Olukalala luno olulina. Naye katukebere tulabe oba ng'a masimu ago gamu kw'ago agali ku lukalala olwo." 
        # You already have this list. But lets check to see if the numbers are already associated.
        print message
        create_Outbox_Message(newSMS.number, message)
    else:
        newList = List(name = name, seller = seller)
        newList.save()
        newListRelationship = create_ListRelationship(newList, newSMS.number, newSMS.number, newSMS.number)
        newListRelationship.save()
        message = 'Otandisewo olukalala olupya oluyitibwa ' + str(name)
        print message # You created a new list called
        create_Outbox_Message(newSMS.number, message)
    createdBy = newSMS.number
    statement = add_Numbers(newList, numberList, createdBy)
    return statement

# pass List Object, list of numbers, and Number Object
# return statement
def add_Numbers(listObject, numberList, createdBy):
    listOwner = listObject.seller
    ownerNumberObject = Number.get(Number.seller == listOwner)
    for number in numberList:
        number = validate_Number(number)
        if type(number) == str:
            print number
            statement = 'E nnamba yayingizi ddwamu bubi'
            # This number was entered incorrectly
            create_Outbox_Message(ownerNumberObject, statement)
        else:
            numberID = store_Number(number)
            numberObject = get_Number_Object(number)
            if check_ListRelationship_Exists(listObject, numberObject):
                statement = str(numberObject.number) + ' is already on your list!'
                create_Outbox_Message(ownerNumberObject, statement)
            else:
                newListRelationship = create_ListRelationship(listObject, numberObject, createdBy, createdBy)
                print newListRelationship
                identity = form_Identity(createdBy)
                statement = str(numberObject.number) + ' eyungiddwa ku lukalala lwo ' + str(identity)
                # this phone number was added to your list by
                create_Outbox_Message(ownerNumberObject, statement)
	    if numberObject.seller:
                memberStatement = str(identity) + " akuyunze kulukalala luno: " + str(listObject.name) + ". Okuddamu eri bonna, tandika obubaka bwo n'ekigambo '" + str(listObject.name) + "' oba '"+ str(listObject.name) + " owner'"
                # someone added you to the following list.
		create_Outbox_Message(numberObject, memberStatement)
	    else:
		nonmemberStatement = str(identity) + " akuyunze kulukalala luno: " + str(listObject.name) + ". Okulambika ebikwatako tandika obubaka bwo n'ekigambo Nze. (Okugeza: Nze erinnya ly'ekika erinnya epatiike)"
                # someone added you to the following list, to se your identity, start your message with ME. (i.e. ME familyName givenName)
                # removed memba ku Bugolobi Mailing List
                create_Outbox_Message(numberObject, nonmemberStatement)
    return statement

# pass Seller object and List name
# check to see if List exists with that name and associated Seller
# return True
def check_Mini_Sellers_ListName_Exists(seller, name):
    for l in List.select():
        if l.seller == seller and l.name == name:
            print 'seller already created this list!'
            return True

# pass Seller object and List name
# return List Object with that name and associated with that Seller
def get_Mini_Sellers_List(seller, name):
    l = List.get(List.name == name and List.seller == seller)
    return l

# pass List name
# return List Object with that name
def get_Mini_List(name):
    print >> sys.stderr, "get_Mini_List"
    l = List.get(List.name == name)
    return l

# pass List name
# return Seller object (owner of that List)
def get_Mini_List_Owner(listName):
    print >> sys.stderr, "within get_Mini_List_Owner"
    l = get_Mini_List(listName)
    listOwner = l.seller
    return listOwner


# pass Seller
# return list of names of mini Lists that Seller has created
def get_Mini_Sellers_ListNames(seller):
    sellersListNames = []
    for l in List.select().where(List.seller == seller):
        sellersListNames.append(l.name)
    return sellersListNames

# pass Number Object
# return list of names of mini Lists that Number has List Relationship with
def get_Mini_ListNames(number):
    print >> sys.stderr, "inside get_Mini_ListNames"
    listNames = []
    for l in ListRelationship.select().where(ListRelationship.number == number):
        listNames.append(l.listName.name)
    return listNames

# pass the name of a List a Seller has created
# returns list of Number objects of the numbers that Seller has included in their mini List
def get_Mini_Sellers_ListNumbers(sellersListName):
    sellersListNumbers = []
    sellersList = List.get(List.name == sellersListName)
    for listRelationship in ListRelationship.select().where(ListRelationship.listName == sellersList):
        sellersListNumbers.append(listRelationship.number)
    return sellersListNumbers

# pass List object and Number object
# check to see if List Relationship exists
# return True
def check_ListRelationship_Exists(listObject, numberObject):
    for lr in ListRelationship.select():
        if lr.listName == listObject and lr.number == numberObject:
            print 'this list relationship already exists and was created by ' + str(lr.createdBy)
            return True

# pass List Object and Number Object to which create the List Relationship, but also the Number Object that is responsible for the SMS sent to create the List Relationship
# check to see if List Relationship exists
# If so, return statement
# If not, return created List Relationship
def create_ListRelationship(listObject, numberObject, createdBy, modifiedBy):
    if check_ListRelationship_Exists(listObject, numberObject):
        statement = 'this list relationship already exists!'
    else:
        newListRelationship = ListRelationship(listName = listObject, number = numberObject, createdBy = createdBy.id, modifiedBy = modifiedBy.id)
        newListRelationship.save()
        statement = newListRelationship
    return statement

# pass Number Object
# create different SMS to promote depending on whether the Number is associated with a registered seller
# return identity of message sender
def form_Identity(numberObject):
    print >> sys.stderr, "inside form_Identity()"
    if check_Seller_Exists(numberObject):
        seller = get_Seller(numberObject)
        givenName = seller.givenName.title()
        familyName = seller.familyName.title()
        # market = seller.market.name.title()
        # identity = givenName + ' ' + familyName + ' okuva ' + market + ' agamba: '
        identity = givenName + ' ' + familyName
        # Kevin Gin from Bugolobi Market says:
        return identity
    else:
        identity = str(numberObject.number)
        # 14845575821 says:
        return identity

# pass SMS object and the intended Seller's mini or default market List
# function only promotes the SMS object to active Numbers
# returns String statement
def promote_SMS(newSMS, sellersListName):
    print >> sys.stderr, "inside promote_SMS"
    if newSMS.number.isActive == True:
        identity = form_Identity(newSMS.number) # creates identity based on whether the sender is a registered seller or not
        print >> sys.stderr, "inside promote_SMS, after form_Identity"
        print >> sys.stderr, sellersListName
        sellersListNumbers = get_Mini_Sellers_ListNumbers(sellersListName) # gets all the numbers on a mini list, but this does not include the owner/creator's number!!
        print >> sys.stderr, sellersListNumbers
        print >> sys.stderr, newSMS.body
        texts = []
        if not newSMS.body:
            message = identity + ' agamba: Omuntu omulala asobola okunnymbako okuweereza obubaka?' 
            # Can someone please help me send a message?
        else: 
            message = identity + ' agamba: ' + newSMS.body
            if len(message) > 160:
                texts = cut_SMS(message)
            else:
                texts.append(message)    
        sendersNumber = newSMS.number
        print >> sys.stderr, sendersNumber
        sellersListNumbers = remove_Senders_Number(sellersListName, sellersListNumbers, sendersNumber) # remove the senders number from the mini list
        # print >> sys.stderr, sellersListNumbers
        for number in sellersListNumbers:
            if number.isActive == True:
                for text in texts:
                    statement = str(text) + " sent to " + str(number)
                    create_Outbox_Message(number, text)
                    print >> sys.stderr, statement
            else:
                statement = "This seller is inactive and will not receive the message."
                print >> sys.stderr, statement
        statement = "Webale kusindika obubaka ku lukalala lwa ba " + str(sellersListName) 
        # Thank you for sending your message to the list of [blank]
        create_Outbox_Message(sendersNumber, statement)
        # print >> sys.stderr, statement
        statement = 'this sms was promoted to the ' + sellersListName + ' list'
    else:
        statement = "Obubaka bwo tebugenze kubanga enamba yo ebadde tekozesebwa. Bw'oba oyagala okuwadiisa enamba yo ddmu n'ekigambo 'okuyunga'"
        # Your message was not sent because your number is not active. If you would like to re-activate your number, reply with 'okuyunga'
        create_Outbox_Message(sendersNumber, statement)
    return statement

# pass sellersListName, sellersListNumbers, and sendersNumber
# returned edited sellersListNumbers with sendersNumber removed
def remove_Senders_Number(sellersListName, sellersListNumbers, sendersNumber):
    print >> sys.stderr, "within remove_Senders_Number"
    if sendersNumber in sellersListNumbers:
        sellersListNumbers.remove(sendersNumber)
        return sellersListNumbers
    else:
        return sellersListNumbers

# pass sellersListName, sellersListNumbers, and sendersNumber
# returned edited sellersListNumbers with owners Number added
def add_Owners_Number(sellersListName, sellersListNumbers):
    print >> sys.stderr, "within add_Owners_Number"
    # print >> sys.stderr, sellersListName
    if sellersListName in MARKETLISTS:
        return sellersListNumbers
    else:
        listOwner = get_Mini_List_Owner(sellersListName)
        ownerNumberObject = Number.get(Number.seller == listOwner)
        sellersListNumbers.append(ownerNumberObject)
        return sellersListNumbers

# notify active members of new Seller registered
# returns String statement   
def notify_Members(newSeller, sellersListName='bugolobi market'):
    print >> sys.stderr, "within notify members"
    givenName = newSeller.givenName.title()
    familyName = newSeller.familyName.title()
    market = newSeller.market.name.title()
    if newSeller.product:
        product = newSeller.product.title()
        message = 'Munnakibiina Oomupya yaakeewandiisa! ' + givenName + ' ' + familyName + ' ebitundibwa ' + product + ' mu ' + market
        # A new member just registered! Kevin Gin sells philsophy in Bugolobi Market. 
    else:
        message = 'Munnakibiina Oomupya yaakeewandiisa! ' + givenName + ' ' + familyName + ' is a customer of ' + market 
        # A new member just registered! Kevin Gin is a customer of Bugolobi Market.
    sellersListNumbers = get_Mini_Sellers_ListNumbers(sellersListName)
    for number in sellersListNumbers:
        print >> sys.stderr, "within notify members for"
        print >> sys.stderr, number
        if number.seller:
            print >> sys.stderr, "within notify if"
            if number.seller != newSeller and number.isActive == True:
                print >> sys.stderr, "within notify if if"
                statement = str(message) + " sent to " + str(number)
                create_Outbox_Message(number, message)
                print >> sys.stderr, statement
            elif number.seller == newSeller:
                print >> sys.stderr, "within notify if elif"
                statement = "Webale okutwegatako. Osobola kati okusindika obubaka ku lukalala lwa kataale e Bugolobi."
                # Thank you for joining. You are now able to send messages to the Bugolobi Market Mailing List.
                create_Outbox_Message(number, statement)
                print >> sys.stderr, statement
            else:
                print >> sys.stderr, "within notify if else"
                statement = "This seller is inactive and will not receive the notification."
                print >> sys.stderr, statement
        else:
            print >> sys.stderr, "within notify else"
            statement = "This number is not associated with a seller so they will not receive the notification."
            print >> sys.stderr, statement
    statement = 'members were notified of a new seller!'
    return statement

# pass newSMS object    
# change Numbers isActive status to False
def deactivate_Number(newSMS):
    numberObject = newSMS.number
    # print >> sys.stderr, numberObject
    update_query = Number.update(isActive = False).where(Number.number == numberObject.number)
    update_query.execute()
    update_query = Number.update(modifiedAt = datetime.datetime.now()).where(Number.number == numberObject.number)
    update_query.execute()
    statement = str(newSMS.number.number) + ': baakusazeeko tojja kwongera kufuna bubaka. Bwobeera oyagala okuddamu okukozesa obunnakibiina bwo, weereza- okuyunga eri 0784820672'
    # You have been deactivated and will no longer receive messages If you would like to re-activate your membership, please send okuyunga to 0784820672
    create_Outbox_Message(numberObject, statement)
    return statement

# pass newSMS object    
# change Numbers isActive status to True
def reactivate_Number(newSMS):
    numberObject = newSMS.number
    update_query = Number.update(isActive = True).where(Number.number == numberObject.number)
    update_query.execute()
    update_query = Number.update(modifiedAt = datetime.datetime.now()).where(Number.number == numberObject.number)
    update_query.execute()
    statement = str(newSMS.number.number) + ': Oyungidwa nate'
    # You have been re-activated!
    create_Outbox_Message(numberObject, statement)
    return statement

# pass Number object and listName as string  
# change ListRelationship isActive status to False
def deactivate_ListRelationship(numberObject, listName):
    listObject = get_Mini_List(listName)
    update_query = ListRelationship.update(isActive = False).where((ListRelationship.number == numberObject) and (ListRelationship.listName == listObject))
    update_query.execute()
    update_query = ListRelationship.update(modifiedAt = datetime.datetime.now()).where((ListRelationship.number == numberObject) and (ListRelationship.listName == listObject))
    update_query.execute()
    statement = str(number) + ' has been removed from ' + str(listName) + ' and will no longer receive messages.'
    create_Outbox_Message(numberObject, statement)
    return statement

# for all incoming SMS messages
def incoming_SMS(message):
    print >> sys.stderr, "within incoming_SMS"
    newSMS = store_SMS(message) # stores incoming SMS
    print >> sys.stderr, "within incoming_SMS, after store_SMS"
    statement = check_SMS(newSMS)
    return statement

def modify_Seller(newSMS, bodyList):
    print >> sys.stderr, "inside modify_Seller"
    if (check_Seller_Exists(newSMS.number)) and ((bodyList[0] == 'me') or (bodyList[0] == 'nze')):
        print >> sys.stderr, "within modify_Seller, seller exists + me"
        seller = get_Seller(newSMS.number)
        if len(bodyList) == 3:
            givenName = bodyList[1]
            familyName = bodyList[2]
            givenName_query = Seller.update(givenName = givenName).where(Seller.id == seller.id)
            givenName_query.execute()
            familyName_query = Seller.update(familyName = familyName).where(Seller.id == seller.id)
            familyName_query.execute()
            now_query = Seller.update(modifiedAt = datetime.datetime.now()).where(Seller.id == seller.id)
            now_query.execute()
            statement = 'Obubaka bwo bukyusidwamu: ' + str(givenName) + ' ' + str(familyName) # information updated
            create_Outbox_Message(newSMS.number, statement)
        elif bodyList[1].isdigit(): # new Number/Seller association from message sent by associated Number
            number = bodyList[1]
            number = validate_Number(number)
            if type(number) == int:
                numberID = store_Number(number)
                newNumber = get_Number_Object(number)
                oldNumber = newSMS.number
                statement = create_Seller_Number_Association(oldNumber, newNumber)
                create_Outbox_Message(newSMS.number, statement)
            else:
                statement = number
                create_Outbox_Message(newSMS.number, statement)
        else:
            givenName = bodyList[1]
            givenName_query = Seller.update(givenName = givenName).where(Seller.id == seller.id)
            givenName_query.execute()
            now_query = Seller.update(modifiedAt = datetime.datetime.now()).where(Seller.id == seller.id)
            now_query.execute()
            statement = 'Obubaka bwo bukyusidwamu: ' + str(givenName) + ' ' + str(seller.familyName)# information updated
            create_Outbox_Message(newSMS.number, statement)
        return statement
    else:
        print >> sys.stderr, "within incoming_SMS, seller does not exist, create!"
        if len(bodyList) == 3:
            givenName = bodyList[1]
            familyName = bodyList[2]
            newSeller = Seller(givenName = givenName, familyName = familyName)
            newSeller.save()
            update_query = Number.update(seller=newSeller).where(Number.number == newSMS.number.number)
            update_query.execute()
            statement = 'Obubaka bwo bukyusidwamu: ' + str(givenName) + ' ' + str(familyName)
            create_Outbox_Message(newSMS.number, statement)
        elif bodyList[1].isdigit(): # new Number/Seller association from message sent by unassociated Number
            number = bodyList[1]
            number = validate_Number(number)
            if type(number) == int:
                oldNumber = get_Number_Object(number)
                newNumber = newSMS.number
                statement = create_Seller_Number_Association(oldNumber, newNumber)
                create_Outbox_Message(newSMS.number, statement)
            else:
                statement = number
                create_Outbox_Message(newSMS.number, statement)
        else:
            givenName = bodyList[1]
            familyName = ''
            newSeller = Seller(givenName = givenName, familyName = familyName)
            newSeller.save()
            update_query = Number.update(seller=newSeller).where(Number.number == newSMS.number.number)
            update_query.execute()
            statement = 'Obubaka bwo bukyusidwamu: ' + str(givenName) + ' ' + str(familyName)
            create_Outbox_Message(newSMS.number, statement)
        return statement


# pass two Number objects
# return success statement
def create_Seller_Number_Association(oldNumber, newNumber):
    seller = oldNumber.seller
    update_query = Number.update(seller=seller).where(Number.number == newNumber.number)
    update_query.execute()
    newNumber = Number.get(Number.number == newNumber.number)
    statement = str(oldNumber.number) + ' : ' + str(oldNumber.seller) + ' // ' + str(newNumber.number) + ' : ' + str(newNumber.seller)
    return statement

# pass newSMS
# return statement 
def check_Seller_Keywords(newSMS, bodyList, seller, listNames):
    print >> sys.stderr, "inside check_Seller_Keywords"
    # listNames.remove('bugolobi market')
    if ((bodyList[0] == 'tandikawo') or (bodyList[0]=='okutandikawo')) or (bodyList[0] == 'start'): # create 
        print >> sys.stderr, "inside tandikawo"
        statement = create_Mini_Seller_List(newSMS)
    elif (bodyList[0] == 'okuyunga') or (bodyList[0] == 'join'): # join
        if newSMS.number.isActive == False:
            statement = reactivate_Number(newSMS)
        else:
            statement = "Okimanyi nti e nnamba eno wagiwaandiisa dda ku lukalala?" # do you know you've already registered?
            create_Outbox_Message(newSMS.number, statement)
    elif (bodyList[0] == 'kuvawo') or (bodyList[0] == 'leave'): # leave
        print >> sys.stderr, "inside elif kuvawo"
        statement = deactivate_Number(newSMS) # leave all lists
    elif (bodyList[0] == 'yongerako') or (bodyList[0] == 'add'):
        miniSellersListNames = get_Mini_Sellers_ListNames(seller)
        if (bodyList[1] in miniSellersListNames):
            listName = str(bodyList[1])
            bodyList.pop(0) # remove add keyword
            bodyList.pop(0) # remove list name
            numberList = bodyList # remove list name so that it is just a list of numbers
            l = get_Mini_List(listName)
            createdBy = newSMS.number
            statement = add_Numbers(l, numberList, createdBy)
        else:
            statement = "Twetonda, tolina lukalala luyitibwa " + str(bodyList[1]) + ". Okutandikawo olukalala, sindika obubaka ng'ogoberera emitendera gino: Tandikawo, erinnya lyo ozzeeko e namba oe  z'oyagala okuyunga ko."
            create_Outbox_Message(newSMS.number, statement)
	    # Sorry you dont have a list called listName. To start a list send a message following these steps- start your name and the number you want add.
    elif (bodyList[0] == 'me') or (bodyList[0] == 'nze'):
        print >> sys.stderr, 'within check_Seller_Keywords me'
        statement = modify_Seller(newSMS, bodyList)
    else:
        statement = "Twetonda obubaka bwo tetubutegedde. Tandikawo: tandikawo olukalala lwo mu bufunze \n Yongerako: gattako olukalala olulwo \n Kuvawo: leekawo lukalala lwonna"
        # Sorry, we didn't understand your message. tandikawo: start your own list \n Yongerako: add a number to your list \n Kuvawo: leave all mailing lists
        create_Outbox_Message(newSMS.number, statement)
    return statement

def check_Keywords(newSMS, bodyList, seller):
    if (bodyList[0] == 'okuyunga') or (bodyList[0] == 'join'):
        print >> sys.stderr, "seller not yet associated with a market"
        statement = create_Seller_Market_Association(newSMS, bodyList, seller)
    else:
        statement = "Sorry, we didn't understand your message. Yogerako ne Maama Zaina."
        create_Outbox_Message(newSMS.number, statement)
    return statement

def help_Function(newSMS, bodyList):
    if (bodyList[0] == 'help') or (bodyList[0] == 'obuyambi'):
        statement = "Olukalala lw'omu katale k'e Bugolobi lukosobozesa okusindikira abantu obubaka. Reply with one of these keywords: okuyunga, tandikawo, yongerako" #explanation of how to join
        # The Bugolobi Market Mailing List allows you to send messages to over 40 members, but you only need to pay for one message! Instructions on how to join, etc.
        create_Outbox_Message(newSMS.number, statement)
    elif ((bodyList[0] == 'tandikawo') or (bodyList[0]=='okutandikawo')) or (bodyList[0] == 'start'):
        statement = "Bwoba oli memba, osobola okutandikawo olukalala lwo: 'tandikawo listname number number number'"
        # If you are already a member, you can start your own private list: 'tandikawo listname number number number'
	create_Outbox_Message(newSMS.number, statement)
    elif (bodyList[0] == 'yongerako') or (bodyList[0] == 'add'):
        statement = "Bwoba oli memba ku lukalala luno osobola okugatako abantu abalala ku lukalala olwo (elinnya ly'olukalala yongerako ennamba yo)"
	# If you are a member of a private list, you can add other participants to that list: 'listname yongerako number'
        create_Outbox_Message(newSMS.number, statement)
    elif (bodyList[0] == 'okuyunga') or (bodyList[0] == 'join'):
        if newSMS.number.isActive == False:
            statement = reactivate_Number(newSMS)
        elif newSMS.number.seller and not newSMS.number.seller.market:
            statement = "Reply with 'Okuyunga marketName' to join a specific market list"
            create_Outbox_Message(newSMS.number, statement)
        else:
            statement = "Okutwegattako Goberera enkola eno 'okuyunga Erinnya Eppaatiike Erinnya Ery'ekika Byotunda'"
            create_Outbox_Message(newSMS.number, statement)
    elif (bodyList[0] == 'me') or (bodyList[0] == 'nze'):
        statement = "Ddamu ne 'nze erinnya epastiike erinnya ly'ekika' okutereza ebikwatako"
	# Reply with 'me givenName familyName' to update your personal information.
        create_Outbox_Message(newSMS.number, statement)
    elif (bodyList[0] == 'who') or (bodyList[0] == 'ani'):
        statement = "Damu ne 'erinnya lyolukalala' okulaba abali ku lukalala"
	# Reply with 'listname who' to see who is on a private list.
        create_Outbox_Message(newSMS.number, statement)
    else:
        statement = "Walyagadde okwegatta ku lukalala lwa kataale ke'Bugolobi? Yogerako ne Maama Zaina."
        # Would you like to join the Bugolobi Market Mailing List? Please talk to Maama Zaina.
        create_Outbox_Message(newSMS.number, statement)
    return statement

def query_ListRelationship(listname):
    print >> sys.stderr, "inside query_ListRelationship"
    l = get_Mini_List(listname)
    whoList = []
    whoStr = ''
    whoStr2 = ''
    for lr in ListRelationship.select():
        if lr.listName == l:
            if lr.number.seller:
                who = str(lr.number.seller.givenName) + " " + str(lr.number.seller.familyName)
                whoStr = whoStr + who + ', '
            else:
                who = str(lr.number.number)
                whoStr2 = whoStr2 + who + ', '
        else:
            print "list relationship doesn't match"
    whoWhole = whoStr + whoStr2
    return whoWhole

def create_Seller_Market_Association(newSMS, bodyList, seller):
    marketNickname = str(bodyList[1])
    marketList = create_Market_List()
    if marketNickname in marketList:
        marketObject = Market.get(Market.nickname == marketNickname)
        update_query = Seller.update(market = marketObject).where(Seller.id == seller.id)
        update_query.execute()
        listObject = List.get(List.id == marketObject.id)
        statement = create_ListRelationship(listObject, newSMS.number, newSMS.number, newSMS.number)
        message = 'You are now associated with ' + str(marketObject.name)
        create_Outbox_Message(newSMS.number, message)
        seller = get_Seller(newSMS.number)
        notify_Members(seller, marketObject.name)
    else:
        message = 'Sorry! ' + str(marketNickname) + " doesn't have a mailing list yet. Yogerako ne Maama Zaina."
        create_Outbox_Message(newSMS.number, message)
    return message

def create_Market_List():
    print >> sys.stderr, "inside create_Market_List"
    marketList = []
    for market in Market.select():
        marketList.append(market.nickname)
    return marketList



# first check to determine user goals
def check_SMS(newSMS):
    print >> sys.stderr, "inside check_SMS"
    bodyList = split_Body(newSMS)
    listNames = get_Mini_ListNames(newSMS.number) # pass Number object, get list of names of mini Lists that Number has List Relationship with
    print >> sys.stderr, listNames
    if not newSMS.body:
        if check_Seller_Exists(newSMS.number):
            seller = get_Seller(newSMS.number)
            statement = promote_SMS(newSMS, seller.market.name)
        else:
            statement = 'Obubaka tebutuuse kubuli omu! That message was blank. Please try resending.'
            create_Outbox_Message(newSMS.number, statement)
            return statement
    elif (bodyList[0] in listNames): # sender is any member of mini list EXCEPT the creator/owner of the mini list
        print >> sys.stderr, "inside bodyList in listNames"
        listName = str(bodyList[0])
        print >> sys.stderr, listName
        bodyList.pop(0) # remove list name
        if (bodyList[0] == 'yongerako') or (bodyList[0] == 'add'): # member of list trying to add new member to list
            print >> sys.stderr, 'within check_SMS add'
            bodyList.pop(0) # remove keyword so that it is just a list of numbers
            numberList = bodyList # list name and keyword removed so that it is just a list of numbers
            l = get_Mini_List(listName)
            createdBy = newSMS.number
            statement = add_Numbers(l, numberList, createdBy)
            return statement
        elif (bodyList[0] == 'who') or (bodyList[0] == 'ani'):
            print >> sys.stderr, 'within check_SMS who'
            whoStr = query_ListRelationship(listName)
            create_Outbox_Message(newSMS.number, str(whoStr))
            return whoStr
        elif (bodyList[0] == 'owner'):
            print >> sys.stderr, 'meant only to go to creator of mini list'
            body = ' '.join(str(n) for n in bodyList)
            identity = form_Identity(newSMS.number)
            message = identity + ' agamba: ' + body
            listOwner = get_Mini_List_Owner(listName)
            ownerNumberObject = Number.get(Number.seller == listOwner)
            create_Outbox_Message(ownerNumberObject, message)
            statement = "Obubaka bwo bugenze wa nanyinni kutandikawo lukalala luno yekka: " + str(listName)
            create_Outbox_Message(newSMS.number, statement)
            return message
        elif (len(bodyList) == 0) or (bodyList[0] =='help') or (bodyList[0] == 'obuyambi'):
            statement = "Obubaka tebutuuse kubuli omu! Tandika obubakabwo ne '" + listName + "' oba '" + listName + " owner' oba '" + listName + " ani' "
            # That message didn't go to anyone! Either begin your message with listName or listName owner or listName who
	    create_Outbox_Message(newSMS.number, statement)
            return statement
        else:
            print >> sys.stderr, 'default goes to everyone on the mini list'
            body = ' '.join(str(n) for n in bodyList)
            newSMS.body = body
            statement = promote_SMS(newSMS, listName)
            return statement
    elif (len(bodyList) == 1) and (bodyList[0] in HELP_KEYWORDS):
        print >> sys.stderr, "elif bodyList[0] in HELP_KEYWORDS"
        statement = help_Function(newSMS, bodyList)
        return statement
    elif (len(bodyList) > 1) and ((bodyList[0] == 'me') or (bodyList[0] == 'nze')):
        print >> sys.stderr, "inside check_SMS me"
        statement = modify_Seller(newSMS, bodyList)
        return statement
    elif (bodyList[0] == 'kuvawo') or (bodyList[0] == 'leave'):
        statement = deactivate_Number(newSMS) # leave all lists
        return statement
    elif check_Seller_Exists(newSMS.number):
        print >> sys.stderr, "inside check_SMS check_Seller_Exists"
        seller = get_Seller(newSMS.number)
        if seller.market:
            if bodyList[0] in SELLER_KEYWORDS:
                print >> sys.stderr, "elif bodyList[0] in KEYWORDS"
                statement = check_Seller_Keywords(newSMS, bodyList, seller, listNames)
                return statement
            else:
                print >> sys.stderr, "within check_Seller_Exists general promotion"
                statement = promote_SMS(newSMS, seller.market.name) # general promotion to the seller's market list
                return statement
        else:
            statement = check_Keywords(newSMS, bodyList, seller) 
            return statement
    elif (bodyList[0] == 'okuyunga') or (bodyList[0] == 'join'): # new seller trying to join
        print >> sys.stderr, "entering new okuyunga"
        newSeller = store_Seller(newSMS)
        if not type(newSeller) == str:
            statement = notify_Members(newSeller, newSeller.market.name)
            return statement
        else:
            statement = newSeller
            return statement
    elif newSMS.number.number in SPAM:
        statement = 'MTN keeps spamming the mailing list!'
        print >> sys.stderr, statement
        return statement
    else:
        statement = "Obubaka tebutuuse kubuli omu! Walyagadde okwegatta ku lukalala lwa kataale ke'Bugolobi or start your own list? Yogerako ne Maama Zaina."
        # Would you like to join the Bugolobi Market Mailing List? Please talk to Maama Zaina.
        create_Outbox_Message(newSMS.number, statement)
        return statement


@lm.user_loader
def load_user(id):
    return User.get(User.id == int(id))

@app.before_request
def before_request():
    g.user = current_user

@app.route('/')
def hello():
    return str(datetime.datetime.now())

@app.route('/login', methods = ['GET', 'POST'])
def login():
    print >> sys.stderr, "within login"
    print >> sys.stderr, request.args.get('messages')
    print >> sys.stderr, request.args.get('auth')
    if request.method == 'POST':
        print >> sys.stderr, "within POST"
        # print >> sys.stderr, s.auth
        try:
            print >> sys.stderr, "within try"
            if g.user is not None and g.user.is_authenticated():
                print >> sys.stderr, "g.user is not None and is_authenticated()"
                return redirect(url_for('sms_received'))
            auth = request.args.get('auth')
            print >> sys.stderr, auth
            print >> sys.stderr, type(auth)
            authList = ast.literal_eval(auth)
            print >> sys.stderr, type(authList)
            authDict = authList[0]
            print >> sys.stderr, authDict
            password = authDict['pw']
            username = authDict['user']
            user = User.get(User.username == username and User.password == password)
            print >> sys.stderr, user
            # user = User.get(User.username == s.auth[0] and User.password == s.auth[1])
            # print >> sys.stderr, user
            if user is not None:
                print >> sys.stderr, "user is not None"
                login_user(user, remember = True)
                return redirect(request.args.get('next') or url_for('sms_received'))
            else:
                # flash('Invalid login. Please try again.')
                print >> sys.stderr, "not authenticated!"
                return redirect(url_for('login'))
        except:
            print >> sys.stderr, "within except"
            print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
            print >> sys.stderr, str(sys.exc_info()[1])
            statement = 'An exception has Occured'+ str(sys.exc_type) + '[' + str(sys.exc_value) + ']'
            return statement
    else:
        print 'oops!'
        return "that wasn't a post!"
    return render_template("login.html")

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/index/<password>')
def index(password):
    print >> sys.stderr, "within index"
    try:
        if password == 'secret':
            print >> sys.stderr, "within try"
            sellerList = Seller.select()
            smsList = SMS.select()
            #numberList = Number.select()
            l = List.select()
            marketList = Market.select()
            #lrList = ListRelationship.select()
            #outboxList = Outbox.select()
            return render_template("index.html", title = 'TABLES', sellerList = sellerList, smsList = smsList, l = l, marketList = marketList)
        else:
            print >> sys.stderr, "wrong password"
    except:
        print >> sys.stderr, "within except"
        print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
        print >> sys.stderr, str(sys.exc_info()[1])
        statement = 'An exception has Occured'+ str(sys.exc_type) + '[' + str(sys.exc_value) + ']'
        return statement

@app.route('/sms_received/', methods=['POST', 'GET'])
def sms_received():
    if request.method == 'POST':
        print >> sys.stderr, "Received POST request to LOCAL marketMessages/sms_received/"
        try:
            print >> sys.stderr, "within try"
            auth = request.args.get('auth')
            print auth
            print type(auth)
            authList = ast.literal_eval(auth)
            print type(authList)
            authDict = authList[0]
            print authDict
            payloadDict = POST_LOAD[0]
            print payloadDict
            if (authDict['pw'] == payloadDict['pw']) and (authDict['user'] == payloadDict['user']):
                print >> sys.stderr, "within auth"
                messages = request.args.get('messages')
                print messages
                print type(messages)
                messageList = ast.literal_eval(messages)
                print messageList
                print type(messageList)
                for m in messageList:
                    incoming_SMS(m)
                    print >> sys.stderr, "within messageList for loop...it may be working"
                return messages
            else:
                statement = "not authenticated!"
                return statement
        except:
            print >> sys.stderr, "within except"
            print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
            print >> sys.stderr, str(sys.exc_info()[1])
            statement = 'An exception has Occured'+ str(sys.exc_type) + '[' + str(sys.exc_value) + ']'
            return statement
    else:
        print 'oops!'
        return 'nice try but that was a POST'
        
@app.route('/sms_to_send/', methods=['POST', 'GET'])
def sms_to_send():
    if request.method == 'GET':
        print >> sys.stderr, "Received GET request to LOCAL marketMessages/sms_to_send/"
        try:
            print >> sys.stderr, "within try"
            messageList = []
            for message in Outbox.select():
                if (message.sent == False) and len(messageList) < 8:
                    for x in range(0,20):
                        try: 
                            print >> sys.stderr, 'within sent=True try'
                            sent_query = Outbox.update(sent=True).where(Outbox.id == message.id)
                            sent_output = sent_query.execute()
                            print >> sys.stderr, 'i guess that worked'
                            break
                        except:
                            print >> sys.stderr, 'within sent=True except'
                            if x == 19:
                                print >> sys.stderr, 'sent=True WARNING!'
                            else:
                                print >> sys.stderr, 'that didnt work'
                    for x in range(0,20):
                        try:
                            print >> sys.stderr, 'within modifiedAt try'
                            modify_query = Outbox.update(modifiedAt=datetime.datetime.now()).where(Outbox.id == message.id)
                            modify_output = modify_query.execute()
                            print >> sys.stderr, 'i guess that worked'
                            break
                        except:
                            print >> sys.stderr, 'within modifiedAt except'
                            if x == 19:
                                print >> sys.stderr, 'modifiedAt WARNING!'
                            else:
                                print >> sys.stderr, 'that didnt work'
                    if (sent_output == 1) and (modify_output == 1):
                        print >> sys.stderr, 'within if sent_output and modify_output'
                        mlist = [message.number.number, message.body]
                        messageList.append(mlist)
                        print >> sys.stderr, messageList
                    else:
                        print >> sys.stderr, 'sent=False outbox messages not changed to True or updated modifiedAt time'
                        break
                else:
                    # print >> sys.stderr, 'message has already been sent'
                    statement = 'messageList full'
            if messageList:
                messageDict = create_Message_Dict(messageList)
            else:
                mStr = 'no new messages'
                messageList.append(mStr)
                messageDict = create_Message_Dict(messageList)
            print messageDict
            messageDict = json.dumps(messageDict)
            return messageDict
        except:
            print >> sys.stderr, "within except"
            print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
            print >> sys.stderr, str(sys.exc_info()[1])
            statement = 'An exception has Occurred'+ str(sys.exc_type) + '[' + str(sys.exc_value) + ']'
            return statement
    else:
        print 'oops!'
        return 'nice try but that was not a GET'
