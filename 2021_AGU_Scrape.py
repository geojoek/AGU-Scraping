# Python script to scrape AGU 2021 presenter list
# Joe Kopera, Dept. of Geosciences, U-Mass Amherst
# December 2021

# This script uses the selenium library since AGU's website is dynamically generated using Javascript
# This script has some dependencies, as listed below, but also has an external dependency in needing either
# Firefox or Chrome, and the proper webdriver for them, as this script controls your web browser
# In this script I amm using FireFox and the gecko webriver for it.
# There are many tutorials for installing Selenium's Python bindings that you can find, but a good one is at
# https://www.geeksforgeeks.org/selenium-python-introduction-and-installation/

# %%
# ----- Load libraries -----

import csv
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException # turns out we're not using this but may use this in future iterations of this script.
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# %%
#  ----- PARAMETERS -----

deptListFile = r"" # CSV file with following header fields: fullName,firstName,firstInitial,lastName
outputScheduleHTML = r""
geckoPath = r""
ignored_exceptions=(StaleElementReferenceException) # This is good practice for ignoring stale references in Selenium but I honestly don't know if it's really necessary here.
timezone = "EST" # for use in writing out HTML. This is your local timezone of the computer you're running this script from. The confex site interacts with this script in such a way where it only displays events in your local time, not the timezone of the conference.
# ... therefore, the output of this script will only show event time in your local timezone. You can fix this with a fancy datetime function at the end if you want.

# NOTE: not paramaterizing here because it feels too complicated to do so but boolean logic for which institution your authors are at is in the if statement on line 123 or thereabouts.
# This willl likely be different for each institution, and you might have to write some very complicated logic if your authors have differing affiliations from one another or
# like in our case, there are multiple spellings and abbreviations for your instituion.

# NOTE: Be sure to check your CSV for errors. If it is missing a column for one person, you may get a NoneType error thrown on line 83.  If the name is spelt wrong, no talks may appear for that person.

print("libraries loaded")

# %%
# Initialize selenium and headless browser

options = Options()
options.headless = True # run Firefox headless so it does not load up its GUI
options.add_argument("--window-size=1920,1200")

profile = webdriver.FirefoxProfile()
driver = webdriver.Firefox(options=options, executable_path=geckoPath) # set path to the gecko driver that drives Firefox. Gecko can be downloaded from https://github.com/mozilla/geckodriver
print("Loaded gecko driver for headless Firefox browser")

# %%
# Load dept. members CSV and create either list or dictionary based off it

# The following section reads a CSV file of all people in the department and parses that into a dictionary that can be iterated through.
# The CSV file I use has a specific structure: fullName, firstName, firstInitial, lastName as column headers and that's what the following block of code parses. The first line is fieldnames.

with open(deptListFile) as inputFile:
    reader = csv.DictReader(inputFile) # parses csv file into lsit of dictionaries. One dictionary per line
    deptPeopleList = list(reader) # because running loops against above dictionary is a file i/o operaton, creating list of dictionaries out of the above
    # this creates list wherein each list item is a dictionary where the key/value pairs are the column headers:value of the above dictionary / CSV file.
    print("CSV file read into Python dictionary")

print("\nChecking CSV file for errors....")

# This block of code very crudely checks for errors in the CSV file and aborts script if it finds any
n = 1 # Can't start at 0 since 1st line of file is column names
errorFlag = False
for person in deptPeopleList:
    n = n + 1
    for key,value in person.items():
        if value == None or value == "":
            errorFlag = True
            print("Error on line {} of CSV".format(n))
        else:
            pass
if errorFlag:
    print("\n-----* !!! Aborting script. Please fix errors in CSV file.")
    import sys
    sys.exit()
else:
    print("\nNo errors found. :-D")


# %%
# Iterate though dept. members dictionary and plug into into AGU Search URL to use requests library retrieve page consisting of names that match

print("\n\n ----- Iterating through list of people in {} and seeing if they have a profile in the AGU database... -----\n\n".format(deptListFile))

# Creates list object to place dept members in who are authors on an AGU abstract or are conveners of a session, etc....
# Each list item will be a dictionary in which to dump all the info. that comes of for them on the AGU confex website. These dictionaries will,
# in turn, have nested dictionaries for each talk.

# This is needed because using deptPeopleList as a master list of dictionaries ends up skipping department members who may be listed multiple times
# under slightly different names or affiliations in the AGU database

authorList = []

for person in deptPeopleList: # list but querying key/value pairs as if it were a dictionary
    searchURL = "https://agu.confex.com/agu/fm21/meetingapp.cgi/Search/0?sort=Relevance&size=10&page=1&searchterm={}&ModelType=Person".format(person['firstName'] + " " + person['lastName']) # Concatenates first name and last name persons in file to ignore middle initial, which may cause problems in search URL
    person['searchURL'] = searchURL

    try:
        driver.get(person['searchURL']) # This loads up the the search results page for the dept. member's name.
        print("\nLoading " + person['searchURL'])

        WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.CLASS_NAME, r"searchResults"))) # waits until search results are actually loaded before proceeding with scraping page
        searchResults = driver.find_elements_by_class_name("PersonListItem") # searches the loaded page for all people that come up in the 1st page of this search
        if len(searchResults) < 1:
            print("\n " + person['fullName'] + " isn't returning any search results")
        else:
            aguAuthor = False # resets flag as to whether or not person is an author at AGU for use below so I don't have to retype whole booleaen logic below:

            for result in searchResults:
                try:
                    name = result.find_element_by_class_name("name").find_element_by_tag_name("a").text # retrieves author name for that search result entry as shown in AGU. Necessary because same person may have multiple AGU author profile URLs if they've been listed as co-author on someone else's abstract.
                    affiliation = result.find_element_by_class_name("affiliation").text # retrieves author affiliation for that search result entry
                except Exception as e:
                    print(e)
                if (person['lastName'].lower() in name.lower() and person['firstName'].lower() in name.lower()) and ("mass" in affiliation.lower() or "whoi" in affiliation.lower() or "US Geological Survey" in affiliation): # tests to see if it's really a UMass result. WHOI is because there are some UMass people who very recently went to WHOI
                    # the in / and / (or in) syntax and .lower() method above is pretty critical for catching all permutations of mass and for catching WHOI. Any other way of doing it will miss quite a few people.
                    aguAuthor = True
                    dictionary = {}
                    dictionary['name'] = name # This feels so redundant but ends up being necessary in several places below as getting the person's name from the dictionary name ends up being a pain
                    aguProfileURL = result.find_element_by_class_name("name").find_element_by_tag_name("a").get_attribute("href")
                    dictionary['aguProfileURL'] = aguProfileURL # adds this field to the dictionary for this result
                    authorList.append(dictionary) # adds the dictionary for this person's name to the list
                    print("\n" + name + " - " + dictionary['aguProfileURL'])
                    # print("\n" + name + " - " + affiliation + " - " + dictionary['aguProfileURL']) # use this line if you are searching for person's affiliaton.
                else: # handler for if person is not at UMass
                    continue # i.e, don't do anything and start if loop over with next person

            if not aguAuthor:
                print("\n" + person['fullName'] + " doesn't appear to be an author on anything happening at AGU this year")
                continue

    except Exception as e:
        print("{} on ".format(e) + searchURL)

# %%
# Now go through dept. members who are presenting, access their agu profile pages, and scrape presentations they are part of to dump into dictionary.

print("\n\n ----- Now going through list of people found to be authors and retrieving info. related to ther talks. -----\n")

# Loads AGU profile page for each person, which contains a list of presentations / events they are listed as an author or convener of in the AGU database
for person in authorList: # remember that we set this up as a list object of separate dictionary objects for each person so person variable here is a dictionary with the name of the person *from the AGU database* retrieved above    else:
    person['talks'] = {} # creates nested dictionary for talks for each person
    print("\n\nRetrieving primary author submissions for " + person['name'] + "\n")
    try:
            driver.get(person['aguProfileURL'])
            WebDriverWait(driver, 300).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, r"field_ParentList_Entry"))) # waits until search results are actually loaded before proceeding with scraping page
            # print("Page Loaded...")
    except Exception as e:
        print("{} on ".format(e) + person['aguProfileURL'])
# %%
    # This block of code iterates through all of the submissions on the person's AGU profile and checks if the person first author on that presentaion / session
    # and either skips if not or then retrieves information about that presentation / session and puts it in the appropriate key/value pair in the dictionary
    # item for that name in authorList[name]

    # NOTE: do not get burned by CSS weirdness! In web inspector, the following class names are listed as class="SessionListItem WORKSHOPS    ", class="PaperListItem T", and class="PaperListItem INNOVATIONS"
    # but remember that in CSS spaces DO NOT EXIST in css attributes and are, instead, used as delimiters, so all of those denote MULTIPLE CSS CLASSES
    # and Selenium's .find_element...() methods don't work on multiple class names or attributes if you list them as they are listed in the browser's web inspector. EVIL! EVILLLLLLL!!!!
    # Instead, use .find_element...() methods on the first class name listed in the quotes.
    # yes... I lost hours trying to troubleshoot this. :-)

    try:
        sessions = driver.find_elements_by_class_name("SessionListItem") # if person is chairing a session or workshop
        for x in sessions:
            talkURL = x.find_element_by_class_name("entryContent").find_element_by_tag_name("a").get_attribute("href")
            person['talks'][talkURL] = {} # creates another nested dictionary to put all info for this talk in
            person['talks'][talkURL]['talkType'] = "Convening Session"
            person['talks'][talkURL]['title'] = x.find_element_by_class_name("entryContent").find_element_by_tag_name("a").text
            person['talks'][talkURL]['firstAuthorName'] = person['name'] # copies the person's name from authorList to put in this nested dictionary for each talk.

        talks = driver.find_elements_by_class_name("PaperListItem") # if it's a talk, poster, INNOVATIONS talk, etc...
        for x in talks:
            # check to see if person is primary author / presenting and, if so, puts talk information into dictionary for this person.
            # There's no publicly visible flag / CSS class or HTML element to denote this in agu.confex.com output other than the first presenter's name
            # being encased in an html <b> tag.
            if person['name'] not in x.find_element_by_class_name("topDisplay").find_element_by_tag_name("b").text:
                continue # Every time I use "continue" in a script I feel the need to shout out to @tegareacts on TikTok.
            else:
                talkURL = x.find_element_by_tag_name("a").get_attribute("href")
                person['talks'][talkURL] = {} # creates another nested dictionary to put all info for this talk in
                person['talks'][talkURL]['firstAuthorName'] = person['name'] # copies the person's name from authorList to put in this nested dictionary for each talk.
                person['talks'][talkURL]['talkType'] = "Event"
                person['talks'][talkURL]['title'] = x.find_element_by_tag_name("a").text
                try:
                    talkNumber = x.find_element_by_tag_name("a").find_element_by_tag_name("span").text # Workaround to get rid of paper number listed before talk title
                    person['talks'][talkURL]['title'] = person['talks'][talkURL]['title'].replace(talkNumber,"") # gets rid of talk number that is displayed in a <span> tag within the with talk title in AGU database
                    if ("T" in talkNumber):
                        person['talks'][talkURL]['talkType'] = "Talk"
                    elif "PP" in talkNumber:
                        person['talks'][talkURL]['talkType'] = "Poster"
                    elif "EP" in talkNumber:
                        person['talks'][talkURL]['talkType'] = "Electronic Poster"
                    elif "U" in talkNumber:
                        person['talks'][talkURL]['talkType'] = "Poster"
                    elif "HH" in talkNumber:
                        person['talks'][talkURL]['talkType'] = "Talk"
                    else:
                        person['talks'][talkURL]['talkType'] = "Presentation"
                except Exception as e:
                    print("{} on ".format(e) + talkURL)
    except Exception as e:
        print("{} on ".format(e) + person['aguProfileURL'])

    # %%

    # This code block goes one level deeper into the AGU confex site by loading the page for each talk in which the person
    # is shown as lead author, and grabs the time and date for each talk

    for talkURL in person['talks'].keys(): # iterates through presentation urls collected above
        try:
            person['talks'][talkURL]['url'] = talkURL
            driver.get(talkURL)
            WebDriverWait(driver, 300).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, r"entryInformation"))) # waits until search results are actually loaded before proceeding with scraping page

            # scraping the date and time
            talkDateRaw = driver.find_element_by_class_name("SlotDate").text
            talkTimeRaw = driver.find_element_by_class_name("SlotTime").text
            talkLocation = driver.find_element_by_class_name("propertyName").text

            # Properly formatting the date and time into datetime objects so that they can be sorted later
            reTime = re.search("(.+)\s-", talkTimeRaw)
            startTime = reTime.group(1)
            rawDateTime = talkDateRaw + " " + startTime # this creates a string the formatted as, e.g., Friday, 17 December 2021 14:10
            print(rawDateTime + " - " + person['talks'][talkURL]['talkType'] + ": " + person['talks'][talkURL]['title'])

            dateTimeObj = datetime.strptime(rawDateTime, r"%A, %d %B %Y %H:%M") # This creates datetime object by reading concatenated string above

            person['talks'][talkURL]['talkDateRaw'] = talkDateRaw
            person['talks'][talkURL]['talkTimeRaw'] = talkTimeRaw
            person['talks'][talkURL]['talkLocation'] = talkLocation
            person['talks'][talkURL]['dateTimeObj'] = dateTimeObj
        except Exception as e:
            print("{} on ".format(e) + talkURL)
# %%

# This code block extracts first authors from presenting list and creates list of talks being given that is sorted by presentation time

talkList = [] # list of individual talks, and their dictionary objects, that are only first presenters

# This checks if person in authorList is based on presence of ['talks'] key / dictionary name in their dictionary object and populates the following list of talks.
# People who aren't presenting won't have this key in the dictionary object for their name.
# Also extracts their last name for a separate list of all authors for sort function below.

for person in authorList:
    person['lastName'] = re.search("[\w-]+$", person['name']).group() # uses regex to extract their last name and put it in a last name field in the dictionrary object for the person
    if "talks" in person:
        for talk in person['talks'].keys():
            talkList.append(person['talks'][talk])
    else:
        pass

deptPresenterList = []
for x in deptPeopleList:
    if "aguProfileURL" not in person:
        continue
    else:
        deptPresenterList.append(x)

# %%

# Sorting the presenters list by the datetime object so when we write everything out to HTML below, it's all already sorted

def sortFunc(t): # defining object for use in sort() that only returns value in dictionary key to sort against
    return t['dateTimeObj']
talkList.sort(key=sortFunc)

# Sorting authorList by last name
def lastNameSort(e): # for sorting
    return e['lastName']
authorList.sort(key=lastNameSort)


#%%
# This code block writes out the HTML to teh output file designated in the parameters section at the beginning of the script.

with open(outputScheduleHTML,'a',encoding='utf-8') as outfile:

    # iterators used for logic below as to where to insert a day header into the HTML schedule
    day = ""
    lastTalkFormat = ""

    # Introductory text for HTML file
    outfile.write(r"<p>U-Mass Geosciences has a strong showing at annual Fall meeting of the <a href=\"https://www.agu.org/Fall-Meeting\">American Geophysical Union</a>. If you're attending #AGU21 in New Orleans this year, either virtually or in person, don't miss out! Here is a schedule of who is presenting and when:</p>")
    outfile.write("<p>Only the first author is listed for each presentation below. All times listed are in {}. Be sure to click through to the talk for more information.".format(timezone))
    outfile.write(r"Click <a href=\"#section2\">here</a> for a list of all department members who are co-authors on this year's AGU talks!")
    outfile.write("<table>")

    # Writing out the talk schedule as an HTML table
    for x in talkList:

        # Logic to divide up the table by day and make a header for it
        currentDay = datetime.strftime(x['dateTimeObj'], r"%A, %d %B %Y")
        if currentDay != day:
            outfile.write("<tr><td><h1>{}</h1></td></tr>".format(currentDay))
            day = currentDay
        else:
            day = currentDay

        authors = x['firstAuthorName']

        # logic to replace any weird characters in author names that may appear due to UTF-8 encoding issues
        fixedAuthors = authors.replace("Ã±", "ñ").replace("Â", "").replace("Ã§", "ç") # fixing weird encoding issues
        title = x['title']
        fixedTitle = title.replace("â", "-").replace("Ë", "˚").replace("\n", "").replace("\t", "").replace("\r", "").replace("Ã", "í")
        url = x['url']

        outfile.write("<tr><td>")
        outfile.write("<strong>" + fixedAuthors + "</strong><br>")
        outfile.write("<em>{}</em>".format(x['talkDateRaw'] + " - " + x['talkTimeRaw'] + " " + timezone))
        outfile.write("<br><em>" + x['talkType'] + ":</em>  <a href=\"{}\" target=\"_blank\">{}</a><br>".format(url, fixedTitle))
        outfile.write("</td></tr>")
    outfile.write("</table>")
    outfile.write("<h1 id=\"section2\">List of all department AGU authors</h1>")
    outfile.write("<ul>")

    # Write out list of all the authors of AGU talks in the department.
    for x in authorList:
        outfile.write("<li><a href=\"" + x['aguProfileURL'] + "\">" + x['name'] + "</a></li>")
    outfile.write("</ul>")

print("\n ----* Schedule of department presenters written to {}".format(outputScheduleHTML))
