"""Medical knowledge retrieval tool with embedded diagnosis criteria."""

from langchain.tools import tool

# Diagnosis criteria gathered from multiple authoritative sources like: World Journal of Emergency Surgery Guidelines, American College of Gastroenterology,
# Infectious Diseases Society of America Clinical Practice, Guidelines of the World Society of Emergency Surgery.
# For more detailed information, check out out paper
DIAGNOSIS_CRITERIA = {
    "appendicitis": (
        "To diagnose appendicitis, consider: (1) Symptoms: periumbilical pain migrating to RLQ, "
        "fever, nausea/vomiting. (2) Physical exam: RLQ tenderness, positive rebound, peritonitis "
        "signs. (3) Labs: elevated WBC, elevated CRP. (4) Imaging: enlarged appendix, appendicolith."
    ),
    "cholecystitis": (
        "To diagnose cholecystitis, consider: (1) Symptoms: RUQ pain, fever, nausea. "
        "(2) Physical exam: RUQ tenderness, Murphy's sign, jaundice. (3) Labs: elevated WBC, "
        "elevated CRP, elevated ALT/AST, elevated bilirubin/GGT. (4) Imaging: gallstones, "
        "thickened gallbladder wall, pericholecystic fluid, distended gallbladder."
    ),
    "diverticulitis": (
        "To diagnose diverticulitis, consider: (1) Symptoms: LLQ pain, fever, nausea/vomiting. "
        "(2) Physical exam: LLQ tenderness, fever, peritonitis signs. (3) Labs: elevated WBC, "
        "elevated CRP. (4) Imaging: bowel wall thickening, diverticula, pericolic inflammation, "
        "abscess."
    ),
    "pancreatitis": (
        "To diagnose pancreatitis, consider: (1) Symptoms: epigastric pain, nausea/vomiting. "
        "(2) Physical exam: epigastric tenderness, fever, jaundice. (3) Labs: elevated "
        "amylase/lipase, elevated WBC/CRP; severity markers: hematocrit, BUN, triglycerides, "
        "calcium, Na/K. (4) Imaging: pancreatic inflammation, peripancreatic fluid collection."
    ),
    "bowel obstruction": (
        "To diagnose bowel obstruction, consider: (1) Symptoms: colicky abdominal pain, "
        "distension, nausea/vomiting, obstipation. (2) Physical exam: abdominal distension, "
        "diffuse tenderness, high-pitched bowel sounds, palpable mass. (3) Labs: electrolyte "
        "imbalances, leukocytosis, elevated lactate. (4) Imaging: dilated bowel loops, "
        "air-fluid levels, CT to locate obstruction."
    ),
    "gastroenteritis": (
        "To diagnose gastroenteritis, consider: (1) Symptoms: acute diarrhea, abdominal cramps, "
        "nausea/vomiting, low-grade fever. (2) Physical exam: mild diffuse tenderness, signs of "
        "dehydration. (3) Labs: usually unremarkable, stool studies if bloody or severe. "
        "(4) Imaging: typically not required, CT only to exclude other diagnoses."
    ),
    "nephrolithiasis": (
        "To diagnose nephrolithiasis, consider: (1) Symptoms: sudden severe flank pain radiating "
        "to groin, nausea/vomiting, hematuria. (2) Physical exam: CVA tenderness, restlessness, "
        "soft abdomen. (3) Labs: hematuria on urinalysis, check for pyuria/bacteriuria. "
        "(4) Imaging: non-contrast CT is gold standard, ultrasound for hydronephrosis."
    ),
    "colitis": (
        "To diagnose colitis, consider: (1) Symptoms: bloody diarrhea with mucus, lower abdominal "
        "cramps, urgency, tenesmus, fever. (2) Physical exam: abdominal tenderness over colon, "
        "dehydration signs. (3) Labs: elevated ESR/CRP, leukocytosis, stool culture, C. diff toxin. "
        "(4) Imaging: CT showing wall thickening, colonoscopy for definitive diagnosis."
    ),
    "peptic ulcer disease": (
        "To diagnose peptic ulcer disease, consider: (1) Symptoms: burning epigastric pain related "
        "to meals, bloating, nausea; alarm signs: hematemesis, melena. (2) Physical exam: epigastric "
        "tenderness, rigid abdomen if perforated. (3) Labs: H. pylori testing, CBC for anemia. "
        "(4) Imaging: upper endoscopy is gold standard, X-ray for free air if perforation suspected."
    ),
    "mesenteric ischemia": (
        "To diagnose mesenteric ischemia, consider: (1) Symptoms: sudden severe abdominal pain "
        "out of proportion to exam, nausea/vomiting. (2) Physical exam: initially benign, later "
        "peritoneal signs. (3) Labs: elevated WBC, metabolic acidosis, elevated lactate. "
        "(4) Imaging: CT angiography showing vessel occlusion, bowel ischemia changes."
    ),
    "abdominal aortic aneurysm": (
        "To diagnose AAA, consider: (1) Symptoms: often asymptomatic; if ruptured: sudden severe "
        "back/abdominal pain, syncope. (2) Physical exam: pulsatile abdominal mass, shock signs "
        "if ruptured. (3) Labs: dropping hemoglobin, type and crossmatch, lactate. "
        "(4) Imaging: bedside ultrasound for screening, CT angiography for definitive diagnosis."
    ),
}


@tool
def retrieve_diagnosis_criteria(pathology: str) -> str:
    """Retrieve diagnosis criteria for a specific condition.

    Args:
        pathology: The condition to look up. Supported conditions:
                   'pancreatitis', 'appendicitis', 'cholecystitis', 'diverticulitis',
                   'bowel obstruction', 'gastroenteritis', 'nephrolithiasis', 'colitis',
                   'peptic ulcer disease', 'mesenteric ischemia', 'abdominal aortic aneurysm'

    Returns:
        Diagnosis criteria for the specified condition
    """
    pathology_lower = pathology.lower().strip()

    if pathology_lower in DIAGNOSIS_CRITERIA:
        return f"Diagnosis criteria for {pathology}:\n{DIAGNOSIS_CRITERIA[pathology_lower]}"

    available = list(DIAGNOSIS_CRITERIA.keys())
    return f"No diagnosis criteria found for '{pathology}'. Available: {', '.join(available)}"
