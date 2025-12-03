INFLAMMATION_LAB_TESTS = [
    51301,  # "White Blood Cells",
    51755,
    51300,
    50889,  # "C-Reactive Protein"
    51652,
]

ADDITIONAL_LAB_TEST_MAPPING = {
    "Complete Blood Count (CBC)": [
        51279,  # "Red Blood Cells",
        51301,  # "White Blood Cells",
        51755,
        51300,
        51222,  # "Hemoglobin",
        50811,
        51221,  # "Hematocrit",
        51638,
        50810,
        51250,  # "MCV",
        51248,  # "MCH",
        51249,  # "MCHC",
        51265,  # "Platelet Count",
        51244,  # "Lymphocytes",
        51133,  # "Absolute Lymphocyte Count",
        52769,
        51245,  # "Lymphocytes, Percent",
        51146,  # "Basophils",
        52069,  # "Absolute Basophil Count",
        51200,  # "Eosinophils",
        52073,  # "Absolute Eosinophil Count",
        51254,  # "Monocytes",
        52074,  # "Absolute Monocyte Count",
        51253,  # "Monocyte Count"
        51256,  # "Neutrophils",
        52075,  # "Absolute Neutrophil Count",
        51277,  # "RDW",
        52172,  # "RDW-SD",
    ],
    "Basic Metabolic Panel (BMP)": [
        50809,  # "Glucose",
        50931,
        52569,
        50824,  # "Sodium",
        50983,
        52623,
        50822,  # "Potassium",
        50971,
        52610,
        50806,  # "Chloride",
        50902,
        52535,
        50803,  # "Bicarbonate",
        50882,
        51006,  # "Urea Nitrogen",
        52647,
        50912,  # "Creatinine",
        52024,
        52546,
        50808,  # "Calcium",
        50893,
        51624,
    ],
    "Comprehensive Metabolic Panel (CMP)": [
        50809,  # "Glucose",
        50931,
        52569,
        50824,  # "Sodium",
        50983,
        52623,
        50822,  # "Potassium",
        50971,
        52610,
        50806,  # "Chloride",
        50902,
        52535,
        50803,  # "Bicarbonate",
        50882,
        51006,  # "Urea Nitrogen",
        52647,
        50912,  # "Creatinine",
        52024,
        52546,
        50808,  # "Calcium",
        50893,
        51624,
        50861,  # "Alanine Aminotransferase (ALT)",
        50863,  # "Alkaline Phosphatase",
        50878,  # "Asparate Aminotransferase (AST)",
        50883,  # "Bilirubin",
        50884,
        50885,
        50976,  # "Total Protein",
    ],
    "Blood urea nitrogen (BUN)": [
        51006,  # "Urea Nitrogen",
        52647,
    ],
    "Renal Function Panel (RFP)": [
        50862,  # "Albumin",
        51006,  # "Urea Nitrogen",
        52647,
        50824,  # "Sodium",
        50983,
        52623,
        50808,  # "Calcium",
        50893,
        51624,
        50804,  # "C02",
        51739,
        50806,  # "Chloride",
        50902,
        52535,
        50912,  # "Creatinine",
        52024,
        52546,
        50809,  # "Glucose",
        50931,
        52569,
        50970,  # "Phosphate",
        50822,  # "Potassium",
        50971,
        52610,
    ],
    "Liver Function Panel (LFP)": [
        50861,  # "Alanine Aminotransferase (ALT)",
        50878,  # "Asparate Aminotransferase (AST)",
        50863,  # "Alkaline Phosphatase",
        50927,  # "Gamma Glutamyltransferase",
        50883,  # "Bilirubin",
        50884,
        50885,
        51274,  # "Prothrombin Time (PT)",
        51237,
        51675,
        50976,  # "Total Protein",
        50862,  # "Albumin",
    ],
    "Urinalysis": [
        51508,  # "Urine Color",
        51506,  # "Urine Appearance",
        51512,  # "Urine Mucous",
        51108,  # "Urine Volume",
        51498,  # "Specific Gravity",
        51994,
        51093,  # "Osmolality, Urine",
        51069,  # "Albumin, Urine",
        51070,  # "Albumin/Creatinine, Urine",
        51082,  # "Creatinine, Urine",\
        51106,
        51097,  # "Potassium, Urine",
        51100,  # "Sodium, Urine",
        51102,  # "Total Protein, Urine",
        51068,
        51492,
        51992,
        51104,  # "Urea Nitrogen, Urine",
        51462,  # "Amorphous Crystals",
        51469,  # "Calcium Oxalate Crystals",
        51503,  # "Triple Phosphate Crystals",
        51505,  # "Uric Acid Crystals",
        51510,  # "Urine Crystals, Other",
        51493,  # "RBC",
        51494,  # "RBC Casts",
        51495,  # "RBC Clumps",
        51516,  # "WBC",
        51517,  # "WBC Casts",
        51518,  # "WBC Clumps",
        51507,  # "Urine Casts, Other",
        51094,  # "pH"
        51491,
        52730,
        51464,  # "Bilirubin",
        51966,
        51084,  # "Glucose",
        51478,
        51981,
        51514,  # "Urobilinogen",
        52002,
        51484,  # "Ketone",
        51984,
        51487,  # "Nitrite",
        51987,
        51486,  # "Leukocytes",
        51985,
        51476,  # "Epithelial Cells",
        51497,
        51501,
        51489,
        51488,
    ],
    "Electrolyte Panel": [
        50824,  # "Sodium",
        50983,
        52623,
        50822,  # "Potassium",
        50971,
        52610,
        50806,  # "Chloride",
        50902,
        52535,
        50803,  # "Bicarbonate",
        50882,
    ],
    "Lipid Profile": [
        50907,  # "Cholesterol, Total",
        50905,  # "Cholesterol, LDL, Calculated",
        50906,  # "Cholesterol, LDL, Measured",
        50904,  # "Cholesterol, HDL",
        51000,  # "Triglycerides",
    ],
    "Coagulation Profile": [
        51274,  # "PT",
        51275,  # "PTT",
        51675,  # "INR(PT)",
        51237,  # "INR(PT)",
        # aPTT and TT not found
    ],
    "Iron Studies": [
        50952,  # "Iron",
        50953,  # "Iron Binding Capacity, Total"
        50998,  # "Transferrin",
        50924,  # "Ferritin",
        51250,  # "MCV",
        # TSAT not found
    ],
    "Liver Enzymes": [
        50861,  # "Alanine Aminotransferase (ALT)",
        50878,  # "Asparate Aminotransferase (AST)",
        50863,  # "Alkaline Phosphatase",
        50927,  # "Gamma Glutamyltransferase",
    ],
    "Thyroid Function Test (TFT)": [
        50993,  # "Thyroid Stimulating Hormone",
        50994,  # "Thyroxine (T4)",
        50995,  # "Thyroxine (T4), Free",
        51001,  # "Triiodothyronine (T3)",
        50992,  # "Thyroid Peroxidase Antibody",
    ],
    "Gamma Glutamyltransferase (GGT)": [
        50927,  # "Gamma Glutamyltransferase",
    ],
    "Phosphorus": [
        50970,  # "Phosphate",
    ],
    "Mean Corpuscular Volume (MCV)": [
        51250,  # "MCV",
    ],
    "C-Reactive Protein (CRP)": [
        50889,  # "C-Reactive Protein"
    ],
    "CRP": [
        50889,  # "C-Reactive Protein"
    ],
    "Prostate Specific Antigen (PSA)": [
        50974,  # ["Prostate Specific Antigen"],
    ],
    "PSA": [
        50974,  # ["Prostate Specific Antigen"],
    ],
    "Alkaline Phosphatase (ALP)": [
        50863,  # "Alkaline Phosphatase",
    ],
    "ALP": [
        50863,  # "Alkaline Phosphatase",
    ],
    "Alk Phos": [
        50863,  # "Alkaline Phosphatase",
    ],
    "Pregnancy Test": [
        51085,  # "HCG, Urine, Qualitative",
        52720,
    ],
    "Amylase, Serum": [
        50867,  # "Amylase",
    ],
    "Serum Amylase": [
        50867,  # "Amylase",
    ],
    "Stool Occult Blood": [
        51460,  # "Occult Blood",
    ],
    "Erythrocyte Sedimentation Rate (ESR)": [
        51288,  # "Sedimentation Rate",
    ],
    "ESR": [
        51288,  # "Sedimentation Rate",
    ],
    "Troponin": [
        51003,  # "Troponin T",
    ],
    "Direct Bilirubin": [
        50883,  # "Bilirubin, Direct",
    ],
    "TSH": [
        50993,  # "Thyroid Stimulating Hormone",
    ],
    "Calcium": [
        50893,  # "Calcium, Total",
    ],
    "White Blood Cell Count": [
        51300,  # "WBC Count",
    ],
    "Free T4": [
        50995,  # "Thyroxine (T4), Free",
    ],
    "Blood Culture": [
        90201,  # "Blood Culture, Routine"
    ],
    "Stool Culture": [
        90267,  # "Stool Culture"
    ],
    "O&P": [
        90250,  # "OVA + PARASITES"
    ],
    # Procalcitonin not found
}

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


