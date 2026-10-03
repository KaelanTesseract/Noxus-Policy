# Drittanbieter-Hinweise

Zettelfrieden selbst steht unter der [MIT-Lizenz](LICENSE), Copyright (c) 2026 Dennis Guse. Die Anwendung baut auf freier Software und Schriften Dritter auf. Diese Datei nennt sie mit Lizenz und Urheber und enthält die Lizenztexte, die beim Weitergeben mitgeliefert werden müssen. Die Abhängigkeiten werden beim Bauen aus den Paketquellen (npm, PyPI, Debian) installiert; jedes Paket bringt seine eigene Lizenzdatei mit.

## Direkte Abhängigkeiten

### Frontend (npm)

| Paket | Lizenz | Urheber |
| :--- | :--- | :--- |
| Next.js | MIT | Vercel, Inc. |
| React, React DOM | MIT | Meta Platforms, Inc. and affiliates |
| Base UI (`@base-ui/react`) | MIT | MUI / Material-UI SAS |
| Tailwind CSS, `@tailwindcss/postcss` | MIT | Tailwind Labs, Inc. |
| tailwindcss-animate | MIT | Jamie Kyle |
| tw-animate-css | MIT | Wombosvideo |
| tailwind-merge | MIT | Dany Castillo |
| clsx | MIT | Luke Edwards |
| class-variance-authority | Apache-2.0 | Joe Bell |
| qrcode-generator | MIT | Kazuhiko Arase |
| Lucide (`lucide-react`) | ISC (einzelne Symbole MIT) | Lucide Icons and Contributors, Cole Bemis |
| GSAP (`gsap`) | GreenSock Standard "No Charge" License | GreenSock, Inc. |
| Fraunces (`@fontsource-variable/fraunces`) | SIL OFL 1.1 | The Fraunces Project Authors |
| Instrument Sans (`@fontsource-variable/instrument-sans`) | SIL OFL 1.1 | The Instrument Sans Project Authors |

Nur zum Entwickeln und Bauen, nicht Teil der ausgelieferten Anwendung: TypeScript (Apache-2.0), ESLint, eslint-config-next, `@types/*` (alle MIT) und das shadcn-CLI (MIT).

### Backend (PyPI)

| Paket | Lizenz |
| :--- | :--- |
| FastAPI, SQLAlchemy, Pydantic, PyJWT, pdf2image | MIT |
| Starlette, Uvicorn, HTTPX, python-dotenv, pypdf | BSD-3-Clause |
| bcrypt, python-multipart, pytesseract | Apache-2.0 |
| cryptography | Apache-2.0 oder BSD-3-Clause |
| Pillow | MIT-CMU (HPND) |
| email-validator | Unlicense (gemeinfrei) |

Nur für die Tests: pytest (MIT).

### Programme im Docker-Image

Poppler (`pdftotext`, `pdftoppm`; GPL-2.0-or-later) und Tesseract OCR samt deutschem Sprachpaket (Apache-2.0) kommen als Debian-Pakete ins Backend-Image. Sie werden als eigenständige Programme über die Kommandozeile gestartet und nicht in den Python-Code eingebunden oder mit ihm gelinkt; der Quellcode von Zettelfrieden bleibt dadurch unter der MIT-Lizenz. Ihre Quelltexte und Lizenzen liefert Debian mit (`/usr/share/doc/<paket>/copyright` im Image).

## Hinweise zu einzelnen Lizenzen

- **GSAP** steht nicht unter einer Open-Source-Lizenz, darf aber laut der [GreenSock-Standardlizenz](https://gsap.com/standard-license) kostenlos auch kommerziell verwendet werden. Ausgenommen ist die Verwendung in Werkzeugen, die Dritten das visuelle Gestalten von Animationen ermöglichen und damit mit Webflow konkurrieren. Das trifft auf Zettelfrieden nicht zu. Der Code von Zettelfrieden bleibt MIT-lizenziert; GSAP wird als unveränderte Bibliothek eingebunden und nicht Teil des MIT-Codes.
- **Next.js** installiert für die Bildoptimierung optional `sharp`, das die Bibliothek libvips (LGPL-3.0-or-later) als eigene, austauschbare Binärdatei mitbringt. Zettelfrieden verwendet sie unverändert und nur über Next.js.
- **caniuse-lite** (Browserdaten, über die Next.js-Werkzeuge installiert) steht unter CC-BY-4.0 (Daten von Can I Use, https://caniuse.com, Paket von Ben Briggs) und wird nur beim Bauen verwendet.
- **Schriften:** Fraunces und Instrument Sans werden über Fontsource selbst gehostet (keine Anfrage an Google-Server). Die Schriften dürfen frei genutzt, mitgeliefert und eingebettet werden, aber nicht allein verkauft; die Lizenztexte stehen unten.
- **Unternehmenslogos:** Die Logos der Versicherer lädt der Server auf Wunsch über den Favicon-Dienst von Google nach (siehe README). Marken und Logos bleiben Eigentum der jeweiligen Unternehmen und sind nicht Teil dieses Projekts.

## Von shadcn/ui abgeleiteter Code

Die Dateien in `frontend/src/components/ui/` gehen auf Komponenten von [shadcn/ui](https://ui.shadcn.com) zurück:

```text
MIT License

Copyright (c) 2023 shadcn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Lucide

```text
ISC License

Copyright (c) 2026 Lucide Icons and Contributors

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

---

The following Lucide icons are derived from the Feather project:

airplay, alert-circle, alert-octagon, alert-triangle, aperture, arrow-down-circle, arrow-down-left, arrow-down-right, arrow-down, arrow-left-circle, arrow-left, arrow-right-circle, arrow-right, arrow-up-circle, arrow-up-left, arrow-up-right, arrow-up, at-sign, calendar, cast, check, chevron-down, chevron-left, chevron-right, chevron-up, chevrons-down, chevrons-left, chevrons-right, chevrons-up, circle, clipboard, clock, code, columns, command, compass, corner-down-left, corner-down-right, corner-left-down, corner-left-up, corner-right-down, corner-right-up, corner-up-left, corner-up-right, crosshair, database, divide-circle, divide-square, dollar-sign, download, external-link, feather, frown, hash, headphones, help-circle, info, italic, key, layout, life-buoy, link-2, link, loader, lock, log-in, log-out, maximize, meh, minimize, minimize-2, minus-circle, minus-square, minus, monitor, moon, more-horizontal, more-vertical, move, music, navigation-2, navigation, octagon, pause-circle, percent, plus-circle, plus-square, plus, power, radio, rss, search, server, share, shopping-bag, sidebar, smartphone, smile, square, table-2, tablet, target, terminal, trash-2, trash, triangle, tv, type, upload, x-circle, x-octagon, x-square, x, zoom-in, zoom-out

The MIT License (MIT) (for the icons listed above)

Copyright (c) 2013-present Cole Bemis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Schriften

### Fraunces

```text
Copyright 2020 The Fraunces Project Authors (github.com/undercasetype/Fraunces) Fraunces-Italic[SOFT,WONK,opsz,wght].ttf: Copyright 2020 The Fraunces Project Authors (github.com/undercasetype/Fraunces)

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied below, and is also available with a FAQ at:
http://scripts.sil.org/OFL


-----------------------------------------------------------
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded,
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical
writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless explicit written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
OTHER DEALINGS IN THE FONT SOFTWARE.
```

### Instrument Sans

```text
Copyright 2022 The Instrument Sans Project Authors (https://github.com/Instrument/instrument-sans) InstrumentSans-Italic[wdth,wght].ttf: Copyright 2022 The Instrument Sans Project Authors (https://github.com/Instrument/instrument-sans)

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied below, and is also available with a FAQ at:
http://scripts.sil.org/OFL


-----------------------------------------------------------
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded,
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical
writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless explicit written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
OTHER DEALINGS IN THE FONT SOFTWARE.
```
