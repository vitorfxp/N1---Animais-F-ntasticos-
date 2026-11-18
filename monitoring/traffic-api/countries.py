"""Nome do país (inglês, como vem do DB-IP) -> código ISO 3166-1 alpha-2.
O GeoIP do Promtail não exporta o código do país, só o nome; o site usa o código para bandeira
e para traduzir o nome (Intl.DisplayNames)."""

_RAW = """
AF Afghanistan|AL Albania|DZ Algeria|AS American Samoa|AD Andorra|AO Angola|AI Anguilla|AQ Antarctica|
AG Antigua and Barbuda|AR Argentina|AM Armenia|AW Aruba|AU Australia|AT Austria|AZ Azerbaijan|BS Bahamas|
BS The Bahamas|BH Bahrain|BD Bangladesh|BB Barbados|BY Belarus|BE Belgium|BZ Belize|BJ Benin|BM Bermuda|
BT Bhutan|BO Bolivia|BA Bosnia and Herzegovina|BA Bosnia & Herzegovina|BW Botswana|BR Brazil|
IO British Indian Ocean Territory|VG British Virgin Islands|BN Brunei|BN Brunei Darussalam|BG Bulgaria|
BF Burkina Faso|BI Burundi|CV Cabo Verde|CV Cape Verde|KH Cambodia|CM Cameroon|CA Canada|KY Cayman Islands|
CF Central African Republic|TD Chad|CL Chile|CN China|CO Colombia|KM Comoros|CG Congo|CG Republic of the Congo|
CD DR Congo|CD Democratic Republic of the Congo|CD Congo (Kinshasa)|CG Congo (Brazzaville)|CK Cook Islands|
CR Costa Rica|CI Ivory Coast|CI Côte d'Ivoire|CI Cote d'Ivoire|HR Croatia|CU Cuba|CW Curaçao|CW Curacao|
CY Cyprus|CZ Czechia|CZ Czech Republic|DK Denmark|DJ Djibouti|DM Dominica|DO Dominican Republic|EC Ecuador|
EG Egypt|SV El Salvador|GQ Equatorial Guinea|ER Eritrea|EE Estonia|SZ Eswatini|SZ Swaziland|ET Ethiopia|
FK Falkland Islands|FO Faroe Islands|FJ Fiji|FI Finland|FR France|GF French Guiana|PF French Polynesia|
GA Gabon|GM Gambia|GM The Gambia|GE Georgia|DE Germany|GH Ghana|GI Gibraltar|GR Greece|GL Greenland|
GD Grenada|GP Guadeloupe|GU Guam|GT Guatemala|GG Guernsey|GN Guinea|GW Guinea-Bissau|GY Guyana|HT Haiti|
HN Honduras|HK Hong Kong|HU Hungary|IS Iceland|IN India|ID Indonesia|IR Iran|IQ Iraq|IE Ireland|
IM Isle of Man|IL Israel|IT Italy|JM Jamaica|JP Japan|JE Jersey|JO Jordan|KZ Kazakhstan|KE Kenya|KI Kiribati|
XK Kosovo|KW Kuwait|KG Kyrgyzstan|LA Laos|LV Latvia|LB Lebanon|LS Lesotho|LR Liberia|LY Libya|
LI Liechtenstein|LT Lithuania|LU Luxembourg|MO Macao|MO Macau|MG Madagascar|MW Malawi|MY Malaysia|MV Maldives|
ML Mali|MT Malta|MH Marshall Islands|MQ Martinique|MR Mauritania|MU Mauritius|YT Mayotte|MX Mexico|
FM Micronesia|MD Moldova|MD Republic of Moldova|MC Monaco|MN Mongolia|ME Montenegro|MS Montserrat|MA Morocco|
MZ Mozambique|MM Myanmar|MM Myanmar (Burma)|NA Namibia|NR Nauru|NP Nepal|NL Netherlands|NL The Netherlands|
NC New Caledonia|NZ New Zealand|NI Nicaragua|NE Niger|NG Nigeria|KP North Korea|MK North Macedonia|
MK Macedonia|MP Northern Mariana Islands|NO Norway|OM Oman|PK Pakistan|PW Palau|PS Palestine|PA Panama|
PG Papua New Guinea|PY Paraguay|PE Peru|PH Philippines|PL Poland|PT Portugal|PR Puerto Rico|QA Qatar|
RE Réunion|RE Reunion|RO Romania|RU Russia|RU Russian Federation|RW Rwanda|KN Saint Kitts and Nevis|
LC Saint Lucia|VC Saint Vincent and the Grenadines|WS Samoa|SM San Marino|ST Sao Tome and Principe|
ST São Tomé and Príncipe|SA Saudi Arabia|SN Senegal|RS Serbia|SC Seychelles|SL Sierra Leone|SG Singapore|
SX Sint Maarten|SK Slovakia|SI Slovenia|SB Solomon Islands|SO Somalia|ZA South Africa|KR South Korea|
KR Korea|KR Republic of Korea|SS South Sudan|ES Spain|LK Sri Lanka|SD Sudan|SR Suriname|SE Sweden|
CH Switzerland|SY Syria|TW Taiwan|TJ Tajikistan|TZ Tanzania|TH Thailand|TL Timor-Leste|TL East Timor|TG Togo|
TO Tonga|TT Trinidad and Tobago|TN Tunisia|TR Turkey|TR Türkiye|TM Turkmenistan|TC Turks and Caicos Islands|
TV Tuvalu|UG Uganda|UA Ukraine|AE United Arab Emirates|GB United Kingdom|US United States|
VI U.S. Virgin Islands|UY Uruguay|UZ Uzbekistan|VU Vanuatu|VA Vatican City|VE Venezuela|VN Vietnam|
VN Viet Nam|YE Yemen|ZM Zambia|ZW Zimbabwe|SG Republic of Singapore|LU Grand Duchy of Luxembourg|
BQ Bonaire, Sint Eustatius, and Saba|AX Åland|AX Aland Islands|EH Western Sahara|BL Saint Barthélemy|
MF Saint Martin|PM Saint Pierre and Miquelon|SH Saint Helena|WF Wallis and Futuna|NU Niue|NF Norfolk Island|
CX Christmas Island|CC Cocos (Keeling) Islands|TK Tokelau|PN Pitcairn Islands|SJ Svalbard and Jan Mayen|
UM U.S. Outlying Islands|GS South Georgia and the South Sandwich Islands|TF French Southern Territories|
HM Heard Island and McDonald Islands|BV Bouvet Island
"""

CODES = {}
for item in _RAW.replace("\n", "").split("|"):
    item = item.strip()
    if item:
        code, name = item.split(" ", 1)
        CODES[name.strip().lower()] = code


def code_for(name):
    return CODES.get((name or "").strip().lower(), "")
