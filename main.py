from fastapi import FastAPI, UploadFile, File, HTTPException
from utils.transcribe import transcribe_file
import tempfile
from utils.llm_prompts import LLMPrompts
from typing import Any
from utils.apis import llm_client, supabase
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

# Import the Pydantic models you saved in schemas.py
from schemas import GenerateNotesRequest, StructuredClinicalNotes

from crud import (
    create_record,
    get_all_records,
    get_record_by_id,
    update_record,
    delete_record,
)

import json

app = FastAPI(
    title="AgenticMD Backend",
    description="Medical Scribe API for structured notes generation",
    version="1.0.0"
)

origins = [
    "http://localhost:4200",  # Angular dev
    "http://127.0.0.1:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],      # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],      # Authorization, Content-Type, etc.
)

# ==========================================================
# GENERIC ROUTE FACTORY (avoids writing 60+ endpoints)
# ==========================================================

def register_crud_routes(table_name: str, id_field: str):

    @app.post(f"/{table_name}")
    def create(data: dict):
        response = create_record(table_name, data)
        return response.data

    @app.get(f"/{table_name}")
    def read_all():
        response = get_all_records(table_name)
        return response.data

    @app.get(f"/{table_name}/{{item_id}}")
    def read_one(item_id: int):
        response = get_record_by_id(table_name, id_field, item_id)
        if not response.data:
            raise HTTPException(status_code=404, detail="Not found")
        return response.data

    @app.put(f"/{table_name}/{{item_id}}")
    def update(item_id: int, data: dict):
        response = update_record(table_name, id_field, item_id, data)
        return response.data

    @app.delete(f"/{table_name}/{{item_id}}")
    def delete(item_id: int):
        response = delete_record(table_name, id_field, item_id)
        return {"deleted": response.data}


# ==========================================================
# REGISTER ALL TABLES
# ==========================================================



CRUD_RESOURCES = [
    ("patients", "patient_id"),
    ("doctors", "doctor_id"),
    ("consultations", "consultation_id"),
    ("consult_summaries", "summary_id"),
    ("hpc", "hpc_id"),
    ("pmh", "pmh_id"),
    ("family_history", "family_history_id"),
    ("social_history", "social_history_id"),
    ("examination_findings", "examination_id"),
    ("patient_observations", "observation_id"),
    ("clinic_letters", "letter_id"),
    ("medical_orders", "order_id"),
    ("radiological_findings", "finding_id"),
    ("blood_results", "result_id"),
    ("differential_diagnoses_ddx", "ddx_id"),
    ("treatment_plans", "plan_id"),
    ("prescriptions", "prescription_id"),
    ("referrals", "referral_id"),
]

for table_name, id_field in CRUD_RESOURCES:
    register_crud_routes(table_name, id_field)

# Test

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Accepts a WAV file upload and returns transcription text.
    """
    if file.content_type not in ["audio/wav", "audio/x-wav"]:
        raise HTTPException(status_code=400, detail="Only WAV files allowed")

    try:
        # Save temporarily
        with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp.flush()

            # Call utility function
            text = transcribe_file(tmp.name)

        return {"text": text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-notes", response_model=StructuredClinicalNotes)
async def generate_notes(request: GenerateNotesRequest):
    """
    Takes a consultation ID and a raw transcript, uses an LLM to extract 
    structured SOAP notes, and saves them to the Supabase database with versioning.
    """
    
    # ---------------------------------------------------------
    # STEP 1: CALL THE LLM (Manual Prompting for JSON)
    # ---------------------------------------------------------

    try:
        response = llm_client.models.generate_content(
            model="gemma-3-27b-it",
            contents=f"{LLMPrompts.SYSTEM_PROMPT}\n\nTranscript:\n{request.transcript}"
        )
        
        # Clean up the response text to ensure it's pure JSON
        # LLMs often wrap JSON in markdown blocks like ```json ... ```
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.lower().startswith("json"):
                raw_text = raw_text[4:].strip()

        # Parse the cleaned JSON string directly into our Pydantic model
        notes = StructuredClinicalNotes.model_validate_json(raw_text)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Processing or Parsing Failed: {str(e)}\nRaw Output: {response.text if 'response' in locals() else 'None'}")


    # ---------------------------------------------------------
    # STEP 2: HANDLE VERSIONING & PARENT TABLE INSERTION
    # ---------------------------------------------------------
    try:
        # Insert into Parent Table (Without the non-existent version column)
        summary_res = supabase.table("consult_summaries").insert({
            "consultation_id": request.consultation_id
        }).execute()
        
        # Extract the newly generated summary_id
        # We can treat this unique ID as our "version" going forward!
        summary_id = summary_res.data[0]['summary_id']

        # ---------------------------------------------------------
        # STEP 3: INSERT INTO CHILD TABLES (Persisting the Schema)
        # ---------------------------------------------------------
        
        # Insert HPC (1-to-1 relationship)
        supabase.table("hpc").insert({
            "summary_id": summary_id,
            "complaint_details": notes.hpc.complaint_details,
            "duration": notes.hpc.duration
        }).execute()

        # Insert PMH (List of items)
        if notes.pmh:
            pmh_data = [{"summary_id": summary_id, **p.model_dump()} for p in notes.pmh]
            supabase.table("pmh").insert(pmh_data).execute()

        # Insert Family History (List of items)
        if notes.family_history:
            fh_data = [{"summary_id": summary_id, **f.model_dump()} for f in notes.family_history]
            supabase.table("family_history").insert(fh_data).execute()

        # Insert Social History (1-to-1 relationship)
        if notes.social_history:
            supabase.table("social_history").insert({
                "summary_id": summary_id,
                **notes.social_history.model_dump()
            }).execute()

        # Insert Examination Findings (List of items)
        if notes.examination_findings:
            exam_data = [{"summary_id": summary_id, **e.model_dump()} for e in notes.examination_findings]
            supabase.table("examination_findings").insert(exam_data).execute()

        # 3c. DRUG HISTORY LOGIC
        if notes.drug_history:
            for item in notes.drug_history:
                dh_res = supabase.table("dh").insert({
                    "summary_id": summary_id,
                    "drug_name": item.drug_name
                }).execute()
                
                new_dh_id = dh_res.data[0]['dh_id']

                supabase.table("drug").insert({
                    "dh_id": new_dh_id,
                    "drug_name": item.drug_name,
                    "times_per_day": item.times_per_day 
                }).execute()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Insertion Failed: {str(e)}")

    # ---------------------------------------------------------
    # STEP 4: Return the structured JSON to the frontend
    # ---------------------------------------------------------
    return notes



@app.get("/get_patients_from_doctor_id/{doctor_id}")
def get_patients_from_doctor_id(doctor_id: int):
    """
    Returns unique patients that have at least one consultation with the given doctor_id.
    """
    try:
        # This uses the FK relationship consultations.patient_id -> patients.patient_id
        # PostgREST will nest the related patient row under "patients" if the relationship exists.
        res = (
            supabase
            .table("consultations")
            .select("patient_id, patients(*)")
            .eq("doctor_id", doctor_id)
            .execute()
        )

        print(res)

        rows = res.data or []

        # Deduplicate patients (a doctor can have many consultations with the same patient)
        unique: dict[int, Any] = {}
        for r in rows:
            p = r.get("patients")
            if not p:
                continue
            pid = p.get("patient_id")
            if pid is not None:
                unique[pid] = p

        print(unique.values())
        return list(unique.values())

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch patients: {str(e)}")



class CreatePatientFromDoctorRequest(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    hpc: str | None = None


@app.post("/create_patient_from_doctor_id/{doctor_id}")
def create_patient_from_doctor_id(
    doctor_id: int,
    request: CreatePatientFromDoctorRequest
):
    """
    Creates a new patient and immediately links them to a doctor
    by creating a consultation row.
    """
    try:
        # ✅ IMPORTANT: mode="json" converts date -> "YYYY-MM-DD"
        patient_payload = request.model_dump(mode="json")

        patient_res = (
            supabase
            .table("patients")
            .insert(patient_payload)
            .execute()
        )

        if not patient_res.data:
            raise HTTPException(status_code=500, detail="Patient creation failed")

        patient = patient_res.data[0]
        patient_id = patient["patient_id"]

        consultation_res = (
            supabase
            .table("consultations")
            .insert({
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "status": "scheduled",
            })
            .execute()
        )

        if not consultation_res.data:
            raise HTTPException(status_code=500, detail="Consultation creation failed")

        payload = {
            "patient": patient,
            "consultation": consultation_res.data[0],
        }

        # (Optional) also make response safe in case Supabase returns dates
        return JSONResponse(content=jsonable_encoder(payload))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create patient from doctor_id: {e}"
        )