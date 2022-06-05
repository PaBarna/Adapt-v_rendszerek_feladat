# Házi Feladat - Adaptiv rendszerek modellezése
Készítette: Melicher Martin, Palásty Barnabás

## Modell
A feladat megoldása során neurális háló modellt alkalmazutnk. 

### Neurális háló

Neurális háló megvalósításához pytorch-ot használtunk. Több különböző dense réteget is kipróbáltunk a program elkészítése során, de végül 3 rejtett réteggel működött a legjobban. 
Aktivációs függvénynek a ReLU-t (Rectified Linear Unit) és "Adam" optimalizációs algoritmust használtunk.

### Jutalmak

Ezen felül megerősítéses tanulást (reinforcement learning) alkalmaztunk, ami során az ágens különböző cselekedeteit különböző módon jutalmaztuk:

•	Kaja megtalálása és elfogyasztása esetén jutalmat kapott
•	Ha meghalt, mert megették akkor megbüntettük
•	Jutalmaztuk azt is, ha az ágens mozgott, nem pedig megállt egyhelyben
•	Később mások tanácsára egy mozgóátlagos megoldást is bevezettünk, hogy az ágens ne csak oda vissza mozogjon két mező között

## Tanítás

A feladatunk megoldása során a leggyakoribb probléma, amivel szembenéztünk az volt, hogy az ágens folyamatosan beragadt, 
vagy egyáltalán nem akart mozdulni, 
így a hiperparamétereket úgy hangoltuk, hogy sokat mozogjon, ezzel elkerülve a beragadást. 
Ennek következménye, hogy azokon a pályákon, ahol nincsenek akadályok, sokkal rosszabban teljesít.
Ebből következett, hogy mi a "03_blockade", "04_mirror","05_labirint" pályákon tanítottuk és futtattuk a programot, 
és a tanítás során a legtöbbször a "05_labirint" pályán teljesített a legjobban.
Számos korábbi futtatásnak a hiperparaméter kombinációt nem jegyeztük fel, 
ugyanis legtöbb esetben nem működött rendesen (azaz beakadt), vagy pedig nagyon hasonló eredményt produkált.

### A feladat megoldásához felhasznált linkek a teljesség igénye nélkül


Build Your First Neural Network with PyTorch | Curiousily - Hacker's Guide to Machine Learning
	https://curiousily.com/posts/build-your-first-neural-network-with-pytorch/
How to Create a Simple Neural Network in Python | by Chris Verdence | Better Programming
	https://betterprogramming.pub/how-to-create-a-simple-neural-network-in-python-dbf17f729fe6
Neural Network Python - ActiveState
	https://www.activestate.com/resources/quick-reads/how-to-create-a-neural-network-in-python-with-and-without-keras/
Deep Learning with Python: Neural Networks (complete tutorial) | by Mauro Di Pietro | Towards Data Science
	https://towardsdatascience.com/deep-learning-with-python-neural-networks-complete-tutorial-6b53c0b06af0
Sentdex: Introduction - Deep Learning and Neural Networks with Python and Pytorch p.1
	https://www.youtube.com/watch?v=BzcBsTou0C0&list=PLQVvvaa0QuDdeMyHEYc0gxFpYwHY2Qfdh
