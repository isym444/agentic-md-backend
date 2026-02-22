from pydantic import BaseModel, Field
from typing import List, Optional

# 1. Define the sub-components matching your DB tables
class HPC(BaseModel):
    complaint_details: str
    duration: Optional[str] = None

class PMH(BaseModel):
    condition_name: str
    diagnosis_date: Optional[str] = Field(None, description="YYYY-MM-DD or None")
    status: Optional[str] = Field(None, description="active, resolved, or well-controlled")

class FamilyHistory(BaseModel):
    family_member_relation: str
    condition_name: str

class SocialHistory(BaseModel):
    smoking_status: str
    alcohol_consumption: str
    living_conditions: str

class ExaminationFinding(BaseModel):
    body_system: str
    clinical_findings: str

class DrugHistoryItem(BaseModel):
    drug_name: str  
    times_per_day: Optional[int] = Field(None, description="Frequency of intake per day")

# 2. Define the Master Output Schema for the LLM
class StructuredClinicalNotes(BaseModel):
    hpc: HPC
    pmh: List[PMH] = []
    family_history: List[FamilyHistory] = []
    social_history: SocialHistory
    examination_findings: List[ExaminationFinding] = []
    drug_history: List[DrugHistoryItem] = Field(..., alias="dh") 

# 3. Define the API Request Body
class GenerateNotesRequest(BaseModel):
    consultation_id: int
    transcript: str