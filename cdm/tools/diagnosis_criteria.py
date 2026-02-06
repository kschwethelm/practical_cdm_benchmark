"""Medical knowledge retrieval tool with embedded criteria."""

import re

from langchain.tools import tool

# Diagnosis criteria gathered from multiple authoritative sources like: World Journal of Emergency Surgery Guidelines, American College of Gastroenterology,  
# Infectious Diseases Society of America Clinical Practice, Guidelines of the World Society of Emergency Surgery.
# For more detailed information, check out out paper
DIAGNOSIS_CRITERIA = {
    "appendicitis": {
        "symptoms": [
            ("rlq pain", 28),
            ("rlq", 25),
            ("right lower quadrant pain", 28),
            ("right lower quadrant", 24),
            ("right lower", 18),
            ("periumbilical", 16),
            ("migrating pain", 18),
            ("migration", 14),
            ("anorexia", 12),
            ("nausea", 10),
            ("vomiting", 10),
            ("fever", 10),
        ],
        "exam_findings": [
            ("mcburney", 35),
            ("rovsing", 28),
            ("psoas sign", 26),
            ("obturator sign", 24),
            ("rlq tenderness", 28),
            ("right lower quadrant tenderness", 28),
            ("rebound", 12),
            ("peritoneal", 10),
            ("guarding", 3),
        ],
        "labs": [
            ("leukocytosis", 6),
            ("elevated wbc", 6),
            ("elevated crp", 6),
            ("left shift", 12),
            ("bandemia", 12),
            ("neutrophilia", 12),
        ],
        "imaging": [
            ("acute appendicitis", 55),
            ("appendicitis", 50),
            ("periappendiceal", 42),
            ("appendicolith", 42),
            ("enlarged appendix", 38),
            ("appendix >", 38),
            ("appendix", 22),
            ("fat stranding", 6),
        ],
        "negative": [
            ("normal appendix", -45),
            ("appendix is normal", -45),
            ("unremarkable appendix", -40),
            ("no appendicitis", -50),
            ("without appendicitis", -45),
            ("pancreatitis", -40),
            ("cholecystitis", -40),
            ("diverticulitis", -40),
        ],
        "criteria": [
            "Periumbilical pain migrating to RLQ",
            "McBurney's point tenderness, Rovsing/Psoas/Obturator signs",
            "Leukocytosis with left shift, elevated CRP",
            "CT: appendix >6mm, appendicolith, periappendiceal inflammation",
        ],
    },

    "cholecystitis": {
        "symptoms": [
            ("ruq pain", 30),
            ("right upper quadrant pain", 30),
            ("ruq", 26),
            ("right upper quadrant", 24),
            ("right upper", 18),
            ("biliary colic", 26),
            ("biliary", 10),
            ("postprandial", 18),
            ("after eating", 16),
            ("fatty food", 16),
            ("radiating to shoulder", 14),
            ("nausea", 10),
            ("vomiting", 10),
            ("fever", 10),
        ],
        "exam_findings": [
            ("murphy sign", 40),
            ("murphy's sign", 40),
            ("positive murphy", 40),
            ("murphy", 32),
            ("sonographic murphy", 45),
            ("ruq tenderness", 28),
            ("right upper quadrant tenderness", 28),
            ("jaundice", 18),
            ("icteric", 18),
            ("scleral icterus", 18),
            ("guarding", 2),
        ],
        "labs": [
            ("elevated bilirubin", 18),
            ("hyperbilirubinemia", 18),
            ("elevated alt", 14),
            ("elevated ast", 14),
            ("elevated alk phos", 16),
            ("alkaline phosphatase", 6),
            ("elevated ggt", 16),
            ("leukocytosis", 3),
            ("elevated lft", 12),
        ],
        "imaging": [
            ("acute cholecystitis", 60),
            ("cholecystitis", 55),
            ("pericholecystic fluid", 45),
            ("pericholecystic", 40),
            ("gallbladder wall thickening", 42),
            ("gallbladder wall >3mm", 42),
            ("gb wall thickening", 40),
            ("wall thickening", 8),
            ("gallstone", 20),
            ("gallstones", 20),
            ("cholelithiasis", 18),
            ("distended gallbladder", 24),
            ("gallbladder", 6),
            ("gb", 5),
            ("hida", 22),
            ("nonvisualized gallbladder", 40),
        ],
        "negative": [
            ("normal gallbladder", -45),
            ("gallbladder is normal", -45),
            ("no cholecystitis", -55),
            ("no gallstones", -35),
            ("no cholelithiasis", -35),
            ("pancreatitis", -40),
            ("appendicitis", -40),
            ("diverticulitis", -40),
        ],
        "criteria": [
            "RUQ pain, often postprandial, radiating to shoulder",
            "Positive Murphy's sign",
            "Leukocytosis, elevated bilirubin/LFTs",
            "US: gallstones + wall thickening >3mm + pericholecystic fluid",
        ],
    },

    "pancreatitis": {
        "symptoms": [
            ("epigastric pain", 30),
            ("epigastric", 22),
            ("radiating to back", 32),
            ("band-like pain", 30),
            ("back pain", 12),
            ("alcohol", 26),
            ("alcoholic", 26),
            ("etoh", 26),
            ("alcohol use", 20),
            ("alcohol abuse", 26),
            ("heavy drinking", 24),
            ("drinking", 16),
            ("gallstone pancreatitis", 50),
            ("nausea", 1),
            ("vomiting", 1),
        ],
        "exam_findings": [
            ("epigastric tenderness", 26),
            ("cullen", 40),
            ("cullens sign", 42),
            ("grey turner", 40),
            ("grey-turner", 40),
            ("flank ecchymosis", 38),
            ("guarding", 2),
        ],
        "labs": [
            ("elevated lipase", 60),
            ("lipase elevated", 60),
            ("lipase >3x", 65),
            ("lipase", 50),
            ("elevated amylase", 50),
            ("amylase elevated", 50),
            ("amylase >3x", 55),
            ("amylase", 38),
            ("triglycerides", 22),
            ("hyperlipidemia", 22),
            ("hypertriglyceridemia", 26),
            ("hypercalcemia", 16),
            ("leukocytosis", 2),
        ],
        "imaging": [
            ("acute pancreatitis", 70),
            ("pancreatitis", 65),
            ("interstitial pancreatitis", 65),
            ("necrotizing pancreatitis", 70),
            ("pancreatic edema", 38),
            ("pancreatic inflammation", 42),
            ("pancreatic enlargement", 38),
            ("peripancreatic fluid", 42),
            ("peripancreatic", 35),
            ("pancreatic necrosis", 48),
            ("necrosis", 30),
            ("pseudocyst", 38),
            ("fluid collection", 12),
            ("pancreatic", 5),
            ("pancreas", 3),
        ],
        "negative": [
            ("normal pancreas", -40),
            ("pancreas is normal", -40),
            ("pancreas unremarkable", -38),
            ("unremarkable pancreas", -38),
            ("no pancreatitis", -60),
            ("without pancreatitis", -55),
            ("normal lipase", -55),
            ("lipase normal", -55),
            ("lipase within normal", -55),
            ("lipase wnl", -50),
            ("no evidence of pancreatitis", -60),
            ("cholecystitis", -40),
            ("appendicitis", -40),
            ("diverticulitis", -40),
        ],
        "criteria": [
            "Epigastric pain radiating to back",
            "Lipase or amylase ≥3x upper limit of normal",
            "CT: pancreatic edema, peripancreatic fluid, necrosis",
            "Assess etiology: gallstones, alcohol, hypertriglyceridemia",
        ],
    },

    "diverticulitis": {
        "symptoms": [
            ("llq pain", 38),
            ("left lower quadrant pain", 38),
            ("llq", 34),
            ("left lower quadrant", 34),
            ("left lower", 28),
            ("left-sided pain", 28),
            ("left sided pain", 28),
            ("left-sided", 20),
            ("left sided", 20),
            ("change in bowel habits", 16),
            ("constipation", 14),
            ("diarrhea", 10),
            ("fever", 10),
        ],
        "exam_findings": [
            ("llq tenderness", 38),
            ("left lower quadrant tenderness", 38),
            ("palpable mass", 18),
            ("guarding", 2),
            ("rebound", 6),
        ],
        "labs": [
            ("leukocytosis", 5),
            ("elevated wbc", 5),
            ("elevated crp", 8),
        ],
        "imaging": [
            ("acute diverticulitis", 75),
            ("sigmoid diverticulitis", 75),
            ("diverticulitis", 70),
            ("pericolonic", 50),
            ("pericolic", 50),
            ("diverticular", 45),
            ("diverticula", 38),
            ("diverticulosis", 20),
            ("sigmoid colon", 26),
            ("sigmoid", 22),
            ("colonic wall thickening", 24),
            ("wall thickening", 6),
            ("fat stranding", 8),
            ("abscess", 20),
            ("microperforation", 32),
            ("free air", 12),
        ],
        "negative": [
            ("no diverticulitis", -60),
            ("without diverticulitis", -55),
            ("no evidence of diverticulitis", -60),
            ("appendicitis", -40),
            ("pancreatitis", -40),
            ("cholecystitis", -40),
        ],
        "criteria": [
            "LLQ pain with change in bowel habits",
            "LLQ tenderness, possible palpable mass",
            "Leukocytosis, elevated CRP",
            "CT: diverticula, wall thickening, pericolonic fat stranding",
        ],
    },

    "bowel_obstruction": {
        "symptoms": [
            ("obstipation", 42),
            ("no flatus", 36),
            ("inability to pass flatus", 36),
            ("not passing gas", 32),
            ("no bowel movement", 32),
            ("abdominal distension", 28),
            ("distension", 24),
            ("colicky pain", 20),
            ("crampy pain", 16),
            ("bilious vomiting", 24),
            ("vomiting", 4),
        ],
        "exam_findings": [
            ("distended abdomen", 28),
            ("tympanitic", 24),
            ("high-pitched bowel sounds", 24),
            ("hyperactive bowel sounds", 18),
            ("absent bowel sounds", 18),
            ("tinkling", 16),
            ("surgical scars", 14),
            ("prior surgery", 14),
        ],
        "labs": [
            ("elevated lactate", 22),
            ("lactic acidosis", 22),
            ("metabolic acidosis", 18),
            ("leukocytosis", 5),
            ("hypokalemia", 12),
        ],
        "imaging": [
            ("small bowel obstruction", 55),
            ("large bowel obstruction", 55),
            ("bowel obstruction", 50),
            ("sbo", 45),
            ("lbo", 45),
            ("dilated loops", 32),
            ("dilated bowel", 30),
            ("air-fluid levels", 32),
            ("air fluid levels", 32),
            ("transition point", 38),
            ("closed loop", 40),
            ("volvulus", 40),
            ("hernia", 16),
        ],
        "negative": [
            ("no obstruction", -50),
            ("no evidence of obstruction", -50),
            ("normal bowel gas pattern", -40),
            ("no sbo", -45),
            ("no lbo", -45),
            ("appendicitis", -40),
            ("pancreatitis", -40),
            ("cholecystitis", -40),
            ("diverticulitis", -40),
        ],
        "criteria": [
            "Obstipation, distension, vomiting, colicky pain",
            "Distended tympanitic abdomen, abnormal bowel sounds",
            "Lactate elevation suggests strangulation",
            "CT: dilated loops, transition point, air-fluid levels",
        ],
    },

    "gastroenteritis": {
        "symptoms": [
            ("diarrhea", 18),
            ("watery diarrhea", 26),
            ("non-bloody diarrhea", 24),
            ("loose stool", 20),
            ("vomiting", 10),
            ("nausea", 4),
            ("abdominal cramps", 10),
            ("crampy pain", 8),
            ("sick contacts", 20),
            ("food poisoning", 22),
            ("recent travel", 14),
            ("fever", 2),
        ],
        "exam_findings": [
            ("diffuse tenderness", 6),
            ("hyperactive bowel sounds", 10),
            ("no rebound", 14),
            ("no guarding", 12),
            ("no peritoneal signs", 14),
            ("dehydration", 12),
            ("dry mucous membranes", 10),
        ],
        "labs": [
            ("normal wbc", 8),
            ("fecal leukocytes", 12),
            ("stool culture", 10),
            ("c diff", 14),
        ],
        "imaging": [
            ("normal ct", 12),
            ("no acute findings", 14),
            ("unremarkable", 2),
        ],
        "negative": [
            ("no diarrhea", -24),
            ("no vomiting", -14),
            ("bloody diarrhea", -20),
            ("appendicitis", -40),
            ("pancreatitis", -40),
            ("cholecystitis", -40),
            ("diverticulitis", -40),
        ],
        "criteria": [
            "Acute watery diarrhea with vomiting",
            "Diffuse mild tenderness, hyperactive bowel sounds",
            "Usually self-limited; stool studies if prolonged",
            "Imaging rarely needed",
        ],
    },

    "nephrolithiasis": {
        "symptoms": [
            ("flank pain", 28),
            ("colicky flank pain", 35),
            ("renal colic", 32),
            ("radiating to groin", 24),
            ("groin pain", 18),
            ("hematuria", 24),
            ("kidney stone", 22),
            ("nephrolithiasis", 22),
        ],
        "exam_findings": [
            ("cva tenderness", 28),
            ("costovertebral angle tenderness", 28),
            ("flank tenderness", 22),
            ("writhing", 20),
            ("restless", 14),
        ],
        "labs": [
            ("hematuria", 30),
            ("microhematuria", 26),
            ("rbc in urine", 26),
            ("blood in urine", 26),
            ("crystals", 16),
        ],
        "imaging": [
            ("nephrolithiasis", 42),
            ("ureterolithiasis", 42),
            ("kidney stone", 18),
            ("ureteral stone", 18),
            ("renal calculus", 35),
            ("ureteral calculus", 15),
            ("hydronephrosis", 30),
            ("hydroureter", 30),
            ("stone", 10),
        ],
        "negative": [
            ("no nephrolithiasis", -45),
            ("no stone", -35),
            ("no calculus", -35),
            ("no hydronephrosis", -25),
            ("appendicitis", -40),
            ("pancreatitis", -40),
            ("cholecystitis", -40),
            ("diverticulitis", -40),
        ],
        "criteria": [
            "Sudden severe colicky flank pain radiating to groin",
            "CVA tenderness, restless patient",
            "Hematuria on urinalysis",
            "CT: stone, hydronephrosis",
        ],
    },

    "colitis": {
        "symptoms": [
            ("bloody diarrhea", 32),
            ("blood in stool", 28),
            ("hematochezia", 30),
            ("diarrhea", 8),
            ("tenesmus", 22),
            ("urgency", 16),
            ("abdominal cramps", 10),
            ("fever", 3),
        ],
        "exam_findings": [
            ("bloody stool", 26),
            ("lower abdominal tenderness", 14),
            ("llq tenderness", 6),
            ("diffuse tenderness", 6),
        ],
        "labs": [
            ("c diff", 30),
            ("c difficile", 30),
            ("clostridium difficile", 32),
            ("fecal leukocytes", 16),
            ("leukocytosis", 4),
            ("elevated crp", 6),
            ("anemia", 8),
        ],
        "imaging": [
            ("colitis", 40),
            ("pancolitis", 12),
            ("colonic wall thickening", 26),
            ("wall thickening", 6),
            ("pseudomembranes", 12),
            ("thumbprinting", 24),
        ],
        "negative": [
            ("no colitis", -45),
            ("normal colon", -35),
            ("normal colonoscopy", -40),
            ("appendicitis", -40),
            ("pancreatitis", -40),
            ("cholecystitis", -40),
            ("diverticulitis", -40),
        ],
        "criteria": [
            "Bloody diarrhea with urgency and tenesmus",
            "Lower abdominal tenderness",
            "C. diff testing, fecal leukocytes",
            "CT/colonoscopy: wall thickening, ulceration",
        ],
    },

    "peptic_ulcer_disease": {
        "symptoms": [
            ("epigastric pain", 10),
            ("burning pain", 10),
            ("gnawing pain", 10),
            ("relieved by food", 20),
            ("relieved by antacids", 20),
            ("hematemesis", 22),
            ("coffee ground emesis", 30),
            ("coffee ground", 28),
            ("melena", 32),
            ("black stool", 28),
            ("bloating", 6),
            ("dyspepsia", 14),
        ],
        "exam_findings": [
            ("epigastric tenderness", 10),
            ("rigid abdomen", 20),
            ("guarding", 4),
            ("peritonitis", 20),
        ],
        "labs": [
            ("h pylori", 28),
            ("h. pylori positive", 35),
            ("helicobacter", 28),
            ("anemia", 10),
            ("low hemoglobin", 10),
        ],
        "imaging": [
            ("peptic ulcer", 32),
            ("gastric ulcer", 32),
            ("duodenal ulcer", 32),
            ("ulcer", 12),
            ("free air", 6),
            ("pneumoperitoneum", 35),
            ("perforation", 28),
        ],
        "negative": [
            ("no ulcer", -45),
            ("normal endoscopy", -40),
            ("normal egd", -40),
            ("h pylori negative", -18),
            ("pancreatitis", -40),
            ("cholecystitis", -40),
            ("appendicitis", -40),
            ("diverticulitis", -40),
        ],
        "criteria": [
            "Burning/gnawing epigastric pain, relieved or worsened by food",
            "GI bleeding: hematemesis, melena",
            "H. pylori testing",
            "EGD diagnostic; CT if perforation suspected",
        ],
    },

    "mesenteric_ischemia": {
        "symptoms": [
            ("pain out of proportion", 52),
            ("severe abdominal pain", 16),
            ("sudden severe pain", 28),
            ("postprandial pain", 14),
            ("food fear", 18),
            ("weight loss", 10),
            ("bloody diarrhea", 8),
            ("diarrhea", 2),
        ],
        "exam_findings": [
            ("minimal tenderness", 26),
            ("benign abdominal exam", 24),
            ("soft abdomen", 16),
            ("pain out of proportion to exam", 50),
            ("peritoneal signs", 16),
            ("atrial fibrillation", 18),
            ("afib", 18),
        ],
        "labs": [
            ("elevated lactate", 38),
            ("lactic acidosis", 35),
            ("metabolic acidosis", 30),
            ("leukocytosis", 6),
            ("d-dimer", 14),
        ],
        "imaging": [
            ("mesenteric ischemia", 60),
            ("sma occlusion", 60),
            ("sma thrombus", 60),
            ("mesenteric thrombus", 56),
            ("mesenteric embolus", 56),
            ("bowel ischemia", 50),
            ("pneumatosis", 46),
            ("portal venous gas", 50),
            ("bowel wall enhancement", 24),
        ],
        "negative": [
            ("no ischemia", -52),
            ("mesenteric vessels patent", -48),
            ("normal cta", -42),
            ("appendicitis", -40),
            ("pancreatitis", -40),
            ("cholecystitis", -40),
            ("diverticulitis", -40),
        ],
        "criteria": [
            "Severe pain out of proportion to physical exam",
            "Risk factors: AFib, vascular disease",
            "Elevated lactate, metabolic acidosis",
            "CTA: vessel occlusion, pneumatosis, portal venous gas",
        ],
    },

    "abdominal_aortic_aneurysm": {
        "symptoms": [
            ("pulsatile mass", 46),
            ("abdominal pulsation", 42),
            ("back pain", 14),
            ("flank pain", 10),
            ("abdominal pain", 6),
            ("syncope", 24),
            ("hypotension", 28),
            ("shock", 26),
        ],
        "exam_findings": [
            ("pulsatile abdominal mass", 52),
            ("hypotension", 28),
            ("tachycardia", 8),
            ("periumbilical mass", 24),
        ],
        "labs": [
            ("anemia", 10),
            ("dropping hemoglobin", 22),
            ("elevated lactate", 10),
        ],
        "imaging": [
            ("abdominal aortic aneurysm", 60),
            ("aortic aneurysm", 55),
            ("aaa", 50),
            ("ruptured aaa", 65),
            ("retroperitoneal hematoma", 45),
            ("aortic rupture", 60),
            ("aneurysm", 30),
        ],
        "negative": [
            ("no aneurysm", -52),
            ("normal aorta", -46),
            ("aorta unremarkable", -42),
            ("appendicitis", -40),
            ("pancreatitis", -40),
            ("cholecystitis", -40),
            ("diverticulitis", -40),
        ],
        "criteria": [
            "Sudden abdominal/back pain with pulsatile mass",
            "Hypotension, tachycardia if ruptured",
            "Dropping hemoglobin",
            "CT: aneurysm, retroperitoneal hematoma",
        ],
    },
}


def _normalize_text(text: str) -> str:
    """Normalize text for matching."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text


def _score_match(query: str, condition: str) -> float:
    """Score how well query matches a condition's criteria."""
    query_normalized = _normalize_text(query)
    data = DIAGNOSIS_CRITERIA.get(condition, {})
    
    category_scores = {}
    
    for category in ["symptoms", "exam_findings", "labs", "imaging"]:
        keywords = data.get(category, [])
        cat_score = 0.0
        matched_positions = set()
        
        # Sort by keyword length (longest first) to prioritize specific matches
        sorted_keywords = sorted(
            keywords, 
            key=lambda x: len(x[0]) if isinstance(x, tuple) else len(x), 
            reverse=True
        )
        
        for item in sorted_keywords:
            if isinstance(item, tuple):
                keyword, weight = item
            else:
                keyword, weight = item, 1.0
            
            pattern = re.escape(keyword.lower())
            for match in re.finditer(pattern, query_normalized):
                # Check if this position was already matched by a longer keyword
                match_range = range(match.start(), match.end())
                if not any(pos in matched_positions for pos in match_range):
                    cat_score += weight
                    matched_positions.update(match_range)
                    break  # Only count each keyword once
        
        category_scores[category] = cat_score
    
    # Apply negative keywords
    negative_keywords = data.get("negative", [])
    negative_score = 0.0
    for item in negative_keywords:
        if isinstance(item, tuple):
            keyword, weight = item
        else:
            keyword, weight = item, -10
        pattern = re.escape(keyword.lower())
        if re.search(pattern, query_normalized):
            negative_score += weight
    
    # Base score is sum of all categories
    base_score = sum(category_scores.values()) + negative_score
    
    # Bonus for having strong matches in multiple categories (clinical coherence)
    categories_with_signal = sum(1 for s in category_scores.values() if s >= 15)
    if categories_with_signal >= 3:
        base_score *= 1.30
    elif categories_with_signal >= 2:
        base_score *= 1.15
    
    return max(0, base_score)


def _format_criteria(condition: str) -> str:
    """Format diagnostic criteria for display."""
    data = DIAGNOSIS_CRITERIA.get(condition, {})
    criteria = data.get("criteria", [])
    return "\n".join(f"  - {c}" for c in criteria)


@tool
def retrieve_diagnosis_criteria(clinical_findings: str) -> str:
    """Retrieve relevant diagnostic criteria based on clinical findings.

    Args:
        clinical_findings: Clinical findings to match.

    Returns:
        Matching diagnostic criteria.
    """
    scores = {cond: _score_match(clinical_findings, cond)
              for cond in DIAGNOSIS_CRITERIA}

    matches = [(c, s) for c, s in sorted(scores.items(), key=lambda x: -x[1]) if s > 0]

    if not matches:
        return "No specific criteria matched. Consider broader differential diagnosis."

    results = ["Based on the clinical findings, consider:\n"]
    for condition, score in matches[:3]:
        results.append(f"• Diagnostic criteria (relevance: {score:.1f}):\n{_format_criteria(condition)}\n")

    if len(matches) > 3:
        results.append(f"({len(matches) - 3} additional conditions may be relevant)")

    return "\n".join(results)
