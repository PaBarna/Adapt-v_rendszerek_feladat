#encoding: utf-8

import time
from Client import SocketClient
import json
import numpy as np
import Config


# NaiveHunter stratégia implementációja távoli eléréshez.
class RemoteAdmin:

    # Az egyetlen kötelező elem: A játékmestertől jövő információt feldolgozó és választ elküldő függvény
    def processObservation(self, fulljson, sendData):
        """
        :param fulljson: A játékmestertől érkező JSON dict-be konvertálva.
        Két kötelező kulccsal: 'type' (leaderBoard, readyToStart, started, gameData, serverClose) és 'payload' (az üzenet adatrésze).
        'leaderBoard' type a játék végét jelzi, a payload tartalma {'ticks': a játék hossza tickekben, 'players':[{'name': jáétékosnév, 'active': él-e a játékos?, 'maxSize': a legnagyobb elért méret a játék során},...]}
        'readyToStart' type esetén a szerver az indító üzenetre vár esetén, a payload üres (None)
        'started' type esetén a játék elindul, tickLength-enként kiküldés és akciófogadás várható payload {'tickLength': egy tick hossza }
        'gameData' type esetén az üzenet a játékos által elérhető információkat küldi, a payload:
                                    {"pos": abszolút pozíció a térképen, "tick": az aktuális tick sorszáma, "active": a saját életünk állapota,
                                    "size": saját méret,
                                    "leaderBoard": {'ticks': a játék hossza tickekben eddig, 'players':[{'name': jáétékosnév, 'active': él-e a játékos?, 'maxSize': a legnagyobb elért méret a játék során eddig},...]},
                                    "vision": [{"relative_coord": az adott megfigyelt mező relatív koordinátája,
                                                                    "value": az adott megfigyelt mező értéke (0-3,9),
                                                                    "player": None, ha nincs aktív játékos, vagy
                                                                            {name: a mezőn álló játékos neve, size: a mezőn álló játékos mérete}},...] }
        'serverClose' type esetén a játékmester szabályos, vagy hiba okozta bezáródásáról értesülünk, a payload üres (None)
        :param sendData: A kliens adatküldő függvénye, JSON formátumú str bemenetet vár, melyet a játékmester felé továbbít.
        Az elküldött adat struktúrája {"command": Parancs típusa, "name": A küldő azonosítója, "payload": az üzenet adatrésze}
        Elérhető parancsok:
        'SetName' A kliens felregisztrálja a saját nevét a szervernek, enélkül a nevünkhöz tartozó üzenetek nem térnek vissza.
                 Tiltott nevek: a configban megadott játékmester név és az 'all'.
        'SetAction' Ebben az esetben a payload az akció string, amely két karaktert tartalmaz az X és az Y koordináták (matematikai mátrix indexelés) menti elmozdulásra.
                a karakterek értékei '0': helybenmaradás az adott tengely mentén, '+' pozitív irányú lépés, '-' negatív irányú lépés lehet. Amennyiben egy tick ideje alatt
                nem külünk értéket az alapértelmezett '00' kerül végrehajtásra.
        'GameControl' üzeneteket csak a Config.py-ban megadott játékmester névvel lehet küldeni, ezek a játékmenetet befolyásoló üzenetek.
                A payload az üzenet típusát (type), valamint az ahhoz tartozó 'data' adatokat kell, hogy tartalmazza.
                    'start' type elindítja a játékot egy "readyToStart" üzenetet küldött játék esetén, 'data' mezője üres (None)
                    'reset' type egy játék után várakozó 'leaderBoard'-ot küldött játékot állít alaphelyzetbe. A 'data' mező
                            {'mapPath':None, vagy elérési útvonal, 'updateMapPath': None, vagy elérési útvonal} formátumú, ahol None
                            esetén az előző pálya és növekedési map kerül megtartásra, míg elérési útvonal megadása esetén új pálya kerül betöltésre annak megfelelően.
                    'interrupt' type esetén a 'data' mező üres (None), ez megszakítja a szerver futását és szabályosan leállítja azt.
        :return:
        """

        # Játék rendezéssel kapcsolatos üzenetek lekezelése
        if fulljson["type"] == "leaderBoard":
            print("Game finished after",fulljson["payload"]["ticks"],"ticks!")
            print("Leaderboard:")
            for score in fulljson["payload"]["players"]:
                print(score["name"],score["active"], score["maxSize"])

            time.sleep(50)
            sendData(json.dumps({"command": "GameControl", "name": "master",
                                 "payload": {"type": "reset", "data": {"mapPath": None, "updateMapPath": None}}}))

        if fulljson["type"] == "readyToStart":
            print("Game is ready, starting in 5")
            time.sleep(5)
            sendData(json.dumps({"command": "GameControl", "name": "master",
                                 "payload": {"type": "start", "data": None}}))

        if fulljson["type"] == "started":
            print("Startup message from server.")
            print("Ticks interval is:",fulljson["payload"]["tickLength"])



if __name__=="__main__":
    # Példányosított stratégia objektum
    admin = RemoteAdmin()

    # Socket kliens, melynek a szerver címét kell megadni (IP, port), illetve a callback függvényt, melynek szignatúrája a fenti
    # callback(fulljson, sendData)
    client = SocketClient("localhost", 42069, admin.processObservation)

    # Kliens indítása
    client.start()
    # Kis szünet, hogy a kapcsolat felépülhessen, a start nem blockol, a kliens külső szálon fut
    time.sleep(0.1)
    # Regisztráció a megfelelő névvel
    client.sendData(json.dumps({"command": "SetName", "name": Config.GAMEMASTER_NAME, "payload": None}))

    # Nincs blokkoló hívás, a főszál várakozó állapotba kerül, itt végrehajthatók egyéb műveletek a kliens automata működésétől függetlenül.