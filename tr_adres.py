"""
Türkiye il / ilçe / mahalle veri seti.
Tüm 81 il, tüm ilçeler; büyük kentsel ilçeler için gerçek mahalle isimleri,
diğerleri için genel yaygın mahalle adları.
"""

from __future__ import annotations

DIGER_MAHALLE = "Diğer (elle yazınız)"

# ─── İl → İlçe eşlemesi (81 il, alfabetik) ───────────────────────────────────
IL_ILCE: dict[str, list[str]] = {
    "Adana":           ["Aladağ","Ceyhan","Çukurova","Feke","İmamoğlu","Karaisalı","Karataş","Kozan","Pozantı","Saimbeyli","Sarıçam","Seyhan","Tufanbeyli","Yumurtalık","Yüreğir"],
    "Adıyaman":        ["Besni","Çelikhan","Gerger","Gölbaşı","Kahta","Merkez","Samsat","Sincik","Tut"],
    "Afyonkarahisar":  ["Başmakçı","Bayat","Bolvadin","Çay","Çobanlar","Dazkırı","Dinar","Emirdağ","Evciler","Hocalar","İhsaniye","İscehisar","Kızılören","Merkez","Sandıklı","Sinanpaşa","Sultandağı","Şuhut"],
    "Ağrı":            ["Diyadin","Doğubayazıt","Eleşkirt","Hamur","Merkez","Patnos","Taşlıçay","Tutak"],
    "Aksaray":         ["Ağaçören","Eskil","Gülağaç","Güzelyurt","Merkez","Ortaköy","Sarıyahşi","Sultanhanı"],
    "Amasya":          ["Göynücek","Gümüşhacıköy","Hamamözü","Merkez","Merzifon","Suluova","Taşova"],
    "Ankara":          ["Akyurt","Altındağ","Ayaş","Bala","Beypazarı","Çamlıdere","Çankaya","Çubuk","Elmadağ","Etimesgut","Evren","Gölbaşı","Güdül","Haymana","Kalecik","Kazan","Keçiören","Kızılcahamam","Mamak","Nallıhan","Polatlı","Pursaklar","Sincan","Şereflikoçhisar","Yenimahalle"],
    "Antalya":         ["Aksu","Alanya","Döşemealtı","Elmalı","Finike","Gazipaşa","Gündoğmuş","İbradı","Kaş","Kemer","Kepez","Konyaaltı","Korkuteli","Kumluca","Manavgat","Muratpaşa","Serik"],
    "Ardahan":         ["Çıldır","Damal","Göle","Hanak","Merkez","Posof"],
    "Artvin":          ["Ardanuç","Arhavi","Borçka","Hopa","Kemalpaşa","Merkez","Murgul","Şavşat","Yusufeli"],
    "Aydın":           ["Bozdoğan","Buharkent","Çine","Didim","Efeler","Germencik","İncirliova","Karacasu","Karpuzlu","Koçarlı","Köşk","Kuşadası","Kuyucak","Nazilli","Söke","Sultanhisar","Yenipazar"],
    "Balıkesir":       ["Altıeylül","Ayvalık","Balya","Bandırma","Bigadiç","Burhaniye","Dursunbey","Edremit","Erdek","Gömeç","Gönen","Havran","İvrindi","Karesi","Kepsut","Manyas","Marmara","Savaştepe","Sındırgı","Susurluk"],
    "Bartın":          ["Arit","Kurucaşile","Merkez","Ulus"],
    "Batman":          ["Beşiri","Gercüş","Hasankeyf","Kozluk","Merkez","Sason"],
    "Bayburt":         ["Aydıntepe","Demirözü","Merkez"],
    "Bilecik":         ["Bozüyük","Gölpazarı","İnhisar","Merkez","Osmaneli","Pazaryeri","Söğüt","Yenipazar"],
    "Bingöl":          ["Adaklı","Genç","Karlıova","Kiğı","Merkez","Solhan","Yayladere","Yedisu"],
    "Bitlis":          ["Adilcevaz","Ahlat","Güroymak","Hizan","Merkez","Mutki","Tatvan"],
    "Bolu":            ["Dörtdivan","Gerede","Göynük","Kıbrıscık","Mengen","Merkez","Mudurnu","Seben","Yeniçağa"],
    "Burdur":          ["Ağlasun","Altınyayla","Bucak","Çavdır","Çeltikçi","Gölhisar","Karamanlı","Kemer","Merkez","Tefenni","Yeşilova"],
    "Bursa":           ["Büyükorhan","Gemlik","Gürsu","Harmancık","İnegöl","İznik","Karacabey","Keles","Kestel","Mudanya","Mustafakemalpaşa","Nilüfer","Orhaneli","Orhangazi","Osmangazi","Yenişehir","Yıldırım"],
    "Çanakkale":       ["Ayvacık","Bayramiç","Biga","Bozcaada","Çan","Eceabat","Ezine","Gelibolu","Gökçeada","Lapseki","Merkez","Yenice"],
    "Çankırı":         ["Atkaracalar","Bayramören","Çerkeş","Eldivan","Ilgaz","Kızılırmak","Korgun","Kurşunlu","Merkez","Orta","Şabanözü","Yapraklı"],
    "Çorum":           ["Alaca","Bayat","Boğazkale","Dodurga","İskilip","Kargı","Laçin","Mecitözü","Merkez","Oğuzlar","Ortaköy","Osmancık","Sungurlu","Uğurludağ"],
    "Denizli":         ["Acıpayam","Babadağ","Baklan","Bekilli","Beyağaç","Bozkurt","Buldan","Çal","Çameli","Çardak","Çivril","Güney","Honaz","Kale","Merkezefendi","Pamukkale","Sarayköy","Serinhisar","Tavas"],
    "Diyarbakır":      ["Bağlar","Bismil","Çermik","Çınar","Çüngüş","Dicle","Eğil","Ergani","Hani","Hazro","Kayapınar","Kocaköy","Kulp","Lice","Silvan","Sur","Yenişehir"],
    "Düzce":           ["Akçakoca","Cumayeri","Çilimli","Gölyaka","Gümüşova","Kaynaşlı","Merkez","Yığılca"],
    "Edirne":          ["Enez","Havsa","İpsala","Keşan","Lalapaşa","Merkez","Meriç","Süloğlu","Uzunköprü"],
    "Elazığ":          ["Ağın","Alacakaya","Arıcak","Baskil","Karakoçan","Keban","Kovancılar","Maden","Merkez","Palu","Sivrice"],
    "Erzincan":        ["Çayırlı","İliç","Kemah","Kemaliye","Merkez","Otlukbeli","Refahiye","Tercan","Üzümlü"],
    "Erzurum":         ["Aşkale","Aziziye","Çat","Hınıs","Horasan","İspir","Karaçoban","Karayazı","Köprüköy","Narman","Oltu","Olur","Palandöken","Pasinler","Pazaryolu","Şenkaya","Tekman","Tortum","Uzundere","Yakutiye"],
    "Eskişehir":       ["Alpu","Beylikova","Çifteler","Günyüzü","Han","İnönü","Mahmudiye","Mihalgazi","Mihalıççık","Odunpazarı","Sarıcakaya","Seyitgazi","Sivrihisar","Tepebaşı"],
    "Gaziantep":       ["Araban","İslahiye","Karkamış","Nizip","Nurdağı","Oğuzeli","Şahinbey","Şehitkamil","Yavuzeli"],
    "Giresun":         ["Alucra","Bulancak","Çamoluk","Çanakçı","Dereli","Doğankent","Espiye","Eynesil","Görele","Güce","Keşap","Merkez","Piraziz","Şebinkarahisar","Tirebolu","Yağlıdere"],
    "Gümüşhane":       ["Kelkit","Köse","Kürtün","Merkez","Şiran","Torul"],
    "Hakkari":         ["Çukurca","Derecik","Merkez","Şemdinli","Yüksekova"],
    "Hatay":           ["Altınözü","Antakya","Arsuz","Belen","Defne","Dörtyol","Erzin","Hassa","İskenderun","Kırıkhan","Kumlu","Payas","Reyhanlı","Samandağ","Yayladağı"],
    "Iğdır":           ["Aralık","Karakoyunlu","Merkez","Tuzluca"],
    "Isparta":         ["Aksu","Atabey","Eğirdir","Gelendost","Gönen","Keçiborlu","Merkez","Senirkent","Sütçüler","Şarkikaraağaç","Uluborlu","Yalvaç","Yenişarbademli"],
    "İstanbul":        ["Adalar","Arnavutköy","Ataşehir","Avcılar","Bağcılar","Bahçelievler","Bakırköy","Başakşehir","Bayrampaşa","Beşiktaş","Beykoz","Beylikdüzü","Beyoğlu","Büyükçekmece","Çatalca","Çekmeköy","Esenler","Esenyurt","Eyüpsultan","Fatih","Gaziosmanpaşa","Güngören","Kadıköy","Kağıthane","Kartal","Küçükçekmece","Maltepe","Pendik","Sancaktepe","Sarıyer","Silivri","Sultanbeyli","Sultangazi","Şile","Şişli","Tuzla","Ümraniye","Üsküdar","Zeytinburnu"],
    "İzmir":           ["Aliağa","Balçova","Bayındır","Bayraklı","Bergama","Beydağ","Bornova","Buca","Çeşme","Çiğli","Dikili","Foça","Gaziemir","Güzelbahçe","Karabağlar","Karaburun","Karşıyaka","Kemalpaşa","Kınık","Kiraz","Konak","Menderes","Menemen","Narlıdere","Ödemiş","Seferihisar","Selçuk","Tire","Torbalı","Urla"],
    "Kahramanmaraş":   ["Afşin","Andırın","Çağlayancerit","Dulkadiroğlu","Ekinözü","Elbistan","Göksun","Nurhak","Onikişubat","Pazarcık","Türkoğlu"],
    "Karabük":         ["Eflani","Eskipazar","Merkez","Ovacık","Safranbolu","Yenice"],
    "Karaman":         ["Ayrancı","Başyayla","Ermenek","Kazımkarabekir","Merkez","Sarıveliler"],
    "Kars":            ["Akyaka","Arpaçay","Digor","Kağızman","Merkez","Sarıkamış","Selim","Susuz"],
    "Kastamonu":       ["Abana","Ağlı","Araç","Azdavay","Bozkurt","Cide","Çatalzeytin","Daday","Devrekani","Doğanyurt","Hanönü","İhsangazi","İnebolu","Küre","Merkez","Pınarbaşı","Seydiler","Şenpazar","Taşköprü","Tosya"],
    "Kayseri":         ["Akkışla","Bünyan","Develi","Felahiye","Hacılar","İncesu","Kocasinan","Melikgazi","Özvatan","Pınarbaşı","Sarıoğlan","Sarız","Tomarza","Yahyalı","Yeşilhisar"],
    "Kırıkkale":       ["Bahşili","Balışeyh","Çelebi","Delice","Karakeçili","Keskin","Merkez","Sulakyurt","Yahşihan"],
    "Kırklareli":      ["Babaeski","Demirköy","Kofçaz","Lüleburgaz","Merkez","Pehlivanköy","Pınarhisar","Vize"],
    "Kırşehir":        ["Akçakent","Akpınar","Boztepe","Çiçekdağı","Kaman","Merkez","Mucur"],
    "Kilis":           ["Elbeyli","Merkez","Musabeyli","Polateli"],
    "Kocaeli":         ["Başiskele","Çayırova","Darıca","Derince","Dilovası","Gebze","Gölcük","İzmit","Kandıra","Karamürsel","Kartepe","Körfez"],
    "Konya":           ["Ahırlı","Akören","Akşehir","Altınekin","Beyşehir","Bozkır","Cihanbeyli","Çeltik","Çumra","Derbent","Derebucak","Doğanhisar","Emirgazi","Ereğli","Güneysınır","Hadim","Halkapınar","Hüyük","Ilgın","Kadınhanı","Karapınar","Karatay","Kulu","Meram","Sarayönü","Selçuklu","Seydişehir","Taşkent","Tuzlukçu","Yalıhüyük","Yunak"],
    "Kütahya":         ["Altıntaş","Aslanapa","Çavdarhisar","Domaniç","Dumlupınar","Emet","Gediz","Hisarcık","Merkez","Pazarlar","Simav","Şaphane","Tavşanlı"],
    "Malatya":         ["Akçadağ","Arapgir","Arguvan","Battalgazi","Darende","Doğanşehir","Doğanyol","Hekimhan","Kale","Kuluncak","Pütürge","Yazıhan","Yeşilyurt"],
    "Manisa":          ["Ahmetli","Akhisar","Alaşehir","Demirci","Gölmarmara","Gördes","Kırkağaç","Köprübaşı","Kula","Salihli","Sarıgöl","Saruhanlı","Selendi","Soma","Şehzadeler","Turgutlu","Yunusemre"],
    "Mardin":          ["Artuklu","Dargeçit","Derik","Kızıltepe","Mazıdağı","Midyat","Nusaybin","Ömerli","Savur","Yeşilli"],
    "Mersin":          ["Akdeniz","Anamur","Aydıncık","Bozyazı","Çamlıyayla","Erdemli","Gülnar","Mezitli","Mut","Silifke","Tarsus","Toroslar","Yenişehir"],
    "Muğla":           ["Bodrum","Dalaman","Datça","Fethiye","Kavaklıdere","Köyceğiz","Marmaris","Menteşe","Milas","Ortaca","Seydikemer","Ula","Yatağan"],
    "Muş":             ["Bulanık","Hasköy","Korkut","Malazgirt","Merkez","Varto"],
    "Nevşehir":        ["Acıgöl","Avanos","Derinkuyu","Gülşehir","Hacıbektaş","Kozaklı","Merkez","Ürgüp"],
    "Niğde":           ["Altunhisar","Bor","Çamardı","Çiftlik","Merkez","Ulukışla"],
    "Ordu":            ["Akkuş","Altınordu","Aybastı","Çamaş","Çatalpınar","Çaybaşı","Fatsa","Gölköy","Gülyalı","Gürgentepe","İkizce","Kabadüz","Kabataş","Korgan","Kumru","Mesudiye","Perşembe","Ulubey","Ünye"],
    "Osmaniye":        ["Bahçe","Düziçi","Hasanbeyli","Kadirli","Merkez","Sumbas","Toprakkale"],
    "Rize":            ["Ardeşen","Çamlıhemşin","Çayeli","Derepazarı","Fındıklı","Güneysu","Hemşin","İkizdere","İyidere","Kalkandere","Merkez","Pazar"],
    "Sakarya":         ["Adapazarı","Akyazı","Arifiye","Erenler","Ferizli","Geyve","Hendek","Karapürçek","Karasu","Kaynarca","Kocaali","Pamukova","Sapanca","Serdivan","Söğütlü","Taraklı"],
    "Samsun":          ["Alaçam","Asarcık","Atakum","Ayvacık","Bafra","Canik","Çarşamba","Havza","İlkadım","Kavak","Ladik","Ondokuzmayıs","Salıpazarı","Tekkeköy","Terme","Vezirköprü","Yakakent"],
    "Siirt":           ["Baykan","Eruh","Kurtalan","Merkez","Pervari","Şirvan","Tillo"],
    "Sinop":           ["Ayancık","Boyabat","Dikmen","Durağan","Erfelek","Gerze","Merkez","Saraydüzü","Türkeli"],
    "Sivas":           ["Akıncılar","Altınyayla","Divriği","Doğanşar","Gemerek","Gölova","Gürun","Hafik","İmranlı","Kangal","Koyulhisar","Merkez","Suşehri","Şarkışla","Ulaş","Yıldızeli","Zara"],
    "Şanlıurfa":       ["Akçakale","Birecik","Bozova","Ceylanpınar","Eyyübiye","Halfeti","Haliliye","Harran","Hilvan","Karaköprü","Siverek","Suruç","Viranşehir"],
    "Şırnak":          ["Beytüşşebap","Cizre","Güçlükonak","İdil","Merkez","Silopi","Uludere"],
    "Tekirdağ":        ["Çerkezköy","Çorlu","Ergene","Hayrabolu","Kapaklı","Malkara","Marmaraereğlisi","Muratlı","Saray","Süleymanpaşa","Şarköy"],
    "Tokat":           ["Almus","Artova","Başçiftlik","Erbaa","Merkez","Niksar","Pazar","Reşadiye","Sulusaray","Turhal","Yeşilyurt","Zile"],
    "Trabzon":         ["Akçaabat","Araklı","Arsin","Beşikdüzü","Çarşıbaşı","Çaykara","Dernekpazarı","Düzköy","Hayrat","Köprübaşı","Maçka","Of","Ortahisar","Sürmene","Şalpazarı","Tonya","Vakfıkebir","Yomra"],
    "Tunceli":         ["Çemişgezek","Hozat","Mazgirt","Merkez","Nazımiye","Ovacık","Pertek","Pülümür"],
    "Uşak":            ["Banaz","Eşme","Karahallı","Merkez","Sivaslı","Ulubey"],
    "Van":             ["Bahçesaray","Başkale","Çaldıran","Çatak","Edremit","Erciş","Gevaş","Gürpınar","İpekyolu","Muradiye","Özalp","Saray","Tuşba"],
    "Yalova":          ["Altınova","Armutlu","Çiftlikköy","Çınarcık","Merkez","Termal"],
    "Yozgat":          ["Akdağmadeni","Aydıncık","Boğazlıyan","Çandır","Çayıralan","Çekerek","Kadışehri","Merkez","Saraykent","Sarıkaya","Şefaatli","Sorgun","Yenifakılı","Yerköy"],
    "Zonguldak":       ["Alaplı","Çaycuma","Devrek","Ereğli","Gökçebey","Kilimli","Kozlu","Merkez"],
}

# ─── Genel mahalle listesi (tüm ilçelere varsayılan) ─────────────────────────
_GENEL = [
    "Atatürk Mah.","Bahçelievler Mah.","Bağlar Mah.","Barbaros Mah.",
    "Cumhuriyet Mah.","Çiçek Mah.","Çınarlı Mah.","Fatih Mah.",
    "Güneş Mah.","Güven Mah.","Hürriyet Mah.","İnönü Mah.",
    "Karadeniz Mah.","Kültür Mah.","Merkez Mah.","Mithatpaşa Mah.",
    "Namık Kemal Mah.","Nüfus Mah.","Reşatbey Mah.","Sakarya Mah.",
    "Sanayi Mah.","Sevgi Mah.","Şehit Mah.","Uğur Mumcu Mah.",
    "Vatan Mah.","Yeşil Mah.","Yeni Mah.","Yıldız Mah.",
    DIGER_MAHALLE,
]

# ─── Büyük kentsel ilçeler için gerçek mahalle listeleri ─────────────────────
ILCE_MAHALLE: dict[str, list[str]] = {
    # ── İSTANBUL ──────────────────────────────────────────────────────────────
    "Kadıköy":       ["Acıbadem Mah.","Bostancı Mah.","Caferağa Mah.","Caddebostan Mah.","Erenköy Mah.","Fenerbahçe Mah.","Göztepe Mah.","Koşuyolu Mah.","Kozyatağı Mah.","Moda Mah.","Osmanağa Mah.","Rasimpaşa Mah.","Suadiye Mah.","Zühtüpaşa Mah.", DIGER_MAHALLE],
    "Beşiktaş":      ["Abbasağa Mah.","Arnavutköy Mah.","Balmumcu Mah.","Bebek Mah.","Dikilitaş Mah.","Etiler Mah.","Kuruçeşme Mah.","Levent Mah.","Muradiye Mah.","Ortaköy Mah.","Sinanpaşa Mah.","Türkali Mah.","Vişnezade Mah.","Yıldız Mah.", DIGER_MAHALLE],
    "Şişli":         ["Bomonti Mah.","Cumhuriyet Mah.","Elmadağ Mah.","Esentepe Mah.","Feriköy Mah.","Gülbahar Mah.","Harbiye Mah.","Halaskargazi Mah.","Mecidiyeköy Mah.","Meşrutiyet Mah.","Nişantaşı Mah.","Teşvikiye Mah.", DIGER_MAHALLE],
    "Beyoğlu":       ["Asmalımescit Mah.","Bülbül Mah.","Cihangir Mah.","Çukurcuma Mah.","Galata Mah.","Hacıahmet Mah.","Kameriye Mah.","Kulaksız Mah.","Pürtelaş Mah.","Serdar-ı Ekrem Mah.","Sofyalı Mah.","Tomtom Mah.", DIGER_MAHALLE],
    "Üsküdar":       ["Altunizade Mah.","Aziz Mahmut Hüdayi Mah.","Bulgurlu Mah.","Çengelköy Mah.","Güzeltepe Mah.","Kirazlıtepe Mah.","Kuzguncuk Mah.","Küçüksu Mah.","Mimar Sinan Mah.","Selimiye Mah.","Validebağ Mah.", DIGER_MAHALLE],
    "Ataşehir":      ["Barbaros Mah.","Esatpaşa Mah.","Ferhatpaşa Mah.","İçerenköy Mah.","İnönü Mah.","Kayışdağı Mah.","Küçükbakkalköy Mah.","Mevlana Mah.","Mustafa Kemal Mah.","Yenisahra Mah.", DIGER_MAHALLE],
    "Maltepe":       ["Bağlarbaşı Mah.","Başıbüyük Mah.","Cevizli Mah.","Esenyalı Mah.","Girne Mah.","Gülsuyu Mah.","İdealtepe Mah.","Küçükyalı Mah.","Zümrütevler Mah.", DIGER_MAHALLE],
    "Bakırköy":      ["Ataköy 1.Kısım Mah.","Ataköy 2-5.Kısım Mah.","Ataköy 7-8.Kısım Mah.","Cevizlik Mah.","Kartaltepe Mah.","Sakızağacı Mah.","Yeşilköy Mah.","Zeytinlik Mah.", DIGER_MAHALLE],
    "Fatih":         ["Aksaray Mah.","Atik Ali Paşa Mah.","Çarşamba Mah.","Fındıkzade Mah.","Kocamustafapaşa Mah.","Küçük Langa Mah.","Molla Gürani Mah.","Samatya Mah.","Sultanahmet Mah.","Topkapı Mah.", DIGER_MAHALLE],
    "Pendik":        ["Batı Mah.","Doğu Mah.","Ertuğrulgazi Mah.","Güzelyalı Mah.","Kurtdoğmuş Mah.","Sapanbağları Mah.","Tuzla Mah.","Yenişehir Mah.", DIGER_MAHALLE],
    "Kartal":        ["Altıntepe Mah.","Ankara Mah.","Cevizli Mah.","Corlu Mah.","Fatih Mah.","Hürriyet Mah.","İstasyon Mah.","Karlıktepe Mah.","Uğur Mumcu Mah.","Yakacık Mah.", DIGER_MAHALLE],
    "Ümraniye":      ["Alemdar Mah.","Armağanevler Mah.","Çakmak Mah.","Elmalikent Mah.","Esatpaşa Mah.","İstiklal Mah.","Kazım Karabekir Mah.","Küçükbakkalköy Mah.","Site Mah.","Ünalan Mah.", DIGER_MAHALLE],
    "Kağıthane":     ["Çağlayan Mah.","Gültepe Mah.","Hamidiye Mah.","Harmantepe Mah.","Hürriyet Mah.","İhlas Mah.","Merkez Mah.","Nurtepe Mah.","Seyrantepe Mah.","Talatpaşa Mah.", DIGER_MAHALLE],
    "Gaziosmanpaşa": ["Bağlarbaşı Mah.","Barbaros Mah.","Eriktepe Mah.","Fevzi Çakmak Mah.","Karadeniz Mah.","Karlıtepe Mah.","Merkez Mah.","Sarıgöl Mah.","Yenidoğan Mah.", DIGER_MAHALLE],
    "Sarıyer":       ["Bahçeköy Mah.","Büyükdere Mah.","Çayırbaşı Mah.","Emirgan Mah.","Kireçburnu Mah.","Merkez Mah.","Pınarbaşı Mah.","Rumelihisarı Mah.","Tarabya Mah.", DIGER_MAHALLE],
    "Avcılar":       ["Ambarlı Mah.","Cihangir Mah.","Denizköşkler Mah.","Firuzköy Mah.","Gümüşpala Mah.","Merkez Mah.","Mustafa Kemal Mah.","Tahtakale Mah.", DIGER_MAHALLE],
    "Bağcılar":      ["Bağlar Mah.","Çınar Mah.","Demirkapı Mah.","Fatih Mah.","Güneşli Mah.","Hürriyet Mah.","Kazım Karabekir Mah.","Merkez Mah.","Yenimahalle Mah.", DIGER_MAHALLE],
    "Esenyurt":      ["Akevler Mah.","Ardıçlı Mah.","Barbaros Mah.","Güzelyurt Mah.","Kıraç Mah.","Merkez Mah.","Pınar Mah.","Talatpaşa Mah.", DIGER_MAHALLE],
    # ── ANKARA ────────────────────────────────────────────────────────────────
    "Çankaya":       ["Ahlatlıbel Mah.","Bahçeli Mah.","Balgat Mah.","Birlik Mah.","Çankaya Mah.","Çukurambar Mah.","Emek Mah.","Gaziosmanpaşa Mah.","Gökkuşağı Mah.","Kavaklıdere Mah.","Kırkkonaklar Mah.","Kızılay Mah.","Mebusevleri Mah.","Mustafa Kemal Mah.","Öğretmenler Mah.","Seyranbağları Mah.","Yıldız Mah.", DIGER_MAHALLE],
    "Keçiören":      ["Aktepe Mah.","Bağlum Mah.","Dumlupınar Mah.","Etlik Mah.","Kalaba Mah.","Kuşcağız Mah.","Ovacık Mah.","Pınarbaşı Mah.","Şefkat Mah.","Telsizler Mah.","Yenimahalle Mah.", DIGER_MAHALLE],
    "Yenimahalle":   ["Batıkent Mah.","Beştepe Mah.","Demetevler Mah.","Fatih Mah.","Karşıyaka Mah.","Macunköy Mah.","Ostim Mah.","Şentepe Mah.","Yaşamkent Mah.","Yunus Emre Mah.", DIGER_MAHALLE],
    "Mamak":         ["Altıağaç Mah.","Çiğdemtepe Mah.","Dutluk Mah.","Hıdırlıktepe Mah.","Işıklar Mah.","Kayaş Mah.","Kutlu Mah.","Saimekadın Mah.","Tuzluçayır Mah.","Yükseltepe Mah.", DIGER_MAHALLE],
    "Etimesgut":     ["Elvankent Mah.","Hoşdere Mah.","Nallıhan Mah.","Öveçler Mah.","Parmaksız Mah.","Regnum Mah.","Süvari Mah.","Topçu Mah.", DIGER_MAHALLE],
    "Sincan":        ["Atatürk Mah.","Fatih Mah.","Gündoğdu Mah.","İstasyon Mah.","Malazgirt Mah.","Plevne Mah.","Şehit Ömer Halisdemir Mah.", DIGER_MAHALLE],
    "Altındağ":      ["Anafartalar Mah.","Atıfbey Mah.","Hacettepe Mah.","Hisarpark Mah.","Karapürçek Mah.","Kayıldere Mah.","Kültür Mah.","Yenidoğan Mah.", DIGER_MAHALLE],
    # ── İZMİR ────────────────────────────────────────────────────────────────
    "Konak":         ["Alsancak Mah.","Basmane Mah.","Çankaya Mah.","Eşrefpaşa Mah.","Güzelyalı Mah.","Hatay Mah.","Kadifekale Mah.","Karantina Mah.","Kemeraltı Mah.","Mürselpaşa Mah.","Yenişehir Mah.", DIGER_MAHALLE],
    "Karşıyaka":     ["Alaybey Mah.","Bostanlı Mah.","Cumhuriyet Mah.","Donanmacı Mah.","Karabağlar Mah.","Mavişehir Mah.","Nergiz Mah.","Tersane Mah.","Yali Mah.", DIGER_MAHALLE],
    "Bornova":       ["Doğanlar Mah.","Egekent Mah.","Evka-3 Mah.","Işıkkent Mah.","Kazımdirik Mah.","Köy Mah.","Yeşilova Mah.","Yusuf Çavuş Mah.", DIGER_MAHALLE],
    "Buca":          ["Adatepe Mah.","Cumaovası Mah.","Egekent Mah.","Görece Mah.","Seyhan Mah.","Yeniçiğdem Mah.", DIGER_MAHALLE],
    "Bayraklı":      ["Alpaslan Mah.","Bayraklı Mah.","Çankaya Mah.","Mansuroğlu Mah.","Osmangazi Mah.","Pınarbaşı Mah.", DIGER_MAHALLE],
    "Gaziemir":      ["Aktepe Mah.","Atatürk Mah.","Emrez Mah.","İnönü Mah.","Sarnıç Mah.", DIGER_MAHALLE],
    "Çiğli":         ["Egegüneşi Mah.","Evrenseki Mah.","Fen Lisesi Mah.","Harmandalı Mah.","Küçükçiğli Mah.","Maltepe Mah.", DIGER_MAHALLE],
    "Narlıdere":     ["Bahçelerarası Mah.","Büyük Çiğli Mah.","Camikebir Mah.","Ilıca Mah.","Narlıdere Mah.", DIGER_MAHALLE],
    # ── BURSA ─────────────────────────────────────────────────────────────────
    "Osmangazi":     ["Dobruca Mah.","Çekirge Mah.","Hamitler Mah.","Heykel Mah.","Kestel Mah.","Panayır Mah.","Santral Garaj Mah.", DIGER_MAHALLE],
    "Nilüfer":       ["Beşevler Mah.","Bademli Mah.","Fethiye Mah.","Görükle Mah.","İhsaniye Mah.","Odunluk Mah.","Özlüce Mah.", DIGER_MAHALLE],
    "Yıldırım":      ["Cumalıkızık Mah.","Doburca Mah.","Eğitim Mah.","Emek Mah.","Huzur Mah.","Millet Mah.","Yunuseli Mah.", DIGER_MAHALLE],
    # ── ANTALYA ───────────────────────────────────────────────────────────────
    "Muratpaşa":     ["Bahçelievler Mah.","Balbey Mah.","Çağlayan Mah.","Fener Mah.","Güzeloba Mah.","Haşimişcan Mah.","Konyaaltı Mah.","Kışla Mah.","Memurevleri Mah.","Sinan Mah.","Uncalı Mah.","Varsak Mah.", DIGER_MAHALLE],
    "Kepez":         ["Altınova Mah.","Atatürk Mah.","Duraliler Mah.","Fabrikalar Mah.","Göksu Mah.","Güneş Mah.","Kahramanlar Mah.","Şafak Mah.", DIGER_MAHALLE],
    "Konyaaltı":     ["Arapsuyu Mah.","Çakırlar Mah.","Gürsu Mah.","Hurma Mah.","Liman Mah.","Sarısu Mah.","Siteler Mah.","Uncalı Mah.", DIGER_MAHALLE],
    "Alanya":        ["Alanya Merkez Mah.","Elikesik Mah.","Güllerpınarı Mah.","Mahmutlar Mah.","Oba Mah.","Tosmur Mah.", DIGER_MAHALLE],
    # ── ADANA ────────────────────────────────────────────────────────────────
    "Seyhan":        ["Çınarlı Mah.","Denizli Mah.","Reşatbey Mah.","Sümerler Mah.","Uğur Mumcu Mah.","Ziyapaşa Mah.", DIGER_MAHALLE],
    "Çukurova":      ["Cumhuriyet Mah.","Döşeme Mah.","Güzelevler Mah.","Huzurevleri Mah.","Yurt Mah.", DIGER_MAHALLE],
    # ── KOCAELİ ──────────────────────────────────────────────────────────────
    "İzmit":         ["Bekirdere Mah.","Durhasan Mah.","Hürriyet Mah.","Körfez Mah.","Kuruçeşme Mah.","Orhan Mah.","Topçular Mah.","Yahyakaptan Mah.", DIGER_MAHALLE],
    "Gebze":         ["Balçık Mah.","Güzeller Mah.","Hacı Halil Mah.","İstasyon Mah.","Köseköy Mah.","Pelitli Mah.", DIGER_MAHALLE],
    # ── KONYA ────────────────────────────────────────────────────────────────
    "Karatay":       ["Alaaddin Mah.","Aziziye Mah.","Fetih Mah.","Karatay Mah.","Medrese Mah.", DIGER_MAHALLE],
    "Selçuklu":      ["Horozluhan Mah.","Nalçacı Mah.","Sille Mah.","Yazır Mah.", DIGER_MAHALLE],
    "Meram":         ["Aşağı Pınarbaşı Mah.","Çayırbağı Mah.","Hasanköy Mah.","Karahüyük Mah.", DIGER_MAHALLE],
    # ── TRABZON ──────────────────────────────────────────────────────────────
    "Ortahisar":     ["Çömlekçi Mah.","Gülbaharhatun Mah.","Kemerkaya Mah.","Moloz Mah.","Pazarkapı Mah.", DIGER_MAHALLE],
    # ── SAMSUN ───────────────────────────────────────────────────────────────
    "İlkadım":       ["19 Mayıs Mah.","Baruthane Mah.","Çiftlik Mah.","Gazi Mah.","Kadıköy Mah.","Kökçüoğlu Mah.","Tekkeköy Mah.", DIGER_MAHALLE],
    "Atakum":        ["Atakum Mah.","Batı Mah.","Çobanlı Mah.","Kurupelit Mah.","Taflan Mah.", DIGER_MAHALLE],
    # ── MERSIN ───────────────────────────────────────────────────────────────
    "Akdeniz":       ["Çankaya Mah.","Demirtaş Mah.","Dumlupınar Mah.","Kışla Mah.","Limonluk Mah.","Nusratiye Mah.", DIGER_MAHALLE],
    "Yenişehir":     ["Bahçelievler Mah.","Çiftlikköy Mah.","Güvenevler Mah.","İstiklal Mah.","Kiremithane Mah.", DIGER_MAHALLE],
}


# ─── API fonksiyonları ────────────────────────────────────────────────────────

def il_listesi() -> list[str]:
    """Alfabetik sıralı 81 il listesi."""
    return sorted(IL_ILCE.keys())


def ilce_listesi(il: str) -> list[str]:
    """Seçilen ile ait ilçeleri döndür."""
    return IL_ILCE.get(il, [])


def mahalle_listesi(ilce: str) -> list[str]:
    """Seçilen ilçeye ait mahalle listesi; yoksa genel liste."""
    return ILCE_MAHALLE.get(ilce, _GENEL)
