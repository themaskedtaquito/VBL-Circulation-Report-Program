import csv
import re
import sqlite3

#List to store book objects
bookList = []
titleDict = {}

def getCSVreport ():
    sourceFile = input("Enter your circulation report's file name: ")
    return (sourceFile)


class Book:
    #Attributes align with the columns in the csv
    def __init__(self, itemno, title, author, isbn, callno, collections, transactions ):
        self.itemno = itemno
        self.title = title
        self.author = author
        self.isbn = isbn
        self.callno = callno
        self.collections = collections
        self.transactions = transactions
        
        
    #stringMatch functions can be updated with additional if statements in the future to account for other common variations
    
    def stringMatchTitle (self, a, b):
        #Want to control for which version is longest for regex matches
        stringA = max(a,b).lower()
        stringB = min(a,b).lower()
        
        #Books that have : A Novel appended
        
        if stringA.startswith(stringB) and stringA.endswith(': a novel'):
            return True
        
    
    def stringMatchAuthor (self, a, b):
        
        
        stringA = max(a,b).lower()
        stringB = min(a,b).lower()
        
        #regex for author initials
        match = re.search( '[a-z]*, [a-z]* [a-z].', stringA)
        if match and stringA.startswith(stringB):
            return True
        
        
        
#Determines if self and other are the same book
    def compare(self, other):
        
        #not every book has an isbn
        if self.isbn != '' and self.isbn == other.isbn:
            return True
        
        elif self.title.lower() == other.title.lower() and self.author.lower() == other.author.lower():
            return True
        
        #Same title, fuzzy author
        elif self.title.lower() == other.title.lower() and self.stringMatchAuthor(self.author, other.author) == True:
            return True
        
        #Fuzzy title, same author
        
        elif self.author.lower() == other.author.lower() and self.stringMatchTitle(self.title, other.title) == True:
            return True
        
        else:
            return False
    
    def diffChecker(self, other):
        #keeps track of all the different fields with discrepencies
        toFix = []
        
        if self.collections != other.collections:
            toFix.append('Collections')
        
        if self.callno != other.callno:
            toFix.append('Call number')
        
        if self.author != other.author:
            toFix.append('Author')
        
        if self.title != other.title:
            toFix.append('Title')
            
            
        if len(toFix) > 0:
            return toFix
        
        #Returns false if there are no differences
        else:
            return False
        

#creates a Book object for every book in the circulation report
def createBooks ():
    with open(sourceFile, newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            #Your Library collection is not relevant so we remove it here
            collectionList = row['Item Collections'].split(',')        
            if 'Your library' in collectionList:
                collectionList.remove('Your library')
                
            book = Book(row['Item #'], row['Item Title'], row['Item Author'], row['ISBN'], row['Item Call number'], collectionList, row['Number of Transactions'])
            bookList.append(book)


def appendToTitleDict(bookA, Title = None):
    
    #If the title is in the dictionary already, the new book is added underneath, otherwise a new key is created
    if Title == None:
        titleDict[bookA.title] = [bookA]
        
        
    else:
        titleDict[Title.title].append(bookA)
    
def searchDatabase(book, cur):
    
    #checks if the book is already known to have multiple copies before using the matching algorithm 
    
    cur.execute('''SELECT item_association FROM Books WHERE item_no = (?)''',(book.itemno,))
    try:
        fk=cur.fetchone()[0]
        cur.execute('''SELECT name FROM Data WHERE id = (?)''', (fk,))
        title = cur.fetchone()[0]
        appendToTitleDict(book, title)
        return True
    
    except:
        return False
            
    
#Compares all books within bookList and constructs a dictionary of titles and copies
def compareBooks ():
    
    #check to see if database has been built yet. This will be false the first time the program is run
    
    conn = sqlite3.connect('circulation.sqlite')
    cur = conn.cursor()
    try:
        cur.execute('''SELECT id FROM Data''')
        dbOnline = True
        
    except:
        dbOnline = False
    
    loopCount = 0
    
    for book in bookList:
        if loopCount > 0:
            for b in range(0,loopCount):        

                
                #if two books are the same, we can add it to the dictionary, then break the loop
                if dbOnline == True:
                    if searchDatabase(book, cur) == True:
                        break
                
                if book.compare(bookList[b]) == True:
                    appendToTitleDict(book, bookList[b])
                    break                
                
                #if no matches are found, a new key is created using the book's title
                elif b == loopCount-1:
                    appendToTitleDict(book)
                    
                    
        else:
           appendToTitleDict(book)
            
        loopCount+=1     
    conn.close()
    
    
#uses titleDict and diffChecker method to identify differences between copies of the same book and writes them to a text document

def writeTXT():
    
    outputFile = open('LibraryThing_reviewlist.txt', 'w')
    for title in titleDict:
        blist = titleDict[title]
        #only need to check differences if there are multiple copies
        if len(blist) >1:
            toFix = []
            #compares each copy to each other
            for x in range (0, len(blist)-1):
                tempToFix = blist[x].diffChecker(blist[x+1])
                
                if tempToFix != False:
                    
                    #consolidates the toFix lists from every copy
                    for field in tempToFix:
                        if field not in toFix:
                            toFix.append(field)
                    
                    outputString = "- " + title + " has inconsistencies in the fields: " + ', '.join(toFix) + '\n\n'

                    outputFile.write(outputString)
                    

#Code to get things into a csv file into format we want
def writeCSV():
    with open('temp.csv', 'w', newline='', encoding="utf-8") as file:
        
        #These are all the columns that will be in the new csv
        fieldnames = ['Item Title', 'Item Author', 'Item Collection', 'Total Transactions', 'No. of copies']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        
        #List of tuples to sort by transactions.(transactions, titleDict key) 
        sortList = []
        for (titles, blist) in titleDict.items(): 
            
            #Consolidates transactions for all copies together
            addedTransactions = 0    
            for copy in blist:
                addedTransactions += int(copy.transactions)
            
            #multiply transactions by -1 to sort by descending while keeping titles ascending
            sortList.append((addedTransactions*-1, titles))   
        
        sortList.sort()
        
        for title in sortList:
            
            blist = titleDict[title[1]]
            transactions = title[0]
            
            writer.writerow({'Item Title': blist[0].title, 'Item Author': blist[0].author, 'Item Collection': blist[0].collections,'Total Transactions': transactions*-1, 'No. of copies': len(blist)})

# Has print statements to help explain what happens at each step of the program when presentating to others
def DEMO ():
    
    #Book List construction
    print(bookList)
    input(">")
    
    #Looking at Book objects
    print(bookList[0].title)
    print(bookList[0].author)
    print(bookList[0].isbn)
    print(bookList[0].callno)
    print(bookList[0].transactions)
    input(">")
    
    #Title Dict construction
    print(titleDict)
    input(">")
    
    #Looking at the different copies
    for copy in titleDict["Parable of the Sower"]:
        print(copy.itemno)
        print("ISBN: ", copy.isbn)
        print(copy.title)
        print(copy.author)
        print("-")
    for copy in titleDict["The Vanishing Half: A Novel"]:
        print(copy.itemno)
        print("ISBN: ", copy.isbn)
        print(copy.title)
        print(copy.author)     
    input(">")
    
    #diffChecker output
    print(titleDict["Sister outsider : essays and speeches"][0].title)
    print(titleDict["Sister outsider : essays and speeches"][0].collections)
    print("-")
    print(titleDict["Sister outsider : essays and speeches"][1].title)
    print(titleDict["Sister outsider : essays and speeches"][1].collections)

sourceFile = getCSVreport()
#sourceFile = 'CirculationReport.csv'

createBooks()
compareBooks()
writeTXT()
writeCSV()
#Creating database for storing book data
conn = sqlite3.connect('circulation.sqlite')
conn.execute('''PRAGMA foreign_keys = ON''') #Turn on foreign keyss
cur = conn.cursor()

#Setting up database tables
#Reference columns from Data table to Books table
cur.executescript('''
DROP TABLE IF EXISTS Books;
DROP TABLE IF EXISTS Data;

CREATE TABLE Books (
    id   INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    item_association INTEGER,
    item_no    INTEGER,
	item_title   TEXT,
	item_author	  TEXT,
    isbn   TEXT
);
	
CREATE TABLE Data (
    id   INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    name   TEXT,
    author TEXT
)
''')

conn.commit()

#For loop to get all rows into columns from titleDict
#you need to query and pull the ID - hold it in a variable and 
#either append it to your blist  as foreign key OR append directly 
#in the Sql insert statement you are running as foreign key

for (titles, blist) in titleDict.items():
    
    #Only add to database if there are multiple copies
    if len(blist) > 1:
        cur.execute('''
                    INSERT INTO Data (name, author) VALUES (?, ?)''',
                    (blist[0].title, blist[0].author))
        
        #gets the most recently added row from DATA table id to use as foreign key
        cur.execute('''SELECT id FROM Data ORDER BY id DESC LIMIT 1''')
        fk=cur.fetchone()[0]
    
        
        for copy in blist:
            #foreign key should be the ID from Data table
            cur.execute('''INSERT INTO Books (item_no, item_association, item_title, item_author, isbn) VALUES (?, ?, ?, ?, ?)''',
            (copy.itemno, fk, copy.title, copy.author, copy.isbn))
    

#Save changes and close connection
conn.commit()
conn.close()

print("Reports successfully generated")
