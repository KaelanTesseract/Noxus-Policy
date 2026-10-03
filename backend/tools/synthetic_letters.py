# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Invented letters of other insurers and other kinds of insurance, for ``eval_models.py``.

The real evaluation documents are all motor insurance of two insurers. To see whether the rules
(and a language model that helps them) also hold for other insurers and other layouts, these
letters vary what matters for finding the insurer and the policy number: the layout of the
number (inline, on the next line, in a table, with spaces), the place of the insurer's name
(letterhead only, footer too), an insurance broker's block, other company names in the footer
(banks, reinsurers). Eight insurers are in the rules' list of known companies, eight are not.

The last six ("schwierig") were written after the rules had been improved on the others and are
deliberately awkward: unusual labels, the number only in a subject line or a table, the insurer
only in the small print of the footer (a logo is an image and not read).

All names, numbers and amounts are invented; the insurers' names are only the labels such
letters carry. Nothing here is a real policy.
"""

FOOTER = """{company} · {street} · {city}
Vorsitzender des Aufsichtsrats: Dr. Erika Beispiel · Vorstand: Hans Muster, Petra Probe
Registergericht {court} HRB {hrb} · USt-IdNr. DE{ust}
Bankverbindung: {bank}, IBAN DE02 1234 5678 9012 3456 78, BIC {bic}
"""

BROKER = """Sie werden betreut von:
{broker}
{broker_street}
Telefon {broker_phone}
"""

RECIPIENT = """Herrn
Max Mustermann
Beispielweg 12
12345 Musterstadt
"""

# (insurer as it must be recognised, policy number, category, text)
LETTERS = []


def add(company, number, text, group="synthetisch"):
    LETTERS.append({"company": company, "insurance_number": number, "text": text, "group": group})


def footer(company, street, city, court, hrb, bank, bic="GENODEF1XXX", ust="123456789"):
    return FOOTER.format(company=company, street=street, city=city, court=court, hrb=hrb, bank=bank, bic=bic, ust=ust)


# ----- known to the rules ---------------------------------------------------------------------

add("Allianz", "HV-2024-889123", f"""Allianz Versicherungs-AG
Königinstraße 28, 80802 München
{RECIPIENT}
München, 14.03.2024
Ihre Privathaftpflichtversicherung
Versicherungsschein-Nr. HV-2024-889123
Sehr geehrter Herr Mustermann,
wir bestätigen Ihnen den Versicherungsschutz für Ihre Privathaftpflichtversicherung.
Versicherungsbeginn: 01.04.2024
Ablauf: 01.04.2025
Jahresbeitrag inklusive Versicherungsteuer 78,40 €
Die Deckungssumme beträgt 50 Mio. € pauschal für Personen-, Sach- und Vermögensschäden.
{footer("Allianz Versicherungs-AG", "Königinstraße 28", "80802 München", "München", "7158", "Commerzbank AG München", "COBADEFFXXX")}""")

add("AXA", "7 123 456 789 0", f"""AXA Versicherung AG
Colonia-Allee 10-20, 51067 Köln
{RECIPIENT}
Köln, 02.09.2023
Hausratversicherung - Ihr Versicherungsschein
Vertragsnummer
7 123 456 789 0
Vertragsbeginn 01.10.2023, Ablauf 01.10.2024
Beitrag (inkl. 19 % Versicherungsteuer) 12,90 € monatlich
Versichert sind Schäden durch Einbruchdiebstahl, Feuer, Leitungswasser, Sturm und Hagel.
{footer("AXA Versicherung AG", "Colonia-Allee 10-20", "51067 Köln", "Köln", "13322", "Deutsche Bank AG Köln", "DEUTDEDKXXX")}""")

add("DEVK", "123/456789-A", f"""DEVK Allgemeine Versicherung AG
Riehler Straße 190, 50735 Köln
{RECIPIENT}
Köln, 20.11.2022
Beitragsrechnung zur Kfz-Versicherung
Vertrag 123/456789-A
Für den Zeitraum 01.01.2023 bis 31.12.2023 beträgt Ihr Beitrag
Gesamtbeitrag 612,30 €
Schadenfreiheitsklasse SF 12, Regionalklasse R 14, Typklasse 18
{footer("DEVK Allgemeine Versicherung AG", "Riehler Straße 190", "50735 Köln", "Köln", "4500", "Sparkasse KölnBonn", "COLSDE33XXX")}""")

add("Gothaer", "RS-0099123-44", f"""Gothaer Allgemeine Versicherung AG
Gothaer Allee 1, 50969 Köln
{RECIPIENT}
Köln, 05.05.2021
Rechtsschutzversicherung
Versicherungsschein-Nummer:      RS-0099123-44
Versicherungsbeginn:             01.06.2021
Zahlungsweise:                   vierteljährlich
Beitrag je Zahlung:              41,20 €
Verkehrs- und Privatrechtsschutz mit 150 € Selbstbeteiligung.
{footer("Gothaer Allgemeine Versicherung AG", "Gothaer Allee 1", "50969 Köln", "Köln", "21332", "Postbank Köln", "PBNKDEFFXXX")}""")

add("HDI", "WG 5544-3321", f"""HDI Versicherung AG
HDI-Platz 1, 30659 Hannover
{RECIPIENT}
{BROKER.format(broker="Maklerhaus Nordwind GmbH", broker_street="Hafenstraße 4, 20457 Hamburg", broker_phone="040 123456")}
Hannover, 11.01.2024
Wohngebäudeversicherung - Nachtrag
Versicherungsschein-Nr. WG 5544-3321
Beginn der Änderung 01.02.2024
Neuer Jahresbeitrag 389,00 €
{footer("HDI Versicherung AG", "HDI-Platz 1", "30659 Hannover", "Hannover", "6852", "Nord/LB Hannover", "NOLADE2HXXX")}""")

add("ERGO", "5 123 456 789", f"""ERGO Lebensversicherung AG
Victoriaplatz 2, 40477 Düsseldorf
{RECIPIENT}
Düsseldorf, 30.06.2020
Berufsunfähigkeitsversicherung
Vertragsnummer 5 123 456 789
Versicherungsbeginn 01.07.2020
Ablauf 01.07.2050
Monatlicher Beitrag 57,45 €
Bei Berufsunfähigkeit zahlen wir eine monatliche Rente von 1.500,00 €.
{footer("ERGO Lebensversicherung AG", "Victoriaplatz 2", "40477 Düsseldorf", "Düsseldorf", "41172", "HypoVereinsbank Düsseldorf", "HYVEDEMMXXX")}""")

add("Signal Iduna", "12-3456789-0", f"""SIGNAL IDUNA Gruppe
Joseph-Scherer-Straße 3, 44139 Dortmund
{RECIPIENT}
Dortmund, 08.08.2019
Unfallversicherung
Police: 12-3456789-0
Beginn 01.09.2019, Ablauf 01.09.2020
Jahresbeitrag 134,56 €
Invaliditätsleistung bis 200.000,00 €.
{footer("SIGNAL IDUNA Unfallversicherung a.G.", "Joseph-Scherer-Straße 3", "44139 Dortmund", "Dortmund", "1234", "Sparkasse Dortmund", "DORTDE33XXX")}""")

add("VHV", "KH-77001234-1", f"""VHV Allgemeine Versicherung AG
VHV-Platz 1, 30177 Hannover
{RECIPIENT}
Hannover, 19.12.2023
Nachtrag zur Kraftfahrtversicherung
Versicherungsschein-Nr.   KH-77001234-1
Beginn der Änderung 01.01.2024
Beitrag (inklusive Versicherungsteuer) 54,10 €
Zahlungsperiode monatlich
{footer("VHV Allgemeine Versicherung AG", "VHV-Platz 1", "30177 Hannover", "Hannover", "6606", "Nord/LB Hannover", "NOLADE2HXXX")}""")

# ----- not in the rules' list -----------------------------------------------------------------

add("Württembergische", "00 8812 3345", f"""Württembergische Versicherung AG
Gutenbergstraße 30, 70176 Stuttgart
{RECIPIENT}
Stuttgart, 03.03.2024
Hausratversicherung
Versicherungsschein-Nr. 00 8812 3345
Versicherungsbeginn: 01.04.2024
Jahresbeitrag 98,00 €
{footer("Württembergische Versicherung AG", "Gutenbergstraße 30", "70176 Stuttgart", "Stuttgart", "20203", "BW-Bank Stuttgart", "SOLADEST600")}""")

add("Mecklenburgische", "PH-4410-2288", f"""Mecklenburgische Versicherungs-Gesellschaft a.G.
Platz der Mecklenburgischen 1, 30625 Hannover
{RECIPIENT}
Hannover, 21.07.2022
Privathaftpflicht - Beitragsrechnung
Vertragsnummer: PH-4410-2288
Zeitraum 01.08.2022 bis 31.07.2023
Zu zahlender Beitrag 64,80 €
{footer("Mecklenburgische Versicherungs-Gesellschaft a.G.", "Platz der Mecklenburgischen 1", "30625 Hannover", "Hannover", "6003", "Hannoversche Volksbank", "VOHADE2HXXX")}""")

add("Basler", "30.120.456-7", f"""Basler Versicherung AG
Basler Straße 4, 61352 Bad Homburg
{RECIPIENT}
{BROKER.format(broker="Versicherungsmakler Weber & Söhne", broker_street="Marktplatz 3, 61348 Bad Homburg", broker_phone="06172 998877")}
Bad Homburg, 15.10.2021
Kfz-Versicherung - Versicherungsschein
Versicherungsschein-Nr. 30.120.456-7
Beginn: 01.11.2021, Ablauf: 01.11.2022
Gesamtbeitrag inkl. Versicherungsteuer 418,20 €
Teilkasko mit 300 € Selbstbeteiligung, Kfz-Haftpflicht mit 100 Mio. € Deckung.
{footer("Basler Versicherung AG", "Basler Straße 4", "61352 Bad Homburg", "Bad Homburg", "9901", "Taunus Sparkasse", "HELADEF1TSK")}""")

add("Ostangler", "WG/2018/00412", f"""Ostangler Brandgilde VVaG
Flensburger Straße 22, 24376 Kappeln
{RECIPIENT}
{BROKER.format(broker="Agentur Petersen", broker_street="Hauptstraße 8, 24376 Kappeln", broker_phone="04642 5566")}
Kappeln, 02.02.2018
Wohngebäudeversicherung
Police-Nr.
WG/2018/00412
Beginn 01.03.2018
Jahresbeitrag 512,00 €
{footer("Ostangler Brandgilde VVaG", "Flensburger Straße 22", "24376 Kappeln", "Flensburg", "871", "VR Bank Flensburg", "GENODEF1FL1")}""")

add("Lippische", "LL 2019 556677", f"""Lippische Landes-Brandversicherungsanstalt
Hermannstraße 20, 32756 Detmold
{RECIPIENT}
Detmold, 09.09.2019
Haftpflichtversicherung für Hundehalter
Versicherungsschein-Nr. LL 2019 556677
Versicherungsbeginn: 01.10.2019
Jahresbeitrag 71,50 €
{footer("Lippische Landes-Brandversicherungsanstalt", "Hermannstraße 20", "32756 Detmold", "Lemgo", "1105", "Sparkasse Detmold", "WELADED1DTM")}""")

add("BGV", "RS-5566-7788", f"""BGV Badische Versicherungen
Durlacher Allee 56, 76131 Karlsruhe
{RECIPIENT}
Karlsruhe, 17.04.2023
Rechtsschutzversicherung - Ihr Vertrag
Versicherungsschein-Nummer RS-5566-7788
Beginn der Versicherung: 01.05.2023
Beitrag monatlich 22,30 € inkl. Versicherungsteuer
{footer("Badische Allgemeine Versicherung AG", "Durlacher Allee 56", "76131 Karlsruhe", "Mannheim", "3366", "Sparkasse Karlsruhe", "KARSDE66XXX")}""")

add("Nordlicht", "NL-4711-0815", f"""Nordlicht Assekuranz GmbH
Hafenkante 7, 20457 Hamburg
{RECIPIENT}
Hamburg, 22.05.2024
Auslandsreise-Krankenversicherung
Versicherungsschein-Nr. NL-4711-0815
Reisezeitraum 01.07.2024 bis 15.07.2024
Beitrag einmalig 39,00 €
Rückversicherer: Münchener Rückversicherungs-Gesellschaft
{footer("Nordlicht Assekuranz GmbH", "Hafenkante 7", "20457 Hamburg", "Hamburg", "99887", "Hamburger Sparkasse", "HASPDEHHXXX")}""")

add("Bayerische Beamtenkrankenkasse", "K 4455 6677 88", f"""Bayerische Beamtenkrankenkasse AG
Maximilianstraße 53, 80530 München
{RECIPIENT}
München, 12.12.2022
Krankenversicherung - Beitragsanpassung zum 01.01.2023
Versicherungsnummer: K 4455 6677 88
Ihr neuer Monatsbeitrag ab 01.01.2023 beträgt 412,36 € (bisher 389,10 €).
{footer("Bayerische Beamtenkrankenkasse AG", "Maximilianstraße 53", "80530 München", "München", "5544", "Bayerische Landesbank", "BYLADEMMXXX")}""")


# ----- deliberately awkward (written after the rules were tuned on the letters above) ------------

add("Rheinland", "77-123456-9", f"""{RECIPIENT}
Neuss, 04.04.2023
Ihre Kfz-Versicherung
Vers.-Nr. 77-123456-9
Sehr geehrter Herr Mustermann,
anbei erhalten Sie die Unterlagen zu Ihrer Kraftfahrtversicherung ab 01.05.2023.
Jahresbeitrag 455,00 €
Sitz der Gesellschaft: Rheinland Versicherungs-AG, Rheinlandplatz 1, 41460 Neuss
{footer("Rheinland Versicherungs-AG", "Rheinlandplatz 1", "41460 Neuss", "Neuss", "2211", "Sparkasse Neuss")}""", "schwierig")

add("Concordia", "4455-7788-12", f"""{RECIPIENT}
Hannover, 12.12.2022
Betreff: Ihr Vertrag 4455-7788-12 - Beitragsanpassung zum 01.01.2023
Sehr geehrter Herr Mustermann,
Ihr Beitrag ändert sich auf 233,10 € jährlich.
Concordia Versicherungs-Gesellschaft a.G. - Karl-Wiechert-Allee 55 - 30625 Hannover
""", "schwierig")

add("Hanse", "HV/2021/334455", f"""{RECIPIENT}
Hamburg, 01.03.2021
Unser Zeichen: HV/2021/334455
Ihre Vertrags-ID: 998877665
Privathaftpflichtversicherung - Ihre Bestätigung
Beitrag jährlich 58,00 €
{footer("Hanse Assekuranz AG", "Alsterufer 3", "20354 Hamburg", "Hamburg", "55443", "Hamburger Sparkasse", "HASPDEHHXXX")}""", "schwierig")

add("Hagelversicherung", "AB 123456", f"""{RECIPIENT}
Gießen, 10.10.2020
Ihre Hagelversicherung - Vertragsübersicht
Nr.          Beginn        Ablauf
AB 123456    01.01.2021    01.01.2022
Beitrag 188,00 €
{footer("Vereinigte Hagelversicherung VVaG", "Hagelstraße 7", "35390 Gießen", "Gießen", "1122", "Volksbank Mittelhessen", "VBMHDE5FXXX")}""", "schwierig")

add("Hanseatische", "0099 8877", f"""{RECIPIENT}
Bremen, 06.06.2022
Krankenzusatzversicherung - Mitgliedsnummer 0099 8877
Ihr Beitrag ab 01.07.2022: 33,40 € monatlich
Hanseatische Krankenkasse VVaG · Sögestraße 11 · 28195 Bremen
""", "schwierig")

add("Hagelversicherung", "VH-5544-3322", f"""Finanzberatung Müller & Partner
Marktstraße 5, 20095 Hamburg
{RECIPIENT}
Hamburg, 09.09.2021
Ihre Gebäudeversicherung bei der Vereinigten Hagelversicherung VVaG
Versicherungsschein VH-5544-3322 - Beginn 01.10.2021
Jahresbeitrag 301,00 €
""", "schwierig")
