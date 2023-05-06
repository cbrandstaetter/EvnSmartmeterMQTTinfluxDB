This is based on the outdated documentation from Noe-Netze:
https://www.netz-noe.at/Download-(1)/Smart-Meter/218_9_SmartMeter_Kundenschnittstelle_lektoriert_14.aspx
The dcumentation is dated "3. Auflage, März 2022" at the moment.

| Length (bytes) | Byte Range | Length (hex encode) | Range in the hex encoded string | Purpose                                       |
|----------------|------------|---------------------|---------------------------------|-----------------------------------------------|
| 4              | 1-4        | 8                   | 1-8                             | M-Bus start                                   |
| 7              | 5-11       | 14                  | 9-22                            | unclear at the moment always "53ff000167db08" |
| 8              | 12-19      | 16                  | 23-38                           | System Title                                  |
| 3              | 20-22      | 6                   | 39-44                           | unclear at the moment always "81f820"         |
| 4              | 23-26      | 8                   | 45-52                           | Frame Counter                                 |
| 230            | 27-256     | 460                 | 53-512                          | Encrypted Data                                |
| 24             | 257-280    | 48                  | 513-560                         | unclear                                       |
| 1              | 281        | 2                   | 561-562                         | Checksum (but does not validate)              |
| 1              | 282        | 2                   | 563-564                         | M-Bus End "16"                                |

