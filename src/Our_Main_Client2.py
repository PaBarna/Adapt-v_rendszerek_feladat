#encoding: utf-8
import numpy as np
import json
import torch
import time
from torch import nn
from torch import optim
from numpy.random import choice 
from datetime import datetime 
from Client import SocketClient
import os
import pathlib
import sys

#-----------------------------------Relatív elérés---------------------------------------------------------------------------------------------------

current_working_dir=os.getcwd()
print(current_working_dir)

maps_folder = os.path.join(current_working_dir, "maps\\")
print(maps_folder)

models_folder = os.path.join(current_working_dir, "models\\")
print(models_folder)

log_folder = os.path.join(current_working_dir, "log\\","error_log.json")
print(log_folder)

tanitas_betoltes = os.path.join(current_working_dir, "models\\","model3.p")
print(tanitas_betoltes)


akciok = ["00","0-","0+","+0","+-","++","-0","--","-+"]
#palyak_elerese  = r"C:/Users/Martin/OneDrive/Asztali gép/adaptivegame-main/src/maps/"
palyak_elerese = maps_folder
palyak = ["03_blockade.txt", "04_mirror.txt","05_labirint.txt"]

Tanitas = False
#------------------------------------Stratégia neurális hálóval--------------------------------------------------------------------------------------------
class RemoteStrategy:
    def __init__(self, n_epizod, batchek_merete, tan_rata):
        self.epizodok_szama = n_epizod
        self.batchek_merete = batchek_merete
        self.tanulasi_rata = tan_rata
        # Változók definíciója a dinamikus működéshez
        self.legutobb_jatszott_palya = "03_blockade.txt"
        self.utolso_meret = 5
        self.utolso_aktiv = True
        self.uccso_pozicio = None
        self.minden_pozicio = []
        self.utolso_vegrehajtott_akcio = None
        self.legutobbi_allapota = None


        # Validációs adatok
        self.minden_palya = []
        self.osszes_jutalom = []
        self.vegso_meret = []


        #Tanító adatok 
        self.allapotok = []
        self.jutalmak = []
        self.akciok = []
        self.batch_jutalmak = []
        self.batch_akciok = []
        self.batch_allapot = []

        self.epoch_szamlaloja = 1
        self.batch_szamlaloja = 0

        self.network = nn.Sequential(
            nn.Linear(81, 512),
            nn.ReLU(), 
            nn.Linear(512, 128), 
            nn.ReLU(), 
            nn.Linear(128, 64), 
            nn.ReLU(), 
            nn.Linear(64, 9), 
            nn.Softmax(dim=-1))
        
            #nn.Linear(81, 256),
            #nn.ReLU(), 
            #nn.Linear(256, 128), 
            #nn.ReLU(), 
            #nn.Linear(128, 128),
            #nn.ReLU(),
            #nn.Linear(128, 32), 
            #nn.ReLU(), 
            #nn.Linear(32, 9), 
            #nn.Softmax(dim=-1))
            
            #nn.Linear(81, 256),
            #nn.ReLU(), 
            #nn.Linear(256, 128), 
            #nn.ReLU(), 
            #nn.Linear(128, 64),
            #nn.ReLU(),
            #nn.Linear(64, 32), 
            #nn.ReLU(), 
            #nn.Linear(32, 9), 
            #nn.Softmax(dim=-1))

        self.optimizer = optim.Adam(self.network.parameters(),lr=self.tanulasi_rata)
        
    # Előretekintés az ágens jelenlegi állapota alapján
    def predikcio(self, allapot):
        akcio_leh = self.network(torch.FloatTensor(allapot))
        return akcio_leh

    # Játék Újraindítása
    def jatek_ujrainditasa(self, sendDataFunc, next_map_path):
        sendDataFunc(json.dumps({"command": "GameControl", "name": "master",
                                        "payload": {"type": "reset", "data": {"mapPath": str(palyak_elerese) + str(next_map_path[0]), "updateMapPath": None}}}))
    # Játék megszakítása
    def jatek_megszakitasa(self, sendDataFunc):
        sendDataFunc(json.dumps({"command": "GameControl", "name": "master","payload": {"type": "interrupt", "data": None}}))

    # Leszámított jutalmak 
    def leszamitott_jutalmak(self, j, gamma=0.99):
        lesz_jut = np.zeros_like(j)
        futo_os = 0
        for t in reversed(range(len(j))):
            futo_os = futo_os * gamma + j[t]
            lesz_jut[t] = futo_os
        return lesz_jut

    # Átkonvertáljuk az akciót stringből
    def akcio_konverzio_stringbol(self, action_string):
        vissza = []
        for act in akciok:
            if(act == action_string):
                vissza.append(1)
            else:
                vissza.append(0)
        return vissza

    # Modellünk elmentése
    def modellmentes(self):
        torch.save(self.network.state_dict(),r"model4"+'.p')


#------------------------------------Jutalom--------------------------------------------------------------------------------------------
    # Jutalmak kiszámítása
    def jutalom_szamitas(self, jsonData, mult_a = 10):
        #Legutolsó elvégzett akció jutalmazása
        jutalom = 0
        if(not jsonData["active"]):
            #Ha meghal, megbüntetjük
            jutalom = -10
        else:
            jutalom = jsonData["size"] - 0.1*self.utolso_meret
            if(self.uccso_pozicio != jsonData["pos"] and self.uccso_pozicio != None):
                jutalom+=0.02
        # Pozíció jutalmazása
        pozicio_jutalmazasa = 0
        if(len(self.minden_pozicio)>mult_a):
            pozicio_jutalmazasa = 0.07 * np.max(np.absolute(np.mean(self.minden_pozicio[-mult_a:],0) - self.minden_pozicio[-mult_a]))       
        return jutalom+pozicio_jutalmazasa
#------------------------------------Betanítás (autom. pálya váltás)----------------------------------------------------------------------
    # Tanító lépés
    def tanito_lepes(self):
        self.optimizer.zero_grad()

        allapot_tenzor = torch.FloatTensor(np.array(self.batch_allapot))
        jutalom_tenzor = torch.FloatTensor(np.array(self.batch_jutalmak))
        action_tenzor = torch.LongTensor(self.batch_akciok)

        pred = self.predikcio(allapot_tenzor)

#------------------------------------Pálya és veszély def.----------------------------------------------------------------------------------
    # Állapot kiolvasása JSON input alapján, a player.py kódjával dolgozva
    def allapot_kiolvasas(self, jsonData):
        vals = []
        for field in jsonData["vision"]:
            if field["player"] is not None:
                if tuple(field["relative_coord"]) == (0, 0):
                    if 0 < field["value"] <= 3:
                        #Kaját megeszi
                        vals.append(field["value"])
                    elif field["value"] == 9:
                        #Falról lepattan
                        vals.append(-1)
                    else:
                        vals.append(0)
                elif field["player"]["size"] * 1.1 < jsonData["size"]:
                    # Ha kisebb a játékos, akkor megeszi, mert sok kaját ér
                    vals.append(field["player"]["size"])
                elif field["player"]["size"] * 1.1 >= jsonData["size"] or field["player"]["size"] / 1.1 <= jsonData["size"]:
                    # Ha hasonló méretű a játékos akkor lepattan róla, mint a falról
                    vals.append(-1)
                else:
                    # Ha nagyobb a játékos akkor meneküljön, mert meg fogja enni
                    vals.append(-1*field["player"]["size"])
            else:
                if 0 < field["value"] <= 3:
                    vals.append(field["value"])
                elif field["value"] == 9:
                    vals.append(-1)
                else:
                    vals.append(0)
        return np.array(vals)

#------------------------------------Játék végi kiíratások---------------------------------------------------------------------------------------------------
    # Adatfeldolgozás
    def processObservation(self, fulljson, sendData):

        #Játék végén
        if fulljson["type"] == "leaderBoard":
            self.epoch_szamlaloja += 1
           
           # Méretünk kiiratása
            for score in fulljson["payload"]["players"]:
                if(score["name"] == "RemotePlayer"):
                    if(score["active"]):
                        self.vegso_meret.append(score["maxSize"])
                        self.minden_palya.append(self.legutobb_jatszott_palya)
                        print("  score:", score["maxSize"], "map:", self.legutobb_jatszott_palya[0].replace(".txt",""))
                    else:
                        self.vegso_meret.append((-1)*score["maxSize"])
                        self.minden_palya.append(self.legutobb_jatszott_palya)
                        print("  died at:", score["maxSize"], "map:", self.legutobb_jatszott_palya[0].replace(".txt",""))     
            if(Tanitas):
                if(self.epoch_szamlaloja % 50 == 0):
                    #Modell elmentése
                    self.modellmentes()


                # Hozzáadunk a batch adataihoz
                self.batch_szamlaloja += 1
                self.osszes_jutalom.append(sum(self.jutalmak))
                self.batch_jutalmak.extend(self.leszamitott_jutalmak(self.jutalmak))
                self.batch_allapot.extend(self.allapotok)
                self.batch_akciok.extend(self.akciok)

                #Nullázzuk az adott epizódot
                self.allapotok = []
                self.jutalmak = []
                self.akciok = []
                self.utolso_vegrehajtott_akcio = None
                self.utolso_meret = 5
                self.uccso_pozicio = None

                if(self.batch_szamlaloja < self.batchek_merete):
                    time.sleep(0.01)                    
                    next_map = choice(palyak, 1)
                    self.jatek_ujrainditasa(sendData, next_map)
                    self.legutobb_jatszott_palya = next_map            
                else:
                    # Jutalmak normalizálása
                    self.batch_jutalmak = (self.batch_jutalmak - np.mean(self.batch_jutalmak))/np.std(self.batch_jutalmak)
                    self.tanito_lepes()
                    #Batch adatainak nullázása
                    self.batch_jutalmak = []
                    self.batch_akciok = []
                    self.batch_allapot = []
                    self.batch_szamlaloja = 0
                    if(self.epoch_szamlaloja >= self.epizodok_szama):
                        self.jatek_megszakitasa(sendData)
                        #Legvégső modell elmentése
                        self.modellmentes()
                    else:
                        next_map = choice(palyak, 1)
                        self.jatek_ujrainditasa(sendData, next_map)
                        self.legutobb_jatszott_palya = next_map       
            else:
                # 
                if(self.epoch_szamlaloja >= self.epizodok_szama):
                    time.sleep(0.1)
                    self.jatek_megszakitasa(sendData)
                else:
                    time.sleep(0.1)
                    next_map = choice(palyak, 1)
                    self.jatek_ujrainditasa(sendData, next_map)
                    self.legutobb_jatszott_palya = next_map  

        # Játék indítása
        if fulljson["type"] == "readyToStart":
            time.sleep(0.001)
            sendData(json.dumps({"command": "GameControl", "name": "master",
                                 "payload": {"type": "start", "data": None}}))

        # Akció előkészítése a játék adatai alapján
        elif fulljson["type"] == "gameData":
            jsonData = fulljson["payload"]
            if "pos" in jsonData.keys() and "tick" in jsonData.keys() and "active" in jsonData.keys() and "size" in jsonData.keys() and "vision" in jsonData.keys():              
                
                # Állapot kiolvasás JSON-ből
                allapot = self.allapot_kiolvasas(jsonData)
                if(len(allapot) != 82):
                    with open(log_folder, 'w') as f:
                        json.dump(jsonData, f)
                # Predikció elkészítése
                pred = self.predikcio(allapot).detach().numpy()
                if(Tanitas):
                    # Hozzáadjuk a pozícióhoz
                    self.minden_pozicio.append(jsonData["pos"])
                    #Jutalmak számítása
                    jutalom = self.jutalom_szamitas(jsonData)
                    #Tanító adatsor eltárolása
                    if(self.utolso_vegrehajtott_akcio != None and self.utolso_aktiv):
                        self.allapotok.append(self.legutobbi_allapota)
                        self.jutalmak.append(jutalom)
                        self.akciok.append(self.akcio_konverzio_stringbol(self.utolso_vegrehajtott_akcio))
                    # Akció választása
                    actstring = choice(akciok, 1, p=pred/np.sum(pred))[0]
                    # Régi értékek felülírása
                    self.legutobbi_allapota = allapot
                    self.utolso_vegrehajtott_akcio = actstring
                    self.utolso_meret = jsonData["size"]
                    self.uccso_pozicio = jsonData["pos"].copy()
                    self.utolso_aktiv = jsonData["active"]
                else: 
                    actstring = choice(akciok, 1, p=pred/np.sum(pred))[0]
                # JSON előállítása és elküldése
                sendData(json.dumps({"command": "SetAction", "name": "RemotePlayer", "payload": actstring}))

if __name__=="__main__":
    epizodok_szama = 5
    batchek_merete = 30
    tanulasi_rata = 5e-3
    # Példányosított stratégia objektum
    hunter = RemoteStrategy(epizodok_szama,batchek_merete,tanulasi_rata)
    try:
        hunter.network.load_state_dict(torch.load(tanitas_betoltes))
        print("modell betoltve")
    except:
        print("modell nem talalhato")

    #Tanító és validációs üzemmód
    if(Tanitas):
        hunter.network.train()
    else:
       hunter.network.eval()

    # Socket kliens, melynek a szerver címét kell megadni (IP, port), illetve a callback függvényt, melynek szignatúrája a fenti
     #callback(fulljson, sendData)
    client = SocketClient("localhost", 42069, hunter.processObservation)

    # Kliens indítása
    client.start()
    # Kis szünet, hogy a kapcsolat felépülhessen, a start nem blockol, a kliens külső szálon fut
    time.sleep(0.1)
    # Regisztráció a megfelelő névvel
    client.sendData(json.dumps({"command": "SetName", "name": "RemotePlayer", "payload": None}))

    # Nincs blokkoló hívás, a főszál várakozó állapotba kerül, itt végrehajthatók egyéb műveletek a kliens automata működésétől függetlenül.