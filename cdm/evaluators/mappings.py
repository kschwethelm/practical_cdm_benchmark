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

APPENDECTOMY_PROCEDURES_ICD9 = [4701, 4709]
APPENDECTOMY_PROCEDURES_ICD10 = ["0DTJ4ZZ", "0DTJ0ZZ"]

CHOLECYSTECTOMY_PROCEDURES_ICD9 = [5123, 5122, 5121, 5102, 5124, 5103]
CHOLECYSTECTOMY_PROCEDURES_ICD10 = ["0FB44ZZ", "0FB40ZZ"]

COLECTOMY_PROCEDURES_ICD9 = [
    4575,
    4576,
    4863,
    4562,
    4542,
    4579,
    4531,
    4530,
    4533,
    4562,
    1739,
    1734,
    1736,
    4572,
    4573,
    4576,
    1733,
    4541,
    1732,
    5459,
    5451,
    4574,
    9624,
]

COLECTOMY_PROCEDURES_ICD10 = [
    "0DBM8ZZ",
    "0DBH8ZZ",
    "0DB90ZZ",
    "0DB94ZZ",
    "0DBB0ZZ",
    "0DTK4ZZ",
    "0DTM4ZZ",
    "0DTL4ZZ",
    "0DTN4ZZ",
    "0DBG4ZZ",
    "0DTH0ZZ",
    "0DTF0ZZ",
    "0DTN0ZZ",
    "0DB80ZZ",
    "0DBA0ZZ",
    "0DB84ZZ",
    "0DBB4ZZ",
    "0DTF4ZZ",
    "0DBH0ZZ",
    "0DTH4ZZ",
    "0DNN0ZZ",
    "0DBM4ZZ",
    "0DTM0ZZ",
    "0DNB0ZZ",
    "0DBM0ZZ",
    "0DBE0ZZ",
    "0DBG0ZZ",
    "0DNE0ZZ",
    "0DNE4ZZ",
    "0DN90ZZ",
    "0DNL4ZZ",
    "0DNA0ZZ",
    "0DBH4ZZ",
    "0DTK0ZZ",
    "0DTL0ZZ",
    "0DNB4ZZ",
    "0DNL0ZZ",
    "0DNN4ZZ",
    "0DBA8ZZ",
    "0DBA4ZZ",
    "0DNB7ZZ",
    "0DBE4ZZ",
    "0DTNFZZ",
    "0DNA4ZZ",
    "0DN94ZZ",
    "0DB98ZZ",
    "0DTH8ZZ",
    "0DTN7ZZ",
    "0DBB3ZZ",
    "0DBN0ZZ",
    "0DBN4ZZ",
    "0DT80ZZ",
]

DRAINAGE_PROCEDURES_ICD9 = [5491]

DRAINAGE_PROCEDURES_ALL_ICD10 = [
    "0W2JX0Z",
    "0W9J30Z",
    "0W9J3ZZ",
    "0W9J3ZX",
    "0W9G30Z",
    "0W9G3ZZ",
    "0W9G3ZX",
]

DRAINAGE_PROCEDURES_PANCREATITIS_ICD10 = [
    "0F2BX0Z",
    "0F9430Z",
    "0F9G30Z",
    "0F998ZZ",
    "0F998ZX",
]

ERCP_PROCEDURES_ICD10 = [
    "0F798DZ",
    "0F798ZZ",
    "0F7D8DZ",
    "0FB98ZX",
    "0FBD8ZX",
    "0FC98ZZ",
    "0FD98ZX",
    "0FDG8ZX",
    "BF101ZZ",
    "BF10YZZ",
    "BF11YZZ",
    "BF141ZZ",
    "BF14YZZ",
    "0FJB8ZZ",
    "0FJD8ZZ",
]


ERCP_PROCEDURES_ICD9 = [
    8766,
    5181,
    5184,
    5221,
    5187,
    5293,
    5188,
    5110,
    5185,
    8754,
    5114,
    9705,
]