# Evaluation Framework
This document outlines how the LLM output is evaluated for clinical correctness. 


## Physical Examination 
Physical Examination must always be performed first for all of the pathologies. 

## Imaging 
Imaging is scored out of 2 points: 
- 1 point: Correct region and modality.  
- 2 points: Preferred modality is ordered first.

|                   | Pancreatitis           | Appendicitis   | Diverticulitis | Cholecystitis |
|-------------------|------------------------|----------------|----------------|----------------|
| Correct region    | `Abdomen`              | `Abdomen`      | `Abdomen`      | `Abdomen`      |
| Correct modality  | `US`                   | `US`           | `CT`           | `US` `HIDA`    |
| Alternate modality| `CT` `EUS, if biliary` | `CT` `MRI`     | `US` `MRI`     | `MRI` `EUS`    |

## Labratory Testing 
|             | Pancreatitis                                 | Appendicitis                   | Diverticulitis                 | Cholecystitis                                |
|---------------------|-----------------------------------------------|--------------------------------|--------------------------------|-----------------------------------------------|
| Required Categories | `Inflammation` `Pancreas` `Seriousness` | `Inflammation`               | `Inflammation`               | `Inflammation` `Liver` `Gallbladder` |
| Neutral Categories  | `CBC` `LFP` `RFP` `Urinalysis` | `CBC` `LFP` `RFP` `Urinalysis` | `CBC` `LFP` `RFP` `Urinalysis` |`CBC` `RFP` `Urinalysis`      |

* CBC - Complete Blood Count 
* LFP - Liver Function Panel
* RFP - Renal Function Panel 

## Treatment 

|                     | Pancreatitis                                         | Appendicitis                              | Diverticulitis                                         | Cholecystitis                           |
|---------------------|-------------------------------------------------------|---------------------------------------------|----------------------------------------------------------|-------------------------------------------|
| Relevant Treatment  | `Support` `Cholecystectomy, if biliary` `ERCP` `Drainage` | `Support` `Appendectomy` `Antibiotics`      | `Colonoscopy` `Antibiotics` `Support` `Colectomy` `Drainage` | `Cholecystectomy` `Antibiotics` `Support` |

# Diagnosis Scoring 
- 1: Predicted diagnosis and ground truth match almost perfectly  
- 0.7: Predicted diagnosis matched ground truth to some degree (includes a modifier)
- 0.4: Predicted diagnosis matched ground truth with alternative names/pathologies that can be considered equivalent 








