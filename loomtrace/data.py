"""Reference data for LoomTrace.

OFFICIAL  : GI registry rows (IP India registration list) and state weaver counts
            (4th All India Handloom Census 2019-20, Ministry of Textiles, via PIB).
KNOWLEDGE : GI statement-of-case passages, summarised from the IP India GI
            application documents for the three products in scope.
SIMULATED : individual weaver and batch/provenance records. Real individual
            records are not published (privacy), so these are generated from the
            census clusters and clearly labelled as simulated.
"""
from __future__ import annotations

import random

# --------------------------------------------------------------------------- #
# OFFICIAL: GI registry (IP India registration list)
# --------------------------------------------------------------------------- #
GI_REGISTRY = {
    "Kancheepuram Silk": {
        "gi_no": 15,
        "state": "Tamil Nadu",
        "goods_class": "Class 24 - Textiles (Handicraft)",
        "districts": ["Kancheepuram", "Thiruvallur"],
        "aliases": ["kanchipuram silk", "kanjivaram", "kanjeevaram", "kancheepuram saree", "kanchi pattu", "kancheepuram"],
        "materials": ["mulberry silk", "zari"],
        "source_id": "IPINDIA-GI-REG#15",
    },
    "Pochampalli Ikat": {
        "gi_no": 4,
        "state": "Telangana",
        "goods_class": "Class 24, 25 - Textiles",
        "districts": ["Yadadri Bhuvanagiri", "Nalgonda"],
        "aliases": ["pochampally ikat", "pochampally", "pochampalli", "telia rumal", "ikkat", "ikat"],
        "materials": ["cotton", "silk", "sico"],
        "source_id": "IPINDIA-GI-REG#4",
    },
    "Banaras Brocades and Sarees": {
        "gi_no": 99,
        "state": "Uttar Pradesh",
        "goods_class": "Class 24, 25 - Textiles",
        "districts": ["Varanasi", "Mirzapur", "Chandauli", "Bhadohi", "Jaunpur", "Azamgarh"],
        "aliases": ["banarasi", "banarasi saree", "benarasi", "banaras brocade", "banaras saree", "varanasi silk", "banaras"],
        "materials": ["silk", "zari", "cotton"],
        "source_id": "IPINDIA-GI-REG#99",
    },
}

# Registered handloom GIs from the Government GI catalogue (PIB / TRIFED, Ministry of Tribal
# Affairs, Nov 2021: static.pib.gov.in/WriteReadData/specificdocs/documents/2021/nov/doc2021112441.pdf).
# Places and materials are taken only from that document; the catalogue does not print GI
# application numbers, so gi_no is None. state_wide=True means the document ties the GI to the
# whole state/region rather than named districts.
_PIB = "PIB-GI-2021"
_MORE = [
    ("Chanderi Sarees", "Madhya Pradesh", ["Chanderi"], ["silk", "zari", "cotton"], ["chanderi"], False,
     "Chanderi is a traditional ethnic fabric characterized by its lightweight, sheer texture and fine luxurious feel. It is produced by weaving in silk and golden zari in the traditional cotton yarn. The fabric borrowed its name from the small town Chanderi in Madhya Pradesh where traditional weavers produce textured sarees in cotton and silk decorated with fine zari work."),
    ("Maheshwari Sarees", "Madhya Pradesh", ["Maheshwar", "Khargone"], ["cotton", "silk"], ["maheshwari", "maheshwar"], False,
     "The looms of Maheshwar, a city in Khargone district of Madhya Pradesh, epitomize the traditional skills of local artisans. Maheshwari sarees use fine cotton yarns in the weft and silk in the warp with stripes and checks; a distinctive feature is the reversible border, locally known as Bugdi."),
    ("Kotpad Handloom", "Odisha", ["Kotpad", "Koraput"], ["cotton", "vegetable dye"], ["kotpad"], False,
     "Kotpad Handloom is a vegetable-dyed fabric woven by the tribal weavers of the Mirgan community of Kotpad village in Koraput district, Odisha. Cotton sarees with solid border and Pata Anchal, dupattas with typical butis and motifs."),
    ("Bomkai Saree", "Odisha", ["Subarnapur", "Sonepur", "Bomkai"], [], ["bomkai", "sonepuri"], False,
     "Bomkai sari (also Sonepuri sari) is a handloom saree from Odisha. It originates in Bomkai and is primarily produced by the Bhulia community of Subarnapur district. Bomkai is one of the identified Geographical Indications of India."),
    ("Sambalpuri Bandha", "Odisha", ["Sambalpur", "Balangir", "Bargarh", "Boudh", "Sonepur"], [], ["sambalpuri", "bandha", "sambalpuri ikat"], False,
     "Sambalpuri sari is a traditional handwoven ikat (locally called bandha) wherein the warp and the weft are tie-dyed before weaving. It is produced in the Sambalpur, Balangir, Bargarh, Boudh and Sonepur districts of Odisha."),
    ("Mangalagiri Sarees and Fabrics", "Andhra Pradesh", ["Mangalagiri", "Guntur"], [], ["mangalagiri"], False,
     "Mangalagiri Sarees and Fabrics are produced by handloom weaving in Mangalagiri, a town in Guntur district of Andhra Pradesh. The fabric is woven on pit looms from combed yarn by warp and woof interlacing and then dyed. The Nizam design is a characteristic of the fabric."),
    ("Baluchari Saree", "West Bengal", ["Bishnupur"], ["silk"], ["baluchari"], False,
     "Baluchari sari originated in West Bengal and is known for depictions of mythological scenes on the pallu. It used to be produced in Murshidabad but presently Bishnupur and its surrounding areas are the only place where authentic Baluchari saris are produced. The main material used is silk."),
    ("Muga Silk", "Assam", ["Brahmaputra Valley"], ["muga silk", "silk"], ["muga"], True,
     "Muga silk is a variety of wild silk geographically tagged to the state of Assam. It is known for its extreme durability and natural yellowish-golden tint. In the Brahmaputra Valley the larvae of the Assam silkmoth feed on aromatic Som and Sualu leaves."),
    ("Chakhesang Shawl", "Nagaland", ["Nagaland"], ["cotton", "nettle", "jute", "wool", "acrylic"], ["chakhesang"], True,
     "Chakhesang shawls are an exclusive GI product from Nagaland, woven by the Chakhesang tribe (Chokri, Kheza and Sangtam). The shawls are made not only of cotton but also of nettle and jute plants, dyed with natural material collected from the forest."),
    ("Kullu Shawls", "Himachal Pradesh", ["Kullu"], ["wool"], ["kullu"], False,
     "Kullu shawl is a type of shawl made in Kullu, Himachal Pradesh, with geometrical designs on both ends and fine woollen fabric. The shawls are usually called Loi or Pattu."),
    ("Kota Doria", "Rajasthan", ["Kaithoon", "Kota"], ["cotton", "silk"], ["kota doria", "kota doriya", "kota sari", "kota saree"], False,
     "Kota Doria is a light weight fabric made of tiny woven squares (khat), hand woven on traditional pit looms in Kaithoon near Kota in Rajasthan and some surrounding villages. Kota Doriya sarees are made of pure cotton and silk."),
    ("Champa Silk", "Chhattisgarh", ["Champa", "Raipur"], ["kosa silk", "silk"], ["champa", "kosa"], False,
     "The Kosa silk industry covers sericulture, reeling of yarn and silk weaving, found in the Raipur and Champa region only. Temple and tribal motifs inspire the designs; cocoons are collected from the forests by traditional tribes."),
]
for i, (name, state, places, mats, aliases, wide, text) in enumerate(_MORE, 1):
    GI_REGISTRY[name] = {"gi_no": None, "state": state, "goods_class": "Handloom textile",
                         "districts": places, "aliases": aliases, "materials": mats, "state_wide": wide,
                         "source_id": f"{_PIB}#{i}", "summary": text}


# --------------------------------------------------------------------------- #
# OFFICIAL: 4th All India Handloom Census 2019-20 (state handloom weavers)
# --------------------------------------------------------------------------- #
_CENSUS_ROWS = """Andhra Pradesh|127662|49785;Arunachal Pradesh|77600|17016;Assam|1107428|176453;Bihar|7216|5631;
Chhattisgarh|14077|7426;Delhi|3236|1049;Goa|22|4;Gujarat|10179|422;Haryana|14414|11128;Himachal Pradesh|13211|477;
Jammu and Kashmir|15784|7544;Jharkhand|12364|10133;Karnataka|27175|27616;Kerala|15480|6604;Madhya Pradesh|12805|5267;
Maharashtra|2882|627;Manipur|212481|12203;Meghalaya|41221|1553;Mizoram|17298|10242;Nagaland|35950|7534;Odisha|53472|64364;
Puducherry|908|782;Punjab|631|338;Rajasthan|8687|1403;Sikkim|632|65;Tamil Nadu|197818|45757;Telangana|25930|21922;
Tripura|111927|25712;Uttar Pradesh|130778|60179;Uttarakhand|7967|4594;West Bengal|366656|264791"""
# Source: PIB annexure, Ministry of Textiles (Release ID 2202869), "State/UT-wise number of handloom
# weavers and allied workers as per 4th All India Handloom Census 2019-20". All India: 26,73,891 / 8,48,621.
CENSUS = {}
for _r in _CENSUS_ROWS.replace(chr(10), "").split(";"):
    _st, _w, _a = _r.strip().split("|")
    CENSUS[_st] = {"weavers": int(_w), "allied": int(_a),
                   "source_id": "HLCENSUS-2019-20#" + _st.replace(" ", "_")}

# --------------------------------------------------------------------------- #
# KNOWLEDGE BASE: GI application passages (statement of case summaries)
# --------------------------------------------------------------------------- #
GI_DOCS = [
    # Kancheepuram
    {"id": "GI15-p3", "product": "Kancheepuram Silk", "page": 3,
     "text": "Kancheepuram silk sarees are woven by hand on pit looms in Kancheepuram and the adjoining areas of Thiruvallur district in Tamil Nadu. The geographical area of production is the Kancheepuram region."},
    {"id": "GI15-p5", "product": "Kancheepuram Silk", "page": 5,
     "text": "The saree is woven from pure mulberry silk yarn with zari made of silver thread gilded with gold. Body and border are woven separately and interlocked using the korvai technique."},
    {"id": "GI15-p7", "product": "Kancheepuram Silk", "page": 7,
     "text": "Weavers of the Kancheepuram cluster belong to traditional weaving communities and work through cooperative societies registered in the district. Contrast borders and temple motifs are characteristic."},
    # Pochampalli
    {"id": "GI4-p2", "product": "Pochampalli Ikat", "page": 2,
     "text": "Pochampalli Ikat is produced in Bhoodan Pochampally and surrounding villages of the Nalgonda region, now Yadadri Bhuvanagiri district, Telangana. Weaving clusters include Pochampally, Koyalagudem and Puttapaka."},
    {"id": "GI4-p4", "product": "Pochampalli Ikat", "page": 4,
     "text": "The ikat technique involves tie-and-dye resist dyeing of the warp and weft yarns before weaving so that geometric patterns emerge on the loom. Cotton, silk and sico (silk-cotton) yarns are used."},
    {"id": "GI4-p6", "product": "Pochampalli Ikat", "page": 6,
     "text": "Products include sarees, dress material and the telia rumal. Fabric is woven on traditional frame looms by registered handloom weavers of the cluster."},
    # Banaras
    {"id": "GI99-p3", "product": "Banaras Brocades and Sarees", "page": 3,
     "text": "Banaras brocades and sarees are produced in the districts of Varanasi, Mirzapur, Chandauli, Bhadohi, Jaunpur and Azamgarh in Uttar Pradesh."},
    {"id": "GI99-p6", "product": "Banaras Brocades and Sarees", "page": 6,
     "text": "Brocade is woven with silk and gold or silver zari using extra-weft figuring on handlooms with jacquard or naksha attachments. Kadwa, fekwa and jangla are traditional weaving styles."},
    {"id": "GI99-p9", "product": "Banaras Brocades and Sarees", "page": 9,
     "text": "Motifs include buti, buta, kalga and bel, inspired by Mughal design. Weavers of the Varanasi cluster work in households and through cooperative societies."},
]

for _name, _info in GI_REGISTRY.items():
    if "summary" in _info:
        GI_DOCS.append({"id": _info["source_id"].replace("#", "-p"), "product": _name, "page": 0, "text": _info["summary"]})

# --------------------------------------------------------------------------- #
# SIMULATED: weaver registry + provenance records (seeded, reproducible)
# --------------------------------------------------------------------------- #
_FIRST = ["Lakshmi", "Murugan", "Saravanan", "Meena", "Ravi", "Anjali", "Srinivas", "Padma",
          "Ramesh", "Sunita", "Iqbal", "Fatima", "Mohan", "Kavita", "Abdul", "Geeta",
          "Venkat", "Shabana", "Rajesh", "Devi"]
_LAST = {"Kancheepuram Silk": ["Sundaram", "Pillai", "Mudaliar", "Selvam"],
         "Pochampalli Ikat": ["Gajam", "Chintakindi", "Tadaka", "Rapolu"],
         "Banaras Brocades and Sarees": ["Ansari", "Maurya", "Patel", "Khan"]}
_CODE = {"Kancheepuram Silk": "KAN", "Pochampalli Ikat": "POC", "Banaras Brocades and Sarees": "BAN",
         "Chanderi Sarees": "CHA", "Maheshwari Sarees": "MAH", "Kotpad Handloom": "KOT", "Bomkai Saree": "BOM",
         "Sambalpuri Bandha": "SAM", "Mangalagiri Sarees and Fabrics": "MNG", "Baluchari Saree": "BAL",
         "Muga Silk": "MUG", "Chakhesang Shawl": "CHK", "Kullu Shawls": "KUL", "Kota Doria": "KTD", "Champa Silk": "CMP"}
_GENERIC_LAST = ["Das", "Sahu", "Meher", "Rao", "Devi", "Singh", "Thakur", "Bora", "Kumar", "Ansari"]


def _build_simulated():
    rng = random.Random(42)
    weavers, batches = {}, {}
    for product, info in GI_REGISTRY.items():
        code = _CODE[product]
        for i in range(1, 13):
            wid = f"WV-{code}-{i:03d}"
            weavers[wid] = {
                "weaver_id": wid,
                "name": f"{rng.choice(_FIRST)} {rng.choice(_LAST.get(product, _GENERIC_LAST))}",
                "product": product,
                "cluster": info["districts"][i % len(info["districts"])],
                "district": info["districts"][i % len(info["districts"])],
                "state": info["state"],
                "looms": rng.randint(1, 4),
                "source_id": f"SIM-WEAVER#{wid}",
            }
            for j in range(2):
                bid = f"B-{code}-{i:03d}{j}"
                batches[bid] = {
                    "batch_id": bid,
                    "weaver_id": wid,
                    "product": product,
                    "loom": f"LOOM-{code}-{i:03d}-{j+1}",
                    "yarn": info["materials"][j % len(info["materials"])] if info["materials"] else "handloom yarn",
                    "started": f"2026-0{rng.randint(1, 8)}-{rng.randint(10, 28)}",
                    "finished": f"2026-0{rng.randint(8, 9)}-{rng.randint(10, 28)}",
                    "source_id": f"SIM-PROV#{bid}",
                }
    return weavers, batches


WEAVERS, BATCHES = _build_simulated()
