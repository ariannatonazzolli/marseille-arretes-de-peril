import requests
import time
import re
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from map.models import Place
import urllib3

# Disable SSL warnings (ONLY for this specific use case)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Dictionary of manual corrections for addresses that fail geocoding
MANUAL_CORRECTIONS = {
    # Typos
    "69 eur d'Aubagne, Marseille":                                  "69 rue d'Aubagne, Marseille",
    "19 rtue Lafayette, Marseille":                                 "19 rue Lafayette, Marseille",
    "43 ru du Patit Saint-Jean, Marseille":                         "43 rue du Petit Saint-Jean, Marseille",
    "86 rue Bernard Dubois, Marseille":                             "86 rue Bernard du Bois, Marseille",
    "4 rue Rodolphe\xa0Pollack, Marseille":                         "4 rue Rodolphe Pollak, Marseille",
    "7 rue Rodolphe \xa0Pollack, Marseille":                        "7 rue Rodolphe Pollak, Marseille",
    "11 rue Rodolphe \xa0Polak, Marseille":                       "11 rue Rodolphe Pollak, Marseille",
    "2 rue des Feuilants, Marseille":                               "2 rue des Feuillants, Marseille",
    "58 rue de Sénac de Meilhan, Marseille":                        "58 rue Sénac de Meilhan, Marseille",
    "49 rue Pierre Albran, Marseille":                              "49 rue Pierre Albrand, Marseille",
    "68 rue Pierre Albran, Marseille":                              "68 rue Pierre Albrand, Marseille",
    "2 bis/ter rue d'Anthoine, Marseille":                          "2 rue d'Anthoine, Marseille",
    "11 rue de la Fontaine de Caylus, Marseille":                   "11 rue Font de Caylus, Marseille",
    "44 rue Saint-Françoise, Marseille":                            "44 rue Sainte-Françoise, Marseille",
    "21 avenue Robert Schumann, Marseille":                         "21 Av. Robert Schuman, Marseille",
    "31 avenue Robert Schumann, Marseille":                         "31 Av. Robert Schuman, Marseille",
    "35 avenue Robert Schumann, Marseille":                         "35 Av. Robert Schuman, Marseille",
    "36 avenue du du Docteur Jean-Pierre Franceschi, Marseille":    "36 avenue Dr Jean Pierre Franceschi, Marseille",
    "84 rue Bernard Dubois, Marseille":                             "84 rue Bernard du Bois, Marseille",
    "29 rue des Rimas, Marseille":                                  "29 rue Rimas, Marseille",
    "47 \xa0rue des Rimas, Marseille":                              "47 rue Rimas, Marseille",
    "19 rue Juia, Marseille":                                       "19 rue Julia, Marseille",
    "29 allées Léon Gambetta, Marseille":                           "29 allée Léon Gambetta, Marseille",
    "55 allées Léon Gambetta, Marseille":                           "55 allée Léon Gambetta, Marseille",
    "63 allées Léon Gambetta, Marseille":                           "63 allée Léon Gambetta, Marseille",
    "73 allées Léon Gambetta, Marseille":                           "73 allée Léon Gambetta, Marseille",
    "40 rue Sainte-Bazile, Marseille":                              "40 rue Saint-Bazile, Marseille",
    "1 boulevard Sidole, Marseille":                                "1 Bd Sidolle, Marseille",
    "2 rue Antoine Del Bello, Marseille":                           "2 rue Antoine Bello, Marseille",
    "13 rue Antoine Del Bello, Marseille":                          "13 rue Antoine Bello, Marseille",
    "215 chemin des Prudhommes, Marseille":                         "215 chemin des Prud'hommes, Marseille",
    "179 chemin des Jonquill/es, Marseille":                        "179 chemin des Jonquilles, Marseille",
    "15 avenue Roquefvour, Marseille":                              "15 avenue Roquefavour, Marseille",
    "193 boulevard Bolivard, Marseille":                            "193 boulevard Simon Bolivar, Marseille",
    "29 boulevard Demandlox, Marseille":                            "29 boulevard Demandolx, Marseille",
    "40 boulevard Demandlox, Marseille":                            "40 boulevard Demandolx, Marseille",
    "4 palce Cazemajou, Marseille":                                 "4 place Cazemajou, Marseille",
    "42 avenue Félix Zaccola, Marseille":                           "42 avenue Félix Zoccola, Marseille",
    "9001 Quai d'honneur - île de Ratonneau, Marseille":            "9001 Quai d'Honneur, Marseille",
    "29 rue Alleman, Marseille":                                    "29 rue César Aleman, Marseille",
    "1 rue Antoine Perrin, Marseille":                              "1 rue Perrin, Marseille",
    "47 rue des Bon Enfants, Marseille":                            "47 rue des Bons Enfants, Marseille",
    "24 place ND-du-Mont, Marseille":                               "24 place Notre Dame du Mont, Marseille",
    "124 rue Edmond Rostant, Marseille":                            "124 rue Edmond Rostand, Marseille",
    "11 rue Sainte-Célile, Marseille":                              "11 rue Sainte Cécile, Marseille",
    "64 traverse du Moulin de la Vilette, Marseille":               "64 traverse du Moulin de la Villette, Marseille",
    "61 boulevard de Stasbourg, Marseille":                         "61 boulevard de Strasbourg, Marseille",
    "55 rue Clovis Huges, Marseille":                               "55 rue Clovis Hugues, Marseille",
    "59\xa0\xa0rue Clovis Huges, Marseille":                        "59 rue Clovis Hugues, Marseille",
    "31 impassse Icard, Marseille":                                 "31 impasse Icard, Marseille",
    "1 impassse Sylvestre, Marseille":                              "1 impasse Sylvestre, Marseille",
    # Change street type (such as avenue, boulevard, montée, etc.)
    "23 Boulevard de Vaisseau, Marseille":                          "23 Bd du Vaisseau, Marseille",
    "135\xa0 avenue Alexanddre Delabre, Marseille":                 "135 boulevard Alexandre Delabre, Marseille",
    "36 rue montée Mouren, Marseille":                              "36 montée Mouren, Marseille",   
    "30 rue Bonniot, Marseille":                                    "30 Bd Bonniot, Marseille",
    "31 boulevard des Bonnes Grâces, Marseille":                    "31 Bd Bonnes Grâces, Marseille",
    "33 boulevard des Bonnes Grâces, Marseille":                    "33 Bd Bonnes Grâces, Marseille",
    "35 boulevard des Bonnes Grâces, Marseille":                    "35 boulevard Bonnes Grâces, Marseille",
    "16 rue Raoul Follereau, Marseille":                            "16 Av. Raoul Follereau, Marseille",                      
    "56 bouloevard de la Cartonerie, Marseille":                    "56 Bd de la Cartonnerie, Marseille",
    "29 bouvevard Boisson, Marseille":                              "29 Bd Boisson, Marseille",
    "15 boulevard Louis Bottinelly, Marseille":                     "15 Bd Louis Botinelly, Marseille",
    "5 boulevard Colonnel Rossi, Marseille":                        "5 Bd Colonel Robert Rossi, Marseille",
    "8 montée de la Tête noire, Marseille":                         "8 Esc. de la Tête Noire, Marseille",
    "11 boulevard Beltrandon, Marseille":                           "11 Bd Bertrandon, Marseille",
    "2 chemin de la Butineuse, Marseille":                          "2 rue de la Butineuse, Marseille",
    "6 Travers Bernabo, Marseille":                                 "6 rue Bernabo, Marseille",
    "130 rue Roger Salengro, Marseille":                            "130 avenue Roger Salengro, Marseille",
    # Remove additional info
    "46 rue Caisserie (4eet 5eétages), Marseille":                  "46 rue Caisserie, Marseille",
    "10 place de la Joliette (Les Docks), Marseille":               "10 place de la Joliette, Marseille",
    "250 chemin de la Madrague Ville (parcelle 277), Marseille":    "250 chemin de la Madrague Ville, Marseille",
    "30T boulevard Bonne Brise (Plage Bonne Brise), Marseille":     "30 Bd Bonne Brise, Marseille",
    "4 et 4 B traverse de la Gironne, Marseille":                   "4 traverse de la Gironne, Marseille",
    "11 chemin du Maupas - parcelle 534, Marseille":                "11 chemin du Maupas, Marseille",
    "11 chemin du Maupas - parcelle 535, Marseille":                "11 Chemin du Maupas, Marseille",
    "41 avenue Bernard Lecache - Parc de Clairville, Marseille":    "41 Av. Bernard Lecache, Marseille",
    "546 boulevard Mireille Lauze - Bel ombre bat D, Marseille":    "546 Bd Mireille Lauze, Marseille",
    "359 boulevard Mireille Lauze \xa0- bat X, Marseille":          "359 Bd Mireille Lauze, Marseille",
    "197 boulevard de la Libération / Angle Espérandieu, Marseille": "197 Bd de la Libération, Marseille",
    "60-60A rue de Trois Frères Carasso, Marseille":                 "60 rue des Trois Frères Carasso, Marseille",
    "29 rue d'Isly (immeuble de fond de cour), Marseille":           "29 rue d'Isly, Marseille",
    "13 rue George Picot - 13010, Marseille":                        "13 rue Georges Picot, Marseille",
    "171 avenue de Toulon - Caserne MDC Lucien Donadieu, Marseille":    "171 avenue de Toulon, Marseille",
    "30 rue d'Eguison Ramifiée, Marseille":                          "30 rue d'Eguison, Marseille",
    "153 chemin des Campanules - Groupe La Moularde, Marseille":     "153 chemin des Campanules, Marseille",
    "2 place granet – Rue du Grand Pascal, Marseille":               "2 place Granet, Marseille",
    "17 boulevard Guichou, Marseille":                               "17 Bd Guichoux, Marseille",
    "2 boulevard d'Hanoï et jardin public du 19 mars 1962 (avenue de la Viste), Marseille":             "2 Bd d'Hanoï, Marseille",
    "38 ou 40 impasse des Muriers, Marseille":                       "38 impasse des Mûriers, Marseille",
    "4 boulevard des Platanes / 48 promenade du Grand Large, Marseille":    "4 boulevard des Platanes, Marseille",
    "48 promenade du Grand Large / 4 boulevard des Platanes, Marseille":    "48 promenade du Grand Large, Marseille",
    "301 Corniche Kennedy et Traverse de la Pey, Marseille":         "301 Corniche Kennedy, Marseille",
    "6 rue Crudère (immeuble sur rue), Marseille":                   "6 rue Crudère, Marseille",
    "6 rue Crudère (fond de cour), Marseille":                       "6 rue Crudère, Marseille",
    "3 rue Fernand Pauriol (appartement du 9e étage gauche), Marseille":    "3 rue Fernand Pauriol, Marseille",
    "1 boulevard Eugène Pierre (appartement 3e étage droit), Marseille":    "1 boulevard Eugène Pierre, Marseille",
    "59 rue Peyssonnel (69 selon cadastre), Marseille":              "59 rue Peyssonnel, Marseille",
    "213 boulevard National - Bt D, Marseille":                      "213 boulevard National, Marseille",
    # Streets Nominatim doesn't find with "de/du"
    "36 rue de Chateauredon, Marseille":        "36 rue Chateauredon, Marseille",
    "40 rue du Commandant Mages, Marseille":    "40 rue Commandant Mages, Marseille",
    "60 rue du Commandant Mages, Marseille":    "60 rue Commandant Mages, Marseille",
    "5 rue de Lulli, Marseille":                "5 rue Lulli, Marseille",
    "7 rue de Lulli, Marseille":                "7 rue Lulli, Marseille",
    "15 rue du Tapis Vert, Marseille":          "15 rue Tapis Vert, Marseille",
    "55 rue du Tapis Vert, Marseille":          "55 rue Tapis Vert, Marseille",
    "44 \xa0rue du Tapis Vert, Marseille":      "44 rue Tapis Vert, Marseille",
    "41 rue de Montolieu, Marseille":           "41 rue Montolieu, Marseille",
    "49 boulavard Saint-Loup, Marseille":       "49 boulevard de Saint-Loup, Marseille",
    "17 montée de la Graille, Marseille":       "17 montée Graille, Marseille",
    "23 taverse de l'Hermitage, Marseille":     "23 traverse l'Hermitage, Marseille",
    "8 rue de Crinas, Marseille":               "8 rue Crinas, Marseille",
    "15 rue de Navarin, Marseille":             "15 rue Navarin, Marseille",
    "3 rue de Thiepval, Marseille":             "3 Thiepval, Marseille",
    "2 rue de Sery, Marseille":                 "2 rue Séry, Marseille",
    "18 rue de Sery, Marseille":                "18 rue Séry, Marseille",
    "22 rue de Sery, Marseille":                "22 rue Séry, Marseille",
}

ALL_ARRONDISSEMENTS = [
    "1er", "2e", "3e", "4e", "5e", "6e", "7e", "8e",
    "9e", "10e", "11e", "12e", "13e", "14e", "15e", "16e",
]


class Command(BaseCommand):
    help = "Scrapes addresses from Marseille website and geocodes them"

    def scrape_addresses(self, arrondissement, soup):
        addresses = []

        for dl in soup.find_all("dl", class_="ckeditor-accordion"):
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")

            for dt, dd in zip(dts, dds):
                dt_text = dt.get_text(strip=True)
                if re.search(r'(?<!\d)' + re.escape(arrondissement.replace(" ", "").lower()), dt_text.replace(" ", "").lower()):
                    self.stdout.write(f"  Found section: '{dt_text}'")

                    # Trova tutti i <li> dentro questo <dd>
                    for li in dd.find_all("li"):
                        text = li.get_text(strip=True)
                        # Try split on ":" first, fall back to first " -" or " –"
                        colon_match = re.match(r"^(.+?)\s*:(.*)", text)
                        if colon_match:
                            addr = colon_match.group(1).strip()
                            after_sep = colon_match.group(2)
                        else:
                            dash_match = re.match(r"^(.+?)\s+[-–—](.*)", text)
                            if not dash_match:
                                continue
                            addr = dash_match.group(1).strip()
                            after_sep = dash_match.group(2)
                        # Keep only addresses that start with a number
                        if re.match(r"^\d", addr):
                            full = f"{addr}, Marseille"
                            # The last event in the history determines current status.
                            # Separators used on the site: /, –, —, or standalone -
                            segments = re.split(r'/(?=[A-Za-zÀ-ÿ])|[–—]|-(?=[A-Z])', after_sep)
                            last_segment = segments[-1].strip()
                            is_mainlevee = bool(re.match(r'Mainlev[eé]e', last_segment, re.IGNORECASE))
                            if full not in [a for a, _ in addresses]:
                                addresses.append((full, is_mainlevee))

        return addresses
    
    def split_composite_address(self, address):
        """
        Splits composite addresses into individual ones. Cases handled:

        Case A — multiple numbers, single street:
          "3, 5, 7, 9 et 11 Impasse Puget, Marseille"
          → ["3 Impasse Puget, Marseille", "5 Impasse Puget, Marseille", ...]

        Case B — multiple full addresses separated by et / / + / ainsi que:
          "13 rue d'Aix et 2 rue Puvis de Chavannes, Marseille"
          "95 rue d'Aubagne / 50 cours Lieutaud, Marseille"
          → one entry per full address

        Case C — number range on a single street (take only the first number):
          "51 à 55 allées Léon Gambetta, Marseille"
          "79 au 85 rue Curiol, Marseille"
          → ["51 allées Léon Gambetta, Marseille"]
        """
        STREET_PATTERN = (
            r'rue|boulevard|bd|cours|place|avenue|av\.|impasse|chemin|'
            r'montée|mnt|traverse|allée|allées|promenade|corniche|'
            r'domaine|escalier|esc\.|passage|square'
        )

        base = address.replace(", Marseille", "").strip()
        base = re.sub(r'\(.*?\)', '', base).strip()

        # --- Case A: "3, 5, 7, 9 et 11 Impasse Puget" ---
        case_a = re.match(
            rf'^(\d[\d,\s]*(?:et\s+\d+)?)\s+({STREET_PATTERN}\b.+)$',
            base, re.IGNORECASE
        )
        if case_a:
            numbers = re.findall(r'\d+', case_a.group(1))
            street = case_a.group(2).strip()
            if len(numbers) > 1:
                return [f"{n} {street}, Marseille" for n in numbers]

        # --- Case C: "51 à 55 ..." or "79 au 85 ..." → keep first number ---
        base = re.sub(r'(\d+)\s+(?:au|à)\s+\d+', r'\1', base, flags=re.IGNORECASE)

        # --- Case B: split on et / / + / ainsi que ---
        base = re.sub(r'\s+ainsi que\s+', '|', base, flags=re.IGNORECASE)
        base = re.sub(r'\s+et\s+', '|', base, flags=re.IGNORECASE)
        base = re.sub(r'\s*/\s*', '|', base)
        base = re.sub(r'\s*\+\s*', '|', base)

        # Building/complex qualifiers that can trail an address after a separator
        _BUILDING = r'résidences?|bâtiments?|bat\b|immeuble|groupe|lotissement|parc\b|villa\b'

        parts = base.split('|')
        result = []
        for part in parts:
            part = part.strip()
            # Strip trailing building qualifiers and everything after them
            part = re.sub(rf'\s+\b(?:{_BUILDING})\b.*$', '', part, flags=re.IGNORECASE).strip()
            if part and re.search(rf'\b({STREET_PATTERN})\b', part, re.IGNORECASE):
                result.append(f"{part}, Marseille")

        return result if result else [address]


    def geocode(self, address):
        # Check manual corrections first
        corrected = MANUAL_CORRECTIONS.get(address, address)
        if corrected != address:
            address = corrected
        
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": address, "format": "json", "limit": 1}
        headers = {"User-Agent": "mia-app-map/1.0"}
        response = requests.get(url, params=params, headers=headers)
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
        return None

    def handle(self, *args, **kwargs):
        self.stdout.write("Fetching page...")
        url = "https://www.marseille.fr/logement-urbanisme/amelioration-de-lhabitat/arretes-de-peril"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        addresses = []
        for arr in ALL_ARRONDISSEMENTS:
            self.stdout.write(f"Scraping arrondissement {arr}...")
            for addr, is_mainlevee in self.scrape_addresses(arr, soup):
                addresses.append((addr, is_mainlevee, arr))
        self.stdout.write(f"Found {len(addresses)} addresses total")

        for address, is_mainlevee, arr in addresses:
            if Place.objects.filter(address=address, geocoded=True).exists():
                self.stdout.write(f"  Already geocoded: {address}")
                continue

            corrected = MANUAL_CORRECTIONS.get(address, address)
            suffix = f" → {corrected}" if corrected != address else ""
            self.stdout.write(f"  Geocoding: {address}{suffix}")
            coords = self.geocode(address)

            # If not found, try splitting the address
            if not coords:
                self.stdout.write(f"  Trying to split composite address...")
                sub_addresses = self.split_composite_address(address)

                if len(sub_addresses) > 1:
                    self.stdout.write(f"  Split into {len(sub_addresses)} parts: {sub_addresses}")
                    Place.objects.filter(address=address).delete()
                    for sub in sub_addresses:
                        sub_coords = self.geocode(sub)
                        if sub_coords:
                            Place.objects.filter(address=sub).delete()
                            Place.objects.create(
                                address=sub,
                                lat=sub_coords[0],
                                lon=sub_coords[1],
                                geocoded=True,
                                mainlevee=is_mainlevee,
                                arrondissement=arr,
                            )
                            label = " [Mainlevée]" if is_mainlevee else ""
                            self.stdout.write(self.style.SUCCESS(f"  Saved: {sub}{label}"))
                        else:
                            self.stdout.write(self.style.WARNING(f"  Not found: {sub}"))
                            Place.objects.update_or_create(
                                address=sub,
                                defaults={"geocoded": False, "arrondissement": arr},
                            )
                        time.sleep(1)
                    continue  # composite address handled, skip normal save below

            if coords:
                Place.objects.filter(address=address).delete()
                Place.objects.create(
                    address=address,
                    lat=coords[0],
                    lon=coords[1],
                    geocoded=True,
                    mainlevee=is_mainlevee,
                    arrondissement=arr,
                )
                label = " [Mainlevée]" if is_mainlevee else ""
                self.stdout.write(self.style.SUCCESS(f"  Saved: {address}{label}"))
            else:
                self.stdout.write(self.style.WARNING(f"  Not found: {address}"))
                Place.objects.update_or_create(
                    address=address,
                    defaults={"geocoded": False, "arrondissement": arr},
                )
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Done!"))