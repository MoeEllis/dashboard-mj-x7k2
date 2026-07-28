# -*- coding: utf-8 -*-
"""Italienisch-Kurs für das Dashboard.

Reine Datendatei ohne Abhängigkeiten – sie wird von build_dashboard.py
importiert und als JSON in die Seite gelegt. Bewusst getrennt gehalten, damit
der Lernstoff ohne Risiko am Dashboard-Code erweitert werden kann.

Aufbau: 48 Lektionen in 4 Blöcken à 12. Jede Lektion ist eine Portion für
einen Tag (15–20 Minuten). Die letzte Lektion jedes Blocks ist ein
Meilenstein, der den Block zusammenführt statt neuen Stoff zu bringen.

Wortpaare und Satzpaare sind ["italienisch", "deutsch"] – kurz gehalten,
weil die Liste vollständig in die verschlüsselte Seite eingebettet wird.
"""

# Reihenfolge der Blöcke bestimmt die Reihenfolge im Kurs.
BLOECKE = [
    {
        "nr": 1,
        "titel": "Fundament",
        "claim": "Ich komme klar",
        "ziel": "Nach Block 1 bestellst du im Restaurant, stellst dich vor "
                "und stellst die Fragen, mit denen du dich überall "
                "durchschlägst.",
        "farbe": "b1",
    },
    {
        "nr": 2,
        "titel": "Alltag",
        "claim": "Ich lebe auf Italienisch",
        "ziel": "Nach Block 2 erzählst du frei von deinem Wochenende, "
                "verabredest dich, telefonierst und führst ein "
                "Restaurantgespräch von der Begrüßung bis zur Rechnung.",
        "farbe": "b2",
    },
    {
        "nr": 3,
        "titel": "Business-Grundlagen",
        "claim": "Ich arbeite auf Italienisch",
        "ziel": "Nach Block 3 stellst du dich beruflich vor, schreibst "
                "E-Mails, hältst dich im Video-Call und im Meeting und "
                "sprichst über Produkte, Zahlen und Termine.",
        "farbe": "b3",
    },
    {
        "nr": 4,
        "titel": "Feinschliff",
        "claim": "Ich überzeuge auf Italienisch",
        "ziel": "Nach Block 4 verhandelst du, präsentierst, widersprichst "
                "diplomatisch und klingst dabei nicht mehr wie ein "
                "Anfänger, sondern wie ein Kollege.",
        "farbe": "b4",
    },
]

LEKTIONEN = [
    # ------------------------------------------------------------------
    # Block 1 – Fundament: die Sätze, die sofort funktionieren
    # ------------------------------------------------------------------
    {
        "nr": 1,
        "block": 1,
        "titel": "Begrüßen und sich vorstellen",
        "ziel": "Du kannst jemanden begrüßen, deinen Namen sagen und fragen, "
                "wie es geht.",
        "woerter": [
            ["ciao", "hallo / tschüss (locker)"],
            ["buongiorno", "guten Tag (bis nachmittags)"],
            ["buonasera", "guten Abend"],
            ["arrivederci", "auf Wiedersehen (höflich)"],
            ["grazie", "danke"],
            ["prego", "bitte / gern"],
            ["scusa", "entschuldige"],
            ["sì / no", "ja / nein"],
            ["piacere", "freut mich"],
            ["il nome", "der Name"],
        ],
        "saetze": [
            ["Ciao, io sono Moritz.", "Hallo, ich bin Moritz."],
            ["Come stai?", "Wie geht es dir?"],
            ["Sto bene, grazie. E tu?", "Mir geht es gut, danke. Und dir?"],
            ["Come ti chiami?", "Wie heißt du?"],
            ["Piacere di conoscerti.", "Freut mich, dich kennenzulernen."],
        ],
        "grammatik": {
            "titel": "essere – sein",
            "text": "io sono, tu sei, lui/lei è, noi siamo, voi siete, loro "
                    "sono. Das Personalpronomen darf weg: „Sono Moritz“ "
                    "reicht, die Verbform sagt schon, wer gemeint ist.",
        },
        "aufgabe": "Sprich laut: Begrüße drei verschiedene Personen – morgens, "
                   "abends und locker. Sage jeweils deinen Namen und frage "
                   "nach dem Namen.",
    },
    {
        "nr": 2,
        "block": 1,
        "titel": "Woher ich komme, was ich mache",
        "ziel": "Du kannst sagen, woher du kommst, wo du wohnst und was du "
                "arbeitest.",
        "woerter": [
            ["la Germania", "Deutschland"],
            ["tedesco / tedesca", "deutsch (m/f)"],
            ["l'Italia", "Italien"],
            ["abitare", "wohnen"],
            ["lavorare", "arbeiten"],
            ["parlare", "sprechen"],
            ["un po'", "ein wenig"],
            ["anche", "auch"],
            ["ma", "aber"],
            ["molto", "sehr / viel"],
        ],
        "saetze": [
            ["Vengo dalla Germania.", "Ich komme aus Deutschland."],
            ["Abito a Stoccarda.", "Ich wohne in Stuttgart."],
            ["Lavoro nel marketing.", "Ich arbeite im Marketing."],
            ["Parlo un po' d'italiano.", "Ich spreche ein wenig Italienisch."],
            ["Non parlo ancora bene, ma imparo.",
             "Ich spreche noch nicht gut, aber ich lerne."],
        ],
        "grammatik": {
            "titel": "Verben auf -are",
            "text": "parlare → io parlo, tu parli, lui parla, noi parliamo, "
                    "voi parlate, loro parlano. Dieses Muster gilt für "
                    "hunderte Verben – lernst du es einmal, kannst du sie alle.",
        },
        "aufgabe": "Erzähle in fünf Sätzen, wer du bist: Name, Herkunft, "
                   "Wohnort, Beruf, Sprachen. Laut, ohne abzulesen.",
    },
    {
        "nr": 3,
        "block": 1,
        "titel": "Zahlen und Uhrzeit",
        "ziel": "Du verstehst Preise und Uhrzeiten und kannst sie selbst sagen.",
        "woerter": [
            ["uno, due, tre", "eins, zwei, drei"],
            ["quattro, cinque, sei", "vier, fünf, sechs"],
            ["sette, otto, nove, dieci", "sieben, acht, neun, zehn"],
            ["venti / trenta", "zwanzig / dreißig"],
            ["cento / mille", "hundert / tausend"],
            ["l'ora", "die Stunde / Uhrzeit"],
            ["il minuto", "die Minute"],
            ["mezzo", "halb"],
            ["quarto", "Viertel"],
            ["l'euro", "der Euro"],
        ],
        "saetze": [
            ["Quanto costa?", "Was kostet das?"],
            ["Costa dodici euro e cinquanta.", "Es kostet 12,50 Euro."],
            ["Che ore sono?", "Wie viel Uhr ist es?"],
            ["Sono le nove e mezzo.", "Es ist halb zehn."],
            ["A che ora apre?", "Wann öffnet es?"],
        ],
        "grammatik": {
            "titel": "Uhrzeit",
            "text": "„Sono le“ + Zahl: sono le tre. Nur bei eins: „È l'una“. "
                    "Minuten mit e: le tre e venti. Vor der Stunde mit meno: "
                    "le tre meno dieci.",
        },
        "aufgabe": "Sage zehn Uhrzeiten laut, quer über den Tag verteilt. "
                   "Dann fünf Preise mit Komma-Cent.",
    },
    {
        "nr": 4,
        "block": 1,
        "titel": "In der Bar: Kaffee und Kleinigkeiten",
        "ziel": "Du bestellst am Tresen wie ein Einheimischer – kurz und "
                "freundlich.",
        "woerter": [
            ["il caffè", "der Espresso"],
            ["il cappuccino", "der Cappuccino"],
            ["l'acqua", "das Wasser"],
            ["frizzante / naturale", "mit / ohne Kohlensäure"],
            ["il cornetto", "das Hörnchen"],
            ["il bicchiere", "das Glas"],
            ["per favore", "bitte"],
            ["vorrei", "ich möchte"],
            ["subito", "sofort"],
            ["il conto", "die Rechnung"],
        ],
        "saetze": [
            ["Un caffè, per favore.", "Einen Espresso, bitte."],
            ["Vorrei un cappuccino e un cornetto.",
             "Ich möchte einen Cappuccino und ein Hörnchen."],
            ["Un'acqua naturale, grazie.", "Ein stilles Wasser, danke."],
            ["Posso pagare con la carta?", "Kann ich mit Karte zahlen?"],
            ["Tutto a posto, grazie.", "Alles gut, danke."],
        ],
        "grammatik": {
            "titel": "vorrei – der höfliche Zauberstab",
            "text": "„Vorrei“ heißt „ich möchte“ und ist immer richtig: "
                    "vorrei un caffè, vorrei prenotare, vorrei sapere. "
                    "Ein Wort, das dich in jeder Situation höflich macht.",
        },
        "aufgabe": "Bestelle laut fünf verschiedene Dinge an einer Bar – "
                   "einmal mit „vorrei“, einmal ganz kurz mit „per favore“.",
    },
    {
        "nr": 5,
        "block": 1,
        "titel": "Fragen stellen",
        "ziel": "Du kannst nach allem fragen und um Wiederholung bitten – die "
                "wichtigste Fähigkeit am Anfang.",
        "woerter": [
            ["dove", "wo"],
            ["come", "wie"],
            ["quando", "wann"],
            ["perché", "warum / weil"],
            ["quanto", "wie viel"],
            ["chi", "wer"],
            ["che cosa", "was"],
            ["capire", "verstehen"],
            ["ripetere", "wiederholen"],
            ["lentamente", "langsam"],
        ],
        "saetze": [
            ["Scusa, non ho capito.", "Entschuldige, ich habe nicht verstanden."],
            ["Puoi ripetere, per favore?", "Kannst du wiederholen, bitte?"],
            ["Puoi parlare più lentamente?", "Kannst du langsamer sprechen?"],
            ["Come si dice … in italiano?", "Wie sagt man … auf Italienisch?"],
            ["Che cosa significa?", "Was bedeutet das?"],
        ],
        "grammatik": {
            "titel": "Fragen ohne Umbau",
            "text": "Im Italienischen bleibt die Wortstellung gleich, nur die "
                    "Stimme geht hoch: „Parli italiano.“ → „Parli italiano?“ "
                    "Kein Hilfsverb, keine Inversion.",
        },
        "aufgabe": "Übe die fünf Rettungssätze aus dieser Lektion so lange, "
                   "bis sie ohne Nachdenken kommen. Sie kaufen dir in jedem "
                   "Gespräch Zeit.",
    },
    {
        "nr": 6,
        "block": 1,
        "titel": "Im Restaurant: Tisch und Bestellung",
        "ziel": "Du reservierst, wirst platziert und bestellst ein komplettes "
                "Essen.",
        "woerter": [
            ["il tavolo", "der Tisch"],
            ["prenotare", "reservieren"],
            ["il menù", "die Speisekarte"],
            ["l'antipasto", "die Vorspeise"],
            ["il primo", "erster Gang (Pasta)"],
            ["il secondo", "Hauptgang (Fleisch/Fisch)"],
            ["il contorno", "die Beilage"],
            ["il dolce", "die Nachspeise"],
            ["il vino rosso / bianco", "Rot- / Weißwein"],
            ["ordinare", "bestellen"],
        ],
        "saetze": [
            ["Buonasera, un tavolo per due, per favore.",
             "Guten Abend, einen Tisch für zwei, bitte."],
            ["Ho prenotato a nome Janisch.",
             "Ich habe auf den Namen Janisch reserviert."],
            ["Il menù, per favore.", "Die Karte, bitte."],
            ["Come primo prendo le tagliatelle.",
             "Als ersten Gang nehme ich die Tagliatelle."],
            ["Che cosa mi consiglia?", "Was empfehlen Sie mir?"],
        ],
        "grammatik": {
            "titel": "Artikel il / la / lo",
            "text": "Männlich: il tavolo, vor s+Konsonant und z: lo "
                    "spuntino. Weiblich: la carta. Vor Vokal wird es l': "
                    "l'acqua, l'antipasto. Mehrzahl: i tavoli, gli "
                    "antipasti, le carte.",
        },
        "aufgabe": "Spiele den Restaurantbesuch bis zur Bestellung laut "
                   "durch: Begrüßung, Tisch, Karte, Getränk, drei Gänge.",
    },
    {
        "nr": 7,
        "block": 1,
        "titel": "Im Restaurant: loben, bitten, zahlen",
        "ziel": "Du kommst durch die zweite Hälfte des Essens – inklusive "
                "Nachfragen und Bezahlen.",
        "woerter": [
            ["buonissimo", "sehr lecker"],
            ["ancora", "noch"],
            ["il pane", "das Brot"],
            ["senza", "ohne"],
            ["l'allergia", "die Allergie"],
            ["il coltello", "das Messer"],
            ["insieme / separato", "zusammen / getrennt"],
            ["la mancia", "das Trinkgeld"],
            ["lo scontrino", "der Kassenbeleg"],
            ["offrire", "einladen / anbieten"],
        ],
        "saetze": [
            ["Era tutto buonissimo, complimenti!",
             "Es war alles hervorragend, Kompliment!"],
            ["Un altro bicchiere di vino, per favore.",
             "Noch ein Glas Wein, bitte."],
            ["Sono allergico alle noci.", "Ich bin allergisch gegen Nüsse."],
            ["Il conto, per favore.", "Die Rechnung, bitte."],
            ["Paghiamo separato.", "Wir zahlen getrennt."],
        ],
        "grammatik": {
            "titel": "Höflich fragen mit „posso“ und „mi porta“",
            "text": "„Posso …?“ = Darf ich …? (posso pagare, posso vedere). "
                    "„Mi porta …?“ = Bringen Sie mir …? – beides klingt "
                    "freundlicher als der nackte Imperativ.",
        },
        "aufgabe": "Spiele die zweite Hälfte durch: loben, etwas nachbestellen, "
                   "eine Allergie nennen, Rechnung verlangen, getrennt zahlen.",
    },
    {
        "nr": 8,
        "block": 1,
        "titel": "Einkaufen und Mengen",
        "ziel": "Du kaufst ein, fragst nach Größen und Preisen und "
                "verhandelst freundlich.",
        "woerter": [
            ["il negozio", "das Geschäft"],
            ["aperto / chiuso", "offen / geschlossen"],
            ["provare", "probieren / anprobieren"],
            ["la taglia", "die Größe"],
            ["troppo", "zu (viel)"],
            ["caro / economico", "teuer / günstig"],
            ["lo sconto", "der Rabatt"],
            ["un chilo", "ein Kilo"],
            ["un etto", "100 Gramm"],
            ["la busta", "die Tüte"],
        ],
        "saetze": [
            ["Sto solo guardando, grazie.", "Ich schaue nur, danke."],
            ["Posso provarlo?", "Kann ich es anprobieren?"],
            ["Avete una taglia più grande?", "Haben Sie eine größere Größe?"],
            ["È un po' troppo caro per me.", "Das ist mir etwas zu teuer."],
            ["Prendo questo, grazie.", "Ich nehme das, danke."],
        ],
        "grammatik": {
            "titel": "questo / quello",
            "text": "questo = dieses hier, quello = jenes dort. Sie passen "
                    "sich an: questo vino, questa pizza, questi libri, "
                    "queste carte.",
        },
        "aufgabe": "Kaufe laut ein: begrüßen, nach Größe fragen, Preis "
                   "erfragen, Preis kommentieren, kaufen oder ablehnen.",
    },
    {
        "nr": 9,
        "block": 1,
        "titel": "Weg und Orientierung",
        "ziel": "Du findest dich in einer Stadt zurecht und verstehst "
                "Wegbeschreibungen.",
        "woerter": [
            ["a destra / a sinistra", "rechts / links"],
            ["sempre dritto", "immer gerade"],
            ["vicino / lontano", "nah / weit"],
            ["la strada", "die Straße"],
            ["la piazza", "der Platz"],
            ["la stazione", "der Bahnhof"],
            ["il bagno", "die Toilette"],
            ["girare", "abbiegen"],
            ["a piedi", "zu Fuß"],
            ["accanto a", "neben"],
        ],
        "saetze": [
            ["Scusi, dov'è la stazione?",
             "Entschuldigung, wo ist der Bahnhof?"],
            ["È lontano da qui?", "Ist es weit von hier?"],
            ["Vada sempre dritto e poi giri a destra.",
             "Gehen Sie immer gerade und biegen Sie dann rechts ab."],
            ["Sono dieci minuti a piedi.", "Es sind zehn Minuten zu Fuß."],
            ["Mi sono perso.", "Ich habe mich verlaufen."],
        ],
        "grammatik": {
            "titel": "Präposition + Artikel",
            "text": "Sie verschmelzen: a + il = al, a + la = alla, di + il = "
                    "del, in + il = nel, da + il = dal. „Vado al bar“, „vicino "
                    "alla piazza“.",
        },
        "aufgabe": "Beschreibe laut den Weg von deiner Haustür zum nächsten "
                   "Supermarkt – auf Italienisch, mit Abbiegungen.",
    },
    {
        "nr": 10,
        "block": 1,
        "titel": "Mein Tag",
        "ziel": "Du erzählst deinen Tagesablauf – die Basis für alles "
                "spätere Erzählen.",
        "woerter": [
            ["svegliarsi", "aufwachen"],
            ["alzarsi", "aufstehen"],
            ["fare colazione", "frühstücken"],
            ["andare", "gehen / fahren"],
            ["fare", "machen"],
            ["mangiare", "essen"],
            ["tornare", "zurückkommen"],
            ["dormire", "schlafen"],
            ["di solito", "normalerweise"],
            ["poi / dopo", "dann / danach"],
        ],
        "saetze": [
            ["Di solito mi alzo alle sei e mezzo.",
             "Normalerweise stehe ich um halb sieben auf."],
            ["Faccio colazione e poi vado al lavoro.",
             "Ich frühstücke und gehe dann zur Arbeit."],
            ["Lavoro dalle nove alle sei.",
             "Ich arbeite von neun bis sechs."],
            ["La sera cucino qualcosa.", "Abends koche ich etwas."],
            ["Vado a letto verso le undici.",
             "Ich gehe gegen elf ins Bett."],
        ],
        "grammatik": {
            "titel": "andare und fare",
            "text": "Zwei unregelmäßige Dauerbrenner: andare → vado, vai, va, "
                    "andiamo, andate, vanno. fare → faccio, fai, fa, facciamo, "
                    "fate, fanno.",
        },
        "aufgabe": "Erzähle deinen gestrigen Tagesablauf im Präsens, "
                   "chronologisch, mindestens acht Sätze mit „poi“ verbunden.",
    },
    {
        "nr": 11,
        "block": 1,
        "titel": "Familie, Wohnen, Umgebung",
        "ziel": "Du kannst über dein privates Umfeld sprechen – der häufigste "
                "Small-Talk-Stoff.",
        "woerter": [
            ["la moglie / il marito", "die Frau / der Mann"],
            ["il figlio / la figlia", "der Sohn / die Tochter"],
            ["i genitori", "die Eltern"],
            ["il fratello / la sorella", "der Bruder / die Schwester"],
            ["l'amico / l'amica", "der Freund / die Freundin"],
            ["la casa", "das Haus / Zuhause"],
            ["l'appartamento", "die Wohnung"],
            ["il giardino", "der Garten"],
            ["il cane / il gatto", "der Hund / die Katze"],
            ["avere", "haben"],
        ],
        "saetze": [
            ["Ho due fratelli.", "Ich habe zwei Brüder."],
            ["Mia sorella abita a Berlino.",
             "Meine Schwester wohnt in Berlin."],
            ["Abitiamo in un appartamento con un piccolo giardino.",
             "Wir wohnen in einer Wohnung mit einem kleinen Garten."],
            ["Quanti anni hai?", "Wie alt bist du?"],
            ["Ho trentacinque anni.", "Ich bin 35 Jahre alt."],
        ],
        "grammatik": {
            "titel": "avere und Possessiv",
            "text": "avere → ho, hai, ha, abbiamo, avete, hanno. Alter mit "
                    "avere: „ho 35 anni“. Possessiv mit Artikel: il mio "
                    "lavoro, la mia casa – außer bei einzelnen Verwandten: "
                    "mia sorella.",
        },
        "aufgabe": "Beschreibe laut deine Familie und dein Zuhause in zehn "
                   "Sätzen. Nenne Alter, Personen, Wohnsituation.",
    },
    {
        "nr": 12,
        "block": 1,
        "titel": "Meilenstein 1: Der erste echte Dialog",
        "ziel": "Du führst ohne Hilfe ein komplettes Kennenlern- und "
                "Restaurantgespräch. Kein neuer Stoff – nur Beweis.",
        "woerter": [
            ["allora", "also / nun"],
            ["certo", "klar / sicher"],
            ["volentieri", "gern"],
            ["magari", "vielleicht / am besten"],
            ["davvero", "wirklich"],
            ["senti", "hör mal"],
            ["va bene", "in Ordnung"],
            ["nessun problema", "kein Problem"],
            ["che bello!", "wie schön!"],
            ["a dopo", "bis später"],
        ],
        "saetze": [
            ["Allora, che cosa prendiamo?", "Also, was nehmen wir?"],
            ["Senti, posso farti una domanda?",
             "Hör mal, darf ich dich etwas fragen?"],
            ["Volentieri, con piacere.", "Gern, mit Vergnügen."],
            ["Va bene così, grazie mille.", "So ist es gut, vielen Dank."],
            ["È stato un piacere, a dopo!",
             "Es war ein Vergnügen, bis später!"],
        ],
        "grammatik": {
            "titel": "Füllwörter machen dich flüssig",
            "text": "allora, senti, certo, magari, va bene: Diese kleinen "
                    "Wörter geben dir Denkzeit und lassen dich sofort "
                    "natürlicher klingen als perfekte Grammatik.",
        },
        "aufgabe": "Meilenstein: Führe einen 5-Minuten-Monolog – du kommst "
                   "in ein Restaurant, wirst begrüßt, stellst dich vor, "
                   "bestellst, lobst, zahlst, verabschiedest dich. "
                   "Alles laut, ohne Notizen.",
    },
]

LEKTIONEN += [
    # ------------------------------------------------------------------
    # Block 2 – Alltag: Vergangenheit, Erzählen, Verabreden
    # ------------------------------------------------------------------
    {
        "nr": 13,
        "block": 2,
        "titel": "Vergangenheit 1: passato prossimo mit avere",
        "ziel": "Du kannst sagen, was du gemacht hast – die wichtigste Zeit "
                "im gesprochenen Italienisch.",
        "woerter": [
            ["ieri", "gestern"],
            ["stamattina", "heute Morgen"],
            ["la settimana scorsa", "letzte Woche"],
            ["ho fatto", "ich habe gemacht"],
            ["ho mangiato", "ich habe gegessen"],
            ["ho visto", "ich habe gesehen"],
            ["ho letto", "ich habe gelesen"],
            ["ho lavorato", "ich habe gearbeitet"],
            ["ho comprato", "ich habe gekauft"],
            ["ho bevuto", "ich habe getrunken"],
        ],
        "saetze": [
            ["Ieri ho lavorato molto.", "Gestern habe ich viel gearbeitet."],
            ["Ho mangiato una pizza fantastica.",
             "Ich habe eine fantastische Pizza gegessen."],
            ["Che cosa hai fatto ieri?", "Was hast du gestern gemacht?"],
            ["Non ho ancora visto quel film.",
             "Ich habe diesen Film noch nicht gesehen."],
            ["Abbiamo comprato il vino al mercato.",
             "Wir haben den Wein auf dem Markt gekauft."],
        ],
        "grammatik": {
            "titel": "avere + Partizip",
            "text": "ho / hai / ha / abbiamo / avete / hanno + Partizip. "
                    "Regelmäßig: -are → -ato, -ere → -uto, -ire → -ito. "
                    "Unregelmäßig und häufig: fatto, visto, letto, preso, "
                    "detto, scritto, bevuto.",
        },
        "aufgabe": "Erzähle laut fünf Dinge, die du gestern gemacht hast – "
                   "alle mit avere gebildet.",
    },
    {
        "nr": 14,
        "block": 2,
        "titel": "Vergangenheit 2: passato prossimo mit essere",
        "ziel": "Du beherrschst die zweite Hälfte der Vergangenheit – "
                "Bewegungs- und Zustandsverben.",
        "woerter": [
            ["sono andato", "ich bin gegangen / gefahren"],
            ["sono stato", "ich bin gewesen"],
            ["sono arrivato", "ich bin angekommen"],
            ["sono partito", "ich bin abgefahren"],
            ["sono tornato", "ich bin zurückgekommen"],
            ["sono uscito", "ich bin ausgegangen"],
            ["sono rimasto", "ich bin geblieben"],
            ["mi sono svegliato", "ich bin aufgewacht"],
            ["mi sono divertito", "ich habe mich amüsiert"],
            ["insieme a", "zusammen mit"],
        ],
        "saetze": [
            ["Sono andato a Milano in treno.",
             "Ich bin mit dem Zug nach Mailand gefahren."],
            ["Sono stato in Italia due volte.",
             "Ich war zweimal in Italien."],
            ["Siamo usciti con gli amici.",
             "Wir sind mit den Freunden ausgegangen."],
            ["Mi sono divertito molto.", "Ich habe mich sehr amüsiert."],
            ["A che ora sei tornato a casa?",
             "Wann bist du nach Hause zurückgekommen?"],
        ],
        "grammatik": {
            "titel": "essere + Partizip, das sich anpasst",
            "text": "Bei essere richtet sich das Partizip nach der Person: "
                    "sono andato / andata, siamo andati / andate. Merkhilfe: "
                    "Bewegung, Bleiben und alle Reflexivverben nehmen essere.",
        },
        "aufgabe": "Erzähle laut deine letzte Reise: hingefahren, angekommen, "
                   "geblieben, ausgegangen, zurückgekommen.",
    },
    {
        "nr": 15,
        "block": 2,
        "titel": "Mein Wochenende erzählen",
        "ziel": "Dein erklärtes Ziel: Du erzählst flüssig, was du am "
                "Wochenende gemacht hast – und stellst die Frage zurück.",
        "woerter": [
            ["il fine settimana", "das Wochenende"],
            ["sabato / domenica", "Samstag / Sonntag"],
            ["riposare", "ausruhen"],
            ["tranquillo", "ruhig / entspannt"],
            ["fuori", "draußen / auswärts"],
            ["la passeggiata", "der Spaziergang"],
            ["il tempo libero", "die Freizeit"],
            ["niente di speciale", "nichts Besonderes"],
            ["purtroppo", "leider"],
            ["per fortuna", "zum Glück"],
        ],
        "saetze": [
            ["Com'è stato il tuo fine settimana?",
             "Wie war dein Wochenende?"],
            ["È stato tranquillo, niente di speciale.",
             "Es war ruhig, nichts Besonderes."],
            ["Sabato ho fatto una passeggiata, poi siamo andati fuori a cena.",
             "Samstag habe ich einen Spaziergang gemacht, dann sind wir "
             "auswärts essen gegangen."],
            ["Domenica mi sono riposato e ho guardato una partita.",
             "Sonntag habe ich mich ausgeruht und ein Spiel geschaut."],
            ["E tu, che cosa hai fatto?", "Und du, was hast du gemacht?"],
        ],
        "grammatik": {
            "titel": "Erzählgerüst in drei Schritten",
            "text": "1. Gesamturteil: „È stato bello / tranquillo / "
                    "faticoso.“ 2. Zwei bis drei Ereignisse mit sabato / "
                    "domenica / poi. 3. Frage zurück: „E tu?“ Mit diesem "
                    "Gerüst klingt jede Antwort vollständig.",
        },
        "aufgabe": "Erzähle dein letztes Wochenende nach dem Dreischritt – "
                   "Urteil, drei Ereignisse, Rückfrage. Zweimal laut.",
    },
    {
        "nr": 16,
        "block": 2,
        "titel": "Wetter, Datum, Kalender",
        "ziel": "Du sprichst über Wetter, Wochentage und Monate – der "
                "Türöffner für jedes Gespräch.",
        "woerter": [
            ["che tempo fa?", "wie ist das Wetter?"],
            ["fa caldo / freddo", "es ist warm / kalt"],
            ["piove / nevica", "es regnet / schneit"],
            ["il sole", "die Sonne"],
            ["lunedì, martedì, mercoledì", "Mo, Di, Mi"],
            ["giovedì, venerdì", "Do, Fr"],
            ["gennaio / febbraio", "Januar / Februar"],
            ["l'estate / l'inverno", "der Sommer / der Winter"],
            ["la settimana prossima", "nächste Woche"],
            ["il mese", "der Monat"],
        ],
        "saetze": [
            ["Oggi fa molto caldo.", "Heute ist es sehr warm."],
            ["Ieri ha piovuto tutto il giorno.",
             "Gestern hat es den ganzen Tag geregnet."],
            ["Ci vediamo martedì prossimo.",
             "Wir sehen uns nächsten Dienstag."],
            ["In agosto siamo in vacanza.", "Im August sind wir im Urlaub."],
            ["Quanti ne abbiamo oggi?", "Welches Datum ist heute?"],
        ],
        "grammatik": {
            "titel": "Wetter mit fare",
            "text": "Das Wetter läuft über fare: fa caldo, fa freddo, fa "
                    "bel tempo, fa brutto. Ausnahmen sind eigene Verben: "
                    "piove, nevica, c'è vento, c'è nebbia.",
        },
        "aufgabe": "Beschreibe laut das Wetter der letzten drei Tage und "
                   "verabrede dich für drei verschiedene Wochentage.",
    },
    {
        "nr": 17,
        "block": 2,
        "titel": "Hobbys, Sport und Sammeln",
        "ziel": "Du kannst über deine Interessen sprechen – und über das "
                "Sammeln, dein Fachgebiet auch privat.",
        "woerter": [
            ["mi piace", "mir gefällt / ich mag"],
            ["mi piacciono", "ich mag (mehrere)"],
            ["il calcio", "der Fußball"],
            ["la partita", "das Spiel"],
            ["la squadra", "die Mannschaft"],
            ["collezionare", "sammeln"],
            ["la collezione", "die Sammlung"],
            ["l'album", "das Album"],
            ["giocare", "spielen"],
            ["il tifoso", "der Fan"],
        ],
        "saetze": [
            ["Mi piace il calcio.", "Ich mag Fußball."],
            ["Mi piacciono le figurine dei calciatori.",
             "Ich mag Fußballsammelbilder."],
            ["Colleziono carte da quando ero bambino.",
             "Ich sammle Karten, seit ich ein Kind war."],
            ["Non mi piace molto la palestra.",
             "Ins Fitnessstudio mag ich nicht so gern."],
            ["Che squadra tifi?", "Welchem Verein hältst du die Daumen?"],
        ],
        "grammatik": {
            "titel": "piacere denkt umgekehrt",
            "text": "„Mi piace il vino“ heißt wörtlich „mir gefällt der "
                    "Wein“. Einzahl: mi piace. Mehrzahl: mi piacciono. "
                    "Anderen: ti piace, le piace, ci piace.",
        },
        "aufgabe": "Nenne laut fünf Dinge, die du magst, und drei, die du "
                   "nicht magst – achte auf piace / piacciono.",
    },
    {
        "nr": 18,
        "block": 2,
        "titel": "Gefühle und Meinungen",
        "ziel": "Du sagst, wie es dir geht und was du denkst – auch "
                "differenziert.",
        "woerter": [
            ["contento / felice", "zufrieden / glücklich"],
            ["stanco", "müde"],
            ["stressato", "gestresst"],
            ["arrabbiato", "wütend"],
            ["secondo me", "meiner Meinung nach"],
            ["penso che", "ich denke, dass"],
            ["sono d'accordo", "ich stimme zu"],
            ["forse", "vielleicht"],
            ["dipende", "es hängt davon ab"],
            ["mi sembra", "es scheint mir"],
        ],
        "saetze": [
            ["Oggi sono un po' stanco.", "Heute bin ich etwas müde."],
            ["Secondo me è una buona idea.",
             "Meiner Meinung nach ist das eine gute Idee."],
            ["Sono completamente d'accordo con te.",
             "Ich stimme dir völlig zu."],
            ["Mi sembra un po' complicato.",
             "Es scheint mir etwas kompliziert."],
            ["Non sono sicuro, dipende.",
             "Ich bin nicht sicher, es hängt davon ab."],
        ],
        "grammatik": {
            "titel": "Adjektive passen sich an",
            "text": "Auf -o: contento, contenta, contenti, contente. Auf -e: "
                    "felice, felici (gleich für beide Geschlechter). Das "
                    "Adjektiv steht meist hinter dem Nomen: un vino buono.",
        },
        "aufgabe": "Nimm drei Aussagen und reagiere jeweils laut: einmal "
                   "zustimmend, einmal skeptisch, einmal unentschieden.",
    },
    {
        "nr": 19,
        "block": 2,
        "titel": "Verabreden und Vorschläge",
        "ziel": "Du machst Vorschläge, sagst zu und sagst freundlich ab.",
        "woerter": [
            ["andiamo?", "gehen wir?"],
            ["ci vediamo", "wir sehen uns"],
            ["libero / occupato", "frei / beschäftigt"],
            ["stasera", "heute Abend"],
            ["domani", "morgen"],
            ["più tardi", "später"],
            ["Ti va bene?", "Passt es dir?"],
            ["mi dispiace", "es tut mir leid"],
            ["un'altra volta", "ein anderes Mal"],
            ["l'appuntamento", "der Termin / die Verabredung"],
        ],
        "saetze": [
            ["Ti va di andare a cena stasera?",
             "Hast du Lust, heute Abend essen zu gehen?"],
            ["Perché non andiamo a bere qualcosa?",
             "Warum gehen wir nicht etwas trinken?"],
            ["Volentieri! A che ora ci vediamo?",
             "Gern! Wann sehen wir uns?"],
            ["Mi dispiace, stasera non posso.",
             "Es tut mir leid, heute Abend kann ich nicht."],
            ["Facciamo un'altra volta?",
             "Machen wir es ein anderes Mal?"],
        ],
        "grammatik": {
            "titel": "Vorschläge mit noi",
            "text": "Die wir-Form ist gleichzeitig der Vorschlag: "
                    "„Andiamo!“ = Gehen wir! „Facciamo così“ = Machen wir "
                    "es so. Ein Wort, kein Hilfsverb nötig.",
        },
        "aufgabe": "Mache laut drei Vorschläge, nimm einen an und lehne zwei "
                   "höflich mit Begründung ab.",
    },
    {
        "nr": 20,
        "block": 2,
        "titel": "Telefonieren und Nachrichten",
        "ziel": "Du kommst durch ein Telefonat und schreibst kurze "
                "Nachrichten.",
        "woerter": [
            ["pronto?", "hallo? (am Telefon)"],
            ["chiamare", "anrufen"],
            ["richiamare", "zurückrufen"],
            ["il numero", "die Nummer"],
            ["attenda", "warten Sie (höflich)"],
            ["la linea", "die Leitung"],
            ["il messaggio", "die Nachricht"],
            ["scrivere", "schreiben"],
            ["mandare", "senden"],
            ["Ci sentiamo", "wir hören uns"],
        ],
        "saetze": [
            ["Pronto, sono Moritz.", "Hallo, hier ist Moritz."],
            ["Posso parlare con Marco?", "Kann ich mit Marco sprechen?"],
            ["Ti richiamo più tardi.", "Ich rufe dich später zurück."],
            ["Non ti sento bene.", "Ich höre dich nicht gut."],
            ["Ti mando un messaggio.", "Ich schicke dir eine Nachricht."],
        ],
        "grammatik": {
            "titel": "Indirekte Pronomen mi / ti / gli / le",
            "text": "„Ti chiamo“ = ich rufe dich an. „Mi chiami?“ = rufst du "
                    "mich an? „Le scrivo“ = ich schreibe ihr / Ihnen. Das "
                    "Pronomen steht vor dem Verb.",
        },
        "aufgabe": "Spiele ein Telefonat laut: melden, nach jemandem fragen, "
                   "Rückruf vereinbaren, verabschieden.",
    },
    {
        "nr": 21,
        "block": 2,
        "titel": "Reisen: Zug, Hotel, Taxi",
        "ziel": "Du organisierst eine Reise auf Italienisch von der Buchung "
                "bis zum Check-out.",
        "woerter": [
            ["il biglietto", "das Ticket"],
            ["andata e ritorno", "hin und zurück"],
            ["il binario", "das Bahngleis"],
            ["in ritardo", "verspätet"],
            ["la camera", "das Zimmer"],
            ["la prenotazione", "die Reservierung"],
            ["la chiave", "der Schlüssel"],
            ["la colazione inclusa", "Frühstück inklusive"],
            ["i bagagli", "das Gepäck"],
            ["portare", "bringen / tragen"],
        ],
        "saetze": [
            ["Un biglietto per Firenze, andata e ritorno.",
             "Ein Ticket nach Florenz, hin und zurück."],
            ["Da quale binario parte il treno?",
             "Von welchem Gleis fährt der Zug?"],
            ["Il treno è in ritardo di venti minuti.",
             "Der Zug hat 20 Minuten Verspätung."],
            ["Ho una prenotazione a nome Janisch.",
             "Ich habe eine Reservierung auf den Namen Janisch."],
            ["A che ora è la colazione?", "Wann gibt es Frühstück?"],
        ],
        "grammatik": {
            "titel": "c'è / ci sono",
            "text": "c'è = es gibt (Einzahl), ci sono = es gibt (Mehrzahl). "
                    "„C'è il wifi?“, „Ci sono camere libere?“ Verneint: "
                    "„Non c'è …“",
        },
        "aufgabe": "Spiele laut eine komplette Reise: Ticket kaufen, "
                   "Verspätung erfragen, einchecken, Frühstück klären.",
    },
    {
        "nr": 22,
        "block": 2,
        "titel": "Wenn etwas schiefgeht",
        "ziel": "Du kannst Hilfe holen, Beschwerden äußern und Probleme "
                "erklären.",
        "woerter": [
            ["aiuto!", "Hilfe!"],
            ["il medico", "der Arzt"],
            ["la farmacia", "die Apotheke"],
            ["il mal di testa", "die Kopfschmerzen"],
            ["mi fa male", "es tut mir weh"],
            ["non funziona", "es funktioniert nicht"],
            ["il problema", "das Problem"],
            ["rotto", "kaputt"],
            ["perdere", "verlieren"],
            ["chiedere", "fragen / bitten"],
        ],
        "saetze": [
            ["Ho bisogno di un medico.", "Ich brauche einen Arzt."],
            ["Mi fa male la testa.", "Ich habe Kopfschmerzen."],
            ["Il wifi non funziona.", "Das WLAN funktioniert nicht."],
            ["Ho perso il portafoglio.", "Ich habe die Geldbörse verloren."],
            ["C'è un problema con la mia prenotazione.",
             "Es gibt ein Problem mit meiner Reservierung."],
        ],
        "grammatik": {
            "titel": "avere bisogno di",
            "text": "„Ich brauche“ heißt „ho bisogno di“: ho bisogno di "
                    "aiuto, ho bisogno di tempo. Vor Verben genauso: „ho "
                    "bisogno di parlare con qualcuno“.",
        },
        "aufgabe": "Erkläre laut drei Probleme und bitte jeweils konkret um "
                   "Hilfe – ruhig, aber deutlich.",
    },
    {
        "nr": 23,
        "block": 2,
        "titel": "Small Talk, der weitergeht",
        "ziel": "Du hältst ein Gespräch am Leben, statt nach zwei Sätzen zu "
                "verstummen.",
        "woerter": [
            ["ah sì?", "ach wirklich?"],
            ["davvero interessante", "wirklich interessant"],
            ["e poi?", "und dann?"],
            ["come mai?", "wie kommt's?"],
            ["anch'io", "ich auch"],
            ["neanch'io", "ich auch nicht"],
            ["dimmi", "sag mir / erzähl"],
            ["capisco", "ich verstehe"],
            ["che peccato", "wie schade"],
            ["in effetti", "tatsächlich"],
        ],
        "saetze": [
            ["Ah sì? Racconta!", "Ach wirklich? Erzähl!"],
            ["Come mai hai scelto Milano?",
             "Wie kommt es, dass du Mailand gewählt hast?"],
            ["Anch'io! Che coincidenza.", "Ich auch! Was für ein Zufall."],
            ["Capisco, e poi che cosa è successo?",
             "Ich verstehe, und dann, was ist passiert?"],
            ["Che peccato, mi dispiace.", "Wie schade, das tut mir leid."],
        ],
        "grammatik": {
            "titel": "Reagieren statt vortragen",
            "text": "Ein Gespräch lebt von kurzen Reaktionen plus einer "
                    "Rückfrage. Merke drei Reaktionen (ah sì?, capisco, che "
                    "peccato) und drei Rückfragen (e poi?, come mai?, "
                    "davvero?) – damit trägst du jedes Gespräch.",
        },
        "aufgabe": "Lass jemanden (oder ein Video) erzählen und reagiere "
                   "laut zehnmal mit Reaktion plus Rückfrage.",
    },
    {
        "nr": 24,
        "block": 2,
        "titel": "Meilenstein 2: Abend mit Freunden",
        "ziel": "Du führst einen kompletten Abend: verabreden, Restaurant, "
                "Wochenende erzählen, Small Talk, zahlen. Kein neuer Stoff.",
        "woerter": [
            ["Com'è andata?", "Wie ist es gelaufen?"],
            ["alla fine", "am Ende / schließlich"],
            ["comunque", "jedenfalls / trotzdem"],
            ["per esempio", "zum Beispiel"],
            ["soprattutto", "vor allem"],
            ["di nuovo", "wieder"],
            ["ogni tanto", "ab und zu"],
            ["quasi", "fast"],
            ["abbastanza", "ziemlich / genug"],
            ["alla prossima", "bis zum nächsten Mal"],
        ],
        "saetze": [
            ["Com'è andata la settimana?", "Wie ist die Woche gelaufen?"],
            ["Abbastanza bene, soprattutto venerdì.",
             "Ziemlich gut, vor allem am Freitag."],
            ["Alla fine siamo rimasti fino a mezzanotte.",
             "Am Ende sind wir bis Mitternacht geblieben."],
            ["Comunque, la prossima volta offro io.",
             "Jedenfalls, das nächste Mal lade ich ein."],
            ["È stata una bella serata, alla prossima!",
             "Es war ein schöner Abend, bis zum nächsten Mal!"],
        ],
        "grammatik": {
            "titel": "Verbinden statt aufzählen",
            "text": "comunque, alla fine, soprattutto, per esempio, ogni "
                    "tanto: Diese Verbinder machen aus fünf Einzelsätzen "
                    "eine Erzählung. Sie sind der Unterschied zwischen "
                    "„kann Sätze“ und „kann sprechen“.",
        },
        "aufgabe": "Meilenstein: Erzähle 5 Minuten frei über deine Woche und "
                   "dein Wochenende, mit mindestens fünf Verbindern und "
                   "beiden Vergangenheitsformen.",
    },
]

LEKTIONEN += [
    # ------------------------------------------------------------------
    # Block 3 – Business-Grundlagen: Lei-Form, Meetings, Zahlen, Produkt
    # ------------------------------------------------------------------
    {
        "nr": 25,
        "block": 3,
        "titel": "Die Höflichkeitsform Lei",
        "ziel": "Du wechselst sicher vom Du ins Sie – die Grundvoraussetzung "
                "für jeden Geschäftskontakt.",
        "woerter": [
            ["Lei", "Sie (höflich)"],
            ["Come sta?", "Wie geht es Ihnen?"],
            ["Mi scusi", "Entschuldigen Sie"],
            ["Si accomodi", "Nehmen Sie Platz"],
            ["Le presento", "Ich stelle Ihnen vor"],
            ["Signore / Signora", "Herr / Frau"],
            ["gentile", "freundlich / geehrt"],
            ["Dottore / Dottoressa", "Anrede für Akademiker"],
            ["cortesemente", "freundlicherweise"],
            ["a disposizione", "zur Verfügung"],
        ],
        "saetze": [
            ["Buongiorno, come sta?", "Guten Tag, wie geht es Ihnen?"],
            ["Mi scusi, Lei è la signora Rossi?",
             "Entschuldigen Sie, sind Sie Frau Rossi?"],
            ["Le presento il mio collega.",
             "Ich stelle Ihnen meinen Kollegen vor."],
            ["Può ripetere, per favore?",
             "Können Sie das bitte wiederholen?"],
            ["Sono a Sua disposizione.", "Ich stehe Ihnen zur Verfügung."],
        ],
        "grammatik": {
            "titel": "Lei benutzt die er/sie-Form",
            "text": "Für „Sie“ nimmst du die 3. Person Einzahl: „Lei parla“, "
                    "„Come sta?“, „Può …?“. Die Pronomen werden Le / La: "
                    "„Le scrivo domani“. Groß geschrieben nur im Brief.",
        },
        "aufgabe": "Nimm fünf Sätze aus Block 1 und 2 und formuliere sie laut "
                   "in die Lei-Form um.",
    },
    {
        "nr": 26,
        "block": 3,
        "titel": "Sich beruflich vorstellen",
        "ziel": "Du hast eine saubere 60-Sekunden-Vorstellung für Meetings "
                "und Messen parat.",
        "woerter": [
            ["il product manager", "der Produktmanager"],
            ["mi occupo di", "ich befasse mich mit"],
            ["responsabile di", "verantwortlich für"],
            ["l'azienda", "das Unternehmen"],
            ["la sede", "der Standort / Sitz"],
            ["il settore", "die Branche"],
            ["da tre anni", "seit drei Jahren"],
            ["il mercato", "der Markt"],
            ["il ruolo", "die Rolle"],
            ["il team", "das Team"],
        ],
        "saetze": [
            ["Sono product manager alla Panini Germania.",
             "Ich bin Produktmanager bei Panini Deutschland."],
            ["Mi occupo del mercato hobby delle carte da collezione.",
             "Ich befasse mich mit dem Hobby-Markt für Sammelkarten."],
            ["Lavoro in questo settore da diversi anni.",
             "Ich arbeite seit mehreren Jahren in dieser Branche."],
            ["Sono responsabile dello sviluppo prodotto.",
             "Ich bin verantwortlich für die Produktentwicklung."],
            ["La nostra sede è a Stoccarda.",
             "Unser Standort ist in Stuttgart."],
        ],
        "grammatik": {
            "titel": "da + Zeitraum",
            "text": "Für „seit“ nimmst du das Präsens plus da: „Lavoro qui da "
                    "tre anni“ – ich arbeite hier seit drei Jahren. Nicht die "
                    "Vergangenheit, obwohl es im Deutschen so klingt.",
        },
        "aufgabe": "Baue deine eigene Vorstellung: Rolle, Firma, Aufgabe, "
                   "Erfahrung, Standort. Sprich sie fünfmal laut, bis sie "
                   "sitzt.",
    },
    {
        "nr": 27,
        "block": 3,
        "titel": "Firma, Abteilungen, Zuständigkeiten",
        "ziel": "Du erklärst, wer bei dir was macht, und verstehst die "
                "Gegenseite.",
        "woerter": [
            ["il reparto", "die Abteilung"],
            ["le vendite", "der Vertrieb"],
            ["il marketing", "das Marketing"],
            ["la produzione", "die Produktion"],
            ["la logistica", "die Logistik"],
            ["il capo", "der Chef"],
            ["il collega / la collega", "der Kollege / die Kollegin"],
            ["il cliente", "der Kunde"],
            ["il fornitore", "der Lieferant"],
            ["decidere", "entscheiden"],
        ],
        "saetze": [
            ["Chi si occupa della logistica?",
             "Wer ist für die Logistik zuständig?"],
            ["Il mio reparto lavora con le vendite.",
             "Meine Abteilung arbeitet mit dem Vertrieb zusammen."],
            ["Devo parlarne con il mio capo.",
             "Ich muss darüber mit meinem Chef sprechen."],
            ["Chi prende la decisione finale?",
             "Wer trifft die endgültige Entscheidung?"],
            ["Vi metto in contatto con il collega giusto.",
             "Ich bringe Sie mit dem richtigen Kollegen zusammen."],
        ],
        "grammatik": {
            "titel": "dovere, potere, volere",
            "text": "Die drei Modalverben, die dich im Büro tragen: devo "
                    "(ich muss), posso (ich kann/darf), voglio (ich will). "
                    "Danach steht der Infinitiv: „Devo controllare“, „Posso "
                    "confermare“.",
        },
        "aufgabe": "Beschreibe laut deine Firma: Abteilungen, deine Rolle, "
                   "wer entscheidet, mit wem du zusammenarbeitest.",
    },
    {
        "nr": 28,
        "block": 3,
        "titel": "Termine vereinbaren und verschieben",
        "ziel": "Du koordinierst Termine, sagst ab und schlägst Alternativen "
                "vor – höflich.",
        "woerter": [
            ["fissare un appuntamento", "einen Termin festlegen"],
            ["spostare", "verschieben"],
            ["annullare", "absagen"],
            ["disponibile", "verfügbar"],
            ["l'agenda", "der Kalender"],
            ["la riunione", "die Besprechung"],
            ["confermare", "bestätigen"],
            ["la scadenza", "die Frist / Deadline"],
            ["urgente", "dringend"],
            ["entro", "bis (spätestens)"],
        ],
        "saetze": [
            ["Possiamo fissare una riunione per giovedì?",
             "Können wir eine Besprechung für Donnerstag festlegen?"],
            ["Sarebbe possibile spostare l'appuntamento?",
             "Wäre es möglich, den Termin zu verschieben?"],
            ["Purtroppo giovedì non sono disponibile.",
             "Leider bin ich am Donnerstag nicht verfügbar."],
            ["Le confermo l'orario entro domani.",
             "Ich bestätige Ihnen die Zeit bis morgen."],
            ["La scadenza è la fine del mese.",
             "Die Frist ist Monatsende."],
        ],
        "grammatik": {
            "titel": "Sarebbe possibile … ?",
            "text": "Die höflichste Bitte im Geschäftsleben: „Sarebbe "
                    "possibile + Infinitiv“ – wäre es möglich zu … Genauso "
                    "brauchbar: „Le andrebbe bene …?“ (Würde es Ihnen "
                    "passen …?).",
        },
        "aufgabe": "Vereinbare laut einen Termin, verschiebe ihn, sage einen "
                   "zweiten ab und schlage eine Alternative vor.",
    },
    {
        "nr": 29,
        "block": 3,
        "titel": "E-Mails schreiben",
        "ziel": "Du schreibst eine korrekte Geschäftsmail – Anrede, Anlass, "
                "Bitte, Gruß.",
        "woerter": [
            ["Gentile Signora", "Sehr geehrte Frau"],
            ["Egregio Signore", "Sehr geehrter Herr"],
            ["Le scrivo in merito a", "ich schreibe Ihnen bezüglich"],
            ["in allegato", "im Anhang"],
            ["La ringrazio", "ich danke Ihnen"],
            ["resto in attesa", "ich verbleibe in Erwartung"],
            ["Cordiali saluti", "Mit freundlichen Grüßen"],
            ["Distinti saluti", "Mit vorzüglicher Hochachtung"],
            ["come concordato", "wie besprochen"],
            ["Le allego", "ich lege Ihnen bei"],
        ],
        "saetze": [
            ["Gentile Signora Rossi, Le scrivo in merito al nostro progetto.",
             "Sehr geehrte Frau Rossi, ich schreibe Ihnen bezüglich unseres "
             "Projekts."],
            ["In allegato trova la presentazione.",
             "Im Anhang finden Sie die Präsentation."],
            ["Le sarei grato se potesse confermare entro venerdì.",
             "Ich wäre Ihnen dankbar, wenn Sie bis Freitag bestätigen könnten."],
            ["Resto a disposizione per qualsiasi chiarimento.",
             "Ich stehe für jede Rückfrage zur Verfügung."],
            ["Cordiali saluti, Moritz Janisch",
             "Mit freundlichen Grüßen, Moritz Janisch"],
        ],
        "grammatik": {
            "titel": "Der E-Mail-Baukasten",
            "text": "Vier Bausteine, immer gleich: Anrede (Gentile …), Anlass "
                    "(Le scrivo in merito a …), Bitte (Le sarei grato se "
                    "potesse …), Schluss (Resto a disposizione. Cordiali "
                    "saluti). Damit schreibst du jede Mail.",
        },
        "aufgabe": "Schreibe eine echte Mail auf Italienisch: bitte um "
                   "Bestätigung eines Termins und kündige eine Anlage an.",
    },
    {
        "nr": 30,
        "block": 3,
        "titel": "Telefon- und Video-Calls",
        "ziel": "Du überlebst einen Video-Call inklusive Technikproblemen und "
                "Nachfragen.",
        "woerter": [
            ["la videochiamata", "der Video-Call"],
            ["Mi sente?", "Hören Sie mich?"],
            ["il microfono", "das Mikrofon"],
            ["condividere lo schermo", "den Bildschirm teilen"],
            ["la connessione", "die Verbindung"],
            ["si è interrotto", "es ist abgebrochen"],
            ["il link", "der Link"],
            ["riassumere", "zusammenfassen"],
            ["andare avanti", "weitermachen"],
            ["chiarire", "klären"],
        ],
        "saetze": [
            ["Buongiorno a tutti, mi sentite bene?",
             "Guten Tag an alle, hören Sie mich gut?"],
            ["Scusate, la connessione non è stabile.",
             "Entschuldigung, die Verbindung ist nicht stabil."],
            ["Posso condividere lo schermo?",
             "Darf ich meinen Bildschirm teilen?"],
            ["Scusi, può ripetere l'ultimo punto?",
             "Entschuldigung, können Sie den letzten Punkt wiederholen?"],
            ["Riassumo brevemente quello che abbiamo detto.",
             "Ich fasse kurz zusammen, was wir gesagt haben."],
        ],
        "grammatik": {
            "titel": "Der Call-Notausgang",
            "text": "Drei Sätze retten jeden Call: „Scusi, non ho capito "
                    "bene.“ „Può ripetere più lentamente?“ „Le mando un "
                    "riassunto per iscritto.“ Wer sie parat hat, muss nie "
                    "bluffen.",
        },
        "aufgabe": "Spiele einen Call-Beginn laut: begrüßen, Ton prüfen, "
                   "Agenda nennen, Bildschirm teilen, zusammenfassen.",
    },
    {
        "nr": 31,
        "block": 3,
        "titel": "Im Meeting mitreden",
        "ziel": "Du meldest dich zu Wort, stimmst zu, hakst nach und hältst "
                "Ergebnisse fest.",
        "woerter": [
            ["l'ordine del giorno", "die Agenda"],
            ["il punto", "der Punkt"],
            ["prendere la parola", "das Wort nehmen"],
            ["aggiungere", "hinzufügen"],
            ["proporre", "vorschlagen"],
            ["l'obiettivo", "das Ziel"],
            ["il risultato", "das Ergebnis"],
            ["i prossimi passi", "die nächsten Schritte"],
            ["verificare", "prüfen"],
            ["a mio avviso", "meines Erachtens"],
        ],
        "saetze": [
            ["Posso aggiungere una cosa?",
             "Darf ich etwas hinzufügen?"],
            ["A mio avviso dovremmo verificare i numeri prima.",
             "Meines Erachtens sollten wir zuerst die Zahlen prüfen."],
            ["Propongo di rimandare questo punto.",
             "Ich schlage vor, diesen Punkt zu verschieben."],
            ["Quindi, quali sono i prossimi passi?",
             "Also, was sind die nächsten Schritte?"],
            ["Riassumo: Lei prepara l'offerta, io parlo con il team.",
             "Ich fasse zusammen: Sie erstellen das Angebot, ich spreche mit "
             "dem Team."],
        ],
        "grammatik": {
            "titel": "dovremmo / potremmo – der Vorschlagsmodus",
            "text": "Mit dem Konditional klingt ein Vorschlag kollegial statt "
                    "fordernd: dovremmo (wir sollten), potremmo (wir "
                    "könnten), vorrei proporre (ich möchte vorschlagen).",
        },
        "aufgabe": "Melde dich laut fünfmal zu Wort: hinzufügen, "
                   "widersprechen, vorschlagen, nachfragen, zusammenfassen.",
    },
    {
        "nr": 32,
        "block": 3,
        "titel": "Zahlen im Business",
        "ziel": "Du sprichst über Umsatz, Absatz, Prozente und Quartale ohne "
                "zu stocken.",
        "woerter": [
            ["il fatturato", "der Umsatz"],
            ["la crescita", "das Wachstum"],
            ["aumentare / diminuire", "steigen / sinken"],
            ["per cento", "Prozent"],
            ["il trimestre", "das Quartal"],
            ["rispetto a", "im Vergleich zu"],
            ["la quota di mercato", "der Marktanteil"],
            ["il margine", "die Marge"],
            ["le vendite", "die Verkäufe"],
            ["circa", "etwa"],
        ],
        "saetze": [
            ["Il fatturato è aumentato del dodici per cento.",
             "Der Umsatz ist um 12 Prozent gestiegen."],
            ["Rispetto all'anno scorso siamo cresciuti.",
             "Im Vergleich zum Vorjahr sind wir gewachsen."],
            ["Nel primo trimestre le vendite sono state stabili.",
             "Im ersten Quartal waren die Verkäufe stabil."],
            ["La nostra quota di mercato è circa il venti per cento.",
             "Unser Marktanteil beträgt etwa 20 Prozent."],
            ["I margini sono sotto pressione.",
             "Die Margen sind unter Druck."],
        ],
        "grammatik": {
            "titel": "Prozent mit di + Artikel",
            "text": "Veränderungen mit „del“: è aumentato del 12%. "
                    "Vergleiche mit „rispetto a“: rispetto al 2025. "
                    "Größenordnungen: circa, quasi, oltre (über), meno di.",
        },
        "aufgabe": "Präsentiere laut fünf echte Kennzahlen aus deinem Job – "
                   "mit Veränderung, Vergleichszeitraum und Einordnung.",
    },
    {
        "nr": 33,
        "block": 3,
        "titel": "Trading Cards: dein Fachvokabular",
        "ziel": "Du sprichst über dein eigenes Produkt – der Punkt, an dem "
                "Italienisch für dich sofort nützlich wird.",
        "woerter": [
            ["la figurina", "das Sammelbild / Sticker"],
            ["la carta da collezione", "die Trading Card"],
            ["la bustina", "das Päckchen / Pack"],
            ["la scatola", "die Box"],
            ["l'espositore", "das Display"],
            ["l'autografo", "die Autogrammkarte"],
            ["la carta rara", "die seltene Karte"],
            ["la tiratura limitata", "die limitierte Auflage"],
            ["la licenza", "die Lizenz"],
            ["il lancio", "der Launch / die Einführung"],
        ],
        "saetze": [
            ["Il lancio del prodotto è previsto per settembre.",
             "Der Produktlaunch ist für September geplant."],
            ["Ogni bustina contiene cinque carte.",
             "Jedes Päckchen enthält fünf Karten."],
            ["Questa collezione ha una tiratura limitata.",
             "Diese Kollektion hat eine limitierte Auflage."],
            ["Abbiamo la licenza ufficiale del campionato.",
             "Wir haben die offizielle Lizenz der Liga."],
            ["Il segmento hobby cresce più del retail.",
             "Das Hobby-Segment wächst stärker als Retail."],
        ],
        "grammatik": {
            "titel": "Zusammensetzungen mit di und da",
            "text": "Deutsche Komposita werden im Italienischen aufgelöst: "
                    "Sammelkarte = carta da collezione, Produktlaunch = "
                    "lancio del prodotto, Marktanteil = quota di mercato. "
                    "Merke: „da“ = Zweck, „di“ = Zugehörigkeit.",
        },
        "aufgabe": "Erklär laut einem italienischen Kollegen dein aktuelles "
                   "Produkt: was es ist, Inhalt, Lizenz, Launch, Zielgruppe.",
    },
    {
        "nr": 34,
        "block": 3,
        "titel": "Produkt und Sortiment beschreiben",
        "ziel": "Du beschreibst Eigenschaften und Vorteile so, dass es "
                "überzeugt.",
        "woerter": [
            ["la caratteristica", "das Merkmal"],
            ["il vantaggio", "der Vorteil"],
            ["la qualità", "die Qualität"],
            ["il prezzo consigliato", "der empfohlene Preis"],
            ["il target", "die Zielgruppe"],
            ["adatto a", "geeignet für"],
            ["l'assortimento", "das Sortiment"],
            ["la novità", "die Neuheit"],
            ["disponibile", "verfügbar"],
            ["esaurito", "ausverkauft"],
        ],
        "saetze": [
            ["Il vantaggio principale è la qualità della stampa.",
             "Der Hauptvorteil ist die Druckqualität."],
            ["Questo prodotto è adatto ai collezionisti esperti.",
             "Dieses Produkt ist für erfahrene Sammler geeignet."],
            ["Sarà disponibile da ottobre in tutta Europa.",
             "Es wird ab Oktober in ganz Europa verfügbar sein."],
            ["Il prezzo consigliato è di quindici euro.",
             "Der empfohlene Preis liegt bei 15 Euro."],
            ["La prima edizione è già esaurita.",
             "Die erste Auflage ist bereits ausverkauft."],
        ],
        "grammatik": {
            "titel": "Steigerung",
            "text": "più … di = mehr als, meno … di = weniger als, il più … "
                    "= der/die/das …ste. „Più forte del mercato“, „il "
                    "prodotto più venduto“. Unregelmäßig: buono → migliore, "
                    "cattivo → peggiore.",
        },
        "aufgabe": "Beschreibe laut drei Produkte mit je zwei Merkmalen, "
                   "einem Vorteil und einem Vergleich zum Wettbewerb.",
    },
    {
        "nr": 35,
        "block": 3,
        "titel": "Probleme klären: Liefertermine und Reklamationen",
        "ziel": "Du klärst Verzögerungen und Fehler sachlich, ohne unhöflich "
                "zu werden.",
        "woerter": [
            ["la consegna", "die Lieferung"],
            ["il ritardo", "die Verzögerung"],
            ["la quantità", "die Menge"],
            ["il difetto", "der Mangel / Defekt"],
            ["il reclamo", "die Reklamation"],
            ["la soluzione", "die Lösung"],
            ["risolvere", "lösen"],
            ["il malinteso", "das Missverständnis"],
            ["purtroppo", "leider"],
            ["appena possibile", "so bald wie möglich"],
        ],
        "saetze": [
            ["C'è un ritardo nella consegna.",
             "Es gibt eine Verzögerung bei der Lieferung."],
            ["La quantità ricevuta non corrisponde all'ordine.",
             "Die erhaltene Menge stimmt nicht mit der Bestellung überein."],
            ["Come possiamo risolvere la situazione?",
             "Wie können wir die Situation lösen?"],
            ["Credo che ci sia stato un malinteso.",
             "Ich glaube, es gab ein Missverständnis."],
            ["Le faccio sapere appena possibile.",
             "Ich lasse es Sie so bald wie möglich wissen."],
        ],
        "grammatik": {
            "titel": "Sachlich bleiben mit unpersönlichen Formen",
            "text": "Statt Schuld zuzuweisen: „C'è stato un problema“, „Si è "
                    "verificato un ritardo“, „Credo che ci sia stato un "
                    "malinteso“. Das entschärft, ohne die Sache "
                    "abzuschwächen.",
        },
        "aufgabe": "Führe laut ein Klärungsgespräch: Problem benennen, "
                   "Auswirkung erklären, Lösung vorschlagen, Frist setzen.",
    },
    {
        "nr": 36,
        "block": 3,
        "titel": "Meilenstein 3: Der Business-Call",
        "ziel": "Du führst ein komplettes Geschäftsgespräch in der Lei-Form. "
                "Kein neuer Stoff – nur Beweis.",
        "woerter": [
            ["dunque", "also / folglich"],
            ["in effetti", "in der Tat"],
            ["per quanto riguarda", "was … betrifft"],
            ["d'altra parte", "andererseits"],
            ["in ogni caso", "in jedem Fall"],
            ["come detto", "wie gesagt"],
            ["di conseguenza", "folglich"],
            ["in sintesi", "zusammenfassend"],
            ["se ho capito bene", "wenn ich richtig verstanden habe"],
            ["La ringrazio molto", "ich danke Ihnen sehr"],
        ],
        "saetze": [
            ["Per quanto riguarda i tempi, siamo in linea.",
             "Was die Termine betrifft, sind wir im Plan."],
            ["Se ho capito bene, Lei propone di aspettare.",
             "Wenn ich richtig verstanden habe, schlagen Sie vor zu warten."],
            ["D'altra parte dobbiamo considerare i costi.",
             "Andererseits müssen wir die Kosten berücksichtigen."],
            ["In sintesi: confermiamo la data e verifichiamo i numeri.",
             "Zusammenfassend: Wir bestätigen den Termin und prüfen die "
             "Zahlen."],
            ["La ringrazio molto per il Suo tempo.",
             "Ich danke Ihnen sehr für Ihre Zeit."],
        ],
        "grammatik": {
            "titel": "Gliedern macht souverän",
            "text": "dunque, per quanto riguarda, d'altra parte, di "
                    "conseguenza, in sintesi: Wer sein Gespräch hörbar "
                    "gliedert, wirkt sicher – auch mit begrenztem "
                    "Wortschatz.",
        },
        "aufgabe": "Meilenstein: Führe einen 10-Minuten-Call laut: begrüßen, "
                   "vorstellen, Agenda, Produkt erklären, Zahlen nennen, "
                   "Problem klären, Termin vereinbaren, zusammenfassen, "
                   "verabschieden. Durchgehend Lei.",
    },
]

LEKTIONEN += [
    # ------------------------------------------------------------------
    # Block 4 – Feinschliff: Zeiten, Verhandeln, Präsentieren, Ton
    # ------------------------------------------------------------------
    {
        "nr": 37,
        "block": 4,
        "titel": "Futuro: Pläne und Zusagen",
        "ziel": "Du sprichst verbindlich über die Zukunft – wichtig für "
                "Zusagen und Roadmaps.",
        "woerter": [
            ["sarà", "es wird sein"],
            ["avrà", "er/sie wird haben"],
            ["farò", "ich werde machen"],
            ["andrò", "ich werde gehen"],
            ["manderò", "ich werde senden"],
            ["il prossimo anno", "nächstes Jahr"],
            ["presto", "bald"],
            ["più avanti", "später / weiter vorn"],
            ["prevedere", "vorsehen / planen"],
            ["garantire", "garantieren"],
        ],
        "saetze": [
            ["Le manderò l'offerta domani.",
             "Ich werde Ihnen das Angebot morgen senden."],
            ["Il prodotto sarà disponibile in autunno.",
             "Das Produkt wird im Herbst verfügbar sein."],
            ["Ne parleremo nella prossima riunione.",
             "Wir werden in der nächsten Besprechung darüber sprechen."],
            ["Presto avremo i primi risultati.",
             "Bald werden wir die ersten Ergebnisse haben."],
            ["Non prevediamo ritardi.", "Wir erwarten keine Verzögerungen."],
        ],
        "grammatik": {
            "titel": "futuro semplice",
            "text": "Endungen für alle Verben: -ò, -ai, -à, -emo, -ete, -anno "
                    "an den Stamm: parlerò, parlerai, parlerà. Häufig "
                    "unregelmäßig: essere → sarò, avere → avrò, fare → farò, "
                    "andare → andrò.",
        },
        "aufgabe": "Formuliere laut fünf berufliche Zusagen im Futur – mit "
                   "Termin, Inhalt und Verantwortlichkeit.",
    },
    {
        "nr": 38,
        "block": 4,
        "titel": "Verhandeln: fordern und nachgeben",
        "ziel": "Du verhandelst Preise und Bedingungen und behältst dabei die "
                "Beziehung.",
        "woerter": [
            ["l'offerta", "das Angebot"],
            ["la condizione", "die Bedingung"],
            ["trattare", "verhandeln"],
            ["il compromesso", "der Kompromiss"],
            ["accettare / rifiutare", "annehmen / ablehnen"],
            ["a condizione che", "unter der Bedingung, dass"],
            ["in cambio", "im Gegenzug"],
            ["il limite", "die Grenze"],
            ["ragionevole", "vernünftig / angemessen"],
            ["l'accordo", "die Vereinbarung"],
        ],
        "saetze": [
            ["La Sua offerta è interessante, ma il prezzo è troppo alto.",
             "Ihr Angebot ist interessant, aber der Preis ist zu hoch."],
            ["Possiamo accettare a condizione che la consegna sia a settembre.",
             "Wir können annehmen, unter der Bedingung, dass die Lieferung im "
             "September erfolgt."],
            ["In cambio potremmo aumentare la quantità.",
             "Im Gegenzug könnten wir die Menge erhöhen."],
            ["Questo è il nostro limite.", "Das ist unsere Grenze."],
            ["Allora siamo d'accordo, perfetto.",
             "Dann sind wir uns einig, perfekt."],
        ],
        "grammatik": {
            "titel": "Weich fordern",
            "text": "Drei Stufen: „Sarebbe possibile …?“ (Bitte), „Preferirei "
                    "…“ (Wunsch), „Purtroppo non possiamo …“ (Grenze). Wer "
                    "diese drei Register kennt, verhandelt ohne verbal "
                    "auszurutschen.",
        },
        "aufgabe": "Verhandle laut einen Preis: fordern, Gegenforderung "
                   "hören, Kompromiss anbieten, abschließen.",
    },
    {
        "nr": 39,
        "block": 4,
        "titel": "Imperfetto: beschreiben und erinnern",
        "ziel": "Du erzählst Hintergründe und Gewohnheiten – erst damit "
                "klingen Geschichten rund.",
        "woerter": [
            ["ero", "ich war"],
            ["avevo", "ich hatte"],
            ["facevo", "ich machte"],
            ["c'era", "es gab / es war"],
            ["da bambino", "als Kind"],
            ["sempre", "immer"],
            ["spesso", "oft"],
            ["mentre", "während"],
            ["una volta", "einmal / früher"],
            ["di solito", "normalerweise"],
        ],
        "saetze": [
            ["Da bambino collezionavo le figurine.",
             "Als Kind sammelte ich Sammelbilder."],
            ["Il ristorante era pieno e c'era molto rumore.",
             "Das Restaurant war voll und es war sehr laut."],
            ["Prima lavoravo in un'altra azienda.",
             "Früher arbeitete ich in einer anderen Firma."],
            ["Faceva freddo e pioveva.", "Es war kalt und es regnete."],
            ["Mentre parlavo, è arrivato il capo.",
             "Während ich sprach, kam der Chef."],
        ],
        "grammatik": {
            "titel": "imperfetto",
            "text": "Endungen: -avo, -evo, -ivo … parlavo, leggevo, dormivo. "
                    "Nur drei echte Ausnahmen: essere → ero, fare → facevo, "
                    "dire → dicevo.",
        },
        "aufgabe": "Beschreibe laut eine Erinnerung: wie es war, was du "
                   "gewöhnlich machtest, wie die Umgebung aussah.",
    },
    {
        "nr": 40,
        "block": 4,
        "titel": "Imperfetto oder passato prossimo?",
        "ziel": "Du triffst die Entscheidung, an der die meisten Lerner "
                "scheitern – sicher und schnell.",
        "woerter": [
            ["improvvisamente", "plötzlich"],
            ["all'improvviso", "auf einmal"],
            ["per tre anni", "drei Jahre lang"],
            ["ogni giorno", "jeden Tag"],
            ["a un certo punto", "irgendwann"],
            ["succedere", "passieren"],
            ["cominciare", "beginnen"],
            ["finire", "beenden"],
            ["durare", "dauern"],
            ["poi improvvisamente", "dann plötzlich"],
        ],
        "saetze": [
            ["Mangiavo tranquillamente quando è suonato il telefono.",
             "Ich aß gerade ruhig, als das Telefon klingelte."],
            ["Ogni estate andavamo in Italia.",
             "Jeden Sommer fuhren wir nach Italien."],
            ["L'anno scorso siamo andati in Sicilia.",
             "Letztes Jahr sind wir nach Sizilien gefahren."],
            ["Era tardi, così ho deciso di tornare.",
             "Es war spät, also entschied ich zurückzugehen."],
            ["La riunione è durata due ore.",
             "Die Besprechung hat zwei Stunden gedauert."],
        ],
        "grammatik": {
            "titel": "Bühne und Ereignis",
            "text": "imperfetto = Bühne (wie es war, was üblich war, "
                    "Hintergrund). passato prossimo = Ereignis (was dann "
                    "genau passierte, einmalig, abgeschlossen). Faustregel: "
                    "Kulisse imperfetto, Handlung passato prossimo.",
        },
        "aufgabe": "Erzähle laut eine kleine Geschichte mit beiden Zeiten: "
                   "erst die Kulisse, dann drei Ereignisse.",
    },
    {
        "nr": 41,
        "block": 4,
        "titel": "Condizionale: höflich und hypothetisch",
        "ziel": "Du klingst diplomatisch statt fordernd – der Ton, der im "
                "Business zählt.",
        "woerter": [
            ["vorrei", "ich möchte"],
            ["potrei", "ich könnte"],
            ["dovrei", "ich sollte"],
            ["sarebbe", "es wäre"],
            ["mi piacerebbe", "ich würde gern"],
            ["preferirei", "ich würde vorziehen"],
            ["se possibile", "wenn möglich"],
            ["direi che", "ich würde sagen, dass"],
            ["avrei una domanda", "ich hätte eine Frage"],
            ["consiglierei", "ich würde empfehlen"],
        ],
        "saetze": [
            ["Preferirei discuterne la settimana prossima.",
             "Ich würde es vorziehen, nächste Woche darüber zu sprechen."],
            ["Potrebbe inviarmi i dati?",
             "Könnten Sie mir die Daten schicken?"],
            ["Sarebbe utile avere un secondo parere.",
             "Es wäre nützlich, eine zweite Meinung zu haben."],
            ["Direi che è la soluzione migliore.",
             "Ich würde sagen, das ist die beste Lösung."],
            ["Mi piacerebbe visitare la vostra sede.",
             "Ich würde gern Ihren Standort besuchen."],
        ],
        "grammatik": {
            "titel": "condizionale",
            "text": "Wie das Futur, aber mit -ei, -esti, -ebbe, -emmo, "
                    "-este, -ebbero: parlerei, parleresti, parlerebbe. Gleiche "
                    "unregelmäßige Stämme wie im Futur: sarei, avrei, farei.",
        },
        "aufgabe": "Nimm fünf direkte Forderungen und formuliere sie laut ins "
                   "Konditional um – höflich, aber klar.",
    },
    {
        "nr": 42,
        "block": 4,
        "titel": "Präsentieren",
        "ziel": "Du führst durch eine Präsentation und hältst die Zuhörer.",
        "woerter": [
            ["la presentazione", "die Präsentation"],
            ["la diapositiva", "die Folie"],
            ["prima di tutto", "zunächst einmal"],
            ["passiamo a", "gehen wir zu"],
            ["come si vede", "wie man sieht"],
            ["vorrei sottolineare", "ich möchte betonen"],
            ["in conclusione", "abschließend"],
            ["il grafico", "die Grafik"],
            ["la domanda", "die Frage"],
            ["Grazie per l'attenzione", "Danke für die Aufmerksamkeit"],
        ],
        "saetze": [
            ["Prima di tutto vorrei ringraziarvi per l'invito.",
             "Zunächst möchte ich Ihnen für die Einladung danken."],
            ["Oggi vi presento i risultati del primo semestre.",
             "Heute stelle ich Ihnen die Ergebnisse des ersten Halbjahres vor."],
            ["Come si vede dal grafico, la crescita continua.",
             "Wie man an der Grafik sieht, hält das Wachstum an."],
            ["Vorrei sottolineare tre punti.",
             "Ich möchte drei Punkte betonen."],
            ["In conclusione: grazie per l'attenzione, avete domande?",
             "Abschließend: Danke für die Aufmerksamkeit, haben Sie Fragen?"],
        ],
        "grammatik": {
            "titel": "Der Präsentations-Rahmen",
            "text": "Vier Signale genügen: Einstieg (Prima di tutto …), "
                    "Übergang (Passiamo a …), Betonung (Vorrei sottolineare "
                    "…), Schluss (In conclusione …). Dazwischen darf dein "
                    "Italienisch einfach bleiben.",
        },
        "aufgabe": "Halte laut eine 3-Minuten-Präsentation über ein echtes "
                   "Produkt – mit allen vier Signalen.",
    },
    {
        "nr": 43,
        "block": 4,
        "titel": "Pronomen: lo, la, ne, ci",
        "ziel": "Du wiederholst nicht mehr jedes Wort – dein Italienisch "
                "wirkt dadurch sofort erwachsener.",
        "woerter": [
            ["lo / la", "ihn / sie (Sache)"],
            ["li / le", "sie (Mehrzahl)"],
            ["ne", "davon"],
            ["ci", "dort / dabei"],
            ["ce l'ho", "ich habe es"],
            ["lo so", "ich weiß es"],
            ["non lo so", "ich weiß es nicht"],
            ["me lo mandi?", "schickst du es mir?"],
            ["ci penso io", "ich kümmere mich darum"],
            ["ne parliamo", "wir sprechen darüber"],
        ],
        "saetze": [
            ["Hai visto il campione? – Sì, l'ho visto.",
             "Hast du das Muster gesehen? – Ja, ich habe es gesehen."],
            ["Quante scatole vuoi? – Ne prendo dieci.",
             "Wie viele Boxen willst du? – Ich nehme zehn davon."],
            ["Ci penso io, non si preoccupi.",
             "Ich kümmere mich darum, machen Sie sich keine Sorgen."],
            ["Ne parliamo domani.", "Wir sprechen morgen darüber."],
            ["Me lo può confermare per iscritto?",
             "Können Sie mir das schriftlich bestätigen?"],
        ],
        "grammatik": {
            "titel": "Pronomen stehen vor dem Verb",
            "text": "„Lo vedo“, „ne prendo due“, „ci vado“. Beim Infinitiv "
                    "hängen sie hinten an: „posso vederlo“, „devo farlo“. Mit "
                    "avere-Vergangenheit passt sich das Partizip an: „l'ho "
                    "vista“.",
        },
        "aufgabe": "Nimm zehn Sätze mit Wiederholung und ersetze das "
                   "wiederholte Wort laut durch lo, la, ne oder ci.",
    },
    {
        "nr": 44,
        "block": 4,
        "titel": "Congiuntivo, so viel du brauchst",
        "ziel": "Du beherrschst den Konjunktiv in den fünf Wendungen, in "
                "denen er wirklich vorkommt.",
        "woerter": [
            ["penso che sia", "ich denke, dass es ist"],
            ["credo che sia", "ich glaube, dass es ist"],
            ["spero che", "ich hoffe, dass"],
            ["è importante che", "es ist wichtig, dass"],
            ["benché / anche se", "obwohl"],
            ["sia", "sei (Konjunktiv von essere)"],
            ["abbia", "habe (Konjunktiv von avere)"],
            ["possa", "könne"],
            ["faccia", "mache"],
            ["prima che", "bevor"],
        ],
        "saetze": [
            ["Penso che sia una buona idea.",
             "Ich denke, dass es eine gute Idee ist."],
            ["Spero che il prodotto piaccia ai clienti.",
             "Ich hoffe, dass das Produkt den Kunden gefällt."],
            ["È importante che tutti siano informati.",
             "Es ist wichtig, dass alle informiert sind."],
            ["Credo che abbiano già deciso.",
             "Ich glaube, dass sie schon entschieden haben."],
            ["Benché sia complicato, è possibile.",
             "Obwohl es kompliziert ist, ist es möglich."],
        ],
        "grammatik": {
            "titel": "Fünf Auslöser genügen",
            "text": "Nach penso/credo che, spero che, è importante che, "
                    "benché und prima che steht der Konjunktiv. Merke nur "
                    "sia, abbia, possa, faccia, vada – damit deckst du fast "
                    "alles ab. Und: „Penso di sì“ umgeht ihn ganz.",
        },
        "aufgabe": "Formuliere laut zehn Meinungen mit „penso che“ und "
                   "„credo che“ – beruflich und privat gemischt.",
    },
    {
        "nr": 45,
        "block": 4,
        "titel": "Widersprechen, ohne zu verletzen",
        "ziel": "Du sagst Nein und Anderer-Meinung auf eine Weise, die "
                "Beziehungen erhält.",
        "woerter": [
            ["non sono sicuro", "ich bin nicht sicher"],
            ["capisco il punto, però", "ich verstehe den Punkt, aber"],
            ["vedo le cose diversamente", "ich sehe die Dinge anders"],
            ["temo che", "ich fürchte, dass"],
            ["in parte sì", "teilweise ja"],
            ["mi permetta", "erlauben Sie mir"],
            ["forse mi sbaglio", "vielleicht irre ich mich"],
            ["il rischio", "das Risiko"],
            ["il dubbio", "der Zweifel"],
            ["riconsiderare", "neu überdenken"],
        ],
        "saetze": [
            ["Capisco il Suo punto, però vedo un rischio.",
             "Ich verstehe Ihren Punkt, aber ich sehe ein Risiko."],
            ["Forse mi sbaglio, ma i numeri dicono altro.",
             "Vielleicht irre ich mich, aber die Zahlen sagen etwas anderes."],
            ["Temo che i tempi siano troppo stretti.",
             "Ich fürchte, die Zeiten sind zu knapp."],
            ["In parte sono d'accordo, in parte no.",
             "Teilweise stimme ich zu, teilweise nicht."],
            ["Le propongo di riconsiderare questo punto.",
             "Ich schlage Ihnen vor, diesen Punkt neu zu überdenken."],
        ],
        "grammatik": {
            "titel": "Die Dreischritt-Widerrede",
            "text": "1. Anerkennen: „Capisco …“ 2. Einwand mit però oder "
                    "temo che. 3. Vorschlag: „Le propongo di …“ Nie mit „no“ "
                    "beginnen – der Einwand kommt in der Mitte.",
        },
        "aufgabe": "Widersprich laut fünfmal nach dem Dreischritt – "
                   "anerkennen, einwenden, vorschlagen.",
    },
    {
        "nr": 46,
        "block": 4,
        "titel": "Ton und Redewendungen",
        "ziel": "Du klingst wie ein Mensch, nicht wie ein Lehrbuch.",
        "woerter": [
            ["in bocca al lupo", "viel Glück"],
            ["figurati", "keine Ursache"],
            ["dai!", "komm schon!"],
            ["meno male", "zum Glück"],
            ["più o meno", "mehr oder weniger"],
            ["a proposito", "übrigens"],
            ["tutto sommato", "alles in allem"],
            ["fare il punto", "Bilanz ziehen"],
            ["andare a gonfie vele", "bestens laufen"],
            ["non vedo l'ora", "ich kann es kaum erwarten"],
        ],
        "saetze": [
            ["A proposito, come va il progetto?",
             "Übrigens, wie läuft das Projekt?"],
            ["Tutto sommato è andata bene.",
             "Alles in allem ist es gut gelaufen."],
            ["Meno male che abbiamo controllato.",
             "Zum Glück haben wir kontrolliert."],
            ["Facciamo il punto la settimana prossima.",
             "Ziehen wir nächste Woche Bilanz."],
            ["Non vedo l'ora di vedere i risultati.",
             "Ich kann es kaum erwarten, die Ergebnisse zu sehen."],
        ],
        "grammatik": {
            "titel": "Dosierung",
            "text": "Redewendungen wirken nur sparsam eingesetzt: eine pro "
                    "Gespräch macht dich sympathisch, fünf machen dich "
                    "anstrengend. Sicher sind: a proposito, tutto sommato, "
                    "meno male, in bocca al lupo.",
        },
        "aufgabe": "Baue in fünf laute Alltagssätze je eine Wendung ein – "
                   "und prüfe, ob sie natürlich klingt.",
    },
    {
        "nr": 47,
        "block": 4,
        "titel": "Messe und Netzwerken",
        "ziel": "Du arbeitest einen Messestand ab: ansprechen, erklären, "
                "Kontakt sichern.",
        "woerter": [
            ["la fiera", "die Messe"],
            ["lo stand", "der Stand"],
            ["il biglietto da visita", "die Visitenkarte"],
            ["il visitatore", "der Besucher"],
            ["presentare", "vorstellen"],
            ["il contatto", "der Kontakt"],
            ["restare in contatto", "in Kontakt bleiben"],
            ["il catalogo", "der Katalog"],
            ["l'anteprima", "die Vorschau"],
            ["passare da", "vorbeikommen bei"],
        ],
        "saetze": [
            ["Benvenuto al nostro stand, posso mostrarLe le novità?",
             "Willkommen an unserem Stand, darf ich Ihnen die Neuheiten "
             "zeigen?"],
            ["Ecco il mio biglietto da visita.",
             "Hier ist meine Visitenkarte."],
            ["Le mando il catalogo per e-mail.",
             "Ich schicke Ihnen den Katalog per E-Mail."],
            ["Restiamo in contatto, mi scriva quando vuole.",
             "Bleiben wir in Kontakt, schreiben Sie mir, wann Sie möchten."],
            ["Passi domani, avremo un'anteprima.",
             "Kommen Sie morgen vorbei, wir haben eine Vorschau."],
        ],
        "grammatik": {
            "titel": "Höflicher Imperativ",
            "text": "Bei Lei endet der Imperativ auf -i bzw. -a: „Passi!“ "
                    "(kommen Sie vorbei), „Mi scriva!“, „Prenda!“, „Si "
                    "accomodi!“. Freundlich, wenn du „per favore“ oder "
                    "„prego“ danebenstellst.",
        },
        "aufgabe": "Spiele drei Standgespräche laut: ansprechen, Produkt "
                   "erklären, Kontakt vereinbaren, verabschieden.",
    },
    {
        "nr": 48,
        "block": 4,
        "titel": "Meilenstein 4: Verhandlung und Präsentation",
        "ziel": "Du führst das komplette Programm: präsentieren, verhandeln, "
                "widersprechen, abschließen. Der Abschluss des Kurses.",
        "woerter": [
            ["il punto chiave", "der Kernpunkt"],
            ["il valore aggiunto", "der Mehrwert"],
            ["a lungo termine", "langfristig"],
            ["la fiducia", "das Vertrauen"],
            ["la collaborazione", "die Zusammenarbeit"],
            ["il prossimo passo", "der nächste Schritt"],
            ["mettere per iscritto", "schriftlich festhalten"],
            ["contare su", "sich verlassen auf"],
            ["chiudere l'accordo", "die Vereinbarung abschließen"],
            ["è stato un piacere", "es war ein Vergnügen"],
        ],
        "saetze": [
            ["Il punto chiave è il valore aggiunto per il collezionista.",
             "Der Kernpunkt ist der Mehrwert für den Sammler."],
            ["Pensiamo a una collaborazione a lungo termine.",
             "Wir denken an eine langfristige Zusammenarbeit."],
            ["Se siamo d'accordo, mettiamo tutto per iscritto.",
             "Wenn wir einig sind, halten wir alles schriftlich fest."],
            ["Può contare su di noi.", "Sie können sich auf uns verlassen."],
            ["È stato un piacere, chiudiamo così.",
             "Es war ein Vergnügen, so schließen wir ab."],
        ],
        "grammatik": {
            "titel": "Alles zusammen",
            "text": "Präsens, beide Vergangenheiten, Futur, Konditional, "
                    "Konjunktiv-Grundformen, Lei und Pronomen: Du hast alles, "
                    "was ein Gespräch braucht. Ab hier gewinnst du nur noch "
                    "durch Reden, nicht mehr durch Lernen.",
        },
        "aufgabe": "Meilenstein: 15 Minuten laut – präsentiere ein Produkt, "
                   "verhandle Preis und Termin, widersprich einmal "
                   "diplomatisch, schließe ab. Danach: suche dir einen echten "
                   "Gesprächspartner.",
    },
]

# Aussprache-Hinweise, die im Reiter oben stehen. Kurz gehalten – nur die
# Punkte, an denen Deutsche systematisch falsch liegen.
AUSSPRACHE = [
    ["c + e/i", "wie „tsch“: ciao, cena, dolci"],
    ["c + a/o/u", "wie „k“: casa, conto, cultura"],
    ["ch", "immer „k“: chiave, perché, anche"],
    ["g + e/i", "wie „dsch“: gelato, giorno"],
    ["gli", "wie „lj“: famiglia, figlio"],
    ["gn", "wie „nj“: signore, bagno"],
    ["sc + e/i", "wie „sch“: scena, uscire"],
    ["z", "wie „ts“ oder „ds“: pizza, zero"],
    ["Doppelkonsonant", "wirklich doppelt halten: anno ≠ ano"],
    ["Betonung", "meist zweitletzte Silbe; Akzent zeigt Abweichung: caffè"],
]


def kurs_daten():
    """Kompakte Struktur für die Seite. Wird zu JSON und landet im Browser."""
    return {
        "bloecke": BLOECKE,
        "lektionen": LEKTIONEN,
        "aussprache": AUSSPRACHE,
    }
