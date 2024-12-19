import requests
from bs4 import BeautifulSoup

url = "https://www.marseille.fr/logement-urbanisme/am%C3%A9lioration-de-lhabitat/arretes-de-peril" 
response = requests.get(url)

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(response.content, "html.parser")

# Extract specific elements
titles = soup.find_all(['p'])

# Step 5: Print out the titles
for title in titles:
    print(title.get_text())