# AGU-Scraping

Python script using Selenium to scrape the AGU Fall Meeting Website for talks by presenters provided in a CSV file.

The script works with the AGU Fall 2021 meeting website and can be modified for any meeting website that is run off confex.com, though the extent of modification for various html and CSS elements may be substatnial, depending on the conference.  I couldn't test it for all edge cases on the meeting website. Chances are there might be presentation or event types that have element classes or tags that the script won't recognize.

The script writes out an html table containing a schedule of the presentations, and sessions, being given or convenedd by the people listed in your CSV file if they are primary authors or a session convener. It also produces a list of all the people in the CSV file who are included as authors on any AGU 2021 presentation, even if they are not first author or are presenting.

The scipt skips over withdrawn abstracts, but stil includes a link to the abstract author in the list at the end of the html file.

This script has some dependencies, which you can see in the import section at the beginning of the script.

The biggest is an external dependency in needing either Firefox or Chrome installed on your machine, and the proper webdriver for them, as this script is used to control your web browser to scrape the AGU meeting site. This script uses FireFox and the gecko webriver for it. There are many tutorials for installing Selenium's Python bindings so one can uset this script, but a good one is at https://www.geeksforgeeks.org/selenium-python-introduction-and-installation/

Important note: The boolean logic for which institution your authors are at is in the if statement on line 123 or thereabouts. This willl be different for your institution and you might have to write some very complicated logic if your authors have differing affiliations from one another or like in our case, there are multiple spellings and abbreviations for your instituion.

Happy scraping!
