from flask import render_template, flash, redirect
from vapp import app
from peewee import *
from models import Market, Seller, Number, SMS, List, ListRelationship, Outbox
from config import PASSWORD, PAYLOAD, MARKETLISTS, KEYWORDS, SPAM
import requests
from flask import request
import sys, datetime, json, pprint, ast

# simple utility function to create tables
def create_tables():
    Number.create_table(True)
    SMS.create_table(True)
    Seller.create_table(True)
    Market.create_table(True)
    List.create_table(True)
    ListRelationship.create_table(True)
    Outbox.create_table(True)
    
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
    messageDict = {}
    messageString = str(messages)
    messageDict["messages"] = messageString
    messageDict["auth"] = str(PAYLOAD)
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
    number = int(message['address'])
    return number

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
        number = number + ' Ennamba eno tesobodde kuterekebwa kubanga ebadde tewera. Wandiika nga bino 256784820672 oba 0784820672' # incorrect number format
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
    if check_Seller_Exists(newSMS):
        print >> sys.stderr, "within store seller if"
        statement = "Okimanyi nti e nnamba eno wagiwaandiisa dda ku lukalala?"
        # Do you know you've already registered this number for the mailing list?
        create_Outbox_Message(newSMS.number, statement)
    else:
        try:
            print >> sys.stderr, "within store seller else try"
            bodyList = split_Body(newSMS)
            if len(bodyList) > 4:
                print >> sys.stderr, "within store seller else if"
                newSeller = Seller(givenName = bodyList[1], familyName = bodyList[2], product = bodyList[3], kind = bodyList[4], market = 1)
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

# pass SMS object
# check if Number exists AND Number is associated with foreign key Seller
# return True if Number is already associated with a Seller
def check_Seller_Exists(newSMS):
    for number in Number.select():
        if number == newSMS.number and number.seller:
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

# get an already registered Seller based on a stored SMS message 
# return Seller object           
def get_Seller(newSMS):
    smsNumber = newSMS.number.number
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
    seller = get_Seller(newSMS)
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
        message = 'Otandisewo olukalala olupya ayitibwa ' + str(name)
        print message # You created a new list called
        create_Outbox_Message(newSMS.number, message)
    createdBy = newSMS.number
    statement = add_Numbers(newList, numberList, createdBy)
    return statement

# pass List object and list of numbers
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
        else:
            numberID = store_Number(number)
            numberObject = get_Number_Object(number)
            if check_ListRelationship_Exists(listObject, numberObject):
                statement = str(numberObject.number) + ' is already on your list!'
                create_Outbox_Message(ownerNumberObject, statement)
            else:
                newListRelationship = create_ListRelationship(listObject, numberObject, createdBy, createdBy)
                print newListRelationship
                statement = str(numberObject.number) + ' was added to your list!'
                create_Outbox_Message(ownerNumberObject, statement)
                memberStatement = "You've been added to the following list: " + str(listObject.name) + ". To reply, start your message with '" + str(listObject.name) + "'. To reply all, start your message with '" + str(listObject.name) + " all'"
                create_Outbox_Message(numberObject, memberStatement)
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
    l = List.get(List.name == name)
    return l
    
# pass Seller Object and List name
# return Seller object (owner of that List)
def get_Mini_List_Owner(name):
    l = get_Mini_List(name)
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

# pass SMS object
# create different SMS to promote depending on whether the SMS is associated with a registered seller
# return identity of message sender
def form_SMS_To_Promote(newSMS):
    if check_Seller_Exists(newSMS):
        seller = get_Seller(newSMS)
        givenName = seller.givenName.title()
        familyName = seller.familyName.title()
        market = seller.market.name.title()
        identity = givenName + ' ' + familyName + ' okuva ' + market + ' agamba: '
        # Kevin Gin from Bugolobi Market says:
    else:
        identity = str(newSMS.number) + ' agamba: '
        # 14845575821 says:
    return identity
        
# pass SMS object and the intended Seller's mini or default market List
# function only promotes the SMS object to active Numbers
# returns String statement
def promote_SMS(newSMS, sellersListName, fromOwner):
    identity = form_SMS_To_Promote(newSMS) # creates identity based on whether the sender is a registered seller or not
    sellersListNumbers = get_Mini_Sellers_ListNumbers(sellersListName) # gets all the numbers on a mini list, but this does not include the owner/creator's number!!
    # print >> sys.stderr, sellersListNumbers
    if fromOwner == False: # if the message is not from the owner/creator of the mini list, then add the owner's number to the mini list's list of numbers
        sellersListNumbers = add_Owners_Number(sellersListName, sellersListNumbers)
        # print >> sys.stderr, sellersListNumbers
    else:
        sellersListNumbers = sellersListNumbers
    if not newSMS.body:
        message = identity + 'Omuntu omulala asobola okunnymbako okuweereza obubaka?' 
        # Can someone please help me send a message?
        # print >> sys.stderr, 'this message is empty!'
    else: 
        message = identity + newSMS.body
        # print >> sys.stderr, 'this message is full!'
    sendersNumber = newSMS.number
    print >> sys.stderr, sendersNumber
    sellersListNumbers = remove_Senders_Number(sellersListName, sellersListNumbers, sendersNumber) # remove the senders number from the mini list
    # print >> sys.stderr, sellersListNumbers
    for number in sellersListNumbers:
        if number.isActive == True:
            statement = str(message) + " sent to " + str(number)
            create_Outbox_Message(number, message)
            # print >> sys.stderr, statement
        else:
            statement = "This seller is inactive and will not receive the message."
            print >> sys.stderr, statement
    statement = "Webale kusindika obubaka ku lukalala lwa ba " + str(sellersListName) 
    # Thank you for sending your message to the list of [blank]
    create_Outbox_Message(sendersNumber, statement)
    # print >> sys.stderr, statement
    statement = 'this sms was promoted to the ' + sellersListName + ' list'
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
    product = newSeller.product.title()
    message = 'Munnakibiina Oomupya yaakeewandiisa! ' + givenName + ' ' + familyName + ' ebitundibwa ' + product + ' mu ' + market 
    # A new member just registered! Kevin Gin sells philsophy in Bugolobi Market.
    sellersListNumbers = get_Mini_Sellers_ListNumbers(sellersListName)
    for number in sellersListNumbers:
        print >> sys.stderr, "within notify members for"
        # print >> sys.stderr, number
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
    
# change Sellers isActive status to False
def deactivate_Seller(newSMS):
    smsNumber = newSMS.number.number
    sellerNumber = Number.get(Number.number == smsNumber)
    seller = sellerNumber.seller
    update_query = Number.update(isActive = False).where(Number.seller == seller)
    update_query.execute()
    update_query = Number.update(modifiedAt = datetime.datetime.now()).where(Number.seller == seller)
    update_query.execute()
    statement = str(seller) + ': baakusazeeko tojja kwongera kufuna bubaka.'
    # You have been deactivated and will no longer receive messages
    create_Outbox_Message(newSMS.number, statement)
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
    statement = str(newSMS.number.number) + ': You have been reactivated!'
    # You have been deactivated and will no longer receive messages
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
    statement = check_SMS(newSMS) # checks SMS for keywords, and then promotes, saves new Seller objects, notifies existing members, creates mini-lists, etc. accordingly
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
def check_Keywords(newSMS, miniSellersListNames):
    print >> sys.stderr, "inside check_KEYWORDS"
    bodyList = split_Body(newSMS)
    seller = get_Seller(newSMS)
    if (bodyList[0] == 'okuyiya') or (bodyList[0] == 'create'): # create 
        statement = create_Mini_Seller_List(newSMS)
    elif (bodyList[0] == 'okuyunga') or (bodyList[0] == 'join'): # join
        if newSMS.number.isActive == False:
            statement = reactivate_Number(newSMS)
        else:
            statement = "Okimanyi nti e nnamba eno wagiwaandiisa dda ku lukalala?" # do you know you've already registered?
            create_Outbox_Message(newSMS.number, statement)
    elif (bodyList[0] == 'help') or (bodyList[0] == 'obuyambi'):
        message = 'Okuyiya: tandikawo olukalala olulwo \n Okugata: gattako olukalala olulwo \n Kuvawo: leekawo lukalala lwonna'
        create_Outbox_Message(newSMS.number, message)
    elif bodyList[0].isdigit(): # new number / seller association sent from seller's associated number
        number = bodyList[0]
        number = validate_Number(number)
        if type(number) == int:
            numberID = store_Number(number)
            newNumber = get_Number_Object(number)
            oldNumber = newSMS.number
            statement = create_Seller_Number_Association(oldNumber, newNumber)
        else:
            statement = number
    elif (bodyList[0] == 'kuvawo') or (bodyList[0] == 'leave'): # leave
        print >> sys.stderr, "inside elif kuvawo"
        statement = deactivate_Number(newSMS) # leave all lists
    elif (bodyList[0] == 'okugata') or (bodyList[0] == 'add'):
        if (bodyList[1] in miniSellersListNames):
            listName = str(bodyList[1])
            bodyList.pop(0) # remove add keyword
            bodyList.pop(0) # remove list name
            numberList = bodyList # remove list name so that it is just a list of numbers
            l = get_Mini_List(listName)
            createdBy = newSMS.number
            statement = add_Numbers(l, numberList, createdBy)
        else:
            message = "Sorry, you don't have a list called " + str(bodyList[1]) + ". To create a list, send a message using the following format: Okuyiya listname number number number"
            create_Outbox_Message(newSMS.number, message)
    else:
        message = "Sorry, we didn't understand your message. Okuyiya: tandikawo olukalala olulwo \n Okugata: gattako olukalala olulwo \n Kuvawo: leekawo lukalala lwonna"
        # Sorry, we didn't understand your message. Okuyiya: create your own list \n Okugata: add a number to your list \n Kuvawo: leave all mailing lists
        create_Outbox_Message(newSMS.number, message)
    return statement

# first check to determine user goals
def check_SMS(newSMS):
    print >> sys.stderr, "inside check_SMS"
    bodyList = split_Body(newSMS)
    listNames = get_Mini_ListNames(newSMS.number)
    # print >> sys.stderr, listNames
    if (bodyList[0] in listNames): # sender is any member of mini list EXCEPT the creator/owner of the mini list
        print >> sys.stderr, "inside bodyList listNames"
        listName = str(bodyList[0])
        # print >> sys.stderr, listName
        bodyList.pop(0)
        if (bodyList[0] == 'all'): # message meant to go to everyone on the list
            print >> sys.stderr, 'within all'
            bodyList.pop(0)
            body = ' '.join(str(n) for n in bodyList)
            # print >> sys.stderr, body
            newSMS.body = body
            statement = promote_SMS(newSMS, listName, False)
            return statement
        elif (bodyList[0] == 'okugata') or (bodyList[0] == 'add'): # member of list trying to add new member to list
            print >> sys.stderr, 'within check_SMS add'
            bodyList.pop(0)
            numberList = bodyList # list name and keyword removed so that it is just a list of numbers
            l = get_Mini_List(listName)
            createdBy = newSMS.number
            statement = add_Numbers(l, numberList, createdBy)
        else: # message meant to only go to the creator/owner of the list
            print >> sys.stderr, 'meant only to send to owner of list'
            body = ' '.join(str(n) for n in bodyList)
            identity = form_SMS_To_Promote(newSMS)
            message = identity + body
            listOwner = get_Mini_List_Owner(listName)
            ownerNumberObject = Number.get(Number.seller == listOwner)
            create_Outbox_Message(ownerNumberObject, message)
            statement = "Your message was delivered only to the creator of the " + str(listName) + " list"
            # Thank you for sending your message to the list of [blank]
            create_Outbox_Message(newSMS.number, statement)
            return message
    elif check_Seller_Exists(newSMS):
        seller = get_Seller(newSMS)
        miniSellersListNames = get_Mini_Sellers_ListNames(seller)
        # print >> sys.stderr, miniSellersListNames
        if not bodyList: # blank message sent
            statement = promote_SMS(newSMS, seller.market.name, False)
        elif bodyList[0] in miniSellersListNames: # message sent by the creator/owner of the mini list and meant to go to all members
            print >> sys.stderr, 'bodyList[0] in miniSellersListNames'
            miniSellersListName = str(bodyList[0])
            bodyList.pop(0)
            body = ' '.join(str(n) for n in bodyList)
            newSMS.body = body
            statement = promote_SMS(newSMS, miniSellersListName, True)
        elif bodyList[0] in KEYWORDS:
            print >> sys.stderr, "elif bodyList[0] in KEYWORDS"
            statement = check_Keywords(newSMS, miniSellersListNames)
        else:
            print >> sys.stderr, "within check_Seller_Exists general promotion"
            statement = promote_SMS(newSMS, seller.market.name, False) # general promotion to the seller's market list
    elif (bodyList[0] == 'okuyunga') or (bodyList[0] == 'join'): # new seller trying to join
        print >> sys.stderr, "entering new okuyunga"
        newSeller = store_Seller(newSMS)
        if not type(newSeller) == str:
            statement = notify_Members(newSeller, newSeller.market.name)
        else:
            statement = newSeller
    elif (bodyList[0] == 'help') or (bodyList[0] == 'obuyambi'):
        statement = "Olukalala lw'omu katale k'e Bugolobi lukosobozesa okusindikira abantu obubaka. Osasulira obubaka bwa muntu omu bwokka 'okuyunga Erinnya Eppaatiike Erinnya Ery'ekika Byotunda'" #explanation of how to join
        # The Bugolobi Market Mailing List allows you to send messages to over 40 members, but you only need to pay for one message! Instructions on how to join, etc.
        create_Outbox_Message(newSMS.number, statement)
    elif (bodyList[0] == 'kuvawo') or (bodyList[0] == 'leave'):
        statement = deactivate_Number(newSMS) # leave all lists
    elif bodyList[0].isdigit(): # new Number/Seller association from message sent by unassociated Number
        number = bodyList[0]
        number = validate_Number(number)
        if type(number) == int:
            oldNumber = get_Number_Object(number)
            newNumber = newSMS.number
            statement = create_Seller_Number_Association(oldNumber, newNumber)
        else:
            statement = number
    elif newSMS.number.number in SPAM:
        statement = 'MTN keeps spamming the mailing list!'
    else:
        statement = "Walyagadde okwegatta ku lukalala lwa kataale ke'Bugolobi? Yogerako ne Maama Zaina."
        # Would you like to join the Bugolobi Market Mailing List? Please talk to Maama Zaina.
        create_Outbox_Message(newSMS.number, statement)
    return statement



@app.route('/')
def hello():
    return str(datetime.datetime.now())
    
@app.route('/index/<password>')
def index(password):
    print >> sys.stderr, "within index"
    try:
        if password == PASSWORD:
            print >> sys.stderr, "within try"
            sellerList = Seller.select()
            smsList = SMS.select()
            numberList = Number.select()
            l = List.select()
            marketList = Market.select()
            lrList = ListRelationship.select()
            outboxList = Outbox.select()
            return render_template("index.html", title = 'TABLES', sellerList = sellerList, smsList = smsList, l = l, marketList = marketList)
            #return 'hello world'
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
        print >> sys.stderr, "Received POST request to /sms_received/"
        try:
            print >> sys.stderr, "within try"
            auth = request.args.get('auth')
            print auth
            print type(auth)
            authList = ast.literal_eval(auth)
            print type(authList)
            authDict = authList[0]
            print authDict
            payloadDict = PAYLOAD[0]
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
        print >> sys.stderr, "Received GET request to /sms_to_send/"
        try:
            print >> sys.stderr, "within try"
            messageList = []
            for message in Outbox.select():
                if message.sent == False:
                    mlist = [message.number.number, message.body]
                    messageList.append(mlist)
                else:
                    statement = 'message has already been sent'
            if messageList:
                messageDict = create_Message_Dict(messageList) 
                # print messageDict
                # print type(messageDict)
                messageDict = json.dumps(messageDict)
                for message in Outbox.select():
                    update_query = Outbox.update(sent=True)
                    update_query.execute()
                return messageDict
            else:
                statement = 'empty message list'
            return statement
        except:
            print >> sys.stderr, "within except"
            print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
            print >> sys.stderr, str(sys.exc_info()[1])
            statement = 'An exception has Occurred'+ str(sys.exc_type) + '[' + str(sys.exc_value) + ']'
            return statement
    else:
        print 'oops!'
        return 'nice try but that was not a GET'
