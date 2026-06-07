import requests
import time
import re
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from map.models import Place

class Command(BaseCommand):
    help = "Scrapes addresses from Marseille website and geocodes them"

    def scrape_addresses(self, arrondissement="1er"):
        url = "https://www.marseille.fr/logement-urbanisme/amelioration-de-lhabitat/arretes-de-peril"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        addresses = []

        # Trova tutti i <dl class="ckeditor-accordion">
        for dl in soup.find_all("dl", class_="ckeditor-accordion"):
            # Ogni <dt> è un arrondissement, ogni <dd> è il contenuto
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")

            for dt, dd in zip(dts, dds):
                # Controlla se questo è l'arrondissement che cerchiamo
                dt_text = dt.get_text(strip=True)  # es. "1erarrondissement"
                if arrondissement.replace(" ", "").lower() in dt_text.replace(" ", "").lower():
                    self.stdout.write(f"  Sezione trovata: '{dt_text}'")

                    # Trova tutti i <li> dentro questo <dd>
                    for li in dd.find_all("li"):
                        text = li.get_text(strip=True)
                        # Prende solo la parte prima del ":"
                        match = re.match(r"^(.+?)\s*:", text)
                        if match:
                            addr = match.group(1).strip()
                            # Verifica che inizi con un numero
                            if re.match(r"^\d", addr):
                                full = f"{addr}, Marseille"
                                if full not in addresses:
                                    addresses.append(full)

        return addresses

    def geocode(self, address):
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": address, "format": "json", "limit": 1}
        headers = {"User-Agent": "mia-app-map/1.0"}
        response = requests.get(url, params=params, headers=headers)
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
        return None

    def handle(self, *args, **kwargs):
        self.stdout.write("Scraping addresses...")
        addresses = self.scrape_addresses("1er")
        self.stdout.write(f"Found {len(addresses)} addresses")

        for a in addresses[:5]:
            self.stdout.write(f"  Esempio: {a}")

        for address in addresses:
            if Place.objects.filter(address=address).exists():
                self.stdout.write(f"  Already in DB: {address}")
                continue

            self.stdout.write(f"  Geocoding: {address}")
            coords = self.geocode(address)
            if coords:
                Place.objects.create(
                    name=address,
                    address=address,
                    lat=coords[0],
                    lon=coords[1],
                    geocoded=True
                )
                self.stdout.write(self.style.SUCCESS(f"  Saved: {address}"))
            else:
                self.stdout.write(self.style.WARNING(f"  Not found: {address}"))
                Place.objects.create(
                    name=address,
                    address=address,
                    geocoded=False
                )
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Done!"))