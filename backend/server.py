from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone

# Import custom modules
from data_loader import extract_text_from_pdf, clean_text, save_case, load_case, update_case
from case_processor import CaseProcessor
from classifier import BaselineClassifier
from orchestrator import DebateOrchestrator
from auditor import BiasAuditor

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Legal Multi-Agent Courtroom Simulator")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize components
case_processor = CaseProcessor()
classifier = BaselineClassifier()
orchestrator = DebateOrchestrator()
auditor = BiasAuditor()


# Define Models
class CaseUploadResponse(BaseModel):
    case_id: str
    raw_text: str
    message: str


class CaseProcessResponse(BaseModel):
    case_id: str
    facts: str
    issues: str
    holding: str


class ClassifierResponse(BaseModel):
    case_id: str
    prediction: str
    confidence: float
    method: str


class SimulationResponse(BaseModel):
    case_id: str
    debate_transcript: List[Dict[str, Any]]
    verdict: Dict[str, Any]
    rounds_completed: int


class AuditResponse(BaseModel):
    case_id: str
    audit_result: Dict[str, Any]


# Routes
@api_router.get("/")
async def root():
    return {"message": "Legal Multi-Agent Courtroom Simulator API"}


@api_router.post("/upload", response_model=CaseUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload PDF or text document and extract raw text."""
    try:
        content = await file.read()
        
        # Extract text based on file type
        if file.filename.endswith('.pdf'):
            raw_text = extract_text_from_pdf(content)
        elif file.filename.endswith('.txt'):
            raw_text = content.decode('utf-8')
        else:
            raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")
        
        # Clean text
        cleaned_text = clean_text(raw_text)
        
        # Save case
        case_data = {
            'filename': file.filename,
            'raw_text': cleaned_text,
            'upload_timestamp': datetime.now(timezone.utc).isoformat()
        }
        case_id = save_case(case_data)
        
        return CaseUploadResponse(
            case_id=case_id,
            raw_text=cleaned_text[:1000] + "..." if len(cleaned_text) > 1000 else cleaned_text,
            message="Document uploaded successfully"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@api_router.post("/process-case/{case_id}", response_model=CaseProcessResponse)
async def process_case(case_id: str):
    """Extract facts, issues, and holding from case document."""
    try:
        case_data = load_case(case_id)
        raw_text = case_data.get('raw_text', '')
        
        # Extract case details using LLM
        extracted = await case_processor.extract_case_details(raw_text)
        
        # Update case with extracted details
        update_case(case_id, extracted)
        
        return CaseProcessResponse(
            case_id=case_id,
            facts=extracted['facts'],
            issues=extracted['issues'],
            holding=extracted['holding']
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing case: {str(e)}")


@api_router.post("/predict/{case_id}", response_model=ClassifierResponse)
async def predict_outcome(case_id: str):
    """Predict case outcome using baseline classifier."""
    try:
        case_data = load_case(case_id)
        
        # Run baseline classifier
        prediction = classifier.predict(case_data)
        
        # Update case with prediction
        update_case(case_id, {'baseline_prediction': prediction})
        
        return ClassifierResponse(
            case_id=case_id,
            prediction=prediction['prediction'],
            confidence=prediction['confidence'],
            method=prediction['method']
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting outcome: {str(e)}")


@api_router.post("/simulate/{case_id}", response_model=SimulationResponse)
async def run_simulation(case_id: str, rounds: int = 2):
    """Run multi-agent debate simulation."""
    try:
        case_data = load_case(case_id)
        
        # Ensure case has been processed
        if 'facts' not in case_data:
            raise HTTPException(status_code=400, detail="Case must be processed before simulation")
        
        # Run simulation
        simulation_result = await orchestrator.run_simulation(case_data, rounds)
        
        # Update case with simulation results
        update_case(case_id, {'simulation': simulation_result})
        
        return SimulationResponse(
            case_id=case_id,
            debate_transcript=simulation_result['debate_transcript'],
            verdict=simulation_result['verdict'],
            rounds_completed=simulation_result['rounds_completed']
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running simulation: {str(e)}")


@api_router.post("/audit/{case_id}", response_model=AuditResponse)
async def audit_case(case_id: str):
    """Perform bias audit on case and verdict."""
    try:
        case_data = load_case(case_id)
        
        # Ensure simulation has been run
        if 'simulation' not in case_data:
            raise HTTPException(status_code=400, detail="Simulation must be run before audit")
        
        verdict = case_data['simulation']['verdict']
        
        # Run audit
        audit_result = await auditor.audit(case_data, verdict)
        
        # Update case with audit results
        update_case(case_id, {'audit': audit_result})
        
        return AuditResponse(
            case_id=case_id,
            audit_result=audit_result
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error auditing case: {str(e)}")


@api_router.get("/case/{case_id}")
async def get_case(case_id: str):
    """Get complete case details."""
    try:
        case_data = load_case(case_id)
        return JSONResponse(content=case_data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving case: {str(e)}")


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
