# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Passwords that appear at the top of every public breach list. Checked offline
(no request to an external "have I been pwned" service - that would tell a third
party about every password change) against new passwords, lower-cased, with
trailing digits and symbols stripped so that "Passwort123!" is caught as well."""

COMMON_PASSWORDS = frozenset("""
password passwort passw0rd passwd pass1234 password1 password12 password123 password1234 pa55word pa55w0rd
123456 1234567 12345678 123456789 1234567890 12345 1234 123123 111111 000000 654321 987654321 121212 112233 123321
qwerty qwertz qwertyuiop qwertzuiop qwerty123 qwertz123 qwerty1 qwertzu asdfgh asdfghjk asdfghjkl asdf1234 asdfasdf
yxcvbn yxcvbnm zxcvbn zxcvbnm 1q2w3e4r 1q2w3e 1qaz2wsx q1w2e3r4 qazwsx qazwsxedc abc123 abcd1234 abcdefg abcdefgh abcdef
iloveyou ichliebedich liebe ichliebedir schatz schatzi schatzi1 sonnenschein spatz mausi maus hase hasi bärchen baerchen
hallo hallo123 hallo1234 hallo12345 hello hello123 hello1234 welcome welcome1 willkommen willkommen1 guten gutentag
admin admin123 admin1234 administrator adminadmin root toor test test123 test1234 testtest guest user user123 login master
letmein monkey dragon football fussball fussball1 bayern bayernmuenchen borussia hamburg berlin muenchen koeln schalke
baseball basketball hockey soccer batman superman spiderman starwars pokemon naruto minecraft fortnite
sunshine princess flower shadow michael jennifer jordan hunter buster killer tigger charlie daniel thomas robert
andreas michael1 stefan sebastian alexander christian markus thomas1 michael123 daniela sabine sandra claudia
sommer winter fruehling herbst sommer2020 sommer2021 sommer2022 sommer2023 sommer2024 sommer2025 winter2020 winter2021
winter2022 winter2023 winter2024 winter2025 herbst2023 herbst2024 fruehling2024 passwort2020 passwort2021 passwort2022
passwort2023 passwort2024 passwort2025 password2020 password2021 password2022 password2023 password2024 password2025
geheim geheim123 geheimnis meinpasswort meinpasswort1 mypassword mypass secret secret123 changeme changeme123 change123
default trustno1 whatever freedom cheese pepper ginger summer winter spring autumn internet computer laptop
versicherung versicherung1 versicherungen noxus noxuspolicy versicherungsmanager policy police
aaaaaa aaaaaaaa aaaa1111 zzzzzzzz xxxxxxxx qqqqqqqq 11111111 22222222 00000000 12341234 11223344 1234abcd abcd1234abcd
""".split())

_TRAILING = "0123456789!?.#*+-_ "


def is_common_password(password: str) -> bool:
    folded = password.strip().lower()
    if folded in COMMON_PASSWORDS:
        return True
    stripped = folded.rstrip(_TRAILING)
    return len(stripped) >= 4 and stripped in COMMON_PASSWORDS
