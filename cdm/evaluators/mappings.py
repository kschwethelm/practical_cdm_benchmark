INFLAMMATION_LAB_TESTS = [
    51301,  # "White Blood Cells",
    51755,
    51300,
    50889,  # "C-Reactive Protein"
    51652,
]

APPENDECTOMY_PROCEDURES_KEYWORDS = ["appendectomy"]

ALTERNATE_APPENDECTOMY_KEYWORDS = [
    {
        "location": "appendix",
        "modifiers": ["surgery", "surgical", "removal", "remove"],
    }
]

CHOLECYSTECTOMY_PROCEDURES_KEYWORDS = [
    "cholecystectomy",
    "cholecystecotmy",
    "cholecsytectomy",
    "cholecystecomy",
    "cholecytectomy",
    "laparoscopic cholecystitis",
    "cholecyctectomy",
]

ALTERNATE_CHOLECYSTECTOMY_KEYWORDS = [
    {
        "location": "gallbladder",
        "modifiers": ["surgery", "surgical", "removal", "remove"],
    }
]

DRAINAGE_PROCEDURES_KEYWORDS = ["drain", "pigtail", "catheter", "aspiration"]

DRAINAGE_LOCATIONS_DIVERTICULITIS = [
    "abscess",
    "abdom",
    "pelvic",
    "peritoneal",
    "pericolonic",
    "sigmoid",
    "diverticular",
    "pararectal",
]

ALTERNATE_DRAINAGE_KEYWORDS_DIVERTICULITIS = [
    {"location": loc, "modifiers": DRAINAGE_PROCEDURES_KEYWORDS}
    for loc in DRAINAGE_LOCATIONS_DIVERTICULITIS
]

COLECTOMY_PROCEDURES_KEYWORDS = [
    "low anterior resection",
    "colectomy",
    "colonic resection",
    "colostomy",
    "resection of rectosigmoid colon",
    "resection of sigmoid colon",
    "rectosigmoid resection",
    "resection of colon",
    "sigmoidectomy",
    "sigmoid resection",
    "small bowel resection",
]

ALTERNATE_COLECTOMY_KEYWORDS = [
    {
        "location": "colon",
        "modifiers": ["surgery", "surgical", "removal", "remove"],
    }
]

DRAINAGE_LOCATIONS_PANCREATITIS = [
    "abscess",
    "abdom",
    "pelvic",
    "peritoneal",
    "pancrea",
    "gallbladder",
    "biliary",
    "bile duct",
    "perirectal",
]

ALTERNATE_DRAINAGE_KEYWORDS_PANCREATITIS = [
    {"location": loc, "modifiers": DRAINAGE_PROCEDURES_KEYWORDS}
    for loc in DRAINAGE_LOCATIONS_PANCREATITIS
]


ERCP_PROCEDURES_KEYWORDS = [
    "biliary stent",
    "biliary cannulation",
    "ercp",
    "endoscopic retrograde cholangiography",
    "endoscopic retrograde cholangiopancreatography",
    "cholangiogram",
    "cbd stent",
    "pancreatic stent",
    "sphincterotomy",
    "sphinctertomy",
]
