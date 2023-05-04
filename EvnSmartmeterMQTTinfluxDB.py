#!/usr/bin/python3
import serial
import time
from binascii import unhexlify
import sys
import string
import paho.mqtt.client as mqtt
from gurux_dlms.GXDLMSTranslator import GXDLMSTranslator
from bs4 import BeautifulSoup
from influxdb import InfluxDBClient
from Cryptodome.Cipher import AES
import xml.etree.ElementTree as ET
from time import sleep

# EVN Schlüssel eingeben zB. "36C66639E48A8CA4D6BC8B282A793BBB"
evn_schluessel = ""

#MQTT Verwenden (True | False)
useMQTT = True
mqttBroker = "hostname1.localdomain.at"
mqttuser =""
mqttpasswort = ""
mqttport = 1883

#influxDB aktivieren
useInfluxDB = True
influxHost = "hostname1.localdomain.at"
influxPort = 8086
influxDatabase = 'Smartmeter'

#Comport Config
comport = "/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_CKA9t114J20-if00-port0"

#Aktuelle Werte auf Console ausgeben (True | False)
printValue = True

octet_string_values = {}
octet_string_values['0100010800FF'] = 'WirkenergieP'
octet_string_values['0100020800FF'] = 'WirkenergieN'
octet_string_values['0100010700FF'] = 'MomentanleistungP'
octet_string_values['0100020700FF'] = 'MomentanleistungN'
octet_string_values['0100200700FF'] = 'SpannungL1'
octet_string_values['0100340700FF'] = 'SpannungL2'
octet_string_values['0100480700FF'] = 'SpannungL3'
octet_string_values['01001F0700FF'] = 'StromL1'
octet_string_values['0100330700FF'] = 'StromL2'
octet_string_values['0100470700FF'] = 'StromL3'
octet_string_values['01000D0700FF'] = 'Leistungsfaktor'

def evn_decrypt(frame, evn_schluessel, systemTitel, frameCounter):
    frame = unhexlify(frame)
    encryption_key = unhexlify(evn_schluessel)
    init_vector = unhexlify(systemTitel + frameCounter)
    cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=init_vector)
    return cipher.decrypt(frame).hex()

# MQTT Init
if useMQTT:
    try:
        client = mqtt.Client("SmartMeter")
        client.username_pw_set(mqttuser, mqttpasswort)
        client.connect(mqttBroker, mqttport)
    except:
        print("Die Ip Adresse des Brokers ist falsch!")
        sys.exit()

# InfluxDB Init
if useInfluxDB:
    try:
        influx = InfluxDBClient(host=influxHost, port=influxPort, database=influxDatabase)
    except Exception as err:
        print("Kann nicht mit InfluxDB verbinden!")
        print()
        print("Fehler: ", format(err))
        sys.exit()

tr = GXDLMSTranslator()
ser = serial.Serial( port=comport,
         baudrate=2400,
         bytesize=serial.EIGHTBITS,
         parity=serial.PARITY_NONE,
         stopbits=serial.STOPBITS_ONE
)


while 1:
    print("===================== reading fresh data ======================")
    daten = ser.read(size=282).hex()

    print("Daten: ",daten)
    mbusstart = daten[0:8]
    print("mbusstart: ",mbusstart," len(hex)=",len(mbusstart)," strlen=",int(len(mbusstart)/2))
    if mbusstart[0:2] == "68" and mbusstart[2:4] == mbusstart[4:6] and mbusstart[6:8] == "68" :
        print("ok")
    else:
        print("wrong M-Bus Start, restarting")
        sys.exit()

    frameLen=int("0x" + mbusstart[2:4],16)
    print("frameLen: ",frameLen)

    systemTitel = daten[22:38]
    print("systemTitel: ",systemTitel," len(hex)=",len(systemTitel)," strlen=",int(len(systemTitel)/2))
    frameCounter = daten[44:52]
    print("frameCounter: ",frameCounter," len(hex)=",len(frameCounter)," strlen=",int(len(frameCounter)/2)," = (int) ",int(frameCounter,16))
    frame = daten[52:12+frameLen*2]
    print("frame len(hex)=",len(frame)," strlen=",int(len(frame)/2))
#    print("frame: ",frame)

    apdu = evn_decrypt(frame,evn_schluessel,systemTitel,frameCounter)
    if apdu[0:6] != "0f8000" :
        continue
    else:
        print("apdu is fine: ",apdu)
    try:
        xml = tr.pduToXml(apdu,)
#        print("xml: ",xml)

        root = ET.fromstring(xml)
        found_lines = []
        momentan = []

        items = list(root.iter())
        for i, child in enumerate(items):
            if child.tag == 'OctetString' and 'Value' in child.attrib:
                value = child.attrib['Value']
                if value in octet_string_values.keys():
                    if ('Value' in items[i+1].attrib):
                        if value in ['0100010700FF', '0100020700FF']:
                            # special handling for momentanleistung
                            momentan.append(int(items[i+1].attrib['Value'], 16))
                        found_lines.append({'key': octet_string_values[value], 'value': int(items[i+1].attrib['Value'], 16)});

#        print(found_lines)
    except BaseException as err:
        #print("APU: ", format(apdu))
        print("Fehler: ", format(err))
        continue;

    try:
        if len(momentan) == 2:
            found_lines.append({'key': 'Momentanleistung', 'value': momentan[0]-momentan[1]})

        for element in found_lines:
            #ConsoleText
            #if printValue:
            #    print(element['key']+ ': '+ str(element['value']))

            if element['key'] == "WirkenergieP":
               WirkenergieP = element['value']/1000
            if element['key'] == "WirkenergieN":
               WirkenergieN = element['value']/1000

            if element['key'] == "MomentanleistungP":
               MomentanleistungP = element['value']
            if element['key'] == "MomentanleistungN":
               MomentanleistungN = element['value']

            if element['key'] == "SpannungL1":
               SpannungL1 = element['value']*0.1
            if element['key'] == "SpannungL2":
               SpannungL2 = element['value']*0.1
            if element['key'] == "SpannungL3":
               SpannungL3 = element['value']*0.1

            if element['key'] == "StromL1":
               StromL1 = element['value']*0.01
            if element['key'] == "StromL2":
               StromL2 = element['value']*0.01
            if element['key'] == "StromL3":
               StromL3 = element['value']*0.01

            if element['key'] == "Leistungsfaktor":
               Leistungsfaktor = element['value']*0.001

    except BaseException as err:
        print("Fehler: ", format(err))
        continue;


    try:
        if printValue:
            print('Wirkenergie+: ' + str(WirkenergieP))
            print('Wirkenergie-: ' + str(WirkenergieN))
            print('MomentanleistungP+: ' + str(MomentanleistungP))
            print('MomentanleistungP-: ' + str(MomentanleistungN))
            print('Spannung L1: ' + str(SpannungL1))
            print('Spannung L2: ' + str(SpannungL2))
            print('Spannung L3: ' + str(SpannungL3))
            print('Strom L1: ' + str(StromL1))
            print('Strom L2: ' + str(StromL2))
            print('Strom L3: ' + str(StromL3))
            print('Leistungsfaktor: ' + str(Leistungsfaktor))
            print('Momentanleistung: ' + str(MomentanleistungP-MomentanleistungN))


        #MQTT
        if useMQTT:
            client.publish("Smartmeter/WirkenergieP",WirkenergieP)
            client.publish("Smartmeter/WirkenergieN",WirkenergieN)
            client.publish("Smartmeter/MomentanleistungP",MomentanleistungP)
            client.publish("Smartmeter/MomentanleistungN",MomentanleistungN)
            client.publish("Smartmeter/Momentanleistung",MomentanleistungP - MomentanleistungN)
            client.publish("Smartmeter/SpannungL1",SpannungL1)
            client.publish("Smartmeter/SpannungL2",SpannungL2)
            client.publish("Smartmeter/SpannungL3",SpannungL3)
            client.publish("Smartmeter/StromL1",StromL1)
            client.publish("Smartmeter/StromL2",StromL2)
            client.publish("Smartmeter/StromL3",StromL3)
            client.publish("Smartmeter/Leistungsfaktor",Leistungsfaktor)

        if useInfluxDB:
            mytime = int(time.time()*1000000000)
            json_body = [
            {
                "measurement": "Wirkenergie",
                "fields": {
                    "P": WirkenergieP,
                    "N": WirkenergieN
                },
                "time": mytime
            },
            {
                "measurement": "Momentanleistung",
                "fields": {
                    "P": MomentanleistungP,
                    "N": MomentanleistungN,
                    "value": MomentanleistungP-MomentanleistungN
                },
                "time": mytime
            },
            {
                "measurement": "Spannung",
                "fields": {
                    "L1": SpannungL1,
                    "L2": SpannungL2,
                    "L3": SpannungL3,
                },
                "time": mytime
            },
            {
                "measurement": "Strom",
                "fields": {
                    "L1": StromL1,
                    "L2": StromL2,
                    "L3": StromL3,
                },
                "time": mytime
            },
            {
                "measurement": "Leistungsfaktor",
                "fields": {
                    "value": Leistungsfaktor
                },
                "time": mytime
            }
            ]
            print("writing to influxDB")
            print(json_body)
            influx.write_points(json_body)
            print("finished influxDB")

    except BaseException as err:
        print("Es ist ein Fehler aufgetreten.")
        print()
        print("Fehler: ", format(err))

        sys.exit()
